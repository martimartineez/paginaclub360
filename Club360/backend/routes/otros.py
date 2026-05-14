from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Usuario, Actividad, Asistencia, Reserva, Suspension, Pago, Clase
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
    usuarios = query.all()
    result = []
    for u in usuarios:
        d = u.to_dict()
        suspensiones = Suspension.query.filter_by(usuario_id=u.id, activa=True).all()
        d['suspensiones_activas'] = [s.to_dict() for s in suspensiones]
        result.append(d)
    return jsonify(result), 200


@usuarios_bp.route('/<int:uid>', methods=['GET'])
@jwt_required()
def get_usuario(uid):
    user_id = get_jwt_identity()
    user = Usuario.query.get(int(user_id))
    if int(user_id) != uid and user.rol not in ('administrador', 'empleado'):
        return jsonify({'error': 'Sin permisos'}), 403
    target = Usuario.query.get_or_404(uid)
    data = target.to_dict()
    suspensiones = Suspension.query.filter_by(usuario_id=uid, activa=True).all()
    data['suspensiones_activas'] = [s.to_dict() for s in suspensiones]
    return jsonify(data), 200


@usuarios_bp.route('/<int:uid>/reservas', methods=['GET'])
@jwt_required()
@require_rol('administrador', 'empleado')
def get_reservas_usuario(uid):
    """Ver todas las reservas de un cliente específico"""
    reservas = Reserva.query.filter_by(usuario_id=uid).order_by(Reserva.fecha_creacion.desc()).all()
    result = []
    for r in reservas:
        d = r.to_dict()
        # Incluir senia pendiente
        senia_pendiente = (
            r.tipo == 'no_abonado' and
            not r.senia_pagada and
            r.estado == 'activa'
        )
        d['senia_pendiente'] = senia_pendiente
        d['monto_senia'] = float(r.monto_total or 0) * 0.5 if senia_pendiente else 0
        result.append(d)
    return jsonify(result), 200


@usuarios_bp.route('/<int:uid>/pagar-senia/<int:reserva_id>', methods=['POST'])
@jwt_required()
@require_rol('administrador', 'empleado')
def pagar_senia_empleado(uid, reserva_id):
    """Empleado registra el pago de la seña pendiente de un cliente"""
    user_id = get_jwt_identity()
    reserva = Reserva.query.get_or_404(reserva_id)
    if reserva.usuario_id != uid:
        return jsonify({'error': 'La reserva no pertenece a este usuario'}), 400
    if reserva.senia_pagada:
        return jsonify({'error': 'La seña ya fue pagada'}), 400

    data = request.get_json()
    metodo = data.get('metodo', 'efectivo')
    monto_senia = float(reserva.monto_total or 0) * 0.5

    pago = Pago(
        reserva_id=reserva_id,
        monto=monto_senia,
        metodo=metodo,
        tipo_pago='senia',
        registrado_por=int(user_id)
    )
    db.session.add(pago)
    reserva.senia_pagada = True
    reserva.monto_pagado = float(reserva.monto_pagado or 0) + monto_senia
    db.session.commit()
    return jsonify({'mensaje': 'Seña registrada', 'pago': pago.to_dict(), 'reserva': reserva.to_dict()}), 200


@usuarios_bp.route('/<int:uid>/inscribir', methods=['POST'])
@jwt_required()
@require_rol('administrador', 'empleado')
def inscribir_cliente(uid):
    """Empleado/admin inscribe a un cliente en una clase (siempre en efectivo)"""
    from routes.reservas import crear_reserva_interna
    data = request.get_json()
    data['usuario_id'] = uid
    data['metodo_pago'] = 'efectivo'  # inscripción presencial siempre es efectivo
    return crear_reserva_interna(data, get_jwt_identity())


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
    result = []
    for s in suspensiones:
        d = s.to_dict()
        d['usuario'] = s.usuario.to_dict() if s.usuario else None
        result.append(d)
    return jsonify(result), 200


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
    metodo = data.get('metodo', 'efectivo')

    susp.activa = False
    susp.fecha_levantamiento = datetime.utcnow()
    db.session.commit()

    return jsonify({'mensaje': 'Suspensión levantada', 'suspension': susp.to_dict()}), 200
