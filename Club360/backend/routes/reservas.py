from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Reserva, Clase, Usuario, ListaEspera, Suspension, Pago
from datetime import datetime, date
import qrcode, io, base64

reservas_bp = Blueprint('reservas', __name__)


def generar_qr(reserva_id):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(f'CLUB360-RESERVA-{reserva_id}')
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode('utf-8')


def crear_reserva_unica(usuario_id, clase_id, tipo, actor_id, metodo_pago=None, monto_pagar=None):
    """Crea una reserva para una clase individual. Retorna (reserva, monto_a_pagar, en_espera)"""
    clase = Clase.query.get(clase_id)
    if not clase:
        return None, 'Clase no encontrada', None
    if clase.cancelada:
        return None, 'Esta clase fue cancelada', None

    now = datetime.utcnow()

    # Verificar suspensión para no abonados
    if tipo == 'no_abonado':
        susp = Suspension.query.filter_by(usuario_id=usuario_id, activa=True, tipo='no_abonado').first()
        if susp:
            return None, 'Cliente suspendido como no abonado', None

    # Verificar cupo → lista de espera
    if clase.cupos_disponibles() <= 0:
        ya = ListaEspera.query.filter_by(
            usuario_id=usuario_id, clase_id=clase_id,
            estado='esperando', mes=now.month, anio=now.year
        ).first()
        if not ya:
            lista = ListaEspera(
                usuario_id=usuario_id, clase_id=clase_id,
                tipo_preferencia=tipo, mes=now.month, anio=now.year
            )
            db.session.add(lista)
            db.session.commit()
            total_espera = ListaEspera.query.filter_by(
                clase_id=clase_id, estado='esperando', mes=now.month, anio=now.year
            ).count()
            return 'espera', lista.to_dict(), total_espera >= 10
        return 'espera_ya', None, None

    # Verificar duplicado
    existente = Reserva.query.filter_by(usuario_id=usuario_id, clase_id=clase_id, estado='activa').first()
    if existente:
        return None, 'Ya existe una reserva activa para esta clase', None

    precio = float(clase.actividad.precio_clase)
    # monto_pagar puede ser 'total' o 'senia'
    if monto_pagar == 'total':
        monto = precio
        senia_pagada = True
    else:  # senia por defecto
        monto = precio * 0.5
        senia_pagada = False

    reserva = Reserva(
        usuario_id=usuario_id, clase_id=clase_id, tipo=tipo,
        mes=clase.fecha.month, anio=clase.fecha.year,
        monto_total=precio, monto_pagado=0, senia_pagada=senia_pagada
    )
    db.session.add(reserva)
    db.session.flush()
    reserva.qr_code = generar_qr(reserva.id)

    # Registrar pago si hay método
    if metodo_pago:
        pago = Pago(
            reserva_id=reserva.id, monto=monto,
            metodo=metodo_pago,
            tipo_pago='senia' if not senia_pagada else 'mensualidad',
            registrado_por=actor_id
        )
        db.session.add(pago)
        reserva.monto_pagado = monto

    db.session.commit()
    return reserva, monto, False


def crear_reserva_interna(data, actor_id):
    """Para inscripción desde empleado/admin — siempre efectivo"""
    clase_id = int(data.get('clase_id'))
    tipo = data.get('tipo', 'no_abonado')
    target_user_id = int(data.get('usuario_id', actor_id))
    monto_pagar = data.get('monto_pagar', 'senia')  # 'senia' o 'total'

    actor = Usuario.query.get(int(actor_id))
    if str(target_user_id) != str(actor_id) and actor.rol not in ('empleado', 'administrador'):
        return jsonify({'error': 'Sin permisos'}), 403

    resultado, extra, alerta = crear_reserva_unica(
        target_user_id, clase_id, tipo, int(actor_id),
        metodo_pago='efectivo', monto_pagar=monto_pagar
    )

    if resultado is None:
        return jsonify({'error': extra}), 400
    if resultado == 'espera':
        return jsonify({'mensaje': 'Sin cupo. Cliente añadido a lista de espera.', 'en_espera': True, 'alerta_admin': alerta}), 200
    if resultado == 'espera_ya':
        return jsonify({'mensaje': 'Ya estaba en lista de espera', 'en_espera': True}), 200

    return jsonify({'reserva': resultado.to_dict(), 'monto_pagado': extra}), 201


