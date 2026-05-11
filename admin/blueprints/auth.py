from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from models import Usuario, Rol

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/api/login', methods=['POST'])
def login():
    datos = request.get_json()
    usuario = Usuario.query.filter_by(email=datos.get('email')).first()
    
    # Verificamos que el usuario exista y que la contraseña coincida
    if usuario and check_password_hash(usuario.password_hash, datos.get('password')):
        return jsonify({
            'id': usuario.id,
            'nombre': usuario.nombre,
            'apellido': usuario.apellido,
            'email': usuario.email,
            'rol': usuario.rol.nombre
        }), 200
        
    return jsonify({'mensaje': 'Correo o contraseña incorrectos'}), 401

@auth_bp.route('/api/registro', methods=['POST'])
def registro():
    datos = request.get_json()
    
    if Usuario.query.filter_by(email=datos['email']).first() or Usuario.query.filter_by(dni=datos['dni']).first():
        return jsonify({'mensaje': 'El DNI o Correo ya están registrados'}), 400
        
   # Buscamos el rol solicitado o usamos 'Cliente' por defecto
    nombre_rol = datos.get('rol', 'Cliente')
    rol_seleccionado = Rol.query.filter_by(nombre=nombre_rol).first()
    
    nuevo_usuario = Usuario(
        nombre=datos['nombre'],
        apellido=datos['apellido'],
        dni=datos['dni'],
        email=datos['email'],
        password_hash=generate_password_hash(datos['password']),
        rol_id=rol_seleccionado.id
    )
    db.session.add(nuevo_usuario)
    db.session.commit()
    
    return jsonify({'mensaje': f'Registro de {nombre_rol} exitoso.'}), 201

@auth_bp.route('/api/usuario/cambiar-password', methods=['POST'])
def cambiar_password():
    datos = request.get_json()
    usuario_id = datos.get('usuario_id')
    pass_actual = datos.get('password_actual')
    pass_nueva = datos.get('password_nueva')

    # Buscamos al usuario por su ID
    usuario = Usuario.query.get(usuario_id)
    
    if not usuario:
        return jsonify({'mensaje': 'Usuario no encontrado'}), 404

    # Verificamos si la contraseña actual que puso en el formulario es la correcta
    if not check_password_hash(usuario.password_hash, pass_actual):
        return jsonify({'mensaje': 'La contraseña actual es incorrecta'}), 400

    # Si todo está bien, encriptamos la nueva y la guardamos
    usuario.password_hash = generate_password_hash(pass_nueva)
    db.session.commit()
    
    return jsonify({'mensaje': 'Contraseña actualizada con éxito'}), 200