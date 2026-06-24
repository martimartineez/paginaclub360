from datetime import datetime

from email_service import enviar_aviso_cupo_liberado
from models import db, Clase, Credito, ListaEspera, MovimientoFinanciero, Reserva, Turno


MOTIVO_CANCELACION_ADMIN = 'Cancelacion de clase por admin'


def _money(value):
    return round(float(value or 0), 2)


def _clase_datetime(clase):
    return datetime.combine(clase.fecha, clase.hora_inicio)


def _clase_ya_paso(clase, ahora=None):
    ahora = ahora or datetime.now()
    return _clase_datetime(clase) <= ahora


def _horas_hasta_clase(reserva):
    return (_clase_datetime(reserva.clase) - datetime.utcnow()).total_seconds() / 3600


def _crear_credito_si_no_existe(reserva, monto, origen, motivo=None):
    monto = _money(monto)
    if monto <= 0:
        return None

    existente = Credito.query.filter_by(
        usuario_id=reserva.usuario_id,
        reserva_origen_id=reserva.id,
        origen=origen
    ).first()
    if existente:
        if motivo and not existente.motivo:
            existente.motivo = motivo
        return existente

    credito = Credito(
        usuario_id=reserva.usuario_id,
        actividad_id=reserva.clase.actividad_id,
        monto=monto,
        monto_restante=monto,
        origen=origen,
        reserva_origen_id=reserva.id,
        estado='disponible',
        motivo=motivo
    )
    db.session.add(credito)
    return credito


def calcular_valor_clase_abono(reserva):
    monto_reserva = _money(reserva.monto_total)
    if monto_reserva > 0:
        return monto_reserva

    abono = reserva.abono
    if not abono:
        return 0

    reservas = [r for r in abono.reservas if r.tipo == 'abonado']
    if not reservas:
        return 0

    return _money(_money(abono.monto_total) / len(reservas))


def _registrar_movimiento(reserva, tipo, monto, actor_id, credito=None):
    movimiento = MovimientoFinanciero(
        usuario_id=reserva.usuario_id,
        clase_id=reserva.clase_id,
        reserva_id=reserva.id,
        abono_id=reserva.abono_id,
        credito_id=credito.id if credito and credito.id else None,
        tipo=tipo,
        monto=_money(monto),
        motivo=MOTIVO_CANCELACION_ADMIN,
        registrado_por=actor_id
    )
    db.session.add(movimiento)
    return movimiento


def _marcar_reserva_cancelada_por_admin(reserva, actor_id, ahora):
    reserva.estado = 'cancelada'
    reserva.cancelada_por = actor_id
    reserva.motivo_cancelacion = MOTIVO_CANCELACION_ADMIN
    reserva.fecha_cancelacion = ahora


def _cancelar_lista_espera_de_clase(clase_id):
    entradas = (
        ListaEspera.query
        .filter(
            ListaEspera.clase_id == clase_id,
            ListaEspera.estado.in_(('esperando', 'notificado'))
        )
        .all()
    )
    for entrada in entradas:
        entrada.estado = 'rechazado'
    return len(entradas)


def cancelar_clase_por_admin(clase_id, actor_id, ahora=None):
    clase = Clase.query.get(clase_id)
    if not clase:
        raise ValueError('La clase no existe')
    if clase.cancelada:
        raise ValueError('La clase ya esta cancelada')
    if _clase_ya_paso(clase, ahora):
        raise ValueError('No se puede cancelar una clase que ya paso')

    ahora = ahora or datetime.now()
    clase.cancelada = True
    clase.cancelada_fecha = ahora
    clase.cancelada_por = actor_id

    reservas = (
        Reserva.query
        .filter_by(clase_id=clase_id, estado='activa')
        .all()
    )

    resultado = {
        'mensaje': f'Clase del {clase.fecha} cancelada.',
        'reservas_canceladas': 0,
        'reservas_asistidas_omitidas': 0,
        'devolucion_senia': 0,
        'descuento_abonos': 0,
        'creditos_generados': 0,
        'lista_espera_cancelada': 0,
        'movimientos': []
    }

    resultado['lista_espera_cancelada'] = _cancelar_lista_espera_de_clase(clase_id)

    for reserva in reservas:
        if reserva.asistencia_estado()[0] == 'asistida':
            resultado['reservas_asistidas_omitidas'] += 1
            continue

        _marcar_reserva_cancelada_por_admin(reserva, actor_id, ahora)
        resultado['reservas_canceladas'] += 1

        if reserva.tipo == 'no_abonado':
            senia = min(_money(reserva.monto_pagado), _money(reserva.monto_total) * 0.5)
            if senia > 0:
                _registrar_movimiento(reserva, 'devolucion_senia', senia, actor_id)
                resultado['devolucion_senia'] += senia
                resultado['movimientos'].append({
                    'usuario_id': reserva.usuario_id,
                    'reserva_id': reserva.id,
                    'tipo': 'devolucion_senia',
                    'monto': senia
                })
            continue

        valor_clase = calcular_valor_clase_abono(reserva)
        abono = reserva.abono
        if not abono or valor_clase <= 0:
            continue

        abono_pagado = _money(abono.monto_pagado) >= _money(abono.monto_total)
        if abono_pagado:
            credito = _crear_credito_si_no_existe(
                reserva,
                valor_clase,
                'abono_cancelacion',
                motivo=MOTIVO_CANCELACION_ADMIN
            )
            db.session.flush()
            reserva.credito_a_favor = True
            _registrar_movimiento(reserva, 'credito_abono_pagado', valor_clase, actor_id, credito=credito)
            resultado['creditos_generados'] += valor_clase
            resultado['movimientos'].append({
                'usuario_id': reserva.usuario_id,
                'reserva_id': reserva.id,
                'tipo': 'credito_abono_pagado',
                'monto': valor_clase
            })
        else:
            deuda_abono = max(0, _money(abono.monto_total) - _money(abono.monto_pagado))
            descuento = min(valor_clase, deuda_abono)
            if descuento > 0:
                abono.monto_total = max(
                    _money(abono.monto_pagado),
                    _money(abono.monto_total) - descuento
                )
                _registrar_movimiento(reserva, 'descuento_abono_pendiente', descuento, actor_id)
                resultado['descuento_abonos'] += descuento
                resultado['movimientos'].append({
                    'usuario_id': reserva.usuario_id,
                    'reserva_id': reserva.id,
                    'abono_id': abono.id,
                    'tipo': 'descuento_abono_pendiente',
                    'monto': descuento
                })

    resultado['devolucion_senia'] = _money(resultado['devolucion_senia'])
    resultado['descuento_abonos'] = _money(resultado['descuento_abonos'])
    resultado['creditos_generados'] = _money(resultado['creditos_generados'])
    resultado['mensaje'] = (
        f"Clase cancelada. {resultado['reservas_canceladas']} reserva(s) afectada(s), "
        f"${resultado['devolucion_senia']:,.0f} en senias a devolver, "
        f"${resultado['descuento_abonos']:,.0f} descontados de abonos pendientes y "
        f"${resultado['creditos_generados']:,.0f} en creditos generados."
    )
    if resultado['reservas_asistidas_omitidas'] > 0:
        resultado['mensaje'] += f" {resultado['reservas_asistidas_omitidas']} reserva(s) con asistencia no se cancelaron."

    return resultado


