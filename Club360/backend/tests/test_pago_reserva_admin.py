import unittest
from datetime import date, time

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

from models import Abono, Actividad, Clase, Pago, Reserva, Usuario, db
from routes.otros import usuarios_bp


class PagoReservaAdminTestCase(unittest.TestCase):
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
        self.app.register_blueprint(usuarios_bp, url_prefix='/api/usuarios')
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
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def auth_headers(self):
        token = create_access_token(identity=str(self.admin.id))
        return {'Authorization': f'Bearer {token}'}

    def crear_reserva(self, fecha, pagado=500):
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
            monto_pagado=pagado,
            senia_pagada=pagado >= 500
        )
        db.session.add(reserva)
        db.session.commit()
        return reserva

    def test_empleado_paga_saldo_total_de_reserva_futura(self):
        reserva = self.crear_reserva(date(2099, 7, 10), pagado=500)

        response = self.client.post(
            f'/api/usuarios/{self.cliente.id}/pagar-reserva/{reserva.id}',
            json={'metodo': 'efectivo'},
            headers=self.auth_headers()
        )

        self.assertEqual(response.status_code, 200)
        db.session.refresh(reserva)
        self.assertEqual(float(reserva.monto_pagado), 1000)
        self.assertTrue(reserva.senia_pagada)
        pago = Pago.query.one()
        self.assertEqual(float(pago.monto), 500)
        self.assertEqual(pago.tipo_pago, 'mensualidad')

    def test_no_paga_reserva_pasada(self):
        reserva = self.crear_reserva(date(2000, 7, 10), pagado=500)

        response = self.client.post(
            f'/api/usuarios/{self.cliente.id}/pagar-reserva/{reserva.id}',
            json={'metodo': 'efectivo'},
            headers=self.auth_headers()
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Pago.query.count(), 0)

    def test_paga_abono_desde_reserva_futura(self):
        abono = Abono(
            usuario_id=self.cliente.id,
            actividad_id=self.actividad.id,
            mes=7,
            anio=2099,
            monto_total=4000,
            monto_pagado=1000
        )
        db.session.add(abono)
        db.session.flush()
        reserva = self.crear_reserva(date(2099, 7, 10), pagado=0)
        reserva.tipo = 'abonado'
        reserva.abono_id = abono.id
        reserva.senia_pagada = True
        db.session.commit()

        response = self.client.post(
            f'/api/usuarios/{self.cliente.id}/pagar-reserva/{reserva.id}',
            json={'metodo': 'efectivo'},
            headers=self.auth_headers()
        )

        self.assertEqual(response.status_code, 200)
        db.session.refresh(abono)
        db.session.refresh(reserva)
        self.assertEqual(float(abono.monto_pagado), 4000)
        self.assertEqual(float(reserva.monto_pagado), 1000)
        pago = Pago.query.one()
        self.assertEqual(pago.abono_id, abono.id)
        self.assertIsNone(pago.reserva_id)
        self.assertEqual(float(pago.monto), 3000)


if __name__ == '__main__':
    unittest.main()
