import base64
import io

import qrcode
from flask import current_app
from itsdangerous import BadSignature, URLSafeSerializer


QR_PREFIX = 'CLUB360-QR:'
QR_SALT = 'club360-asistencia-v1'


class QrAsistenciaInvalido(ValueError):
    pass


def _serializer():
    return URLSafeSerializer(current_app.config['SECRET_KEY'], salt=QR_SALT)


def generar_token_asistencia(reserva):
    return _serializer().dumps({
        'v': 1,
        'reserva_id': reserva.id,
        'usuario_id': reserva.usuario_id,
        'clase_id': reserva.clase_id,
        'tipo': reserva.tipo,
    })


def contenido_qr_asistencia(reserva):
    return f'{QR_PREFIX}{generar_token_asistencia(reserva)}'


def generar_qr_asistencia(reserva):
    qr = qrcode.QRCode(version=None, box_size=8, border=4)
    qr.add_data(contenido_qr_asistencia(reserva))
    qr.make(fit=True)
    imagen = qr.make_image(fill_color='black', back_color='white')
    buffer = io.BytesIO()
    imagen.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def leer_token_asistencia(qr_data):
    contenido = str(qr_data or '').strip()
    if not contenido.startswith(QR_PREFIX):
        raise QrAsistenciaInvalido('El código QR no pertenece a Club 360 o utiliza un formato anterior.')

    token = contenido[len(QR_PREFIX):].strip()
    if not token:
        raise QrAsistenciaInvalido('El código QR está incompleto.')

    try:
        payload = _serializer().loads(token)
    except BadSignature as exc:
        raise QrAsistenciaInvalido('El código QR fue modificado o no es válido.') from exc

    campos = ('reserva_id', 'usuario_id', 'clase_id', 'tipo')
    if payload.get('v') != 1 or any(payload.get(campo) is None for campo in campos):
        raise QrAsistenciaInvalido('El código QR no contiene una reserva válida.')
    return payload
