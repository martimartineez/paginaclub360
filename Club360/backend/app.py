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
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
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


    @app.cli.command("seed-colo")
    def seed_colo_command():
        """reset-db + datos extra para demo: Maria con pago pendiente, pago realizado, suspension y credito."""
        from models import db
        db.drop_all()
        db.create_all()
        seed_data(app)

        with app.app_context():
            from models import Usuario, Actividad, Clase, Reserva, Pago, Credito, Suspension
            from datetime import date, time, datetime

            maria = Usuario.query.filter_by(email='maria@gmail.com').first()
            futbol = Actividad.query.filter_by(nombre='Fútbol').first()
            padel  = Actividad.query.filter_by(nombre='Pádel').first()
            voley  = Actividad.query.filter_by(nombre='Vóley').first()
            admin  = Usuario.query.filter_by(rol='administrador').first()

            hoy = date.today()

            # --- Clases de soporte ---
            clase_pendiente = Clase(
                actividad_id=futbol.id,
                fecha=hoy,
                hora_inicio=time(10, 0),
                cupo_maximo=10,
                precio_clase=2500,
                activa=True
            )
            clase_pagada = Clase(
                actividad_id=padel.id,
                fecha=hoy,
                hora_inicio=time(12, 0),
                cupo_maximo=10,
                precio_clase=3000,
                activa=True
            )
            db.session.add_all([clase_pendiente, clase_pagada])
            db.session.flush()

            # --- Reserva con pago PENDIENTE (senia_pagada=False, monto_pagado=0) ---
            reserva_pendiente = Reserva(
                usuario_id=maria.id,
                clase_id=clase_pendiente.id,
                tipo='no_abonado',
                estado='activa',
                mes=hoy.month,
                anio=hoy.year,
                monto_total=2500,
                monto_pagado=0,
                senia_pagada=False
            )
            db.session.add(reserva_pendiente)
            db.session.flush()

            # --- Reserva con pago REALIZADO (senia_pagada=True, con Pago asociado) ---
            reserva_pagada = Reserva(
                usuario_id=maria.id,
                clase_id=clase_pagada.id,
                tipo='no_abonado',
                estado='activa',
                mes=hoy.month,
                anio=hoy.year,
                monto_total=3000,
                monto_pagado=1500,
                senia_pagada=True
            )
            db.session.add(reserva_pagada)
            db.session.flush()

            pago = Pago(
                reserva_id=reserva_pagada.id,
                monto=1500,
                metodo='tarjeta_credito',
                tipo_pago='senia',
                fecha=datetime.utcnow(),
                registrado_por=admin.id
            )
            db.session.add(pago)

            # --- Suspension activa ---
            suspension = Suspension(
                usuario_id=maria.id,
                tipo='no_abonado',
                motivo='Inasistencia sin cancelación previa',
                activa=True,
                cantidad_clases=1,
                monto_original=2500,
                recargo=125,
                monto_deuda=2750
            )
            db.session.add(suspension)

            # --- Credito para Vóley ---
            credito = Credito(
                usuario_id=maria.id,
                actividad_id=voley.id,
                monto=2000,
                monto_restante=2000,
                origen='clase_suelta_cancelacion',
                estado='disponible',
                motivo='Crédito por clase cancelada por el club'
            )
            db.session.add(credito)

            db.session.commit()
            print("✅ seed-colo: datos extra de Maria cargados correctamente.")

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

    _iniciar_scheduler(app)

    return app


def _iniciar_scheduler(app):
    scheduler = BackgroundScheduler(timezone='America/Argentina/Buenos_Aires')
    scheduler.add_job(
        func=lambda: _tarea_recordatorio_abonos(app),
        trigger=CronTrigger(day=10, hour=9, minute=0),
        id='recordatorio_abonos_dia_10',
        replace_existing=True
    )
    scheduler.start()
    print('[scheduler] Scheduler iniciado. Recordatorio de abonos programado para el dia 10 de cada mes a las 9:00 AM.', flush=True)


