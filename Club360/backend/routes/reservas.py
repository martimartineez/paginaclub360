from flask import Blueprint, request, jsonify, redirect
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Reserva, Clase, Usuario, ListaEspera, Suspension, Pago, Abono
from datetime import datetime, date
from creditos_logic import aplicar_creditos_a_reserva, cancelar_reserva_con_creditos, notificar_siguiente_en_lista_espera
from email_service import validar_token_rechazo_lista_espera
from suspensiones_logic import (
    sincronizar_suspensiones_usuario,
    tiene_suspension_abonado_para_clase,
    tiene_suspension_no_abonado,
)
from itsdangerous import BadSignature, SignatureExpired
import os
import qrcode, io, base64

reservas_bp = Blueprint('reservas', __name__)


def redirect_rechazo_lista_espera(estado):
    frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173').rstrip('/')
    return redirect(f'{frontend_url}/lista-espera/rechazo?estado={estado}')


def generar_qr(reserva_id):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(f'CLUB360-RESERVA-{reserva_id}')
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode('utf-8')


def es_periodo_gracia():
    return 1 <= date.today().day <= 10


def puede_diferir_pago_abono():
    return es_periodo_gracia()


def validar_prioridad_lista_espera(clase, usuario_id):
    if not clase or not clase.fecha:
        return None

    entrada_notificada = ListaEspera.query.filter_by(
        clase_id=clase.id,
        estado='notificado',
        mes=clase.fecha.month,
        anio=clase.fecha.year
    ).order_by(ListaEspera.fecha_inscripcion).first()

    if entrada_notificada:
        if entrada_notificada.usuario_id != usuario_id:
            return 'Este cupo esta reservado para la primera persona de la lista de espera.'
        return None

    primera_en_espera = ListaEspera.query.filter_by(
        clase_id=clase.id,
        estado='esperando',
        mes=clase.fecha.month,
        anio=clase.fecha.year
    ).order_by(ListaEspera.fecha_inscripcion).first()

    if primera_en_espera and primera_en_espera.usuario_id != usuario_id:
        return 'Este cupo corresponde a una persona que esta antes en la lista de espera.'

    return None


def anotar_en_lista_espera(usuario_id, clase_id, tipo, mes=None, anio=None):
    now = datetime.utcnow()
    mes = mes or now.month
    anio = anio or now.year

    ya = ListaEspera.query.filter_by(
        usuario_id=usuario_id,
        clase_id=clase_id,
        estado='esperando',
        mes=mes,
        anio=anio
    ).first()

    if ya:
        return 'espera_ya', None, None

    lista = ListaEspera(
        usuario_id=usuario_id,
        clase_id=clase_id,
        tipo_preferencia=tipo,
        mes=mes,
        anio=anio
    )
    db.session.add(lista)
    db.session.commit()
    total_espera = ListaEspera.query.filter_by(
        clase_id=clase_id,
        estado='esperando',
        mes=mes,
        anio=anio
    ).count()
    return 'espera', lista.to_dict(), total_espera >= 10


