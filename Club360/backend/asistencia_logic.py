from datetime import date

from sqlalchemy.exc import IntegrityError

from models import Abono, Asistencia, Reserva, db
from qr_asistencia import QrAsistenciaInvalido, leer_token_asistencia
from suspensiones_logic import (
    sincronizar_suspensiones_usuario,
    tiene_suspension_abonado_para_clase,
    tiene_suspension_no_abonado,
)


class AsistenciaRechazada(ValueError):
    def __init__(self, mensaje, codigo, status=422):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo
        self.status = status


def _money(value):
    return round(float(value or 0), 2)


def _rechazar(mensaje, codigo, status=422):
    raise AsistenciaRechazada(mensaje, codigo, status)


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
            400
        )


def _validar_reserva_general(reserva):
    if reserva.estado == 'cancelada':
        _rechazar(
            'No se puede registrar asistencia: la reserva está cancelada.',
            'reserva_cancelada'
        )
    if not reserva.clase or reserva.clase.cancelada or not reserva.clase.activa:
        _rechazar(
            'No se puede registrar asistencia: la clase está cancelada o inactiva.',
            'clase_inactiva'
        )


def _validar_clase_suelta(reserva):
    if _money(reserva.monto_pagado) < _money(reserva.monto_total):
        _rechazar(
            'No se puede registrar asistencia: la clase suelta no está pagada completamente.',
            'clase_suelta_pago_pendiente'
        )
    if tiene_suspension_no_abonado(reserva.usuario_id):
        _rechazar(
            'No se puede registrar asistencia: el usuario está suspendido para clases sueltas.',
            'suspension_clase_suelta'
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
            'abono_invalido'
        )
    if hoy.day >= 11 and _money(abono.monto_pagado) < _money(abono.monto_total):
        _rechazar(
            'No se puede registrar asistencia: el abono no está pagado y ya pasó el día 10.',
            'abono_pago_vencido'
        )
    if tiene_suspension_abonado_para_clase(reserva.usuario_id, reserva.clase):
        _rechazar(
            'No se puede registrar asistencia: el usuario está suspendido para este turno.',
            'suspension_turno'
        )


def registrar_asistencia_qr(qr_data, actor_id, hoy=None):
    hoy = hoy or date.today()
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

    if Asistencia.query.filter_by(reserva_id=reserva.id).first():
        _rechazar(
            'No se puede registrar asistencia: esta reserva ya tiene una asistencia registrada.',
            'asistencia_duplicada',
            409
        )

    if reserva.tipo == 'no_abonado':
        _validar_clase_suelta(reserva)
    elif reserva.tipo == 'abonado':
        _validar_abono(reserva, hoy)
    else:
        _rechazar(
            'No se puede registrar asistencia: el tipo de reserva no es válido.',
            'tipo_reserva_invalido',
            400
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
            409
        )
    return asistencia, reserva
