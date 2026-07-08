import unittest
from datetime import date, time

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

from models import Actividad, Asistencia, Clase, Reserva, Usuario, db
from routes.clases import clases_bp


class ClaseInscriptosAsistenciaTestCase(unittest.TestCase):
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
        self.app.register_blueprint(clases_bp, url_prefix='/api/clases')
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        self.empleado = Usuario(
            nombre='Eva',
            apellido='Empleado',
            dni='1',
            email='empleado@test.com',
            password_hash='x',
            rol='empleado',
        )
        self.cliente_asistido = Usuario(
            nombre='Ana',
            apellido='Asistida',
            dni='2',
            email='ana@test.com',
            password_hash='x',
            rol='cliente',
        )
        self.cliente_pendiente = Usuario(
            nombre='Pedro',
            apellido='Pendiente',
            dni='3',
            email='pedro@test.com',
            password_hash='x',
            rol='cliente',
        )
        self.actividad = Actividad(nombre='Padel', precio_clase=1000)
        db.session.add_all([
            self.empleado,
            self.cliente_asistido,
            self.cliente_pendiente,
            self.actividad,
        ])
        db.session.flush()

        self.clase = Clase(
            actividad_id=self.actividad.id,
            fecha=date(2099, 7, 7),
            hora_inicio=time(18, 0),
            cupo_maximo=10,
            precio_clase=1000,
        )
        db.session.add(self.clase)
        db.session.flush()

        self.reserva_asistida = Reserva(
            usuario_id=self.cliente_asistido.id,
            clase_id=self.clase.id,
            tipo='no_abonado',
            estado='activa',
            mes=7,
            anio=2099,
            monto_total=1000,
            monto_pagado=1000,
            senia_pagada=True,
        )
        self.reserva_pendiente = Reserva(
            usuario_id=self.cliente_pendiente.id,
            clase_id=self.clase.id,
            tipo='no_abonado',
            estado='activa',
            mes=7,
            anio=2099,
            monto_total=1000,
            monto_pagado=0,
            senia_pagada=False,
        )
        db.session.add_all([self.reserva_asistida, self.reserva_pendiente])
        db.session.flush()
        db.session.add(Asistencia(
            reserva_id=self.reserva_asistida.id,
            fecha=date(2099, 7, 7),
            presente=True,
            registrado_por=self.empleado.id,
        ))
        db.session.commit()

        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def auth_headers(self):
        token = create_access_token(identity=str(self.empleado.id))
        return {'Authorization': f'Bearer {token}'}

    def test_inscriptos_incluye_estado_de_asistencia(self):
        response = self.client.get(
            f'/api/clases/{self.clase.id}/inscriptos',
            headers=self.auth_headers(),
        )

        self.assertEqual(response.status_code, 200)
        por_reserva = {item['id']: item for item in response.get_json()}

        asistida = por_reserva[self.reserva_asistida.id]
        self.assertTrue(asistida['asistida'])
        self.assertFalse(asistida['falto'])
        self.assertEqual(asistida['estado_asistencia'], 'asistida')

        pendiente = por_reserva[self.reserva_pendiente.id]
        self.assertFalse(pendiente['asistida'])
        self.assertFalse(pendiente['falto'])
        self.assertEqual(pendiente['estado_asistencia'], 'pendiente')


if __name__ == '__main__':
    unittest.main()
