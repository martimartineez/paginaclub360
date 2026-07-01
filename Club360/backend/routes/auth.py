from flask import Blueprint, request, jsonify, current_app
from datetime import date
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, verify_jwt_in_request
from models import db, Usuario

auth_bp = Blueprint('auth', __name__)


def enviar_link_set_password(user):
    from email_service import enviar_mail_recuperacion_password
    from itsdangerous import URLSafeTimedSerializer
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    reset_token = s.dumps({'usuario_id': user.id}, salt='reset-password')
    enviar_mail_recuperacion_password(user, reset_token)


def mensaje_registro_sin_password(rol):
    etiqueta = 'Cliente' if rol == 'cliente' else 'Empleado' if rol == 'empleado' else 'Usuario'
    return f'{etiqueta} registrado correctamente. Se le envio un mail para que establezca su contrasena.'


def tarjeta_vencida(vencimiento, hoy=None):
    if not vencimiento or len(vencimiento) != 5 or vencimiento[2] != '/':
        return True
    try:
        mes = int(vencimiento[:2])
        anio = int(vencimiento[3:])
    except ValueError:
        return True
    if mes < 1 or mes > 12:
        return True

    hoy = hoy or date.today()
    anio_completo = 2000 + anio
    return anio_completo < hoy.year or (anio_completo == hoy.year and mes < hoy.month)


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    required = ['nombre', 'apellido', 'dni', 'email', 'fecha_nacimiento']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Campo {field} requerido'}), 400

    # Validar mayoría de edad (18+)
    try:
        fnac = date.fromisoformat(data['fecha_nacimiento'])
        hoy = date.today()
        edad = hoy.year - fnac.year - ((hoy.month, hoy.day) < (fnac.month, fnac.day))
        if edad < 18:
            return jsonify({'error': 'Debés tener al menos 18 años para registrarte'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Fecha de nacimiento inválida'}), 400

    rol_pedido = data.get('rol', 'cliente')

    # Verificar permisos según quién registra
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
    except Exception:
        user_id = None

    if user_id:
        actor = Usuario.query.get(int(user_id))
        if actor:
            # Empleado solo puede crear clientes
            if actor.rol == 'empleado' and rol_pedido != 'cliente':
                return jsonify({'error': 'Los empleados solo pueden registrar clientes'}), 403
            # Cliente no puede registrar nadie (excepto a sí mismo al registrarse)
            if actor.rol == 'cliente':
                return jsonify({'error': 'Sin permisos para registrar usuarios'}), 403
    else:
        # Sin sesión: solo se puede registrar como cliente
        rol_pedido = 'cliente'

    # Buscar usuario existente por email o DNI
    por_email = Usuario.query.filter_by(email=data['email']).first()
    por_dni = Usuario.query.filter_by(dni=data['dni']).first()

    # Si existe activo → error
    if por_email and por_email.activo:
        return jsonify({'error': 'El email ya está registrado'}), 409
    if por_dni and por_dni.activo:
        return jsonify({'error': 'El DNI ya está registrado'}), 409

    # Si existe pero está desactivado → reactivar
    if por_email and por_dni and por_email.id != por_dni.id:
        return jsonify({'error': 'El email y el DNI pertenecen a cuentas distintas'}), 409

    usuario_existente = por_email or por_dni
    if usuario_existente and not usuario_existente.activo:
        usuario_existente.activo = True
        usuario_existente.nombre = data['nombre']
        usuario_existente.apellido = data['apellido']
        usuario_existente.dni = data['dni']
        usuario_existente.email = data['email']
        usuario_existente.rol = rol_pedido
        password_recibida = data.get('password', '').strip()
        if password_recibida:
            usuario_existente.set_password(password_recibida)
        else:
            import secrets
            usuario_existente.set_password(secrets.token_hex(32))
        if data.get('fecha_nacimiento'):
            usuario_existente.fecha_nacimiento = date.fromisoformat(data['fecha_nacimiento'])
        db.session.commit()
        user = usuario_existente
        if not user_id:
            token = create_access_token(identity=str(user.id))
            return jsonify({'token': token, 'user': user.to_dict()}), 201
        if not password_recibida:
            enviar_link_set_password(user)
            return jsonify({'user': user.to_dict(), 'mensaje': mensaje_registro_sin_password(rol_pedido)}), 201
        return jsonify({'user': user.to_dict(), 'mensaje': f'Usuario registrado como {rol_pedido}'}), 201

    user = Usuario(
        nombre=data['nombre'],
        apellido=data['apellido'],
        dni=data['dni'],
        email=data['email'],
        rol=rol_pedido,
        fecha_nacimiento=date.fromisoformat(data['fecha_nacimiento'])
    )
    password_recibida = data.get('password', '').strip()
    if password_recibida:
        user.set_password(password_recibida)
    else:
        # Empleado/admin registra sin contraseña: asignar clave temporal inutilizable
        import secrets
        user.set_password(secrets.token_hex(32))

    db.session.add(user)
    db.session.commit()

    # Sin sesión → se registró a sí mismo → devolver token para autologin
    if not user_id:
        token = create_access_token(identity=str(user.id))
        return jsonify({'token': token, 'user': user.to_dict()}), 201

    # Con sesión (empleado/admin) y sin contraseña → enviar mail de bienvenida con link para setear password
    if not password_recibida:
        enviar_link_set_password(user)
        return jsonify({'user': user.to_dict(), 'mensaje': mensaje_registro_sin_password(rol_pedido)}), 201

    return jsonify({'user': user.to_dict(), 'mensaje': f'Usuario registrado como {rol_pedido}'}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = Usuario.query.filter_by(email=data.get('email')).first()
    if not user or not user.check_password(data.get('password', '')):
        return jsonify({'error': 'Credenciales inválidas'}), 401
    if not user.activo:
        return jsonify({'error': 'Credenciales inválidas'}), 403
    token = create_access_token(identity=str(user.id))
    return jsonify({'token': token, 'user': user.to_dict()}), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = Usuario.query.get(int(user_id))
    if not user or not user.activo:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    return jsonify(user.to_dict()), 200


@auth_bp.route('/me', methods=['DELETE'])
@jwt_required()
def eliminar_mi_cuenta():
    user_id = get_jwt_identity()
    user = Usuario.query.get(int(user_id))
    if not user or not user.activo:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    if user.rol == 'administrador':
        admins_activos = Usuario.query.filter_by(rol='administrador', activo=True).count()
        if admins_activos <= 1:
            return jsonify({'error': 'Debe quedar al menos un administrador activo'}), 400

    user.activo = False
    db.session.commit()
    return jsonify({'mensaje': 'Cuenta eliminada correctamente'}), 200


@auth_bp.route('/change-password', methods=['PUT'])
@jwt_required()
def change_password():
    user_id = get_jwt_identity()
    user = Usuario.query.get(int(user_id))
    data = request.get_json()
    if not user or not user.activo:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    if not user.check_password(data.get('password_actual', '')):
        return jsonify({'error': 'Contraseña actual incorrecta'}), 400
    nueva = data.get('nueva_password', '')
    if len(nueva) < 8: # Largo de la contraseña
        return jsonify({'error': 'La nueva contraseña debe tener al menos 8 caracteres'}), 400
    user.set_password(nueva)
    db.session.commit()
    return jsonify({'mensaje': 'Contraseña actualizada'}), 200


@auth_bp.route('/tarjetas', methods=['GET'])
@jwt_required()
def get_tarjetas():
    user_id = get_jwt_identity()
    from models import TarjetaCredito
    tarjetas = TarjetaCredito.query.filter_by(usuario_id=int(user_id), activa=True).all()
    return jsonify([t.to_dict() for t in tarjetas]), 200


@auth_bp.route('/tarjetas', methods=['POST'])
@jwt_required()
def agregar_tarjeta():
    user_id = get_jwt_identity()
    data = request.get_json()
    from models import TarjetaCredito

    numero = data.get('numero', '').replace(' ', '').replace('-', '')
    if len(numero) < 13 or not numero.isdigit():
        return jsonify({'error': 'Número de tarjeta inválido'}), 400

    venc = data.get('vencimiento', '')
    if len(venc) != 5 or venc[2] != '/':
        return jsonify({'error': 'Vencimiento inválido (MM/AA)'}), 400
    if tarjeta_vencida(venc):
        return jsonify({'error': 'La tarjeta esta vencida'}), 400

    tarjeta = TarjetaCredito(
        usuario_id=int(user_id),
        ultimos_4=numero[-4:],
        titular=data.get('titular', '').upper(),
        vencimiento=venc,
    )
    db.session.add(tarjeta)
    db.session.commit()
    return jsonify({'tarjeta': tarjeta.to_dict(), 'mensaje': 'Tarjeta agregada'}), 201


@auth_bp.route('/tarjetas/<int:tid>', methods=['DELETE'])
@jwt_required()
def eliminar_tarjeta(tid):
    user_id = get_jwt_identity()
    from models import TarjetaCredito
    t = TarjetaCredito.query.get_or_404(tid)
    if t.usuario_id != int(user_id):
        return jsonify({'error': 'Sin permisos'}), 403
    t.activa = False
    db.session.commit()
    return jsonify({'mensaje': 'Tarjeta eliminada'}), 200


@auth_bp.route('/recuperar-password', methods=['POST'])
def recuperar_password():
    data = request.get_json()
    email = (data.get('email') or '').strip().lower()
    if not email:
        return jsonify({'error': 'Email requerido'}), 400

    user = Usuario.query.filter_by(email=email, activo=True).first()
    # Siempre responder igual para no revelar si el email existe
    if user:
        from email_service import enviar_mail_recuperacion_password
        from itsdangerous import URLSafeTimedSerializer
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        token = s.dumps({'usuario_id': user.id}, salt='reset-password')
        enviar_mail_recuperacion_password(user, token)

    return jsonify({'mensaje': 'Si el email está registrado, vas a recibir un link para restablecer tu contraseña.'}), 200


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
    data = request.get_json()
    token = data.get('token', '')
    nueva = data.get('nueva_password', '')
    confirmar = data.get('confirmar_password', '')

    if not token:
        return jsonify({'error': 'Token requerido'}), 400
    if len(nueva) < 8:
        return jsonify({'error': 'La contraseña debe tener al menos 8 caracteres'}), 400
    if nueva != confirmar:
        return jsonify({'error': 'Las contraseñas no coinciden'}), 400

    try:
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        payload = s.loads(token, salt='reset-password', max_age=3600)  # 1 hora
    except SignatureExpired:
        return jsonify({'error': 'El link expiró. Solicitá uno nuevo.'}), 400
    except BadSignature:
        return jsonify({'error': 'Link inválido.'}), 400

    user = Usuario.query.get(payload.get('usuario_id'))
    if not user or not user.activo:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    user.set_password(nueva)
    db.session.commit()
    return jsonify({'mensaje': 'Contraseña actualizada correctamente.'}), 200
