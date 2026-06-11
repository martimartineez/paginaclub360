from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Usuario, Actividad, Asistencia, Reserva, Suspension, Pago
from suspensiones_logic import (
    resolver_suspension_con_pago,
    sincronizar_suspensiones_usuario,
    suspensiones_activas_usuario,
    tiene_suspension_abonado_para_clase,
)

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
        sincronizar_suspensiones_usuario(u.id)
        d = u.to_dict()
        suspensiones = Suspension.query.filter_by(usuario_id=u.id, activa=True).all()
        d['suspensiones_activas'] = [s.to_dict() for s in suspensiones]
        result.append(d)
    db.session.commit()
    return jsonify(result), 200


@usuarios_bp.route('/<int:uid>', methods=['GET'])
@jwt_required()
def get_usuario(uid):
    user_id = get_jwt_identity()
    user = Usuario.query.get(int(user_id))
    if int(user_id) != uid and user.rol not in ('administrador', 'empleado'):
        return jsonify({'error': 'Sin permisos'}), 403
    target = Usuario.query.get_or_404(uid)
    sincronizar_suspensiones_usuario(uid, commit=True)
    data = target.to_dict()
    suspensiones = Suspension.query.filter_by(usuario_id=uid, activa=True).all()
    data['suspensiones_activas'] = [s.to_dict() for s in suspensiones]
    return jsonify(data), 200


@usuarios_bp.route('/<int:uid>/reservas', methods=['GET'])
@jwt_required()
@require_rol('administrador', 'empleado')
def get_reservas_usuario(uid):
    """Ver todas las reservas de un cliente específico"""
    sincronizar_suspensiones_usuario(uid, commit=True)
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


@usuarios_bp.route('/<int:uid>/borrar', methods=['POST'])
@jwt_required()
@require_rol('administrador', 'empleado')
def borrar_usuario(uid):
    """Borrado lógico de un usuario (desactivar)"""
    user_id = get_jwt_identity()
    actor = Usuario.query.get(int(user_id))
    target = Usuario.query.get_or_404(uid)

    # Empleado solo puede borrar clientes; admin puede borrar clientes y empleados
    if actor.rol == 'empleado' and target.rol != 'cliente':
        return jsonify({'error': 'Los empleados solo pueden borrar clientes'}), 403
    if target.rol == 'administrador':
        return jsonify({'error': 'No se puede borrar un administrador'}), 403
    if not target.activo:
        return jsonify({'error': 'El usuario ya está desactivado'}), 400

    target.activo = False
    db.session.commit()
    return jsonify({'mensaje': f'Usuario {target.nombre} {target.apellido} desactivado correctamente'}), 200


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

    sincronizar_suspensiones_usuario(cliente.id, commit=True)

    if reserva.tipo == 'abonado' and tiene_suspension_abonado_para_clase(cliente.id, reserva.clase):
        return jsonify({'error': 'Cliente suspendido para este turno'}), 403

    if reserva.estado != 'activa':
        return jsonify({'error': 'La reserva no esta activa'}), 400

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

@suspensiones_bp.route('/mis', methods=['GET'])
@jwt_required()
def mis_suspensiones():
    user_id = int(get_jwt_identity())
    suspensiones = suspensiones_activas_usuario(user_id)
    return jsonify([s.to_dict() for s in suspensiones]), 200


@suspensiones_bp.route('/', methods=['GET'])
@jwt_required()
@require_rol('administrador', 'empleado')
def listar_suspensiones():
    activas = request.args.get('activas', 'true') == 'true'
    usuario_id = request.args.get('usuario_id', type=int)
    if usuario_id:
        sincronizar_suspensiones_usuario(usuario_id, commit=True)
    else:
        for usuario in Usuario.query.filter_by(rol='cliente').all():
            sincronizar_suspensiones_usuario(usuario.id)
        db.session.commit()
    query = Suspension.query.filter_by(activa=activas)
    if usuario_id:
        query = query.filter_by(usuario_id=usuario_id)
    suspensiones = query.all()
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
    monto_original = float(data.get('monto_original', data.get('monto_deuda', 0)) or 0)
    recargo = round(monto_original * 0.05, 2)
    susp = Suspension(
        usuario_id=data['usuario_id'],
        tipo=data['tipo'],
        clase_id=data.get('clase_id'),
        turno_id=data.get('turno_id'),
        abono_id=data.get('abono_id'),
        motivo=data.get('motivo', ''),
        cantidad_clases=data.get('cantidad_clases', 0),
        monto_original=monto_original,
        recargo=recargo,
        monto_deuda=round(monto_original + recargo, 2),
        activa=True
    )
    db.session.add(susp)
    db.session.commit()
    return jsonify(susp.to_dict()), 201


@suspensiones_bp.route('/<int:susp_id>/pagar', methods=['POST'])
@jwt_required()
def pagar_suspension(susp_id):
    return _pagar_suspension(susp_id)


@suspensiones_bp.route('/solicitar-retiro/<int:susp_id>', methods=['POST'])
@jwt_required()
def solicitar_retiro(susp_id):
    return _pagar_suspension(susp_id)


def _pagar_suspension(susp_id):
    user_id = get_jwt_identity()
    susp = Suspension.query.get_or_404(susp_id)
    user = Usuario.query.get(int(user_id))

    if susp.usuario_id != int(user_id) and user.rol not in ('empleado', 'administrador'):
        return jsonify({'error': 'Sin permisos'}), 403

    data = request.get_json()
    metodo = data.get('metodo', 'tarjeta_credito')

    if metodo == 'efectivo' and user.rol not in ('empleado', 'administrador'):
        return jsonify({'error': 'El pago en efectivo debe registrarlo un empleado'}), 403

    try:
        pago = resolver_suspension_con_pago(susp, int(user_id), metodo)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    return jsonify({
        'mensaje': 'Suspension pagada y levantada',
        'pago': pago.to_dict(),
        'suspension': susp.to_dict()
    }), 200
