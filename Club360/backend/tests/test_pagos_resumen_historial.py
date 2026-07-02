import unittest
from datetime import date, time
from unittest.mock import patch

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

from creditos_logic import cancelar_reserva_con_creditos
from models import Abono, Actividad, Clase, Pago, Reserva, Usuario, db
from routes.reservas import reservas_bp


class Dia10(date):
    @classmethod
    def today(cls):
        return cls(2026, 7, 10)


class Dia13(date):
    @classmethod
    def today(cls):
        return cls(2026, 7, 13)


class PagosResumenHistorialTestCase(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            SECRET_KEY='test-secret',
            JWT_SECRET_KEY='test-secret',
            JWT_ACCESS_TOKEN_EXPIRES=False,
        )
        db.init_app(self.app)
        JWTManager(self.app)
        self.app.register_blueprint(reservas_bp, url_prefix='/api/reservas')
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        self.cliente = Usuario(
            nombre='Ciro', apellido='Cliente', dni='2',
            email='cliente@test.com', password_hash='x', rol='cliente'
        )
        self.actividad = Actividad(nombre='Padel', precio_clase=1000)
        db.session.add_all([self.cliente, self.actividad])
        db.session.flush()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def auth_headers(self):
        token = create_access_token(identity=str(self.cliente.id))
        return {'Authorization': f'Bearer {token}'}

    def crear_reserva_suelta(self, fecha):
        clase = Clase(
            actividad_id=self.actividad.id,
            fecha=fecha,
            hora_inicio=time(18, 0),
            cupo_maximo=10,
            precio_clase=1000
        )
        db.session.add(clase)
        db.session.flush()
        reserva = Reserva(
            usuario_id=self.cliente.id,
            clase_id=clase.id,
            tipo='no_abonado',
            estado='activa',
            mes=fecha.month,
            anio=fecha.year,
            monto_total=1000,
            monto_pagado=500,
            senia_pagada=True
        )
        db.session.add(reserva)
        db.session.commit()
        return reserva

    def crear_abono_con_reservas(self, fechas=None):
        fechas = fechas or (date(2026, 7, 7), date(2026, 7, 14))
        abono = Abono(
            usuario_id=self.cliente.id,
            actividad_id=self.actividad.id,
            mes=fechas[0].month,
            anio=fechas[0].year,
            monto_total=2000,
            monto_pagado=0
        )
        db.session.add(abono)
        db.session.flush()

        reservas = []
        for fecha in fechas:
            clase = Clase(
                actividad_id=self.actividad.id,
                fecha=fecha,
                hora_inicio=time(18, 0),
                cupo_maximo=10,
                precio_clase=1000
            )
            db.session.add(clase)
            db.session.flush()
            reserva = Reserva(
                usuario_id=self.cliente.id,
                clase_id=clase.id,
                abono_id=abono.id,
                tipo='abonado',
                estado='activa',
                mes=fecha.month,
                anio=fecha.year,
                monto_total=1000,
                monto_pagado=0,
                senia_pagada=True
            )
            db.session.add(reserva)
            reservas.append(reserva)
        db.session.commit()
        return abono, reservas

    def test_clase_ocurrida_con_deuda_va_a_historial_y_no_se_paga(self):
        reserva = self.crear_reserva_suelta(date(2000, 7, 10))

        resumen_response = self.client.get(
            '/api/reservas/pagos-resumen',
            headers=self.auth_headers()
        )

        self.assertEqual(resumen_response.status_code, 200)
        resumen = resumen_response.get_json()
        self.assertNotIn(reserva.id, [item.get('reserva_id') for item in resumen['pendientes']])
        historial = [item for item in resumen['pagados'] if item.get('reserva_id') == reserva.id]
        self.assertEqual(len(historial), 1)
        self.assertTrue(historial[0]['clase_ocurrida'])
        self.assertEqual(historial[0]['deuda'], 500)
        self.assertEqual(historial[0]['deuda_label'], 'No pagado - $500')

        pago_response = self.client.post(
            f'/api/reservas/{reserva.id}/pagar',
            json={'metodo': 'tarjeta_credito', 'monto': 500},
            headers=self.auth_headers()
        )

        self.assertEqual(pago_response.status_code, 400)
        self.assertEqual(Pago.query.count(), 0)

    def test_abono_impago_hasta_dia_10_sigue_pendiente(self):
        abono, _ = self.crear_abono_con_reservas()

        with patch('routes.reservas.date', Dia10), patch('suspensiones_logic.date', Dia10):
            response = self.client.get(
                '/api/reservas/pagos-resumen',
                headers=self.auth_headers()
            )

        self.assertEqual(response.status_code, 200)
        resumen = response.get_json()
        self.assertIn(abono.id, [item.get('abono_id') for item in resumen['pendientes']])
        self.assertNotIn(abono.id, [item.get('abono_id') for item in resumen['pagados']])

    def test_abono_impago_despues_dia_10_va_a_historial_y_suspende_futuras(self):
        abono, reservas = self.crear_abono_con_reservas()
        reserva_futura = reservas[1]

        with patch('routes.reservas.date', Dia13), patch('suspensiones_logic.date', Dia13):
            response = self.client.get(
                '/api/reservas/pagos-resumen',
                headers=self.auth_headers()
            )

        self.assertEqual(response.status_code, 200)
        resumen = response.get_json()
        self.assertNotIn(abono.id, [item.get('abono_id') for item in resumen['pendientes']])
        historial = [item for item in resumen['pagados'] if item.get('abono_id') == abono.id]
        self.assertEqual(len(historial), 1)
        self.assertTrue(historial[0]['abono_vencido'])
        self.assertEqual(historial[0]['estado_pago'], 'vencido')
        self.assertEqual(historial[0]['deuda'], 2000)
        self.assertEqual(historial[0]['deuda_label'], 'No pagado - $2,000')

        db.session.refresh(reserva_futura)
        self.assertEqual(reserva_futura.estado, 'suspendida')

    def test_abono_con_todas_las_clases_canceladas_no_figura_pagado(self):
        abono, reservas = self.crear_abono_con_reservas(
            (date(2099, 7, 7), date(2099, 7, 14))
        )

        for reserva in reservas:
            cancelar_reserva_con_creditos(reserva)
        db.session.commit()
        db.session.refresh(abono)

        self.assertEqual(Pago.query.count(), 0)
        self.assertEqual(float(abono.monto_pagado), 0)
        self.assertEqual(float(abono.monto_total), 0)

        response = self.client.get(
            '/api/reservas/pagos-resumen',
            headers=self.auth_headers()
        )

        self.assertEqual(response.status_code, 200)
        resumen = response.get_json()
        self.assertNotIn(abono.id, [item.get('abono_id') for item in resumen['pendientes']])
        historial = [item for item in resumen['pagados'] if item.get('abono_id') == abono.id]
        self.assertEqual(len(historial), 1)
        self.assertEqual(historial[0]['estado'], 'cancelada')
        self.assertEqual(historial[0]['estado_pago'], 'cancelada')
        self.assertEqual(historial[0]['deuda'], 0)
        self.assertEqual(historial[0]['deuda_label'], 'Cancelada')


if __name__ == '__main__':
    unittest.main()