@reservas_bp.route('/', methods=['GET'])
@jwt_required()
def get_mis_reservas():
    user_id = get_jwt_identity()
    user = Usuario.query.get(int(user_id))
    target_id = request.args.get('usuario_id')
    if target_id and user.rol in ('empleado', 'administrador'):
        reservas = Reserva.query.filter_by(usuario_id=int(target_id)).order_by(Reserva.fecha_creacion.desc()).all()
    else:
        reservas = Reserva.query.filter_by(usuario_id=int(user_id)).order_by(Reserva.fecha_creacion.desc()).all()
    return jsonify([r.to_dict() for r in reservas]), 200


@reservas_bp.route('/abono', methods=['POST'])
@jwt_required()
def crear_abono():
    """Crea múltiples reservas para todas las clases del mes de un mismo día/horario"""
    user_id = get_jwt_identity()
    data = request.get_json()
    clases_ids = data.get('clases_ids', [])  # IDs de las clases a inscribir
    monto_total = float(data.get('monto_total', 0))
    target_user_id = int(data.get('usuario_id', user_id))
    metodo_pago = data.get('metodo_pago', 'tarjeta_credito')

    actor = Usuario.query.get(int(user_id))
    if str(target_user_id) != str(user_id) and actor.rol not in ('empleado', 'administrador'):
        return jsonify({'error': 'Sin permisos'}), 403

    reservas_creadas = []
    clases_espera = []

    for clase_id in clases_ids:
        resultado, extra, _ = crear_reserva_unica(
            target_user_id, clase_id, 'abonado', int(user_id),
            metodo_pago=metodo_pago, monto_pagar='total'
        )
        if resultado == 'espera' or resultado == 'espera_ya':
            clases_espera.append(clase_id)
        elif resultado is not None:
            reservas_creadas.append(resultado.to_dict())

    return jsonify({
        'reservas_creadas': reservas_creadas,
        'clases_en_espera': clases_espera,
        'total_inscripto': len(reservas_creadas),
        'monto_total': monto_total
    }), 201


@reservas_bp.route('/', methods=['POST'])
@jwt_required()
def crear_reserva():
    """Reserva de clase individual por el cliente"""
    user_id = get_jwt_identity()
    data = request.get_json()
    clase_id = int(data.get('clase_id'))
    tipo = data.get('tipo', 'no_abonado')
    monto_pagar = data.get('monto_pagar', 'senia')  # 'senia' o 'total'
    metodo_pago = data.get('metodo_pago', 'tarjeta_credito')

    resultado, extra, alerta = crear_reserva_unica(
        int(user_id), clase_id, tipo, int(user_id),
        metodo_pago=metodo_pago, monto_pagar=monto_pagar
    )

    if resultado is None:
        return jsonify({'error': extra}), 400
    if resultado == 'espera':
        return jsonify({'mensaje': 'Sin cupo. Fuiste añadido a la lista de espera.', 'en_espera': True, 'alerta_admin': alerta}), 200
    if resultado == 'espera_ya':
        return jsonify({'mensaje': 'Ya estabas en la lista de espera', 'en_espera': True}), 200

    return jsonify({'reserva': resultado.to_dict(), 'monto_a_pagar': extra}), 201


