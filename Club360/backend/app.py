from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from dotenv import load_dotenv
import os

load_dotenv()

from models import db
from routes.auth import auth_bp
from routes.clases import clases_bp
from routes.reservas import reservas_bp
from routes.otros import usuarios_bp, actividades_bp, asistencia_bp, suspensiones_bp

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql+psycopg://postgres:postgres@localhost:5432/club360')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'dev-secret-key')

    CORS(app, origins=['http://localhost:5173', 'http://localhost:3000'])
    db.init_app(app)
    Migrate(app, db)
    JWTManager(app)

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(clases_bp, url_prefix='/api/clases')
    app.register_blueprint(reservas_bp, url_prefix='/api/reservas')
    app.register_blueprint(usuarios_bp, url_prefix='/api/usuarios')
    app.register_blueprint(actividades_bp, url_prefix='/api/actividades')
    app.register_blueprint(asistencia_bp, url_prefix='/api/asistencia')
    app.register_blueprint(suspensiones_bp, url_prefix='/api/suspensiones')

    @app.route('/api/health')
    def health():
        return jsonify({'status': 'ok', 'app': 'Club 360'}), 200

    return app


def seed_data(app):
    """Datos iniciales para desarrollo"""
    with app.app_context():
        from models import Usuario, Actividad
        if Usuario.query.first():
            return
        # Admin
        admin = Usuario(nombre='Admin', apellido='Club360', dni='00000000', email='admin@club360.com', rol='administrador')
        admin.set_password('admin123')
        # Empleado
        emp = Usuario(nombre='Carlos', apellido='Gómez', dni='11111111', email='empleado@club360.com', rol='empleado')
        emp.set_password('emp123')
        # Cliente demo
        cli = Usuario(nombre='Juan', apellido='Pérez', dni='22222222', email='cliente@club360.com', rol='cliente')
        cli.set_password('cliente123')

        # Actividades
        actividades = [
            Actividad(nombre='Fútbol', descripcion='Fútbol 5 en cancha de césped sintético', precio_clase=2500),
            Actividad(nombre='Pádel', descripcion='Pádel en cancha cubierta', precio_clase=3000),
            Actividad(nombre='Básquet', descripcion='Básquet en cancha reglamentaria', precio_clase=2000),
            Actividad(nombre='Vóley', descripcion='Vóley en cancha de arena', precio_clase=2000),
        ]
        db.session.add_all([admin, emp, cli] + actividades)
        db.session.commit()

        # Clases demo
        from models import Clase
        from datetime import time
        clases_demo = [
            Clase(actividad_id=1, dia_semana='lunes', hora_inicio=time(8, 0), cupo_maximo=10),
            Clase(actividad_id=1, dia_semana='miercoles', hora_inicio=time(10, 0), cupo_maximo=10),
            Clase(actividad_id=2, dia_semana='martes', hora_inicio=time(9, 0), cupo_maximo=8),
            Clase(actividad_id=2, dia_semana='jueves', hora_inicio=time(18, 0), cupo_maximo=8),
            Clase(actividad_id=3, dia_semana='viernes', hora_inicio=time(20, 0), cupo_maximo=12),
            Clase(actividad_id=4, dia_semana='sabado', hora_inicio=time(10, 0), cupo_maximo=12),
        ]
        db.session.add_all(clases_demo)
        db.session.commit()
        print("✅ Datos de prueba cargados")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
        seed_data(app)
    app.run(debug=True, port=5000)
