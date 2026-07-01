import unittest
from datetime import date, datetime, time

from flask import Flask

from creditos_logic import cancelar_clase_por_admin, cancelar_reserva_con_creditos, cancelar_turno_por_admin
from routes.turnos import generar_clases_para_turno, reactivar_turno_cancelado
from models import (
    Abono,
    Actividad,
    Asistencia,
    Clase,
    Credito,
    ListaEspera,
    MovimientoFinanciero,
    Reserva,
    Turno,
    Usuario,
    db,
)


class CancelacionClaseAdminTestCase(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            SECRET_KEY='test-secret'
        )
        db.init_app(self.app)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        self.admin = Usuario(
            nombre='Ada', apellido='Admin', dni='1',
            email='admin@test.com', password_hash='x', rol='administrador'
        )
        self.cliente = Usuario(
            nombre='Ciro', apellido='Cliente', dni='2',
            email='cliente@test.com', password_hash='x', rol='cliente'
        )
        self.actividad = Actividad(nombre='Padel', precio_clase=1000)
        db.session.add_all([self.admin, self.cliente, self.actividad])
        db.session.flush()

        self.clase = Clase(
            actividad_id=self.actividad.id,
            fecha=date(2026, 7, 10),
            hora_inicio=time(18, 0),
            cupo_maximo=10,
            precio_clase=1000
        )
        db.session.add(self.clase)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def reserva_suelta(self, pagado):
        reserva = Reserva(
            usuario_id=self.cliente.id,
            clase_id=self.clase.id,
            tipo='no_abonado',
            estado='activa',
            mes=7,
            anio=2026,
            monto_total=1000,
            monto_pagado=pagado,
            senia_pagada=pagado >= 500
        )
        db.session.add(reserva)
        db.session.commit()
        return reserva

    def reserva_abonada(self, abono_pagado):
        abono = Abono(
            usuario_id=self.cliente.id,
            actividad_id=self.actividad.id,
            mes=7,
            anio=2026,
            monto_total=4000,
            monto_pagado=4000 if abono_pagado else 1000
        )
        db.session.add(abono)
        db.session.flush()
        reserva = Reserva(
            usuario_id=self.cliente.id,
            clase_id=self.clase.id,
            abono_id=abono.id,
            tipo='abonado',
            estado='activa',
            mes=7,
            anio=2026,
            monto_total=1000,
            monto_pagado=1000 if abono_pagado else 0,
            senia_pagada=True
        )
        db.session.add(reserva)
        db.session.commit()
        return reserva, abono

    def test_devuelve_senia_de_clase_suelta(self):
        reserva = self.reserva_suelta(500)

        resultado = cancelar_clase_por_admin(self.clase.id, self.admin.id)
        db.session.commit()

        self.assertTrue(self.clase.cancelada)
        self.assertEqual(reserva.estado, 'cancelada')
        self.assertEqual(resultado['devolucion_senia'], 500)
        movimiento = MovimientoFinanciero.query.one()
        self.assertEqual(movimiento.tipo, 'devolucion_senia')
        self.assertEqual(float(movimiento.monto), 500)

    def test_devuelve_credito_usado_en_clase_suelta_cancelada_por_admin(self):
        reserva = self.reserva_suelta(1000)
        credito = Credito(
            usuario_id=self.cliente.id,
            actividad_id=self.actividad.id,
            monto=1000,
            monto_restante=0,
            origen='abono_cancelacion',
            reserva_origen_id=None,
            reserva_uso_id=reserva.id,
            estado='usado',
            fecha_uso=datetime(2026, 7, 1, 10, 0)
        )
        db.session.add(credito)
        db.session.commit()

        resultado = cancelar_clase_por_admin(self.clase.id, self.admin.id)
        db.session.commit()

        self.assertEqual(reserva.estado, 'cancelada')
        self.assertEqual(credito.estado, 'disponible')
        self.assertIsNone(credito.reserva_uso_id)
        self.assertIsNone(credito.fecha_uso)
        self.assertEqual(float(credito.monto_restante), 1000)
        self.assertEqual(resultado['creditos_devueltos'], 1000)
        self.assertEqual(resultado['devolucion_senia'], 0)
        movimiento = MovimientoFinanciero.query.one()
        self.assertEqual(movimiento.tipo, 'credito_devuelto_cancelacion_clase')
        self.assertEqual(float(movimiento.monto), 1000)

    def test_descuenta_abono_pendiente_sin_generar_credito(self):
        reserva, abono = self.reserva_abonada(abono_pagado=False)

        resultado = cancelar_clase_por_admin(self.clase.id, self.admin.id)
        db.session.commit()

        self.assertEqual(reserva.estado, 'cancelada')
        self.assertEqual(float(abono.monto_total), 3000)
        self.assertEqual(resultado['descuento_abonos'], 1000)
        self.assertEqual(Credito.query.count(), 0)
        self.assertEqual(MovimientoFinanciero.query.one().tipo, 'descuento_abono_pendiente')

    def test_genera_credito_para_abono_pagado(self):
        reserva, abono = self.reserva_abonada(abono_pagado=True)

        resultado = cancelar_clase_por_admin(self.clase.id, self.admin.id)
        db.session.commit()

        credito = Credito.query.one()
        self.assertEqual(reserva.estado, 'cancelada')
        self.assertEqual(float(abono.monto_total), 4000)
        self.assertEqual(float(credito.monto_restante), 1000)
        self.assertEqual(credito.actividad_id, self.actividad.id)
        self.assertEqual(credito.motivo, 'Cancelacion de clase por admin')
        self.assertEqual(resultado['creditos_generados'], 1000)
        self.assertEqual(MovimientoFinanciero.query.one().tipo, 'credito_abono_pagado')

    def test_no_cancela_dos_veces(self):
        self.reserva_suelta(500)
        cancelar_clase_por_admin(self.clase.id, self.admin.id)
        db.session.commit()

        with self.assertRaises(ValueError):
            cancelar_clase_por_admin(self.clase.id, self.admin.id)

    def test_cancelar_clase_quita_lista_espera_pendiente(self):
        espera = ListaEspera(
            usuario_id=self.cliente.id,
            clase_id=self.clase.id,
            tipo_preferencia='no_abonado',
            estado='esperando',
            mes=7,
            anio=2026
        )
        db.session.add(espera)
        db.session.commit()

        resultado = cancelar_clase_por_admin(self.clase.id, self.admin.id)
        db.session.commit()

        self.assertEqual(resultado['lista_espera_cancelada'], 1)
        self.assertEqual(espera.estado, 'rechazado')

    def test_no_cancela_clase_que_ya_paso(self):
        reserva = self.reserva_suelta(500)

        with self.assertRaises(ValueError):
            cancelar_clase_por_admin(
                self.clase.id,
                self.admin.id,
                ahora=datetime(2026, 7, 10, 18, 1)
            )

        self.assertFalse(self.clase.cancelada)
        self.assertEqual(reserva.estado, 'activa')
        self.assertEqual(MovimientoFinanciero.query.count(), 0)

    def test_no_cancela_reserva_con_asistencia_registrada(self):
        reserva = self.reserva_suelta(1000)
        db.session.add(Asistencia(
            reserva_id=reserva.id,
            fecha=date(2026, 7, 10),
            presente=True,
            registrado_por=self.admin.id
        ))
        db.session.commit()

        with self.assertRaises(ValueError):
            cancelar_reserva_con_creditos(reserva)

        self.assertEqual(reserva.estado, 'activa')

    def test_cancelar_clase_no_cancela_reserva_asistida(self):
        reserva = self.reserva_suelta(1000)
        db.session.add(Asistencia(
            reserva_id=reserva.id,
            fecha=date(2026, 7, 10),
            presente=True,
            registrado_por=self.admin.id
        ))
        db.session.commit()

        resultado = cancelar_clase_por_admin(
            self.clase.id,
            self.admin.id,
            ahora=datetime(2026, 7, 10, 17, 0)
        )
        db.session.commit()

        self.assertTrue(self.clase.cancelada)
        self.assertEqual(reserva.estado, 'activa')
        self.assertEqual(resultado['reservas_canceladas'], 0)
        self.assertEqual(resultado['reservas_asistidas_omitidas'], 1)

    def crear_turno_con_clases(self):
        turno = Turno(
            actividad_id=self.actividad.id,
            dia_semana=4,
            hora_inicio=time(18, 0),
            cupo_maximo=10,
            precio_clase=1000
        )
        db.session.add(turno)
        db.session.flush()
        clase_1 = Clase(
            actividad_id=self.actividad.id,
            turno_id=turno.id,
            fecha=date(2026, 7, 17),
            hora_inicio=time(18, 0),
            cupo_maximo=10,
            precio_clase=1000
        )
        clase_2 = Clase(
            actividad_id=self.actividad.id,
            turno_id=turno.id,
            fecha=date(2026, 7, 24),
            hora_inicio=time(18, 0),
            cupo_maximo=10,
            precio_clase=1000
        )
        db.session.add_all([clase_1, clase_2])
        db.session.commit()
        return turno, clase_1, clase_2

    def test_cancelar_turno_cancela_clases_futuras_y_acumula_movimientos(self):
        turno, clase_suelta, clase_abono = self.crear_turno_con_clases()
        reserva_suelta = Reserva(
            usuario_id=self.cliente.id,
            clase_id=clase_suelta.id,
            tipo='no_abonado',
            estado='activa',
            mes=7,
            anio=2026,
            monto_total=1000,
            monto_pagado=500,
            senia_pagada=True
        )
        abono = Abono(
            usuario_id=self.cliente.id,
            actividad_id=self.actividad.id,
            mes=7,
            anio=2026,
            monto_total=4000,
            monto_pagado=4000
        )
        db.session.add_all([reserva_suelta, abono])
        db.session.flush()
        reserva_abono = Reserva(
            usuario_id=self.cliente.id,
            clase_id=clase_abono.id,
            abono_id=abono.id,
            tipo='abonado',
            estado='activa',
            mes=7,
            anio=2026,
            monto_total=1000,
            monto_pagado=1000,
            senia_pagada=True
        )
        db.session.add(reserva_abono)
        db.session.commit()

        resultado = cancelar_turno_por_admin(turno.id, self.admin.id, desde=date(2026, 7, 1))
        db.session.commit()

        self.assertFalse(turno.activo)
        self.assertTrue(clase_suelta.cancelada)
        self.assertTrue(clase_abono.cancelada)
        self.assertEqual(turno.to_dict()['total_clases'], 0)
        self.assertEqual(reserva_suelta.estado, 'cancelada')
        self.assertEqual(reserva_abono.estado, 'cancelada')
        self.assertEqual(resultado['clases_canceladas'], 2)
        self.assertEqual(resultado['reservas_canceladas'], 2)
        self.assertEqual(resultado['devolucion_senia'], 500)
        self.assertEqual(resultado['creditos_generados'], 1000)
        self.assertEqual(MovimientoFinanciero.query.count(), 2)

    def test_cancelar_turno_no_cancela_clases_que_ya_pasaron(self):
        turno, clase_pasada, clase_futura = self.crear_turno_con_clases()
        reserva_pasada = Reserva(
            usuario_id=self.cliente.id,
            clase_id=clase_pasada.id,
            tipo='no_abonado',
            estado='activa',
            mes=7,
            anio=2026,
            monto_total=1000,
            monto_pagado=500,
            senia_pagada=True
        )
        reserva_futura = Reserva(
            usuario_id=self.cliente.id,
            clase_id=clase_futura.id,
            tipo='no_abonado',
            estado='activa',
            mes=7,
            anio=2026,
            monto_total=1000,
            monto_pagado=500,
            senia_pagada=True
        )
        db.session.add_all([reserva_pasada, reserva_futura])
        db.session.commit()

        resultado = cancelar_turno_por_admin(
            turno.id,
            self.admin.id,
            desde=date(2026, 7, 1),
            ahora=datetime(2026, 7, 20, 12, 0)
        )
        db.session.commit()

        self.assertFalse(clase_pasada.cancelada)
        self.assertTrue(clase_futura.cancelada)
        self.assertEqual(reserva_pasada.estado, 'activa')
        self.assertEqual(reserva_futura.estado, 'cancelada')
        self.assertEqual(resultado['clases_canceladas'], 1)
        self.assertEqual(resultado['clases_pasadas_omitidas'], 1)

    def test_no_cancela_turno_dos_veces(self):
        turno, _, _ = self.crear_turno_con_clases()
        cancelar_turno_por_admin(turno.id, self.admin.id, desde=date(2026, 7, 1))
        db.session.commit()

        with self.assertRaises(ValueError):
            cancelar_turno_por_admin(turno.id, self.admin.id, desde=date(2026, 7, 1))

    def test_reactivar_turno_genera_clase_nueva_si_la_anterior_estaba_cancelada(self):
        turno, clase_cancelada, _ = self.crear_turno_con_clases()
        cancelar_turno_por_admin(turno.id, self.admin.id, desde=date(2026, 7, 17))
        db.session.commit()

        turno.activo = True
        turno.cancelado_fecha = None
        turno.cancelado_por = None
        turno.motivo_cancelacion = None
        generadas, existentes = generar_clases_para_turno(
            turno,
            desde=date(2026, 7, 17),
            hasta=date(2026, 7, 17)
        )

        clases_fecha = Clase.query.filter_by(turno_id=turno.id, fecha=date(2026, 7, 17)).all()
        nuevas_vigentes = [c for c in clases_fecha if c.activa and not c.cancelada]

        self.assertEqual(generadas, 1)
        self.assertEqual(existentes, 0)
        self.assertTrue(clase_cancelada.cancelada)
        self.assertEqual(len(clases_fecha), 2)
        self.assertEqual(len(nuevas_vigentes), 1)

    def test_reactivar_turno_no_reusa_inscripciones_ni_lista_espera_viejas(self):
        turno, clase_cancelada, _ = self.crear_turno_con_clases()
        reserva = Reserva(
            usuario_id=self.cliente.id,
            clase_id=clase_cancelada.id,
            tipo='no_abonado',
            estado='activa',
            mes=7,
            anio=2026,
            monto_total=1000,
            monto_pagado=500,
            senia_pagada=True
        )
        espera = ListaEspera(
            usuario_id=self.cliente.id,
            clase_id=clase_cancelada.id,
            tipo_preferencia='no_abonado',
            estado='esperando',
            mes=7,
            anio=2026
        )
        db.session.add_all([reserva, espera])
        db.session.commit()

        cancelar_turno_por_admin(turno.id, self.admin.id, desde=date(2026, 7, 17))
        db.session.commit()

        resultado = reactivar_turno_cancelado(
            turno,
            desde=date(2026, 7, 17),
            hasta=date(2026, 7, 17)
        )

        clases_fecha = Clase.query.filter_by(turno_id=turno.id, fecha=date(2026, 7, 17)).all()
        clase_nueva = next(c for c in clases_fecha if c.activa and not c.cancelada)

        self.assertTrue(turno.activo)
        self.assertEqual(resultado['clases_generadas'], 1)
        self.assertEqual(reserva.clase_id, clase_cancelada.id)
        self.assertEqual(espera.clase_id, clase_cancelada.id)
        self.assertEqual(Reserva.query.filter_by(clase_id=clase_nueva.id).count(), 0)
        self.assertEqual(ListaEspera.query.filter_by(clase_id=clase_nueva.id).count(), 0)


if __name__ == '__main__':
    unittest.main()
