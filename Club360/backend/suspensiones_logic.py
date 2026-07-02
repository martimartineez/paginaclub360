from datetime import date, datetime

from models import db, Abono, Asistencia, Clase, Pago, Reserva, Suspension


RECARGO_SUSPENSION = 0.05
ULTIMO_DIA_PAGO_ABONO = 10


def _money(value):
    return round(float(value or 0), 2)


def _deuda_reserva(reserva):
    return max(0, _money(reserva.monto_total) - _money(reserva.monto_pagado))


def _tiene_asistencia(reserva):
    return Asistencia.query.filter_by(reserva_id=reserva.id, presente=True).first() is not None


def _monto_con_recargo(monto_original):
    monto_original = _money(monto_original)
    recargo = _money(monto_original * RECARGO_SUSPENSION)
    return monto_original, recargo, _money(monto_original + recargo)


def _clase_misma_unidad_turno(suspension, clase):
    if not suspension or not clase:
        return False
    if suspension.turno_id and clase.turno_id:
        return suspension.turno_id == clase.turno_id
    base = suspension.clase
    if not base:
        return False
    return (
        base.actividad_id == clase.actividad_id
        and base.fecha.weekday() == clase.fecha.weekday()
        and base.hora_inicio == clase.hora_inicio
    )


def tiene_suspension_no_abonado(usuario_id):
    return Suspension.query.filter_by(
        usuario_id=usuario_id,
        tipo='no_abonado',
        activa=True
    ).first() is not None


def tiene_suspension_abonado_para_clase(usuario_id, clase):
    if not clase:
        return False
    suspensiones = Suspension.query.filter_by(
        usuario_id=usuario_id,
        tipo='abonado',
        activa=True
    ).all()
    return any(_clase_misma_unidad_turno(s, clase) for s in suspensiones)


def tiene_suspension_abonado_resuelta_para_clase(usuario_id, abono_id, clase):
    return _suspension_abonado_resuelta_para_clase(usuario_id, abono_id, clase) is not None


def reservas_sueltas_con_inasistencia_pendiente(usuario_id):
    hoy = date.today()
    reservas = (
        Reserva.query
        .join(Clase)
        .filter(
            Reserva.usuario_id == usuario_id,
            Reserva.tipo == 'no_abonado',
            Reserva.estado == 'activa',
            Clase.fecha < hoy
        )
        .order_by(Clase.fecha, Clase.hora_inicio)
        .all()
    )
    return [
        r for r in reservas
        if _deuda_reserva(r) > 0
        and not _tiene_asistencia(r)
        and not _cubierta_por_suspension_resuelta(r)
    ]


def _cubierta_por_suspension_resuelta(reserva):
    if not reserva.clase or not reserva.clase.fecha or not reserva.clase.hora_inicio:
        return False

    inicio_clase = datetime.combine(reserva.clase.fecha, reserva.clase.hora_inicio)
    return Suspension.query.filter(
        Suspension.usuario_id == reserva.usuario_id,
        Suspension.tipo == 'no_abonado',
        Suspension.activa.is_(False),
        Suspension.fecha_levantamiento.isnot(None),
        Suspension.fecha_levantamiento >= inicio_clase
    ).first() is not None


def _upsert_suspension_no_abonado(usuario_id):
    reservas = reservas_sueltas_con_inasistencia_pendiente(usuario_id)
    if len(reservas) < 3:
        return None

    monto_original = sum(_deuda_reserva(r) for r in reservas)
    monto_original, recargo, total = _monto_con_recargo(monto_original)

    suspension = Suspension.query.filter_by(
        usuario_id=usuario_id,
        tipo='no_abonado',
        activa=True
    ).first()

    if not suspension:
        suspension = Suspension(
            usuario_id=usuario_id,
            tipo='no_abonado',
            activa=True
        )
        db.session.add(suspension)

    suspension.clase_id = None
    suspension.turno_id = None
    suspension.abono_id = None
    suspension.cantidad_clases = len(reservas)
    suspension.monto_original = monto_original
    suspension.recargo = recargo
    suspension.monto_deuda = total
    suspension.motivo = (
        f'Acumulaste {len(reservas)} inasistencias con pagos pendientes '
        'en clases sueltas.'
    )
    return suspension


def _find_suspension_abonado(usuario_id, abono_id, turno_id, clase_id):
    query = Suspension.query.filter_by(
        usuario_id=usuario_id,
        tipo='abonado',
        activa=True
    )
    if abono_id:
        query = query.filter_by(abono_id=abono_id)
    if turno_id:
        query = query.filter_by(turno_id=turno_id)
    else:
        query = query.filter_by(clase_id=clase_id)
    return query.first()


