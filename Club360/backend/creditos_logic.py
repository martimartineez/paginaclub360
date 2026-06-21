from datetime import datetime

from email_service import enviar_aviso_cupo_liberado
from models import db, Credito, ListaEspera


def _money(value):
    return round(float(value or 0), 2)


def _clase_datetime(clase):
    return datetime.combine(clase.fecha, clase.hora_inicio)


def _horas_hasta_clase(reserva):
    return (_clase_datetime(reserva.clase) - datetime.utcnow()).total_seconds() / 3600


def _crear_credito_si_no_existe(reserva, monto, origen):
    monto = _money(monto)
    if monto <= 0:
        return None

    existente = Credito.query.filter_by(
        usuario_id=reserva.usuario_id,
        reserva_origen_id=reserva.id,
        origen=origen
    ).first()
    if existente:
        return existente

    credito = Credito(
        usuario_id=reserva.usuario_id,
        actividad_id=reserva.clase.actividad_id,
        monto=monto,
        monto_restante=monto,
        origen=origen,
        reserva_origen_id=reserva.id,
        estado='disponible'
    )
    db.session.add(credito)
    return credito


def creditos_disponibles(usuario_id, actividad_id):
    return (
        Credito.query
        .filter_by(
            usuario_id=usuario_id,
            actividad_id=actividad_id,
            origen='abono_cancelacion',
            estado='disponible'
        )
        .filter(Credito.monto_restante > 0)
        .order_by(Credito.fecha_creacion.asc())
        .all()
    )


def aplicar_creditos_a_reserva(reserva, monto_objetivo):
    monto_objetivo = _money(monto_objetivo)
    if monto_objetivo <= 0 or reserva.tipo != 'no_abonado' or not reserva.clase:
        return 0

    disponibles = creditos_disponibles(reserva.usuario_id, reserva.clase.actividad_id)
    if not disponibles:
        raise ValueError('No tenes creditos disponibles para esta actividad')

    credito = disponibles[0]
    credito.monto_restante = 0
    credito.reserva_uso_id = reserva.id
    credito.estado = 'usado'
    credito.fecha_uso = datetime.utcnow()

    return monto_objetivo


def _buscar_primero_esperando(clase_id, mes, anio, tipo_preferencia=None):
    query = ListaEspera.query.filter_by(
        clase_id=clase_id,
        estado='esperando',
        mes=mes,
        anio=anio
    )
    if tipo_preferencia:
        query = query.filter_by(tipo_preferencia=tipo_preferencia)
    return query.order_by(ListaEspera.fecha_inscripcion).first()


def siguiente_candidato_lista_espera(clase_id, mes, anio, tipo_origen):
    """Decide a quien le toca el cupo liberado, segun el tipo de la reserva
    que se cancelo:

    - Cancela un ABONADO: se ofrece primero a la lista de abonados. Si esta
      vacia, se ofrece a la lista de no_abonados (fallback).
    - Cancela un NO_ABONADO: se ofrece a la 'lista general', que es la union
      cronologica de abonados + no_abonados (quien se anoto primero, sin
      importar el tipo).

    Si no hay nadie en la lista que corresponda, devuelve None y el cupo
    queda libre para cualquiera.
    """
    print(
        f'[lista_espera] buscando candidato: clase_id={clase_id} mes={mes} '
        f'anio={anio} tipo_origen={tipo_origen!r}',
        flush=True
    )

    if tipo_origen == 'abonado':
        candidato = _buscar_primero_esperando(clase_id, mes, anio, 'abonado')
        if candidato:
            print(f'[lista_espera] candidato encontrado en lista de abonados: usuario_id={candidato.usuario_id} lista_espera_id={candidato.id}', flush=True)
            return candidato
        print('[lista_espera] lista de abonados vacia, probando no_abonados (fallback)', flush=True)
        candidato = _buscar_primero_esperando(clase_id, mes, anio, 'no_abonado')
        if candidato:
            print(f'[lista_espera] candidato encontrado en lista de no_abonados: usuario_id={candidato.usuario_id} lista_espera_id={candidato.id}', flush=True)
        else:
            print('[lista_espera] lista de no_abonados tambien vacia. Nadie a notificar.', flush=True)
        return candidato

    # tipo_origen == 'no_abonado' (o desconocido): lista general combinada
    candidato = _buscar_primero_esperando(clase_id, mes, anio, tipo_preferencia=None)
    if candidato:
        print(f'[lista_espera] candidato encontrado en lista general: usuario_id={candidato.usuario_id} lista_espera_id={candidato.id} tipo_preferencia={candidato.tipo_preferencia}', flush=True)
    else:
        print('[lista_espera] lista general vacia. Nadie a notificar.', flush=True)
    return candidato


