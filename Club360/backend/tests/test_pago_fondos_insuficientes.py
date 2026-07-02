import unittest
from datetime import date as real_date, time
from unittest.mock import patch

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

from models import Abono, Actividad, Clase, Pago, Reserva, db
from routes.reservas import reservas_bp


class Dia13(real_date):
    @classmethod
    def today(cls):
        return cls(2026, 7, 13)


class Dia10(real_date):
    @classmethod
    def today(cls):
        return cls(2026, 7, 10)


class PagoFondosInsuficientesTestCase(unittest.TestCase):
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

        from models import Usuario

        self.cliente = Usuario(
            nombre='Jesus', apellido='Cliente', dni='22',
            email='jesus@gmail.com', password_hash='x', rol='cliente'
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

    def crear_clase(self, fecha=real_date(2026, 7, 20)):
        clase = Clase(
            actividad_id=self.actividad.id,
            fecha=fecha,
            hora_inicio=time(18, 0),
            cupo_maximo=10,
            precio_clase=1000
        )
        db.session.add(clase)
        db.session.flush()
        return clase

    def crear_reserva_suelta(self):
        clase = self.crear_clase()
        reserva = Reserva(
            usuario_id=self.cliente.id,
            clase_id=clase.id,
            tipo='no_abonado',
            estado='activa',
            mes=7,
            anio=2026,
            monto_total=1000,
            monto_pagado=500,
            senia_pagada=True
        )
        db.session.add(reserva)
        db.session.commit()
        return reserva

    def crear_abono_impago(self):
        abono = Abono(
            usuario_id=self.cliente.id,
            actividad_id=self.actividad.id,
            mes=7,
            anio=2026,
            monto_total=2000,
            monto_pagado=0
        )
        db.session.add(abono)
        db.session.flush()
        for fecha in (real_date(2026, 7, 20), real_date(2026, 7, 27)):
            clase = self.crear_clase(fecha)
            reserva = Reserva(
                usuario_id=self.cliente.id,
                clase_id=clase.id,
                abono_id=abono.id,
                tipo='abonado',
                estado='activa',
                mes=7,
                anio=2026,
                monto_total=1000,
                monto_pagado=0,
                senia_pagada=True
            )
            db.session.add(reserva)
        db.session.commit()
        return abono

    def assert_fondos_insuficientes(self, response):
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json().get('error'), 'fondos insuficientes')

    def test_rechaza_pago_de_clase_suelta_sin_generar_pago_ni_actualizar_reserva(self):
        reserva = self.crear_reserva_suelta()

        response = self.client.post(
            f'/api/reservas/{reserva.id}/pagar',
            json={'metodo': 'tarjeta_credito', 'monto': 500, 'tipo_pago': 'mensualidad'},
            headers=self.auth_headers()
        )

        self.assert_fondos_insuficientes(response)
        self.assertEqual(Pago.query.count(), 0)
        db.session.refresh(reserva)
        self.assertEqual(float(reserva.monto_pagado), 500)

    def test_rechaza_pago_de_abono_sin_generar_pago_ni_actualizar_abono_o_reservas(self):
        abono = self.crear_abono_impago()

        response = self.client.post(
            f'/api/reservas/abono/{abono.id}/pagar',
            json={'metodo': 'tarjeta_credito', 'monto': 2000},
            headers=self.auth_headers()
        )

        self.assert_fondos_insuficientes(response)
        self.assertEqual(Pago.query.count(), 0)
        db.session.refresh(abono)
        self.assertEqual(float(abono.monto_pagado), 0)
        self.assertTrue(all(float(r.monto_pagado) == 0 for r in abono.reservas))

    def test_rechaza_abono_creado_con_pago_online_y_revierte_la_operacion(self):
        clase = self.crear_clase()

        with patch('routes.reservas.date', Dia13):
            response = self.client.post(
                '/api/reservas/abono',
                json={
                    'clases_ids': [clase.id],
                    'metodo_pago': 'tarjeta_credito',
                    'pago_diferido': False
                },
                headers=self.auth_headers()
            )

        self.assert_fondos_insuficientes(response)
        self.assertEqual(Pago.query.count(), 0)
        self.assertEqual(Abono.query.count(), 0)
        self.assertEqual(Reserva.query.count(), 0)

    def test_abono_en_periodo_de_gracia_no_muestra_fondos_insuficientes_y_queda_pendiente(self):
        clase = self.crear_clase()

        with patch('routes.reservas.date', Dia10):
            response = self.client.post(
                '/api/reservas/abono',
                json={
                    'clases_ids': [clase.id],
                    'metodo_pago': 'tarjeta_credito',
                    'pago_diferido': False
                },
                headers=self.auth_headers()
            )

        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertTrue(data['pago_diferido'])
        self.assertEqual(Pago.query.count(), 0)
        abono = Abono.query.one()
        self.assertEqual(float(abono.monto_pagado), 0)
        self.assertEqual(Reserva.query.count(), 1)
        self.assertEqual(float(Reserva.query.one().monto_pagado), 0)


if __name__ == '__main__':
    unittest.main()
