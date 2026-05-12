from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Usuario, Actividad, Asistencia, Reserva, Suspension, Pago
from datetime import datetime

usuarios_bp = Blueprint('usuarios', __name__)
actividades_bp = Blueprint('actividades', __name__)
asistencia_bp = Blueprint('asistencia', __name__)
suspensiones_bp = Blueprint('suspensiones', __name__)


def require_rol(*roles):
    from functools import wraps
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user_id = get_jwt_identity()
            user = Usuario.query.get(int(user_id))
            if not user or user.rol not in roles:
                return jsonify({'error': 'Sin permisos'}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ---- USUARIOS ----
@usuarios_bp.route('/', methods=['GET'])
@jwt_required()
@require_rol('administrador', 'empleado')
def listar_usuarios():
    rol = request.args.get('rol')
    q = request.args.get('q')
    query = Usuario.query
    if rol:
        query = query.filter_by(rol=rol)
    if q:
        query = query.filter(
            (Usuario.nombre.ilike(f'%{q}%')) |
            (Usuario.apellido.ilike(f'%{q}%')) |
            (Usuario.email.ilike(f'%{q}%')) |
            (Usuario.dni.ilike(f'%{q}%'))
        )
    return jsonify([u.to_dict() for u in query.all()]), 200


@usuarios_bp.route('/<int:uid>', methods=['GET'])
@jwt_required()
def get_usuario(uid):
    user_id = get_jwt_identity()
    user = Usuario.query.get(int(user_id))
    if int(user_id) != uid and user.rol not in ('administrador', 'empleado'):
        return jsonify({'error': 'Sin permisos'}), 403
    target = Usuario.query.get_or_404(uid)
    data = target.to_dict()
    # Incluir suspensiones activas
    suspensiones = Suspension.query.filter_by(usuario_id=uid, activa=True).all()
    data['suspensiones_activas'] = [s.to_dict() for s in suspensiones]
    return jsonify(data), 200


@usuarios_bp.route('/<int:uid>', methods=['PUT'])
@jwt_required()
def update_usuario(uid):
    user_id = get_jwt_identity()
    user = Usuario.query.get(int(user_id))
    if int(user_id) != uid and user.rol != 'administrador':
        return jsonify({'error': 'Sin permisos'}), 403
    target = Usuario.query.get_or_404(uid)
    data = request.get_json()
    for field in ['nombre', 'apellido', 'email']:
        if field in data:
            setattr(target, field, data[field])
    db.session.commit()
    return jsonify(target.to_dict()), 200


# ---- ACTIVIDADES ----
@actividades_bp.route('/', methods=['GET'])
def get_actividades():
    actividades = Actividad.query.filter_by(activa=True).all()
    return jsonify([a.to_dict() for a in actividades]), 200


@actividades_bp.route('/', methods=['POST'])
@jwt_required()
@require_rol('administrador')
def create_actividad():
    data = request.get_json()
    act = Actividad(
        nombre=data['nombre'],
        descripcion=data.get('descripcion', ''),
        precio_clase=data['precio_clase']
    )
    db.session.add(act)
    db.session.commit()
    return jsonify(act.to_dict()), 201


@actividades_bp.route('/<int:aid>', methods=['PUT'])
@jwt_required()
@require_rol('administrador')
def update_actividad(aid):
    act = Actividad.query.get_or_404(aid)
    data = request.get_json()
    for field in ['nombre', 'descripcion', 'precio_clase', 'activa']:
        if field in data:
            setattr(act, field, data[field])
    db.session.commit()
    return jsonify(act.to_dict()), 200


# ---- ASISTENCIA ----
@asistencia_bp.route('/registrar', methods=['POST'])
@jwt_required()
@require_rol('empleado', 'administrador')
def registrar_asistencia():
    user_id = get_jwt_identity()
    data = request.get_json()
    qr_data = data.get('qr_data', '')
    # Extraer reserva_id del QR
    if 'CLUB360-RESERVA-' in qr_data:
        reserva_id = int(qr_data.replace('CLUB360-RESERVA-', ''))
    else:
        return jsonify({'error': 'QR inválido'}), 400

    reserva = Reserva.query.get_or_404(reserva_id)
    cliente = reserva.cliente

    estado_cliente = {'nombre': f'{cliente.nombre} {cliente.apellido}', 'alertas': []}

    suspensiones = Suspension.query.filter_by(usuario_id=cliente.id, activa=True).all()
    for s in suspensiones:
        estado_cliente['alertas'].append(f'Suspensión activa ({s.tipo}): deuda ${s.monto_deuda}')

    if reserva.tipo == 'no_abonado' and not reserva.senia_pagada:
        estado_cliente['alertas'].append('Seña pendiente de pago')

    asistencia = Asistencia(
        reserva_id=reserva_id,
        presente=True,
        registrado_por=int(user_id)
    )
    db.session.add(asistencia)
    db.session.commit()

    estado_cliente['asistencia_registrada'] = True
    estado_cliente['reserva'] = reserva.to_dict()
    return jsonify(estado_cliente), 200


# ---- SUSPENSIONES ----
@suspensiones_bp.route('/', methods=['GET'])
@jwt_required()
@require_rol('administrador', 'empleado')
def listar_suspensiones():
    activas = request.args.get('activas', 'true') == 'true'
    suspensiones = Suspension.query.filter_by(activa=activas).all()
    return jsonify([s.to_dict() for s in suspensiones]), 200


@suspensiones_bp.route('/', methods=['POST'])
@jwt_required()
@require_rol('administrador')
def crear_suspension():
    data = request.get_json()
    susp = Suspension(
        usuario_id=data['usuario_id'],
        tipo=data['tipo'],
        motivo=data.get('motivo', ''),
        monto_deuda=data.get('monto_deuda', 0),
        activa=True
    )
    db.session.add(susp)
    db.session.commit()
    return jsonify(susp.to_dict()), 201


@suspensiones_bp.route('/solicitar-retiro/<int:susp_id>', methods=['POST'])
@jwt_required()
def solicitar_retiro(susp_id):
    user_id = get_jwt_identity()
    susp = Suspension.query.get_or_404(susp_id)
    user = Usuario.query.get(int(user_id))

    if susp.usuario_id != int(user_id) and user.rol not in ('empleado', 'administrador'):
        return jsonify({'error': 'Sin permisos'}), 403

    data = request.get_json()
    metodo = data.get('metodo')  # efectivo o tarjeta_credito

    # Levantar suspensión
    susp.activa = False
    susp.fecha_levantamiento = datetime.utcnow()

    # Registrar pago de deuda
    pago = Pago(
        reserva_id=None,
        monto=susp.monto_deuda,
        metodo=metodo,
        tipo_pago='suspension',
        registrado_por=int(user_id)
    )
    # Nota: reserva_id podría ser null en este caso especial
    db.session.add(susp)
    db.session.commit()

    return jsonify({'mensaje': 'Suspensión levantada', 'suspension': susp.to_dict()}), 200
