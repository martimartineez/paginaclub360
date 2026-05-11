from extensions import db

class Rol(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    apellido = db.Column(db.String(50), nullable=False) 
    dni = db.Column(db.String(15), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    
    # contraseña encriptada
    password_hash = db.Column(db.String(255), nullable=False) 
    
    rol_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    rol = db.relationship('Rol', backref='usuarios')

# ... (Clase y Reserva quedan exactamente igual que antes)
class Clase(db.Model):
    __tablename__ = 'clases'
    id = db.Column(db.Integer, primary_key=True)
    actividad = db.Column(db.String(50), nullable=False) 
    dia = db.Column(db.String(20), nullable=False)
    hora = db.Column(db.String(10), nullable=False) 
    cupo_maximo = db.Column(db.Integer, nullable=False)
    precio = db.Column(db.Float, nullable=False)

class Reserva(db.Model):
    __tablename__ = 'reservas'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, nullable=False)
    clase_id = db.Column(db.Integer, db.ForeignKey('clases.id'), nullable=False)
    es_abonado = db.Column(db.Boolean, nullable=False) 
    estado = db.Column(db.String(20), nullable=False, default='confirmada')