def crear_reserva_unica(usuario_id, clase_id, tipo, actor_id, metodo_pago=None, monto_pagar=None, usar_credito=False):
    clase = Clase.query.get(clase_id)
    if not clase:
        return None, 'Clase no encontrada', None
    if clase.cancelada:
        return None, 'Esta clase fue cancelada', None

    now = datetime.utcnow()
    sincronizar_suspensiones_usuario(usuario_id, commit=True)

    if tipo == 'no_abonado':
        if tiene_suspension_no_abonado(usuario_id):
            return None, 'Tenes una suspension activa para clases sueltas. Debes pagarla antes de hacer nuevas reservas.', None
    elif tipo == 'abonado' and tiene_suspension_abonado_para_clase(usuario_id, clase):
        return None, 'Tenes una suspension activa para este turno. Debes pagarla antes de volver a abonarte.', None

    if clase.cupos_disponibles() <= 0:
        return anotar_en_lista_espera(usuario_id, clase_id, tipo, now.month, now.year)

    error_prioridad = validar_prioridad_lista_espera(clase, usuario_id)
    if error_prioridad:
        return anotar_en_lista_espera(usuario_id, clase_id, tipo, clase.fecha.month, clase.fecha.year)

    existente = Reserva.query.filter_by(usuario_id=usuario_id, clase_id=clase_id, estado='activa').first()
    if existente:
        return None, 'Ya existe una reserva activa para esta clase', None

    precio = clase.get_precio()

    if monto_pagar == 'total':
        monto = precio
        senia_pagada = True
    else:
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

    try:
        monto_cubierto_por_credito = aplicar_creditos_a_reserva(reserva, monto) if tipo == 'no_abonado' and usar_credito else 0
    except ValueError as exc:
        db.session.rollback()
        return None, str(exc), None
    monto_cobrar = max(0, round(float(monto or 0) - float(monto_cubierto_por_credito or 0), 2))

    if metodo_pago and monto_cobrar > 0:
        pago = Pago(
            reserva_id=reserva.id, monto=monto_cobrar,
            metodo=metodo_pago,
            tipo_pago='senia' if not senia_pagada else 'mensualidad',
            registrado_por=actor_id
        )
        db.session.add(pago)
    reserva.monto_pagado = round(float(monto_cubierto_por_credito or 0) + (monto_cobrar if metodo_pago else 0), 2)
    if reserva.monto_pagado >= float(reserva.monto_total or 0) * 0.5:
        reserva.senia_pagada = True

    entrada_lista = ListaEspera.query.filter(
        ListaEspera.usuario_id == usuario_id,
        ListaEspera.clase_id == clase_id,
        ListaEspera.estado.in_(('esperando', 'notificado'))
    ).first()
    if entrada_lista:
        entrada_lista.estado = 'aceptado'

    db.session.commit()
    return reserva, {
        'monto_a_pagar': monto_cobrar,
        'credito_usado': 1 if monto_cubierto_por_credito else 0
    }, False


def crear_reserva_interna(data, actor_id):
    target_user_id = int(data.get('usuario_id'))
    clase_id = int(data.get('clase_id'))
    tipo = data.get('tipo', 'no_abonado')
    monto_pagar = data.get('monto_pagar', 'senia')
    metodo_pago = data.get('metodo_pago', 'efectivo')
    usar_credito = data.get('usar_credito', False)

    resultado, extra, alerta = crear_reserva_unica(
        target_user_id,
        clase_id,
        tipo,
        int(actor_id),
        metodo_pago=metodo_pago,
        monto_pagar=monto_pagar,
        usar_credito=usar_credito
    )

    if resultado is None:
        return jsonify({'error': extra}), 400
    if resultado == 'espera':
        return jsonify({'mensaje': 'Sin cupo. Cliente anadido a la lista de espera.', 'en_espera': True, 'alerta_admin': alerta}), 200
    if resultado == 'espera_ya':
        return jsonify({'mensaje': 'El cliente ya estaba en la lista de espera', 'en_espera': True}), 200

    pago_info = extra if isinstance(extra, dict) else {'monto_a_pagar': extra, 'credito_usado': 0}
    return jsonify({'reserva': resultado.to_dict(), **pago_info}), 201


@reservas_bp.route('/lista-espera/<int:lista_espera_id>/rechazar', methods=['GET'])
def rechazar_cupo_lista_espera(lista_espera_id):
    token = request.args.get('token')
    if not token:
        return redirect_rechazo_lista_espera('invalido')

    try:
        payload = validar_token_rechazo_lista_espera(token)
    except SignatureExpired:
        return redirect_rechazo_lista_espera('expirado')
    except BadSignature:
        return redirect_rechazo_lista_espera('invalido')

    lista = db.session.get(ListaEspera, lista_espera_id)
    if not lista:
        return redirect_rechazo_lista_espera('invalido')
    if (
        payload.get('lista_espera_id') != lista.id or
        payload.get('usuario_id') != lista.usuario_id or
        payload.get('clase_id') != lista.clase_id
    ):
        return redirect_rechazo_lista_espera('invalido')

    if lista.estado == 'rechazado':
        return redirect_rechazo_lista_espera('ya_rechazado')
    if lista.estado != 'notificado':
        return redirect_rechazo_lista_espera('no_pendiente')

    reserva_activa = Reserva.query.filter_by(
        usuario_id=lista.usuario_id,
        clase_id=lista.clase_id,
        estado='activa'
    ).first()
    if reserva_activa:
        return redirect_rechazo_lista_espera('ya_reservado')

    lista.estado = 'rechazado'

    if lista.clase and lista.clase.cupos_disponibles() > 0:
        notificar_siguiente_en_lista_espera(
            lista.clase_id,
            mes=lista.mes,
            anio=lista.anio
        )

    db.session.commit()
    return redirect_rechazo_lista_espera('ok')


