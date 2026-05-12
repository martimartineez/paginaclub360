from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models import db, Usuario

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    required = ['nombre', 'apellido', 'dni', 'email', 'password']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Campo {field} requerido'}), 400

    if Usuario.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'El email ya está registrado'}), 409
    if Usuario.query.filter_by(dni=data['dni']).first():
        return jsonify({'error': 'El DNI ya está registrado'}), 409

    user = Usuario(
        nombre=data['nombre'],
        apellido=data['apellido'],
        dni=data['dni'],
        email=data['email'],
        rol=data.get('rol', 'cliente')
    )
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()
    token = create_access_token(identity=str(user.id))
    return jsonify({'token': token, 'user': user.to_dict()}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = Usuario.query.filter_by(email=data.get('email')).first()
    if not user or not user.check_password(data.get('password', '')):
        return jsonify({'error': 'Credenciales inválidas'}), 401
    if not user.activo:
        return jsonify({'error': 'Cuenta desactivada'}), 403
    token = create_access_token(identity=str(user.id))
    return jsonify({'token': token, 'user': user.to_dict()}), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = Usuario.query.get(int(user_id))
    if not user:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    return jsonify(user.to_dict()), 200


@auth_bp.route('/change-password', methods=['PUT'])
@jwt_required()
def change_password():
    user_id = get_jwt_identity()
    user = Usuario.query.get(int(user_id))
    data = request.get_json()
    if not user.check_password(data.get('password_actual', '')):
        return jsonify({'error': 'Contraseña actual incorrecta'}), 400
    user.set_password(data['nueva_password'])
    db.session.commit()
    return jsonify({'mensaje': 'Contraseña actualizada'}), 200