def notificar_siguiente_en_lista_espera(clase_id, mes=None, anio=None, tipo_origen=None):
    now = datetime.utcnow()
    mes = mes or now.month
    anio = anio or now.year

    lista = siguiente_candidato_lista_espera(clase_id, mes, anio, tipo_origen)

    if not lista:
        return None

    lista.estado = 'notificado'
    lista.origen_cancelacion = tipo_origen
    mail_enviado = enviar_aviso_cupo_liberado(lista)
    print(
        f'[lista_espera] notificado usuario_id={lista.usuario_id} '
        f'lista_espera_id={lista.id} mail_enviado={mail_enviado}',
        flush=True
    )
    return {
        'notificado_usuario_id': lista.usuario_id,
        'lista_espera_id': lista.id,
        'mail_lista_espera_enviado': mail_enviado
    }


def cancelar_reserva_con_creditos(reserva):
    if reserva.estado != 'activa':
        raise ValueError('La reserva no esta activa')
    if not reserva.clase:
        raise ValueError('La reserva no tiene una clase asociada')
    if _clase_datetime(reserva.clase) <= datetime.utcnow():
        raise ValueError('No se pueden cancelar reservas de clases pasadas')

    horas = _horas_hasta_clase(reserva)
    reserva.estado = 'cancelada'
    resultado = {
        'mensaje': 'Reserva cancelada',
        'credito_generado': 0,
        'descuento_aplicado': 0,
        'devolucion_senia': 0,
        'sin_devolucion': False
    }

    if reserva.tipo == 'abonado':
        cancelaciones_previas = reserva.cancelaciones_mes or 0
        reserva.cancelaciones_mes = cancelaciones_previas + 1

        if reserva.cancelaciones_mes == 3:
            resultado['perdida_beneficio'] = True
            resultado['advertencia'] = 'Esta es tu tercera cancelacion. Perdiste el beneficio del 20% de descuento por abonarte a mitad de mes.'
        elif reserva.cancelaciones_mes == 2:
            resultado['advertencia'] = 'Es tu segunda cancelacion. Si cancelas una vez mas perderas el beneficio del 20% de descuento al abonar a mitad de mes.'

        if horas >= 48:
            monto_reserva = _money(reserva.monto_total)
            abono = reserva.abono
            abono_pagado = abono and _money(abono.monto_pagado) >= _money(abono.monto_total)
            reserva_pagada = _money(reserva.monto_pagado) >= monto_reserva

            if reserva_pagada or abono_pagado:
                credito = _crear_credito_si_no_existe(reserva, monto_reserva, 'abono_cancelacion')
                reserva.credito_a_favor = True
                resultado['credito_generado'] = _money(credito.monto_restante if credito else monto_reserva)
                resultado['info'] = 'Se genero un credito para reservar una clase suelta de la misma actividad.'
            elif abono:
                deuda_abono = max(0, _money(abono.monto_total) - _money(abono.monto_pagado))
                descuento = min(monto_reserva, deuda_abono)
                abono.monto_total = max(_money(abono.monto_pagado), _money(abono.monto_total) - descuento)
                resultado['descuento_aplicado'] = descuento
                resultado['info'] = 'Se desconto esta clase del pago pendiente del abono.'
            else:
                resultado['sin_devolucion'] = True
                resultado['info'] = 'La reserva fue cancelada sin credito ni descuento.'
        else:
            resultado['sin_devolucion'] = True
            resultado['info'] = 'La reserva fue cancelada fuera del plazo de 48 horas. No se genero credito.'
    else:
        if horas >= 24:
            senia = min(_money(reserva.monto_pagado), _money(reserva.monto_total) * 0.5)
            if senia > 0:
                resultado['devolucion_senia'] = senia
                resultado['info'] = 'Faltan 24hs o mas para la clase. Corresponde devolver la senia.'
            else:
                resultado['sin_devolucion'] = True
                resultado['info'] = 'La reserva fue cancelada dentro del plazo, pero no tenia pagos para devolver.'
        else:
            resultado['sin_devolucion'] = True
            resultado['info'] = 'La reserva fue cancelada fuera del plazo de 24 horas. No se genero devolucion.'

    notificacion = notificar_siguiente_en_lista_espera(
        reserva.clase_id,
        mes=reserva.clase.fecha.month,
        anio=reserva.clase.fecha.year,
        tipo_origen=reserva.tipo
    )
    if notificacion:
        resultado.update(notificacion)

    return resultado