@reservas_bp.route('/mis-lista-espera', methods=['GET'])
@jwt_required()
def get_mis_lista_espera():
    user_id = int(get_jwt_identity())
    entradas = ListaEspera.query.filter_by(
        usuario_id=user_id, estado='esperando'
    ).order_by(ListaEspera.fecha_inscripcion.desc()).all()
    return jsonify([e.to_dict() for e in entradas]), 200


@reservas_bp.route('/', methods=['GET'])
@jwt_required()
def get_mis_reservas():
    user_id = get_jwt_identity()
    user = Usuario.query.get(int(user_id))
    target_id = request.args.get('usuario_id')
    if target_id and user.rol in ('empleado', 'administrador'):
        sincronizar_suspensiones_usuario(int(target_id), commit=True)
        reservas = Reserva.query.filter_by(usuario_id=int(target_id)).order_by(Reserva.fecha_creacion.desc()).all()
    else:
        sincronizar_suspensiones_usuario(int(user_id), commit=True)
        reservas = Reserva.query.filter_by(usuario_id=int(user_id)).order_by(Reserva.fecha_creacion.desc()).all()
    return jsonify([r.to_dict() for r in reservas]), 200


@reservas_bp.route('/pagos-resumen', methods=['GET'])
@jwt_required()
def get_pagos_resumen():
    user_id = int(get_jwt_identity())
    hoy = date.today()
    sincronizar_suspensiones_usuario(user_id, commit=True)

    pendientes = []
    pagados = []

    # 1. Procesamos los Abonos Agrupados
    abonos = Abono.query.filter_by(usuario_id=user_id).order_by(Abono.fecha_creacion.desc()).all()
    for abono in abonos:
        if not abono.reservas:
            continue
        monto_total = float(abono.monto_total or 0)
        monto_pagado = float(abono.monto_pagado or 0)
        deuda = max(0, monto_total - monto_pagado)

        # Usamos la primera clase del abono para extraer día y horario descriptivo en la interfaz
        primera_reserva = abono.reservas[0] if abono.reservas else None
        clase = primera_reserva.clase if primera_reserva else None

        item = {
            'abono_id': abono.id,
            'tipo': 'abonado',
            'actividad': abono.actividad.nombre if abono.actividad else 'Actividad',
            'fecha_clase': clase.fecha.isoformat() if clase else None,
            'dia_semana': clase.dia_semana_str() if clase else '',
            'hora_inicio': clase.hora_inicio.strftime('%H:%M') if clase and clase.hora_inicio else '',
            'monto_total': monto_total,
            'monto_pagado': monto_pagado,
            'deuda': deuda,
            'mes': abono.mes,
            'anio': abono.anio,
            'fecha_creacion': abono.fecha_creacion.isoformat() if abono.fecha_creacion else None,
            'vence_dia_10': deuda > 0 and hoy.day <= 10,
            'deuda_label': f'Abono pendiente — ${deuda:,.0f}' if deuda > 0 else 'Pagado'
        }

        if deuda > 0:
            pendientes.append(item)
        else:
            pagados.append(item)

    # 2. Procesamos únicamente las Reservas Sueltas ('no_abonado')
    reservas_sueltas = Reserva.query.filter_by(usuario_id=user_id, tipo='no_abonado').order_by(Reserva.fecha_creacion.desc()).all()
    for r in reservas_sueltas:
        if r.estado == 'cancelada' and float(r.monto_pagado or 0) == 0:
            continue

        monto_pagado = float(r.monto_pagado or 0)
        monto_total = float(r.monto_total or 0)
        deuda = max(0, monto_total - monto_pagado)
        clase = r.clase

        item = {
            'reserva_id': r.id,
            'clase_id': r.clase_id,
            'tipo': r.tipo,
            'estado': r.estado,
            'actividad': clase.actividad.nombre if clase and clase.actividad else '',
            'fecha_clase': clase.fecha.isoformat() if clase else None,
            'dia_semana': clase.dia_semana_str() if clase else '',
            'hora_inicio': clase.hora_inicio.strftime('%H:%M') if clase and clase.hora_inicio else '',
            'monto_total': monto_total,
            'monto_pagado': monto_pagado,
            'deuda': deuda,
            'senia_pagada': r.senia_pagada,
            'mes': r.mes,
            'anio': r.anio,
            'fecha_creacion': r.fecha_creacion.isoformat() if r.fecha_creacion else None,
            'qr_code': r.qr_code,
        }

        if r.estado == 'cancelada':
            pagados.append(item)
            continue

        if not r.senia_pagada or deuda > 0:
            if r.senia_pagada and deuda > 0:
                item['deuda_label'] = f'Restante (50%) — ${deuda:,.0f}'
            else:
                item['deuda_label'] = f'Seña pendiente — ${deuda * 0.5:,.0f} o total ${monto_total:,.0f}'
            pendientes.append(item)
        else:
            item['deuda_label'] = 'Pagado'
            pagados.append(item)

    return jsonify({'pendientes': pendientes, 'pagados': pagados}), 200


