from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Reserva, Clase, Usuario, ListaEspera, Suspension, Pago
from datetime import datetime
import qrcode
import io
import base64

reservas_bp = Blueprint('reservas', __name__)


def generar_qr(reserva_id):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(f'CLUB360-RESERVA-{reserva_id}')
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def calcular_monto(clase, tipo):
    precio_unitario = float(clase.actividad.precio_clase)
    if tipo == 'no_abonado':
        return precio_unitario, precio_unitario * 0.5  # total, senia
    # abonado: precio de una clase (la reserva es por fecha única)
    return precio_unitario, precio_unitario


def crear_reserva_interna(data, actor_id):
    """Lógica compartida de creación de reserva, usada por clientes y empleados"""
    clase_id = data.get('clase_id')
    tipo = data.get('tipo')
    target_user_id = int(data.get('usuario_id', actor_id))

    actor = Usuario.query.get(int(actor_id))
    if str(target_user_id) != str(actor_id) and actor.rol not in ('empleado', 'administrador'):
        return jsonify({'error': 'Sin permisos'}), 403

    clase = Clase.query.get(clase_id)
    if not clase:
        return jsonify({'error': 'Clase no encontrada'}), 404
    if clase.cancelada:
        return jsonify({'error': 'Esta clase fue cancelada'}), 400

    now = datetime.utcnow()

    # Verificar suspensión
    susp = Suspension.query.filter_by(
        usuario_id=target_user_id,
        activa=True,
        tipo=tipo
    ).first()
    if susp and tipo == 'no_abonado':
        return jsonify({
            'error': 'Cliente suspendido como no abonado. Debe regularizar su deuda.',
            'suspension': susp.to_dict()
        }), 403

    # Verificar cupo
    if clase.cupos_disponibles() <= 0:
        ya_en_espera = ListaEspera.query.filter_by(
            usuario_id=target_user_id,
            clase_id=clase_id,
            estado='esperando',
            mes=now.month,
            anio=now.year
        ).first()
        if not ya_en_espera:
            lista = ListaEspera(
                usuario_id=target_user_id,
                clase_id=clase_id,
                tipo_preferencia=tipo,
                mes=now.month,
                anio=now.year
            )
            db.session.add(lista)
            db.session.commit()
            total_espera = ListaEspera.query.filter_by(
                clase_id=clase_id,
                estado='esperando',
                mes=now.month,
                anio=now.year
            ).count()
            return jsonify({
                'mensaje': 'Sin cupo disponible. Fuiste añadido a la lista de espera.',
                'en_espera': True,
                'lista_espera': lista.to_dict(),
                'alerta_admin': total_espera >= 10
            }), 200
        return jsonify({'mensaje': 'Ya estás en la lista de espera', 'en_espera': True}), 200

    # Verificar reserva duplicada
    existente = Reserva.query.filter_by(
        usuario_id=target_user_id,
        clase_id=clase_id,
        estado='activa'
    ).first()
    if existente:
        return jsonify({'error': 'Ya existe una reserva activa para esta clase'}), 409

    monto_total, monto_inicial = calcular_monto(clase, tipo)
    reserva = Reserva(
        usuario_id=target_user_id,
        clase_id=clase_id,
        tipo=tipo,
        mes=clase.fecha.month,
        anio=clase.fecha.year,
        monto_total=monto_total,
        monto_pagado=0,
        senia_pagada=(tipo == 'abonado')
    )
    db.session.add(reserva)
    db.session.flush()
    reserva.qr_code = generar_qr(reserva.id)
    db.session.commit()
    return jsonify({'reserva': reserva.to_dict(), 'monto_a_pagar': monto_inicial}), 201


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


@reservas_bp.route('/', methods=['POST'])
@jwt_required()
def crear_reserva():
    data = request.get_json()
    return crear_reserva_interna(data, get_jwt_identity())


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
    clase = reserva.clase
    now = datetime.utcnow()
    resultado = {'mensaje': 'Reserva cancelada'}

    if reserva.tipo == 'abonado':
        reserva.cancelaciones_mes = (reserva.cancelaciones_mes or 0) + 1
        if reserva.cancelaciones_mes == 2:
            resultado['advertencia'] = 'Próxima cancelación perderás el beneficio del 20%'
        if reserva.cancelaciones_mes >= 3:
            resultado['perdida_beneficio'] = True
        resultado['credito'] = 'Si cancelaste con 48hs de anticipación, tenés un crédito para el mes siguiente'
    else:
        resultado['senia'] = 'Si cancelaste con 24hs de anticipación, recuperás la seña'

    # Notificar primer cliente en lista de espera (abonados primero)
    lista = ListaEspera.query.filter_by(
        clase_id=clase.id,
        estado='esperando',
        mes=now.month,
        anio=now.year
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
        reserva_id=reserva_id,
        monto=monto,
        metodo=metodo,
        tipo_pago=tipo_pago,
        registrado_por=int(user_id)
    )
    db.session.add(pago)
    reserva.monto_pagado = float(reserva.monto_pagado or 0) + monto
    if reserva.tipo == 'no_abonado' and monto >= float(reserva.monto_total or 0) * 0.5:
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