def _tarea_recordatorio_abonos(app):
    """Tarea programada: dia 10 de cada mes a las 9 AM.
    Envia un recordatorio por mail a cada cliente abonado que tenga
    deuda pendiente en el mes actual."""
    from datetime import date
    from models import Abono, Usuario
    from email_service import enviar_recordatorio_pago_abono

    hoy = date.today()
    print(f'[scheduler] Ejecutando recordatorio de abonos ({hoy})', flush=True)

    with app.app_context():
        abonos_pendientes = (
            Abono.query
            .filter(
                Abono.mes == hoy.month,
                Abono.anio == hoy.year,
                Abono.monto_pagado < Abono.monto_total
            )
            .all()
        )

        # Agrupar por usuario para mandar un solo mail con todos sus abonos
        por_usuario = {}
        for abono in abonos_pendientes:
            por_usuario.setdefault(abono.usuario_id, []).append(abono)

        enviados = 0
        for usuario_id, abonos in por_usuario.items():
            usuario = Usuario.query.get(usuario_id)
            if usuario and usuario.activo and usuario.email:
                enviado = enviar_recordatorio_pago_abono(usuario, abonos)
                if enviado:
                    enviados += 1

        print(f'[scheduler] Recordatorio de abonos: {enviados} mails enviados de {len(por_usuario)} clientes con deuda.', flush=True)


def ensure_schema_compatibility(app):
    """Agrega columnas opcionales nuevas cuando la base ya existia."""
    with app.app_context():
        inspector = inspect(db.engine)
        dialect = db.engine.dialect.name
        tiene_suspensiones = inspector.has_table('suspensiones')
        columnas_susp = {c['name'] for c in inspector.get_columns('suspensiones')} if tiene_suspensiones else set()
        tiene_clases = inspector.has_table('clases')
        columnas_clases = {c['name'] for c in inspector.get_columns('clases')} if tiene_clases else set()
        tiene_turnos = inspector.has_table('turnos')
        columnas_turnos = {c['name'] for c in inspector.get_columns('turnos')} if tiene_turnos else set()
        tiene_reservas = inspector.has_table('reservas')
        columnas_reservas = {c['name'] for c in inspector.get_columns('reservas')} if tiene_reservas else set()
        tiene_creditos = inspector.has_table('creditos')
        columnas_creditos = {c['name'] for c in inspector.get_columns('creditos')} if tiene_creditos else set()
        tiene_pagos = inspector.has_table('pagos')
        columnas_pago = {c['name'] for c in inspector.get_columns('pagos')} if tiene_pagos else set()
        tiene_lista_espera = inspector.has_table('lista_espera')
        columnas_lista_espera = {c['name'] for c in inspector.get_columns('lista_espera')} if tiene_lista_espera else set()
        tiene_asistencias = inspector.has_table('asistencias')

        numeric_type = 'NUMERIC(10, 2)' if dialect != 'sqlite' else 'NUMERIC'
        alteraciones = []

        for nombre, tipo in {
            'turno_id': 'INTEGER',
            'abono_id': 'INTEGER',
            'cantidad_clases': 'INTEGER DEFAULT 0',
            'monto_original': f'{numeric_type} DEFAULT 0',
            'recargo': f'{numeric_type} DEFAULT 0',
        }.items():
            if tiene_suspensiones and nombre not in columnas_susp:
                alteraciones.append(f'ALTER TABLE suspensiones ADD COLUMN {nombre} {tipo}')

        if tiene_pagos and 'suspension_id' not in columnas_pago:
            alteraciones.append('ALTER TABLE pagos ADD COLUMN suspension_id INTEGER')

        if tiene_lista_espera and 'origen_cancelacion' not in columnas_lista_espera:
            alteraciones.append('ALTER TABLE lista_espera ADD COLUMN origen_cancelacion VARCHAR(20)')

        for nombre, tipo in {
            'cancelada_fecha': 'TIMESTAMP',
            'cancelada_por': 'INTEGER',
        }.items():
            if tiene_clases and nombre not in columnas_clases:
                alteraciones.append(f'ALTER TABLE clases ADD COLUMN {nombre} {tipo}')

        for nombre, tipo in {
            'cancelado_fecha': 'TIMESTAMP',
            'cancelado_por': 'INTEGER',
            'motivo_cancelacion': 'TEXT',
        }.items():
            if tiene_turnos and nombre not in columnas_turnos:
                alteraciones.append(f'ALTER TABLE turnos ADD COLUMN {nombre} {tipo}')

        for nombre, tipo in {
            'cancelada_por': 'INTEGER',
            'motivo_cancelacion': 'TEXT',
            'fecha_cancelacion': 'TIMESTAMP',
        }.items():
            if tiene_reservas and nombre not in columnas_reservas:
                alteraciones.append(f'ALTER TABLE reservas ADD COLUMN {nombre} {tipo}')

        if tiene_creditos and 'motivo' not in columnas_creditos:
            alteraciones.append('ALTER TABLE creditos ADD COLUMN motivo TEXT')

        for sql in alteraciones:
            db.session.execute(text(sql))
        if alteraciones:
            db.session.commit()

        if tiene_asistencias:
            duplicadas = db.session.execute(text(
                'SELECT reserva_id FROM asistencias '
                'GROUP BY reserva_id HAVING COUNT(*) > 1 LIMIT 1'
            )).first()
            if not duplicadas:
                db.session.execute(text(
                    'CREATE UNIQUE INDEX IF NOT EXISTS '
                    'uq_asistencia_reserva ON asistencias (reserva_id)'
                ))
                db.session.commit()