@reservas_bp.route('/abono', methods=['POST'])
@jwt_required()
def crear_abono():
    user_id = get_jwt_identity()
    data = request.get_json()
    clases_ids = data.get('clases_ids', [])
    monto_total = float(data.get('monto_total', 0))
    target_user_id = int(data.get('usuario_id', user_id))
    metodo_pago = data.get('metodo_pago', 'tarjeta_credito')
    aplicar_descuento = data.get('aplicar_descuento', False)
    pago_diferido = data.get('pago_diferido', False)

    if aplicar_descuento:
        reservas_abonado = Reserva.query.filter_by(usuario_id=target_user_id, tipo='abonado').all()
        cancelaciones_totales = sum(r.cancelaciones_mes or 0 for r in reservas_abonado)
        if cancelaciones_totales >= 3:
            aplicar_descuento = False

    actor = Usuario.query.get(int(user_id))
    if str(target_user_id) != str(user_id) and actor.rol not in ('empleado', 'administrador'):
        return jsonify({'error': 'Sin permisos'}), 403

    # Buscamos la primera clase válida para mapear la actividad correspondiente del Abono
    primer_clase = None
    if clases_ids:
        primer_clase = Clase.query.get(clases_ids[0])
    if not primer_clase:
        return jsonify({'error': 'No se enviaron clases válidas para el abono.'}), 400

    sincronizar_suspensiones_usuario(target_user_id, commit=True)
    if tiene_suspension_abonado_para_clase(target_user_id, primer_clase):
        return jsonify({'error': 'El cliente tiene una suspension activa para este turno'}), 403

    # 1. Creamos la entidad padre Abono
    nuevo_abono = Abono(
        usuario_id=target_user_id,
        actividad_id=primer_clase.actividad_id,
        mes=primer_clase.fecha.month,
        anio=primer_clase.fecha.year,
        monto_total=monto_total,
        monto_pagado=0
    )
    db.session.add(nuevo_abono)
    db.session.flush()

    reservas_creadas = []
    clases_en_espera = []
    clases_ya_inscripto = []

    # 2. Iteramos y asociamos las reservas hijas
    for clase_id in clases_ids:
        clase = Clase.query.get(clase_id)
        if not clase or clase.cancelada:
            continue
        if tiene_suspension_abonado_para_clase(target_user_id, clase):
            continue

        existente = Reserva.query.filter_by(usuario_id=target_user_id, clase_id=clase_id, estado='activa').first()
        if existente:
            clases_ya_inscripto.append(clase_id)
            continue

        error_prioridad = validar_prioridad_lista_espera(clase, target_user_id)
        if clase.cupos_disponibles() > 0 and error_prioridad:
            anotar_en_lista_espera(
                target_user_id,
                clase_id,
                'abonado',
                clase.fecha.month,
                clase.fecha.year
            )
            clases_en_espera.append(clase_id)
            continue

        if clase.cupos_disponibles() <= 0:
            now = datetime.utcnow()
            ya = ListaEspera.query.filter_by(
                usuario_id=target_user_id, clase_id=clase_id,
                estado='esperando', mes=now.month, anio=now.year
            ).first()
            if not ya:
                lista = ListaEspera(
                    usuario_id=target_user_id, clase_id=clase_id,
                    tipo_preferencia='abonado', mes=now.month, anio=now.year
                )
                db.session.add(lista)
            clases_en_espera.append(clase_id)
            continue

        precio = clase.get_precio()
        if aplicar_descuento:
            precio = precio * 0.8

        reserva = Reserva(
            usuario_id=target_user_id, clase_id=clase_id, tipo='abonado',
            mes=clase.fecha.month, anio=clase.fecha.year,
            monto_total=precio, monto_pagado=0, senia_pagada=True,
            abono_id=nuevo_abono.id  # <-- Vinculada al abono
        )
        db.session.add(reserva)
        db.session.flush()
        reserva.qr_code = generar_qr(reserva.id)
        entrada_lista = ListaEspera.query.filter(
            ListaEspera.usuario_id == target_user_id,
            ListaEspera.clase_id == clase_id,
            ListaEspera.estado.in_(('esperando', 'notificado'))
        ).first()
        if entrada_lista:
            entrada_lista.estado = 'aceptado'
        reservas_creadas.append(reserva)

    pago_diferido_permitido = puede_diferir_pago_abono()
    pago_diferido = bool(pago_diferido and pago_diferido_permitido)

    if reservas_creadas and not pago_diferido and not metodo_pago:
        db.session.rollback()
        return jsonify({'error': 'Estas fuera del periodo de pago del 1 al 10. El abono debe abonarse en el momento.'}), 400

    # 3. Si no es diferido por periodo de gracia, se cobra el abono completo en el momento
    if not pago_diferido and metodo_pago and reservas_creadas:
        pago = Pago(
            abono_id=nuevo_abono.id,
            monto=monto_total,
            metodo=metodo_pago,
            tipo_pago='mensualidad',
            registrado_por=int(user_id)
        )
        db.session.add(pago)
        nuevo_abono.monto_pagado = monto_total

        for r in reservas_creadas:
            r.monto_pagado = r.monto_total
            # Opcional: si considerás que ya está saldado el total
            r.senia_pagada = True

    if not reservas_creadas:
        db.session.delete(nuevo_abono)

    db.session.commit()

    return jsonify({
        'reservas_creadas': [r.to_dict() for r in reservas_creadas],
        'clases_en_espera': clases_en_espera,
        'clases_ya_inscripto': clases_ya_inscripto,
        'total_inscripto': len(reservas_creadas),
        'monto_total': monto_total,
        'pago_diferido': pago_diferido,
        'abono_id': nuevo_abono.id
    }), 201


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


