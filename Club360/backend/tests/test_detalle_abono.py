import unittest
from datetime import date, time
from unittest.mock import patch

from flask import Flask
from flask_jwt_extended import JWTManager

from models import Actividad, Clase, db
from routes.clases import clases_bp


class FixedDate(date):
    @classmethod
    def today(cls):
        return cls(2099, 7, 1)


class DetalleAbonoTestCase(unittest.TestCase):
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

        self.actividad = Actividad(nombre='Padel', precio_clase=1000)
        db.session.add(self.actividad)
        db.session.flush()

        self.clase_vigente = Clase(
            actividad_id=self.actividad.id,
            fecha=date(2099, 7, 1),
            hora_inicio=time(18, 0),
            cupo_maximo=10,
            precio_clase=1500,
            cancelada=False,
        )
        self.clase_cancelada = Clase(
            actividad_id=self.actividad.id,
            fecha=date(2099, 7, 8),
            hora_inicio=time(18, 0),
            cupo_maximo=10,
            precio_clase=1000,
            cancelada=True,
        )
        db.session.add_all([self.clase_vigente, self.clase_cancelada])
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_detalle_abono_no_devuelve_clases_canceladas(self):
        with patch('routes.clases.date', FixedDate):
            response = self.client.get('/api/clases/detalle-abono', query_string={
                'actividad_id': self.actividad.id,
                'dia_semana_num': self.clase_vigente.fecha.weekday(),
                'hora_inicio': '18:00',
            })

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['total_clases_mes'], 1)
        self.assertEqual(data['total_disponibles'], 1)
        self.assertEqual([c['clase_id'] for c in data['clases']], [self.clase_vigente.id])
        self.assertEqual(data['precio_por_clase'], 1500)
        self.assertEqual(data['monto_total'], 1500)
        self.assertEqual(data['clases'][0]['precio_clase'], 1500)

    def test_fechas_disponibles_devuelve_precio_efectivo_de_clase(self):
        with patch('routes.clases.date', FixedDate):
            response = self.client.get('/api/clases/fechas-disponibles', query_string={
                'actividad_id': self.actividad.id,
                'desde': '2099-07-01',
                'hasta': '2099-07-31',
            })

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data[0]['horarios'][0]['precio_clase'], 1500)

    def test_horarios_disponibles_devuelve_precio_efectivo_de_clase(self):
        with patch('routes.clases.date', FixedDate):
            response = self.client.get('/api/clases/horarios-disponibles', query_string={
                'actividad_id': self.actividad.id,
            })

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data[0]['precio_clase'], 1500)
        self.assertEqual(data[0]['clases_mes'][0]['precio_clase'], 1500)


if __name__ == '__main__':
    unittest.main()
