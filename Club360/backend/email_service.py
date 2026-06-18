import os
import smtplib
import ssl
from email.message import EmailMessage


def _smtp_config():
    host = os.getenv('SMTP_HOST') or os.getenv('MAIL_SERVER')
    port = int(os.getenv('SMTP_PORT') or os.getenv('MAIL_PORT') or 587)
    user = os.getenv('SMTP_USER') or os.getenv('MAIL_USERNAME')
    password = os.getenv('SMTP_PASSWORD') or os.getenv('MAIL_PASSWORD')
    from_email = os.getenv('SMTP_FROM_EMAIL') or os.getenv('MAIL_DEFAULT_SENDER') or user
    use_ssl = (os.getenv('SMTP_USE_SSL') or '').lower() in ('1', 'true', 'yes')
    use_tls = (os.getenv('SMTP_USE_TLS') or 'true').lower() in ('1', 'true', 'yes')

    if not host or not from_email:
        return None

    return {
        'host': host,
        'port': port,
        'user': user,
        'password': password,
        'from_email': from_email,
        'use_ssl': use_ssl,
        'use_tls': use_tls,
    }


def enviar_mail(destinatario, asunto, cuerpo):
    config = _smtp_config()
    if not config:
        print(f'[email] SMTP no configurado. Aviso pendiente para {destinatario}: {asunto}', flush=True)
        return False

    msg = EmailMessage()
    msg['Subject'] = asunto
    msg['From'] = config['from_email']
    msg['To'] = destinatario
    msg.set_content(cuerpo)

    try:
        if config['use_ssl']:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(config['host'], config['port'], context=context) as smtp:
                _login_si_corresponde(smtp, config)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(config['host'], config['port']) as smtp:
                if config['use_tls']:
                    smtp.starttls(context=ssl.create_default_context())
                _login_si_corresponde(smtp, config)
                smtp.send_message(msg)
        print(f'[email] Mail enviado a {destinatario}: {asunto}', flush=True)
        return True
    except Exception as exc:
        print(f'[email] No se pudo enviar mail a {destinatario}: {exc}', flush=True)
        return False


def _login_si_corresponde(smtp, config):
    if config['user'] and config['password']:
        smtp.login(config['user'], config['password'])


def enviar_aviso_cupo_liberado(lista_espera):
    usuario = lista_espera.cliente
    clase = lista_espera.clase
    if not usuario or not usuario.email or not clase:
        print('[email] No se envio aviso de cupo liberado: faltan datos del usuario o de la clase', flush=True)
        return False

    actividad = clase.actividad.nombre if clase.actividad else 'la clase'
    fecha = clase.fecha.strftime('%d/%m/%Y') if clase.fecha else ''
    hora = clase.hora_inicio.strftime('%H:%M') if clase.hora_inicio else ''
    frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173').rstrip('/')
    nombre = usuario.nombre or 'cliente'

    asunto = f'Club360 - Se libero un cupo para {actividad}'
    cuerpo = (
        f'Hola {nombre},\n\n'
        f'Se libero un cupo para {actividad} el {fecha} a las {hora} hs.\n'
        'Entra a Club360 para confirmar tu reserva antes de que el cupo sea tomado por otra persona.\n\n'
        f'{frontend_url}/clases\n\n'
        'Saludos,\n'
        'Club360'
    )

    return enviar_mail(usuario.email, asunto, cuerpo)