def seed_data(app):
    with app.app_context():
        from models import Usuario, Actividad, Clase, Turno, Credito, TarjetaCredito, Suspension, Reserva, Pago
        from datetime import date, time, timedelta

        if Usuario.query.first():
            return

        # Usuarios
        admin = Usuario(nombre='Admin', apellido='Club', dni='00000000', email='lautaromendezportela@gmail.com', rol='administrador')
        admin.set_password('admin123')
        emp = Usuario(nombre='Carlos', apellido='Gómez', dni='11111111', email='empleado@club360.com', rol='empleado')
        emp.set_password('12345678')
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
        cli5 = Usuario(nombre='Lautaro', apellido='Mendez', dni='30000001', email='laumendezporv@hotmail.com', rol='cliente')
        cli5.set_password('12345678')

        actividades = [
            Actividad(nombre='Fútbol', descripcion='Fútbol 5 en cancha de césped sintético', precio_clase=2500),
            Actividad(nombre='Pádel', descripcion='Pádel en cancha cubierta', precio_clase=3000),
            Actividad(nombre='Básquet', descripcion='Básquet en cancha reglamentaria', precio_clase=2000),
            Actividad(nombre='Vóley', descripcion='Vóley en cancha de arena', precio_clase=2000),
        ]
        db.session.add_all([admin, emp, cli, cli1, cli2, cli3, cli4, cli5] + actividades)
        db.session.commit()

        # Credito manual para laumendezporv@hotmail.com — Voley 15:00
        voley = Actividad.query.filter_by(nombre='Vóley').first()
        credito_cli5 = Credito(
            usuario_id=cli5.id,
            actividad_id=voley.id,
            monto=2000,
            monto_restante=2000,
            origen='abono_cancelacion',
            estado='disponible',
            motivo='Crédito manual para clase de Vóley 15:00'
        )
        credito_cli5b = Credito(
            usuario_id=cli5.id,
            actividad_id=voley.id,
            monto=2000,
            monto_restante=2000,
            origen='abono_cancelacion',
            estado='disponible',
            motivo='Crédito manual para clase de Vóley 15:00'
        )
        db.session.add_all([credito_cli5, credito_cli5b])
        db.session.commit()
        # Tarjeta para laumendezporv@hotmail.com 
        for cli_tar in [cli5]:
            tarjeta = TarjetaCredito(
                usuario_id=cli_tar.id,
                ultimos_4='2222',
                titular='Juan Perez',
                vencimiento='09/32',
                activa=True
            )
            db.session.add(tarjeta)

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