from datetime import date, datetime, time, timedelta

from sqlalchemy.exc import IntegrityError

from models import ASISTENCIA_ANTICIPACION_MINUTOS, Abono, Asistencia, Reserva, db
from qr_asistencia import QrAsistenciaInvalido, leer_token_asistencia
from suspensiones_logic import (
    sincronizar_suspensiones_usuario,
    tiene_suspension_abonado_para_clase,
    tiene_suspension_no_abonado,
)


class AsistenciaRechazada(ValueError):
    def __init__(self, mensaje, codigo, status=422, reserva=None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo
        self.status = status
        self.reserva_id = reserva.id if reserva else None
        self.usuario_id = reserva.usuario_id if reserva else None
        self.cliente_nombre = None
        if reserva and reserva.cliente:
            self.cliente_nombre = f'{reserva.cliente.nombre} {reserva.cliente.apellido}'


def _money(value):
    return round(float(value or 0), 2)


def _rechazar(mensaje, codigo, status=422, reserva=None):
    raise AsistenciaRechazada(mensaje, codigo, status, reserva=reserva)


def marcar_falta_reserva(reserva, hoy=None):
    existente = Asistencia.query.filter_by(reserva_id=reserva.id).first()
    if existente:
        return existente

    falta = Asistencia(
        reserva_id=reserva.id,
        fecha=hoy or date.today(),
        presente=False,
        registrado_por=None
    )
    db.session.add(falta)
    return falta


def sincronizar_faltas_reservas(reservas, ahora=None, commit=False):
    ahora = ahora or datetime.now()
    hubo_cambios = False
    for reserva in reservas:
        if reserva.asistencia_vencida(ahora) and not reserva.asistencias:
            marcar_falta_reserva(reserva, hoy=ahora.date())
            hubo_cambios = True

    if hubo_cambios and commit:
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
    return hubo_cambios


def _validar_identidad_qr(payload, reserva):
    if not (
        payload.get('reserva_id') == reserva.id
        and payload.get('usuario_id') == reserva.usuario_id
        and payload.get('clase_id') == reserva.clase_id
        and payload.get('tipo') == reserva.tipo
    ):
        _rechazar(
            'No se puede registrar asistencia: los datos del QR no coinciden con la reserva.',
            'qr_no_coincide',
            400,
            reserva=reserva
        )


def _validar_reserva_general(reserva):
    if reserva.estado == 'cancelada':
        _rechazar(
            'No se puede registrar asistencia: la reserva está cancelada.',
            'reserva_cancelada',
            reserva=reserva
        )
    if not reserva.clase or reserva.clase.cancelada or not reserva.clase.activa:
        _rechazar(
            'No se puede registrar asistencia: la clase está cancelada o inactiva.',
            'clase_inactiva',
            reserva=reserva
        )


def _validar_inicio_ventana_asistencia(reserva, ahora):
    inicio = datetime.combine(reserva.clase.fecha, reserva.clase.hora_inicio)
    apertura = inicio - timedelta(minutes=ASISTENCIA_ANTICIPACION_MINUTOS)
    if ahora < apertura:
        _rechazar(
            'No se puede registrar asistencia: la asistencia se habilita 30 minutos antes del inicio de la clase.',
            'asistencia_demasiado_temprano',
            reserva=reserva
        )


def _validar_clase_suelta(reserva):
    if _money(reserva.monto_pagado) < _money(reserva.monto_total):
        _rechazar(
            'No se puede registrar asistencia: la clase suelta no está pagada completamente.',
            'clase_suelta_pago_pendiente',
            reserva=reserva
        )
    if tiene_suspension_no_abonado(reserva.usuario_id):
        _rechazar(
            'No se puede registrar asistencia: el usuario está suspendido para clases sueltas.',
            'suspension_clase_suelta',
            reserva=reserva
        )


def _validar_abono(reserva, hoy):
    abono = reserva.abono
    if not abono:
        abono = Abono.query.filter_by(
            id=reserva.abono_id,
            usuario_id=reserva.usuario_id
        ).first()
    if not abono:
        _rechazar(
            'No se puede registrar asistencia: la reserva no tiene un abono válido asociado.',
            'abono_invalido',
            reserva=reserva
        )
    if hoy.day >= 11 and _money(abono.monto_pagado) < _money(abono.monto_total):
        _rechazar(
            'No se puede registrar asistencia: el abono no está pagado y ya pasó el día 10.',
            'abono_pago_vencido',
            reserva=reserva
        )
    if tiene_suspension_abonado_para_clase(reserva.usuario_id, reserva.clase):
        _rechazar(
            'No se puede registrar asistencia: el usuario está suspendido para este turno.',
            'suspension_turno',
            reserva=reserva
        )


def registrar_asistencia_qr(qr_data, actor_id, hoy=None, ahora=None):
    hoy_recibido = hoy is not None
    hoy = hoy or date.today()
    ahora = ahora or (datetime.combine(hoy, time.min) if hoy_recibido else datetime.now())
    try:
        payload = leer_token_asistencia(qr_data)
    except QrAsistenciaInvalido as exc:
        _rechazar(f'No se puede registrar asistencia: {exc}', 'qr_invalido', 400)

    reserva = db.session.get(Reserva, int(payload['reserva_id']))
    if not reserva:
        _rechazar(
            'No se puede registrar asistencia: la reserva indicada por el QR no existe.',
            'reserva_inexistente',
            404
        )

    _validar_identidad_qr(payload, reserva)
    sincronizar_suspensiones_usuario(reserva.usuario_id, commit=True)
    _validar_reserva_general(reserva)
    _validar_inicio_ventana_asistencia(reserva, ahora)

    asistencia_existente = Asistencia.query.filter_by(reserva_id=reserva.id).first()
    if asistencia_existente:
        if asistencia_existente.presente:
            _rechazar(
                'No se puede registrar asistencia: esta reserva ya tiene una asistencia registrada.',
                'asistencia_duplicada',
                409,
                reserva=reserva
            )
        _rechazar(
            'No se puede registrar asistencia: esta reserva ya figura como faltó.',
            'asistencia_ausente',
            409,
            reserva=reserva
        )

    if reserva.asistencia_vencida(ahora):
        marcar_falta_reserva(reserva, hoy=ahora.date())
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
        _rechazar(
            'No se puede registrar asistencia: pasaron más de 15 minutos desde el inicio de la clase.',
            'asistencia_fuera_de_tiempo',
            reserva=reserva
        )

    if reserva.tipo == 'no_abonado':
        _validar_clase_suelta(reserva)
    elif reserva.tipo == 'abonado':
        _validar_abono(reserva, hoy)
    else:
        _rechazar(
            'No se puede registrar asistencia: el tipo de reserva no es válido.',
            'tipo_reserva_invalido',
            400,
            reserva=reserva
        )

    asistencia = Asistencia(
        reserva_id=reserva.id,
        fecha=hoy,
        presente=True,
        registrado_por=actor_id
    )
    db.session.add(asistencia)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        _rechazar(
            'No se puede registrar asistencia: esta reserva ya tiene una asistencia registrada.',
            'asistencia_duplicada',
            409,
            reserva=reserva
        )
    return asistencia, reserva
