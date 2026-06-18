from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from dotenv import load_dotenv
from sqlalchemy import inspect, text
import os

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from models import db
from routes.auth import auth_bp
from routes.clases import clases_bp
from routes.reservas import reservas_bp
from routes.otros import usuarios_bp, actividades_bp, asistencia_bp, suspensiones_bp, creditos_bp
from routes.turnos import turnos_bp

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql+psycopg://postgres:postgres@localhost:5432/club360')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'dev-secret-key')
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') or app.config['JWT_SECRET_KEY']
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False # para que no expire

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
    app.register_blueprint(creditos_bp, url_prefix='/api/creditos')
    app.register_blueprint(turnos_bp, url_prefix='/api/turnos')

    @app.cli.command("reset-db")
    def reset_db_command():
        """Borra la base de datos, la recrea y carga los datos de prueba."""
        db.drop_all()
        db.create_all()
        seed_data(app)
        print("✅ Base de datos reiniciada desde cero y con datos de prueba.")

    @app.route('/api/health')
    def health():
        return jsonify({'status': 'ok', 'app': 'Club 360'}), 200

    return app


def ensure_schema_compatibility(app):
    """Agrega columnas opcionales nuevas cuando la base ya existia."""
    with app.app_context():
        inspector = inspect(db.engine)
        if not inspector.has_table('suspensiones'):
            return

        dialect = db.engine.dialect.name
        columnas_susp = {c['name'] for c in inspector.get_columns('suspensiones')}
        tiene_pagos = inspector.has_table('pagos')
        columnas_pago = {c['name'] for c in inspector.get_columns('pagos')} if tiene_pagos else set()

        numeric_type = 'NUMERIC(10, 2)' if dialect != 'sqlite' else 'NUMERIC'
        alteraciones = []

        for nombre, tipo in {
            'turno_id': 'INTEGER',
            'abono_id': 'INTEGER',
            'cantidad_clases': 'INTEGER DEFAULT 0',
            'monto_original': f'{numeric_type} DEFAULT 0',
            'recargo': f'{numeric_type} DEFAULT 0',
        }.items():
            if nombre not in columnas_susp:
                alteraciones.append(f'ALTER TABLE suspensiones ADD COLUMN {nombre} {tipo}')

        if tiene_pagos and 'suspension_id' not in columnas_pago:
            alteraciones.append('ALTER TABLE pagos ADD COLUMN suspension_id INTEGER')

        for sql in alteraciones:
            db.session.execute(text(sql))
        if alteraciones:
            db.session.commit()


def seed_data(app):
    with app.app_context():
        from models import Usuario, Actividad, Clase, Turno
        from datetime import date, time, timedelta

        if Usuario.query.first():
            return

        # Usuarios
        admin = Usuario(nombre='Admin', apellido='Club', dni='00000000', email='admin@club360.com', rol='administrador')
        admin.set_password('admin123')
        emp = Usuario(nombre='Carlos', apellido='Gómez', dni='11111111', email='empleado@club360.com', rol='empleado')
        emp.set_password('emp123')
        cli = Usuario(nombre='Juan', apellido='Pérez', dni='22222222', email='cliente@club360.com', rol='cliente')
        cli.set_password('cliente123')
        cli1 = Usuario(nombre='Alejandro', apellido='Camacho', dni='44000332', email='ale@gmail.com', rol='cliente')
        cli1.set_password('alejandro123')
        cli2 = Usuario(nombre='Lautaro', apellido='Mendez', dni='45002221', email='lauti@gmail.com', rol='cliente')
        cli2.set_password('12345678')
        cli3 = Usuario(nombre='Maria', apellido='Mendez', dni='45229801', email='maria@gmail.com', rol='cliente')
        cli3.set_password('12345678')
        cli4 = Usuario(nombre='Jesus', apellido='Diaz', dni='10675222', email='jesus@gmail.com', rol='cliente')
        cli4.set_password('12345678')

        actividades = [
            Actividad(nombre='Fútbol', descripcion='Fútbol 5 en cancha de césped sintético', precio_clase=2500),
            Actividad(nombre='Pádel', descripcion='Pádel en cancha cubierta', precio_clase=3000),
            Actividad(nombre='Básquet', descripcion='Básquet en cancha reglamentaria', precio_clase=2000),
            Actividad(nombre='Vóley', descripcion='Vóley en cancha de arena', precio_clase=2000),
        ]
        db.session.add_all([admin, emp, cli, cli1, cli2, cli3, cli4] + actividades)
        db.session.commit()

        # # Crear turnos demo (generan clases automáticamente hasta fin de año)
        # from models import Turno
        # from routes.turnos import generar_clases_para_turno

        # turnos_demo = [
        #     Turno(actividad_id=1, dia_semana=0, hora_inicio=time(8, 0), cupo_maximo=10, precio_clase=2500),   # Fútbol Lunes
        #     Turno(actividad_id=1, dia_semana=2, hora_inicio=time(10, 0), cupo_maximo=10, precio_clase=2500),  # Fútbol Miércoles
        #     Turno(actividad_id=2, dia_semana=1, hora_inicio=time(9, 0), cupo_maximo=8, precio_clase=3000),    # Pádel Martes
        #     Turno(actividad_id=2, dia_semana=3, hora_inicio=time(18, 0), cupo_maximo=8, precio_clase=3000),   # Pádel Jueves
        #     Turno(actividad_id=3, dia_semana=4, hora_inicio=time(20, 0), cupo_maximo=12, precio_clase=2000),  # Básquet Viernes
        #     Turno(actividad_id=4, dia_semana=5, hora_inicio=time(10, 0), cupo_maximo=12, precio_clase=2000),  # Vóley Sábado
        # ]
        # db.session.add_all(turnos_demo)
        # db.session.flush()

        # total_clases = 0
        # for t in turnos_demo:
        #     generadas, _ = generar_clases_para_turno(t)
        #     total_clases += generadas

        # db.session.commit()
        # print(f"✅ Datos de prueba cargados: {len(turnos_demo)} turnos, {total_clases} clases generadas")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    ensure_schema_compatibility(app)
    with app.app_context():
        seed_data(app)
    app.run(debug=True, port=5000)
