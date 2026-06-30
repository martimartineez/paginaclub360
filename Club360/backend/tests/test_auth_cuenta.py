import unittest
from datetime import date

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

from models import TarjetaCredito, Usuario, db
from routes.auth import auth_bp


class CuentaAuthTestCase(unittest.TestCase):
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
        self.app.register_blueprint(auth_bp, url_prefix='/api/auth')
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def auth_headers(self, user):
        token = create_access_token(identity=str(user.id))
        return {'Authorization': f'Bearer {token}'}

    def crear_usuario(self, rol='cliente', activo=True, email='u@test.com', dni='1'):
        user = Usuario(
            nombre='Ana',
            apellido='Cuenta',
            dni=dni,
            email=email,
            rol=rol,
            activo=activo,
            fecha_nacimiento=date(1990, 1, 1),
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        return user

    def test_registro_reactiva_cuenta_inactiva_sin_indicarlo(self):
        usuario = self.crear_usuario(activo=False, email='ana@test.com', dni='123')

        response = self.client.post('/api/auth/register', json={
            'nombre': 'Ana Nueva',
            'apellido': 'Cuenta',
            'dni': '123',
            'email': 'ana@test.com',
            'fecha_nacimiento': '1990-01-01',
            'password': 'password456',
        })

        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertIn('token', data)
        self.assertNotIn('reactivado', data)
        self.assertEqual(data['user']['id'], usuario.id)
        db.session.refresh(usuario)
        self.assertTrue(usuario.activo)
        self.assertEqual(usuario.nombre, 'Ana Nueva')
        self.assertTrue(usuario.check_password('password456'))

    def test_usuario_puede_eliminar_su_propia_cuenta(self):
        usuario = self.crear_usuario()

        response = self.client.delete(
            '/api/auth/me',
            headers=self.auth_headers(usuario),
        )

        self.assertEqual(response.status_code, 200)
        db.session.refresh(usuario)
        self.assertFalse(usuario.activo)

        me_response = self.client.get(
            '/api/auth/me',
            headers=self.auth_headers(usuario),
        )
        self.assertEqual(me_response.status_code, 404)

    def test_no_se_puede_eliminar_el_ultimo_admin(self):
        admin = self.crear_usuario(rol='administrador', email='admin@test.com', dni='9')

        response = self.client.delete(
            '/api/auth/me',
            headers=self.auth_headers(admin),
        )

        self.assertEqual(response.status_code, 400)
        db.session.refresh(admin)
        self.assertTrue(admin.activo)

    def test_rechaza_tarjeta_vencida(self):
        usuario = self.crear_usuario()

        response = self.client.post(
            '/api/auth/tarjetas',
            json={
                'numero': '4111111111111111',
                'titular': 'Ana Cuenta',
                'vencimiento': '01/20',
            },
            headers=self.auth_headers(usuario),
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()['error'], 'La tarjeta esta vencida')
        self.assertEqual(TarjetaCredito.query.count(), 0)


if __name__ == '__main__':
    unittest.main()
