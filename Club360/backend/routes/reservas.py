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


def calcular_monto(clase, tipo, mes_actual, anio_actual):
    precio_unitario = float(clase.actividad.precio_clase)
    if tipo == 'no_abonado':
        return precio_unitario, precio_unitario * 0.5  # total, senia
    # abonado: calcular clases del mes
    import calendar
    from datetime import date
    dias_map = {'lunes':0,'martes':1,'miercoles':2,'jueves':3,'viernes':4,'sabado':5}
    dia_num = dias_map.get(clase.dia_semana, 0)
    hoy = date.today()
    primer_dia = date(anio_actual, mes_actual, 1)
    ultimo_dia = calendar.monthrange(anio_actual, mes_actual)[1]
    clases_mes = sum(
        1 for d in range(1, ultimo_dia + 1)
        if date(anio_actual, mes_actual, d).weekday() == dia_num
    )
    # Si es mitad de mes (cliente nuevo), calcular clases restantes con 20% descuento
    if hoy.month == mes_actual and hoy.year == anio_actual and hoy.day > 1:
        clases_restantes = sum(
            1 for d in range(hoy.day, ultimo_dia + 1)
            if date(anio_actual, mes_actual, d).weekday() == dia_num
        )
        if clases_restantes < clases_mes and clases_restantes > 1:
            monto = clases_restantes * precio_unitario * 0.8
        else:
            monto = clases_restantes * precio_unitario
    else:
        monto = clases_mes * precio_unitario
    return monto, monto


@reservas_bp.route('/', methods=['GET'])
@jwt_required()
def get_mis_reservas():
    user_id = get_jwt_identity()
    user = Usuario.query.get(int(user_id))
    # Empleados/admins pueden ver reservas de cualquier usuario
    target_id = request.args.get('usuario_id')
    if target_id and user.rol in ('empleado', 'administrador'):
        reservas = Reserva.query.filter_by(usuario_id=int(target_id)).all()
    else:
        reservas = Reserva.query.filter_by(usuario_id=int(user_id)).all()
    return jsonify([r.to_dict() for r in reservas]), 200


@reservas_bp.route('/', methods=['POST'])
@jwt_required()
def crear_reserva():
    user_id = get_jwt_identity()
    data = request.get_json()
    clase_id = data.get('clase_id')
    tipo = data.get('tipo')  # 'abonado' o 'no_abonado'
    target_user_id = data.get('usuario_id', user_id)  # empleado puede crear para otro

    user = Usuario.query.get(int(user_id))
    if str(target_user_id) != str(user_id) and user.rol not in ('empleado', 'administrador'):
        return jsonify({'error': 'Sin permisos'}), 403

    clase = Clase.query.get_or_404(clase_id)
    now = datetime.utcnow()

    # Verificar suspensión
    susp = Suspension.query.filter_by(
        usuario_id=int(target_user_id),
        activa=True,
        tipo=tipo
    ).first()
    if susp and tipo == 'no_abonado':
        return jsonify({'error': 'Cliente suspendido como no abonado. Debe regularizar su deuda.', 'suspension': susp.to_dict()}), 403

    # Verificar cupo
    if clase.cupos_disponibles() <= 0:
        # Agregar a lista de espera automáticamente
        ya_en_espera = ListaEspera.query.filter_by(
            usuario_id=int(target_user_id),
            clase_id=clase_id,
            estado='esperando',
            mes=now.month,
            anio=now.year
        ).first()
        if not ya_en_espera:
            lista = ListaEspera(
                usuario_id=int(target_user_id),
                clase_id=clase_id,
                tipo_preferencia=tipo,
                mes=now.month,
                anio=now.year
            )
            db.session.add(lista)
            db.session.commit()
            # Verificar si hay 10+ en lista
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
        usuario_id=int(target_user_id),
        clase_id=clase_id,
        mes=now.month,
        anio=now.year,
        estado='activa'
    ).first()
    if existente:
        return jsonify({'error': 'Ya tenés una reserva activa para esta clase este mes'}), 409

    monto_total, monto_inicial = calcular_monto(clase, tipo, now.month, now.year)
    reserva = Reserva(
        usuario_id=int(target_user_id),
        clase_id=clase_id,
        tipo=tipo,
        mes=now.month,
        anio=now.year,
        monto_total=monto_total,
        monto_pagado=0,
        senia_pagada=(tipo == 'abonado')
    )
    db.session.add(reserva)
    db.session.flush()
    reserva.qr_code = generar_qr(reserva.id)
    db.session.commit()
    return jsonify({'reserva': reserva.to_dict(), 'monto_a_pagar': monto_inicial}), 201


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

    # Lógica de cancelación por tipo
    now = datetime.utcnow()
    resultado = {'mensaje': 'Reserva cancelada'}

    if reserva.tipo == 'abonado':
        reserva.cancelaciones_mes = (reserva.cancelaciones_mes or 0) + 1
        if reserva.cancelaciones_mes >= 2:
            resultado['advertencia'] = 'Próxima cancelación perderás el beneficio del 20%'
        if reserva.cancelaciones_mes >= 3:
            resultado['perdida_beneficio'] = True
        resultado['credito'] = 'Si cancelaste con 48hs de anticipación, tenés un crédito para el mes siguiente'
    else:  # no_abonado
        resultado['senia'] = 'Si cancelaste con 24hs de anticipación, recuperás la seña'

    # Notificar lista de espera
    lista_abonados = ListaEspera.query.filter_by(
        clase_id=clase.id,
        tipo_preferencia='abonado' if reserva.tipo == 'abonado' else None,
        estado='esperando',
        mes=now.month,
        anio=now.year
    ).order_by(ListaEspera.fecha_inscripcion).first()

    if lista_abonados:
        lista_abonados.estado = 'notificado'
        resultado['notificado'] = lista_abonados.usuario_id

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

    metodo = data.get('metodo')  # 'efectivo' o 'tarjeta_credito'
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