def cancelar_turno_por_admin(turno_id, actor_id, desde=None, ahora=None):
    turno = Turno.query.get(turno_id)
    if not turno:
        raise ValueError('El turno no existe')
    if not turno.activo:
        raise ValueError('El turno ya esta cancelado')

    ahora = ahora or datetime.now()
    turno.activo = False
    turno.cancelado_fecha = ahora
    turno.cancelado_por = actor_id
    turno.motivo_cancelacion = MOTIVO_CANCELACION_ADMIN

    desde = desde or ahora.date()
    clases = (
        Clase.query
        .filter_by(turno_id=turno_id, activa=True, cancelada=False)
        .filter(Clase.fecha >= desde)
        .order_by(Clase.fecha, Clase.hora_inicio)
        .all()
    )

    resultado = {
        'mensaje': 'Turno cancelado.',
        'clases_canceladas': 0,
        'reservas_canceladas': 0,
        'devolucion_senia': 0,
        'descuento_abonos': 0,
        'creditos_generados': 0,
        'clases_pasadas_omitidas': 0,
        'reservas_asistidas_omitidas': 0,
        'movimientos': []
    }

    for clase in clases:
        if _clase_ya_paso(clase, ahora):
            resultado['clases_pasadas_omitidas'] += 1
            continue

        parcial = cancelar_clase_por_admin(clase.id, actor_id, ahora=ahora)
        resultado['clases_canceladas'] += 1
        resultado['reservas_canceladas'] += parcial.get('reservas_canceladas', 0)
        resultado['devolucion_senia'] += parcial.get('devolucion_senia', 0)
        resultado['descuento_abonos'] += parcial.get('descuento_abonos', 0)
        resultado['creditos_generados'] += parcial.get('creditos_generados', 0)
        resultado['reservas_asistidas_omitidas'] += parcial.get('reservas_asistidas_omitidas', 0)
        resultado['movimientos'].extend(parcial.get('movimientos', []))

    resultado['devolucion_senia'] = _money(resultado['devolucion_senia'])
    resultado['descuento_abonos'] = _money(resultado['descuento_abonos'])
    resultado['creditos_generados'] = _money(resultado['creditos_generados'])
    resultado['mensaje'] = (
        f"Turno cancelado. {resultado['clases_canceladas']} clase(s) futura(s) cancelada(s), "
        f"{resultado['reservas_canceladas']} reserva(s) afectada(s), "
        f"${resultado['devolucion_senia']:,.0f} en senias a devolver, "
        f"${resultado['descuento_abonos']:,.0f} descontados de abonos pendientes y "
        f"${resultado['creditos_generados']:,.0f} en creditos generados."
    )
    if resultado['clases_pasadas_omitidas'] > 0:
        resultado['mensaje'] += f" {resultado['clases_pasadas_omitidas']} clase(s) ya pasadas no se cancelaron."
    if resultado['reservas_asistidas_omitidas'] > 0:
        resultado['mensaje'] += f" {resultado['reservas_asistidas_omitidas']} reserva(s) con asistencia no se cancelaron."

    return resultado


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
    if reserva.asistencia_estado()[0] == 'asistida':
        raise ValueError('No se puede cancelar una reserva con asistencia registrada')
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