@reservas_bp.route('/<int:reserva_id>', methods=['GET'])
@jwt_required()
def get_reserva(reserva_id):
    user_id = get_jwt_identity()
    reserva = Reserva.query.get_or_404(reserva_id)
    user = Usuario.query.get(int(user_id))
    if reserva.usuario_id != int(user_id) and user.rol not in ('empleado', 'administrador'):
        return jsonify({'error': 'Sin permisos'}), 403
    d = reserva.to_dict()
    d['usuario'] = reserva.cliente.to_dict()
    return jsonify(d), 200


@reservas_bp.route('/<int:reserva_id>/cancelar', methods=['POST'])
@jwt_required()
def cancelar_reserva(reserva_id):
    user_id = get_jwt_identity()
    reserva = Reserva.query.get_or_404(reserva_id)
    user = Usuario.query.get(int(user_id))

    if reserva.usuario_id != int(user_id) and user.rol not in ('empleado', 'administrador'):
        return jsonify({'error': 'Sin permisos'}), 403
    if reserva.estado != 'activa':
        return jsonify({'error': 'La reserva no está activa'}), 400

    reserva.estado = 'cancelada'
    now = datetime.utcnow()
    resultado = {'mensaje': 'Reserva cancelada'}

    if reserva.tipo == 'abonado':
        reserva.cancelaciones_mes = (reserva.cancelaciones_mes or 0) + 1
        if reserva.cancelaciones_mes == 2:
            resultado['advertencia'] = 'Próxima cancelación perderás el beneficio del 20%'
        if reserva.cancelaciones_mes >= 3:
            resultado['perdida_beneficio'] = True
        resultado['info'] = 'Si cancelaste con 48hs de anticipación tenés crédito para el mes siguiente'
    else:
        resultado['info'] = 'Si cancelaste con 24hs de anticipación recuperás la seña'

    # Notificar lista de espera
    lista = ListaEspera.query.filter_by(
        clase_id=reserva.clase_id, estado='esperando', mes=now.month, anio=now.year
    ).order_by(ListaEspera.fecha_inscripcion).first()
    if lista:
        lista.estado = 'notificado'
        resultado['notificado_usuario_id'] = lista.usuario_id

    db.session.commit()
    return jsonify(resultado), 200


@reservas_bp.route('/<int:reserva_id>/pagar', methods=['POST'])
@jwt_required()
def registrar_pago(reserva_id):
    user_id = get_jwt_identity()
    reserva = Reserva.query.get_or_404(reserva_id)
    user = Usuario.query.get(int(user_id))
    data = request.get_json()

    if reserva.usuario_id != int(user_id) and user.rol not in ('empleado', 'administrador'):
        return jsonify({'error': 'Sin permisos'}), 403

    metodo = data.get('metodo')
    monto = float(data.get('monto', 0))
    tipo_pago = data.get('tipo_pago', 'mensualidad')

    if metodo == 'efectivo' and user.rol not in ('empleado', 'administrador'):
        return jsonify({'error': 'El pago en efectivo debe registrarlo un empleado'}), 403

    pago = Pago(
        reserva_id=reserva_id, monto=monto, metodo=metodo,
        tipo_pago=tipo_pago, registrado_por=int(user_id)
    )
    db.session.add(pago)
    reserva.monto_pagado = float(reserva.monto_pagado or 0) + monto
    if monto >= float(reserva.monto_total or 0) * 0.5:
        reserva.senia_pagada = True
    db.session.commit()
    return jsonify({'pago': pago.to_dict(), 'reserva': reserva.to_dict()}), 201


@reservas_bp.route('/<int:reserva_id>/qr', methods=['GET'])
@jwt_required()
def get_qr(reserva_id):
    user_id = get_jwt_identity()
    reserva = Reserva.query.get_or_404(reserva_id)
    if reserva.usuario_id != int(user_id):
        user = Usuario.query.get(int(user_id))
        if user.rol not in ('empleado', 'administrador'):
            return jsonify({'error': 'Sin permisos'}), 403
    return jsonify({'qr_code': reserva.qr_code, 'reserva_id': reserva_id}), 200