@reservas_bp.route('/abono/<int:abono_id>/pagar', methods=['POST'])
@jwt_required()
def registrar_pago_abono(abono_id):
    """Nuevo endpoint exclusivo para pagar deudas globales de abono completo"""
    user_id = get_jwt_identity()
    abono = Abono.query.get_or_404(abono_id)
    user = Usuario.query.get(int(user_id))
    data = request.get_json()

    if abono.usuario_id != int(user_id) and user.rol not in ('empleado', 'administrador'):
        return jsonify({'error': 'Sin permisos'}), 403

    metodo = data.get('metodo')
    monto = float(data.get('monto', 0))

    if metodo == 'efectivo' and user.rol not in ('empleado', 'administrador'):
        return jsonify({'error': 'El pago en efectivo debe registrarlo un empleado'}), 403

    pago = Pago(
        abono_id=abono_id, monto=monto, metodo=metodo,
        tipo_pago='mensualidad', registrado_por=int(user_id)
    )
    db.session.add(pago)
    abono.monto_pagado = float(abono.monto_pagado or 0) + monto

    if abono.monto_pagado >= abono.monto_total:
        for r in abono.reservas:
            r.monto_pagado = r.monto_total
            if r.estado == 'suspendida':
                r.estado = 'activa'
        suspensiones = Suspension.query.filter_by(
            abono_id=abono.id,
            tipo='abonado',
            activa=True
        ).all()
        for susp in suspensiones:
            susp.activa = False
            susp.fecha_levantamiento = datetime.utcnow()

    db.session.commit()
    return jsonify({'pago': pago.to_dict(), 'abono': abono.to_dict()}), 201


