import unittest
from datetime import date, datetime, time
from unittest.mock import patch

from flask import Flask

from asistencia_logic import AsistenciaRechazada, registrar_asistencia_qr
from models import (
    Abono,
    Actividad,
    Asistencia,
    Clase,
    Reserva,
    Suspension,
    Turno,
    Usuario,
    db,
)
from qr_asistencia import contenido_qr_asistencia


class AsistenciaQrTestCase(unittest.TestCase):
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

        self.empleado = Usuario(
            nombre='Eva', apellido='Empleado', dni='1',
            email='empleado@test.com', password_hash='x', rol='empleado'
        )
        self.cliente = Usuario(
            nombre='Ciro', apellido='Cliente', dni='2',
            email='cliente@test.com', password_hash='x', rol='cliente'
        )
        self.actividad = Actividad(nombre='Pádel', precio_clase=1000)
        db.session.add_all([self.empleado, self.cliente, self.actividad])
        db.session.flush()

        self.turno = Turno(
            actividad_id=self.actividad.id,
            dia_semana=0,
            hora_inicio=time(18, 0),
            cupo_maximo=10,
            precio_clase=1000
        )
        db.session.add(self.turno)
        db.session.flush()
        self.clase = Clase(
            actividad_id=self.actividad.id,
            turno_id=self.turno.id,
            fecha=date(2026, 6, 22),
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

    def crear_reserva_suelta(self, pagado):
        reserva = Reserva(
            usuario_id=self.cliente.id,
            clase_id=self.clase.id,
            tipo='no_abonado',
            estado='activa',
            mes=6,
            anio=2026,
            monto_total=1000,
            monto_pagado=pagado,
            senia_pagada=pagado >= 500
        )
        db.session.add(reserva)
        db.session.commit()
        return reserva

    def crear_reserva_abono(self, pagado):
        abono = Abono(
            usuario_id=self.cliente.id,
            actividad_id=self.actividad.id,
            mes=6,
            anio=2026,
            monto_total=4000,
            monto_pagado=pagado
        )
        db.session.add(abono)
        db.session.flush()
        reserva = Reserva(
            usuario_id=self.cliente.id,
            clase_id=self.clase.id,
            abono_id=abono.id,
            tipo='abonado',
            estado='activa',
            mes=6,
            anio=2026,
            monto_total=1000,
            monto_pagado=1000 if pagado >= 4000 else 0,
            senia_pagada=True
        )
        db.session.add(reserva)
        db.session.commit()
        return reserva

    def assert_rechazo(self, reserva, codigo, hoy=date(2026, 6, 22)):
        with self.assertRaises(AsistenciaRechazada) as contexto:
            registrar_asistencia_qr(
                contenido_qr_asistencia(reserva),
                self.empleado.id,
                hoy=hoy
            )
        self.assertEqual(contexto.exception.codigo, codigo)

    def test_rechaza_qr_modificado(self):
        reserva = self.crear_reserva_suelta(1000)
        qr = contenido_qr_asistencia(reserva) + 'modificado'
        with self.assertRaises(AsistenciaRechazada) as contexto:
            registrar_asistencia_qr(qr, self.empleado.id)
        self.assertEqual(contexto.exception.codigo, 'qr_invalido')

    def test_rechaza_clase_suelta_con_saldo(self):
        reserva = self.crear_reserva_suelta(500)
        self.assert_rechazo(reserva, 'clase_suelta_pago_pendiente')

    def test_rechaza_suspension_de_clase_suelta(self):
        reserva = self.crear_reserva_suelta(1000)
        db.session.add(Suspension(
            usuario_id=self.cliente.id,
            tipo='no_abonado',
            activa=True
        ))
        db.session.commit()
        self.assert_rechazo(reserva, 'suspension_clase_suelta')

    def test_rechaza_abono_impago_despues_del_dia_10(self):
        reserva = self.crear_reserva_abono(0)
        self.assert_rechazo(reserva, 'abono_pago_vencido')

    def test_rechaza_suspension_del_turno(self):
        reserva = self.crear_reserva_abono(4000)
        db.session.add(Suspension(
            usuario_id=self.cliente.id,
            tipo='abonado',
            turno_id=self.turno.id,
            clase_id=self.clase.id,
            abono_id=reserva.abono_id,
            activa=True
        ))
        db.session.commit()
        self.assert_rechazo(reserva, 'suspension_turno')

    def test_permite_abono_impago_hasta_el_dia_10(self):
        reserva = self.crear_reserva_abono(0)
        with patch('asistencia_logic.sincronizar_suspensiones_usuario'):
            asistencia, _ = registrar_asistencia_qr(
                contenido_qr_asistencia(reserva),
                self.empleado.id,
                hoy=date(2026, 6, 10)
            )
        self.assertTrue(asistencia.presente)

    def test_registra_clase_suelta_pagada_y_evitar_duplicado(self):
        reserva = self.crear_reserva_suelta(1000)
        asistencia, _ = registrar_asistencia_qr(
            contenido_qr_asistencia(reserva),
            self.empleado.id,
            hoy=date(2026, 6, 22)
        )
        self.assertTrue(asistencia.presente)
        self.assertTrue(reserva.to_dict()['asistida'])
        self.assertEqual(reserva.to_dict()['fecha_asistencia'], '2026-06-22')
        self.assertEqual(Asistencia.query.count(), 1)
        self.assert_rechazo(reserva, 'asistencia_duplicada')

    def test_reserva_sigue_pendiente_antes_de_los_15_minutos(self):
        reserva = self.crear_reserva_suelta(1000)
        estado, asistencia = reserva.asistencia_estado(datetime(2026, 6, 22, 18, 14))
        self.assertEqual(estado, 'pendiente')
        self.assertIsNone(asistencia)
        self.assertFalse(reserva.asistencia_vencida(datetime(2026, 6, 22, 18, 14)))

    def test_marca_falta_desde_los_15_minutos_sin_asistencia(self):
        reserva = self.crear_reserva_suelta(1000)
        with self.assertRaises(AsistenciaRechazada) as contexto:
            registrar_asistencia_qr(
                contenido_qr_asistencia(reserva),
                self.empleado.id,
                hoy=date(2026, 6, 22),
                ahora=datetime(2026, 6, 22, 18, 15)
            )

        self.assertEqual(contexto.exception.codigo, 'asistencia_fuera_de_tiempo')
        falta = Asistencia.query.filter_by(reserva_id=reserva.id).first()
        self.assertIsNotNone(falta)
        self.assertFalse(falta.presente)
        self.assertTrue(reserva.to_dict()['falto'])
        self.assertEqual(reserva.to_dict()['estado_asistencia'], 'falto')


if __name__ == '__main__':
    unittest.main()
