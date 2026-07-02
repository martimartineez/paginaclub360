import unittest

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

from models import Usuario, db
from routes.otros import usuarios_bp


class UsuariosListadoTestCase(unittest.TestCase):
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

        self.admin_actual = Usuario(
            nombre='Admin',
            apellido='Actual',
            dni='100',
            email='admin.actual@test.com',
            password_hash='x',
            rol='administrador',
        )
        self.otro_admin = Usuario(
            nombre='Admin',
            apellido='Otro',
            dni='101',
            email='admin.otro@test.com',
            password_hash='x',
            rol='administrador',
        )
        self.cliente = Usuario(
            nombre='Cliente',
            apellido='Uno',
            dni='102',
            email='cliente@test.com',
            password_hash='x',
            rol='cliente',
        )
        db.session.add_all([self.admin_actual, self.otro_admin, self.cliente])
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def auth_headers(self, usuario):
        token = create_access_token(identity=str(usuario.id))
        return {'Authorization': f'Bearer {token}'}

    def test_admin_no_se_ve_a_si_mismo_pero_ve_otros_admins(self):
        response = self.client.get(
            '/api/usuarios/',
            headers=self.auth_headers(self.admin_actual),
        )

        self.assertEqual(response.status_code, 200)
        ids = {u['id'] for u in response.get_json()}
        self.assertNotIn(self.admin_actual.id, ids)
        self.assertIn(self.otro_admin.id, ids)
        self.assertIn(self.cliente.id, ids)

    def test_filtro_administradores_tambien_excluye_admin_actual(self):
        response = self.client.get(
            '/api/usuarios/',
            query_string={'rol': 'administrador'},
            headers=self.auth_headers(self.admin_actual),
        )

        self.assertEqual(response.status_code, 200)
        ids = {u['id'] for u in response.get_json()}
        self.assertEqual(ids, {self.otro_admin.id})


if __name__ == '__main__':
    unittest.main()