@reservas_bp.route('/', methods=['POST'])
@jwt_required()
def crear_reserva():
    user_id = get_jwt_identity()
    data = request.get_json()
    clase_id = int(data.get('clase_id'))
    tipo = data.get('tipo', 'no_abonado')
    monto_pagar = data.get('monto_pagar', 'senia')
    metodo_pago = data.get('metodo_pago', 'tarjeta_credito')
    usar_credito = data.get('usar_credito', False)

    resultado, extra, alerta = crear_reserva_unica(
        int(user_id), clase_id, tipo, int(user_id),
        metodo_pago=metodo_pago, monto_pagar=monto_pagar, usar_credito=usar_credito
    )

    if resultado is None:
        return jsonify({'error': extra}), 400
    if resultado == 'espera':
        return jsonify({'mensaje': 'Sin cupo. Fuiste añadido a la lista de espera.', 'en_espera': True, 'alerta_admin': alerta}), 200
    if resultado == 'espera_ya':
        return jsonify({'mensaje': 'Ya estabas en la lista de espera', 'en_espera': True}), 200

    pago_info = extra if isinstance(extra, dict) else {'monto_a_pagar': extra, 'credito_usado': 0}
    return jsonify({'reserva': resultado.to_dict(), **pago_info}), 201


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
    try:
        resultado = cancelar_reserva_con_creditos(reserva)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    db.session.commit()
    return jsonify(resultado), 200

    if reserva.estado != 'activa':
        return jsonify({'error': 'La reserva no está activa'}), 400

    reserva.estado = 'cancelada'
    now = datetime.utcnow()
    resultado = {'mensaje': 'Reserva cancelada'}

    if reserva.tipo == 'abonado':
        cancelaciones_previas = reserva.cancelaciones_mes or 0
        reserva.cancelaciones_mes = cancelaciones_previas + 1
        if reserva.cancelaciones_mes == 3:
            resultado['perdida_beneficio'] = True
            resultado['advertencia'] = '⚠️ Esta es tu tercera cancelación. Perdiste el beneficio del 20% de descuento por abonarte a mitad de mes.'
        elif reserva.cancelaciones_mes == 2:
            resultado['advertencia'] = '⚠️ Es tu segunda cancelación. Si cancelás una vez más perderás el beneficio del 20% de descuento al abonar a mitad de mes.'
        resultado['info'] = 'Si cancelaste con 48hs de anticipación tenés crédito para el mes siguiente'
    else:
        resultado['info'] = 'Si cancelaste con 24hs de anticipación recuperás la seña'

    lista = ListaEspera.query.filter_by(
        clase_id=reserva.clase_id, estado='esperando', mes=now.month, anio=now.year
    ).order_by(ListaEspera.fecha_inscripcion).first()
    if lista:
        lista.estado = 'notificado'
        resultado['notificado_usuario_id'] = lista.usuario_id

    db.session.commit()
    return jsonify(resultado), 200


@reservas_bp.route('/cliente/<int:uid>/cancelar/<int:reserva_id>', methods=['POST'])
@jwt_required()
def cancelar_reserva_cliente(uid, reserva_id):
    user_id = get_jwt_identity()
    actor = Usuario.query.get(int(user_id))
    if actor.rol not in ('empleado', 'administrador'):
        return jsonify({'error': 'Sin permisos'}), 403

    reserva = Reserva.query.get_or_404(reserva_id)
    if reserva.usuario_id != uid:
        return jsonify({'error': 'La reserva no pertenece a este cliente'}), 400
    try:
        resultado = cancelar_reserva_con_creditos(reserva)
        resultado['mensaje'] = 'Reserva cancelada por empleado/administrador'
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    db.session.commit()
    return jsonify(resultado), 200
    if reserva.estado != 'activa':
        return jsonify({'error': 'La reserva no está activa'}), 400

    reserva.estado = 'cancelada'
    now = datetime.utcnow()
    resultado = {'mensaje': 'Reserva cancelada por empleado/administrador'}

    if reserva.tipo == 'abonado':
        cancelaciones_previas = reserva.cancelaciones_mes or 0
        reserva.cancelaciones_mes = cancelaciones_previas + 1
        if reserva.cancelaciones_mes == 3:
            resultado['perdida_beneficio'] = True
            resultado['advertencia'] = 'El cliente acumula 3 cancelaciones. Perdió el beneficio del 20%.'
        elif reserva.cancelaciones_mes == 2:
            resultado['advertencia'] = 'El cliente lleva 2 cancelaciones. Una más y pierde el beneficio del 20%.'

    lista = ListaEspera.query.filter_by(
        clase_id=reserva.clase_id, estado='esperando', mes=now.month, anio=now.year
    ).order_by(ListaEspera.fecha_inscripcion).first()
    if lista:
        lista.estado = 'notificado'
        resultado['notificado_usuario_id'] = lista.usuario_id

    db.session.commit()
    return jsonify(resultado), 200


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