def _suspension_abonado_resuelta_para_clase(usuario_id, abono_id, clase):
    if not clase:
        return None
    query = Suspension.query.filter_by(
        usuario_id=usuario_id,
        tipo='abonado',
        abono_id=abono_id,
        activa=False
    ).filter(Suspension.fecha_levantamiento.isnot(None))
    return next((s for s in query.all() if _clase_misma_unidad_turno(s, clase)), None)


def _upsert_suspensiones_abonos_vencidos(usuario_id):
    hoy = date.today()
    if hoy.day <= ULTIMO_DIA_PAGO_ABONO:
        return []

    creadas_o_actualizadas = []
    abonos = (
        Abono.query
        .filter(Abono.usuario_id == usuario_id)
        .filter(Abono.monto_pagado < Abono.monto_total)
        .all()
    )

    for abono in abonos:
        reservas = [
            r for r in abono.reservas
            if (
                r.tipo == 'abonado'
                and r.clase
                and r.estado in ('activa', 'suspendida')
                and r.clase.activa
                and not r.clase.cancelada
            )
        ]
        if not reservas:
            continue

        grupos = {}
        for reserva in reservas:
            clase = reserva.clase
            key = (
                'turno',
                clase.turno_id
            ) if clase.turno_id else (
                'horario',
                clase.actividad_id,
                clase.fecha.weekday(),
                clase.hora_inicio.strftime('%H:%M')
            )
            grupos.setdefault(key, []).append(reserva)

        for grupo_reservas in grupos.values():
            representante = grupo_reservas[0].clase
            if not representante:
                continue
            if _suspension_abonado_resuelta_para_clase(usuario_id, abono.id, representante):
                continue

            fin_periodo = date(abono.anio, abono.mes, ULTIMO_DIA_PAGO_ABONO)
            reservas_periodo = [
                r for r in grupo_reservas
                if r.clase.fecha <= fin_periodo
                and r.clase.fecha.month == abono.mes
                and r.clase.fecha.year == abono.anio
            ]
            if not reservas_periodo:
                continue

            monto_periodo = sum(_money(r.monto_total) for r in reservas_periodo)
            monto_original = max(0, monto_periodo - _money(abono.monto_pagado))
            if monto_original <= 0:
                continue

            monto_original, recargo, total = _monto_con_recargo(monto_original)
            turno_id = representante.turno_id
            suspension = _find_suspension_abonado(
                usuario_id,
                abono.id,
                turno_id,
                representante.id
            )

            if not suspension:
                suspension = Suspension(
                    usuario_id=usuario_id,
                    tipo='abonado',
                    abono_id=abono.id,
                    turno_id=turno_id,
                    clase_id=representante.id,
                    activa=True
                )
                db.session.add(suspension)

            suspension.abono_id = abono.id
            suspension.turno_id = turno_id
            suspension.clase_id = representante.id
            suspension.cantidad_clases = len(reservas_periodo)
            suspension.monto_original = monto_original
            suspension.recargo = recargo
            suspension.monto_deuda = total
            suspension.motivo = (
                'Abono pendiente vencido para este turno. '
                f'Incluye {len(reservas_periodo)} clase(s) del periodo de pago.'
            )

            for reserva in grupo_reservas:
                if reserva.estado == 'activa' and reserva.clase.fecha >= hoy:
                    reserva.estado = 'suspendida'

            creadas_o_actualizadas.append(suspension)

    return creadas_o_actualizadas


def sincronizar_suspensiones_usuario(usuario_id, commit=False):
    _upsert_suspension_no_abonado(usuario_id)
    _upsert_suspensiones_abonos_vencidos(usuario_id)
    if commit:
        db.session.commit()


def suspensiones_activas_usuario(usuario_id):
    sincronizar_suspensiones_usuario(usuario_id, commit=True)
    return (
        Suspension.query
        .filter_by(usuario_id=usuario_id, activa=True)
        .order_by(Suspension.fecha_creacion.desc())
        .all()
    )


def resolver_suspension_con_pago(suspension, actor_id, metodo):
    if not suspension.activa:
        raise ValueError('La suspension ya fue resuelta')

    total = _money(suspension.monto_deuda)

    pago = Pago(
        suspension_id=suspension.id,
        abono_id=suspension.abono_id if suspension.tipo == 'abonado' else None,
        monto=total,
        metodo=metodo,
        tipo_pago='suspension',
        registrado_por=actor_id
    )
    db.session.add(pago)

    suspension.activa = False
    suspension.fecha_levantamiento = datetime.utcnow()
    db.session.commit()
    return pago
