from flask import Flask
from flask_cors import CORS
from werkzeug.security import generate_password_hash
from extensions import db
from blueprints.clases import clases_bp
from blueprints.reservas import reservas_bp
from blueprints.auth import auth_bp # Importamos el nuevo módulo

app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:1234@localhost/club360'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

app.register_blueprint(clases_bp)
app.register_blueprint(reservas_bp)
app.register_blueprint(auth_bp) # Registramos el login/registro

# ==========================================
# INYECTOR DE DATOS INICIALES
# ==========================================
def inyectar_datos_por_defecto():
    from models import Rol, Usuario
    
    # 1. Crear Roles
    roles = ['Administrador', 'Empleado', 'Cliente']
    for r in roles:
        if not Rol.query.filter_by(nombre=r).first():
            db.session.add(Rol(nombre=r))
    db.session.commit()
    
    # 2. Crear Administrador por defecto
    rol_admin = Rol.query.filter_by(nombre='Administrador').first()
    if not Usuario.query.filter_by(email='admin@gmail.com').first():
        admin = Usuario(
            nombre='Laura ',
            apellido='Rol (Admin)',
            dni='00000000',
            email='admin@gmail.com',
            password_hash=generate_password_hash('1234'),
            rol_id=rol_admin.id
        )
        db.session.add(admin)
        db.session.commit()

@app.cli.command("init-db")
def init_db():
    with app.app_context():
        db.create_all()
        inyectar_datos_por_defecto()
        print("✅ Base de datos lista con roles y admin@gmail.com creado.")

@app.cli.command("reset-db")
def reset_db():
    with app.app_context():
        db.drop_all()
        db.create_all()
        inyectar_datos_por_defecto()
        print("♻️ Base de datos reseteada. Admin restaurado.")

if __name__ == '__main__':
    app.run(debug=True, port=5000)