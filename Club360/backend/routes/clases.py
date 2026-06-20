from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Clase, Actividad, Reserva, ListaEspera, Usuario
from datetime import datetime, date
from creditos_logic import notificar_siguiente_en_lista_espera
from suspensiones_logic import sincronizar_suspensiones_usuario, tiene_suspension_abonado_para_clase
import calendar

clases_bp = Blueprint('clases', __name__)


def usuario_id_actual():
    """Toma el usuario real de la sesion (JWT) cuando existe. No confia en
    que el frontend mande un usuario_id por query para verse a si mismo
    como el notificado: un cliente logueado siempre usa su propio id.
    Solo un empleado/administrador puede pedir explicitamente el contexto
    de otro usuario (por ejemplo, para gestionar un abono desde el panel),
    igual que ya permite el resto de la API."""
    try:
        identity = get_jwt_identity()
    except Exception:
        identity = None

    if not identity:
        return None

    propio_id = int(identity)
    target_id = request.args.get('usuario_id', type=int)

    if target_id and target_id != propio_id:
        actor = Usuario.query.get(propio_id)
        if actor and actor.rol in ('empleado', 'administrador'):
            return target_id

    return propio_id


def cupos_disponibles_para_usuario(clase, usuario_id=None):
    cupos = clase.cupos_disponibles()
    if cupos <= 0 or not usuario_id or not clase.fecha:
        return cupos

    notificado = ListaEspera.query.filter_by(
        clase_id=clase.id,
        estado='notificado',
        mes=clase.fecha.month,
        anio=clase.fecha.year
    ).order_by(ListaEspera.fecha_inscripcion).first()

    if notificado and notificado.usuario_id != usuario_id:
        return 0

    return cupos


def require_rol(*roles):
    from functools import wraps
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user_id = get_jwt_identity()
            user = Usuario.query.get(int(user_id))
            if not user or user.rol not in roles:
                return jsonify({'error': 'Sin permisos'}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


@clases_bp.route('/', methods=['GET'])
def get_clases():
    actividad_id = request.args.get('actividad_id', type=int)
    usuario_id = request.args.get('usuario_id', type=int)
    desde = request.args.get('desde')
    hasta = request.args.get('hasta')
    solo_activas = request.args.get('solo_activas', 'true') == 'true'

    query = Clase.query.filter_by(activa=True)
    if solo_activas:
        query = query.filter_by(cancelada=False)
    if actividad_id:
        query = query.filter_by(actividad_id=actividad_id)
    if desde:
        query = query.filter(Clase.fecha >= datetime.strptime(desde, '%Y-%m-%d').date())
    if hasta:
        query = query.filter(Clase.fecha <= datetime.strptime(hasta, '%Y-%m-%d').date())

    clases = query.order_by(Clase.fecha, Clase.hora_inicio).all()
    return jsonify([c.to_dict() for c in clases]), 200


@clases_bp.route('/fechas-disponibles', methods=['GET'])
@jwt_required(optional=True)
def get_fechas_disponibles():
    """Fechas únicas con horarios para clase individual — máximo 1 mes desde hoy"""
    actividad_id = request.args.get('actividad_id', type=int)
    usuario_id = usuario_id_actual()
    if not actividad_id:
        return jsonify({'error': 'actividad_id requerido'}), 400

    hoy = date.today()
    hasta_max = date(hoy.year, hoy.month, calendar.monthrange(hoy.year, hoy.month)[1])
    # Si estamos cerca del fin de mes, extender al mes siguiente para dar margen
    desde_str = request.args.get('desde')
    hasta_str = request.args.get('hasta')
    desde = datetime.strptime(desde_str, '%Y-%m-%d').date() if desde_str else hoy
    hasta = datetime.strptime(hasta_str, '%Y-%m-%d').date() if hasta_str else hasta_max
    # Nunca mostrar clases pasadas
    desde = max(desde, hoy)

    query = Clase.query.filter_by(activa=True, cancelada=False, actividad_id=actividad_id)
    query = query.filter(Clase.fecha >= desde, Clase.fecha <= hasta)
    clases = query.order_by(Clase.fecha, Clase.hora_inicio).all()

    fechas = {}
    for c in clases:
        f = c.fecha.isoformat()
        if f not in fechas:
            fechas[f] = {
                'fecha': f,
                'dia_semana': c.dia_semana_str(),
                'horarios': []
            }
        fechas[f]['horarios'].append({
            'clase_id': c.id,
            'hora_inicio': c.hora_inicio.strftime('%H:%M'),
            'cupos_disponibles': cupos_disponibles_para_usuario(c, usuario_id),
            'cupo_maximo': c.cupo_maximo,
            'precio_clase': float(c.actividad.precio_clase)
        })

    return jsonify(list(fechas.values())), 200


@clases_bp.route('/horarios-disponibles', methods=['GET'])
@jwt_required(optional=True)
def get_horarios_disponibles():
    """Para abonos: combinaciones dia+hora del mes actual, solo desde hoy"""
    actividad_id = request.args.get('actividad_id', type=int)
    usuario_id = usuario_id_actual()
    if not actividad_id:
        return jsonify({'error': 'actividad_id requerido'}), 400

    hoy = date.today()
    ultimo_dia_mes = date(hoy.year, hoy.month, calendar.monthrange(hoy.year, hoy.month)[1])

    clases = Clase.query.filter_by(
        activa=True, cancelada=False, actividad_id=actividad_id
    ).filter(
        Clase.fecha >= hoy,
        Clase.fecha <= ultimo_dia_mes
    ).order_by(Clase.fecha, Clase.hora_inicio).all()

    # Clases donde el usuario ya tiene reserva activa (no cuentan como disponibles para el)
    clases_ya_inscripto = set()
    if usuario_id:
        sincronizar_suspensiones_usuario(usuario_id, commit=True)
        reservas_usuario = Reserva.query.filter_by(
            usuario_id=usuario_id, estado='activa'
        ).all()
        clases_ya_inscripto = {r.clase_id for r in reservas_usuario}

    opciones = {}
    for c in clases:
        if usuario_id and tiene_suspension_abonado_para_clase(usuario_id, c):
            continue
        key = f"{c.fecha.weekday()}_{c.hora_inicio.strftime('%H:%M')}"
        if key not in opciones:
            opciones[key] = {
                'dia_semana': c.dia_semana_str(),
                'dia_semana_num': c.fecha.weekday(),
                'hora_inicio': c.hora_inicio.strftime('%H:%M'),
                'precio_clase': float(c.actividad.precio_clase),
                'clases_mes': []
            }
        opciones[key]['clases_mes'].append({
            'clase_id': c.id,
            'fecha': c.fecha.isoformat(),
            'cupos_disponibles': cupos_disponibles_para_usuario(c, usuario_id),
            'cancelada': c.cancelada,
            'ya_inscripto': c.id in clases_ya_inscripto
        })

    return jsonify(list(opciones.values())), 200


@clases_bp.route('/detalle-abono', methods=['GET'])
@jwt_required(optional=True)
def get_detalle_abono():
    """Clases del mes actual para un abono — solo desde hoy en adelante"""
    actividad_id = request.args.get('actividad_id', type=int)
    dia_semana_num = request.args.get('dia_semana_num', type=int)
    hora_inicio = request.args.get('hora_inicio')
    usuario_id = usuario_id_actual()  # para verificar beneficio

    if actividad_id is None or dia_semana_num is None or not hora_inicio:
        return jsonify({'error': 'Parámetros requeridos: actividad_id, dia_semana_num, hora_inicio'}), 400

    hoy = date.today()
    _, dias_en_mes = calendar.monthrange(hoy.year, hoy.month)
    mitad_mes = dias_en_mes // 2
    ultimo_dia_mes = date(hoy.year, hoy.month, calendar.monthrange(hoy.year, hoy.month)[1])
    hora_obj = datetime.strptime(hora_inicio, '%H:%M').time()

    # Solo clases desde HOY (no pasadas) hasta fin del mes actual
    clases_mes = Clase.query.filter_by(
        activa=True,
        actividad_id=actividad_id,
        hora_inicio=hora_obj
    ).filter(
        Clase.fecha >= hoy,
        Clase.fecha <= ultimo_dia_mes
    ).order_by(Clase.fecha).all()

    clases_mes = [c for c in clases_mes if c.fecha.weekday() == dia_semana_num]

    actividad = Actividad.query.get(actividad_id)
    precio_unitario = float(actividad.precio_clase) if actividad else 0

    # Verificar si el usuario ya está inscripto en alguna de estas clases
    from models import Reserva
    clases_ya_inscripto = set()
    clases_suspendidas = set()
    if usuario_id:
        sincronizar_suspensiones_usuario(usuario_id, commit=True)
        reservas_usuario = Reserva.query.filter_by(
            usuario_id=usuario_id, estado='activa'#, tipo='abonado'
        ).all()
        clases_ya_inscripto = {r.clase_id for r in reservas_usuario}
        clases_suspendidas = {
            c.id for c in clases_mes
            if tiene_suspension_abonado_para_clase(usuario_id, c)
        }

    clases_disponibles = [
        c for c in clases_mes
        if not c.cancelada and cupos_disponibles_para_usuario(c, usuario_id) > 0 and c.id not in clases_ya_inscripto and c.id not in clases_suspendidas
    ]
    clases_ya_en = [c for c in clases_mes if c.id in clases_ya_inscripto]
    total_clases = len(clases_mes)
    total_disponibles = len(clases_disponibles)

    # Detectar en cuáles el usuario ya está en lista de espera
    clases_en_espera_usuario = set()
    if usuario_id:
        from models import ListaEspera as LE
        now = datetime.utcnow()
        esperas = LE.query.filter_by(
            usuario_id=usuario_id,
            estado='esperando',
            mes=now.month,
            anio=now.year
        ).all()
        clases_en_espera_usuario = {e.clase_id for e in esperas}

    # Verificar si el usuario perdió el beneficio por 3+ cancelaciones de abono
    usuario_tiene_beneficio = True
    if usuario_id:
        from models import Reserva as R
        reservas_abonado = R.query.filter_by(usuario_id=usuario_id, tipo='abonado').all()
        cancelaciones_totales = sum(r.cancelaciones_mes or 0 for r in reservas_abonado)
        if cancelaciones_totales >= 3:
            usuario_tiene_beneficio = False

    # Descuento 20% por clase si es mitad de mes, hay más de 1 clase disponible
    # Y el usuario no perdió el beneficio
    es_mitad_de_mes = hoy.day >= mitad_mes
    aplicar_descuento = es_mitad_de_mes and total_disponibles > 1 and usuario_tiene_beneficio
    precio_por_clase = precio_unitario * 0.8 if aplicar_descuento else precio_unitario
    monto_total = precio_por_clase * total_disponibles

    detalle_clases = []
    for c in clases_mes:
        ya_inscripto = c.id in clases_ya_inscripto
        suspendida = c.id in clases_suspendidas
        cupos_usuario = cupos_disponibles_para_usuario(c, usuario_id)
        disponible = not c.cancelada and cupos_usuario > 0 and not ya_inscripto and not suspendida
        sin_cupo = not c.cancelada and cupos_usuario <= 0 and not ya_inscripto
        en_espera = sin_cupo and c.id in clases_en_espera_usuario
        detalle_clases.append({
            'clase_id': c.id,
            'fecha': c.fecha.isoformat(),
            'dia_semana': c.dia_semana_str(),
            'hora_inicio': c.hora_inicio.strftime('%H:%M'),
            'cupos_disponibles': cupos_usuario,
            'cancelada': c.cancelada,
            'ya_inscripto': ya_inscripto,
            'suspendida': suspendida,
            'incluida_en_abono': disponible,
            'en_espera': en_espera,
            'precio_clase': precio_por_clase if disponible else 0
        })

    return jsonify({
        'actividad': actividad.nombre if actividad else '',
        'dia_semana': clases_mes[0].dia_semana_str() if clases_mes else '',
        'hora_inicio': hora_inicio,
        'precio_unitario': precio_unitario,
        'precio_por_clase': precio_por_clase,
        'aplicar_descuento': aplicar_descuento,
        'descuento_pct': 20 if aplicar_descuento else 0,
        'usuario_tiene_beneficio': usuario_tiene_beneficio,
        'total_clases_mes': total_clases,
        'total_disponibles': total_disponibles,
        'ya_inscripto_en': [c.id for c in clases_ya_en],
        'monto_total': monto_total,
        'clases': detalle_clases
    }), 200


@clases_bp.route('/<int:clase_id>', methods=['GET'])
@jwt_required(optional=True)
def get_clase(clase_id):
    clase = Clase.query.get_or_404(clase_id)
    usuario_id = usuario_id_actual()
    data = clase.to_dict()
    data['cupos_disponibles'] = cupos_disponibles_para_usuario(clase, usuario_id)
    return jsonify(data), 200


@clases_bp.route('/', methods=['POST'])
@jwt_required()
@require_rol('administrador')
def create_clase():
    data = request.get_json()
    fecha_str = data.get('fecha')
    if not fecha_str:
        return jsonify({'error': 'La fecha es requerida'}), 400
    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Formato de fecha inválido (YYYY-MM-DD)'}), 400

    hora = datetime.strptime(data['hora_inicio'], '%H:%M').time()
    actividad_id = int(data['actividad_id'])
    cupo_maximo = int(data['cupo_maximo'])

    # Verificar unicidad: misma actividad + fecha + hora
    existente = Clase.query.filter_by(
        actividad_id=actividad_id,
        fecha=fecha,
        hora_inicio=hora
    ).first()

    if existente:
        if existente.activa and not existente.cancelada:
            return jsonify({'error': 'Ya existe una clase activa con esa actividad, fecha y horario'}), 409
        # Reactivar clase cancelada o inactiva
        existente.activa = True
        existente.cancelada = False
        existente.cupo_maximo = cupo_maximo
        db.session.commit()
        return jsonify({**existente.to_dict(), 'reactivada': True,
                        'mensaje': 'La clase fue reactivada correctamente'}), 200

    clase = Clase(
        actividad_id=actividad_id,
        fecha=fecha,
        hora_inicio=hora,
        cupo_maximo=cupo_maximo
    )
    db.session.add(clase)
    db.session.commit()
    return jsonify(clase.to_dict()), 201


@clases_bp.route('/<int:clase_id>', methods=['PUT'])
@jwt_required()
@require_rol('administrador')
def update_clase(clase_id):
    clase = Clase.query.get_or_404(clase_id)
    data = request.get_json()
    cupos_antes = clase.cupos_disponibles()
    resultado = None
    if 'cupo_maximo' in data:
        nuevo_cupo = int(data['cupo_maximo'])
        inscriptos = Reserva.query.filter_by(clase_id=clase_id, estado='activa').count()
        if nuevo_cupo < inscriptos:
            return jsonify({'error': f'No podés bajar el cupo por debajo de los inscriptos actuales ({inscriptos})'}), 400
        clase.cupo_maximo = nuevo_cupo
        if cupos_antes <= 0 and clase.cupos_disponibles() > 0:
            resultado = notificar_siguiente_en_lista_espera(
                clase.id,
                mes=clase.fecha.month,
                anio=clase.fecha.year
            )
    db.session.commit()
    response = clase.to_dict()
    if resultado:
        response.update(resultado)
    return jsonify(response), 200


@clases_bp.route('/<int:clase_id>/cancelar', methods=['POST'])
@jwt_required()
@require_rol('administrador')
def cancelar_clase(clase_id):
    """Borrado lógico: marca como cancelada y libera reservas"""
    clase = Clase.query.get_or_404(clase_id)
    if clase.cancelada:
        return jsonify({'error': 'La clase ya está cancelada'}), 400
    clase.cancelada = True
    reservas = Reserva.query.filter_by(clase_id=clase_id, estado='activa').all()
    for r in reservas:
        r.estado = 'cancelada'
    db.session.commit()
    return jsonify({'mensaje': f'Clase del {clase.fecha} cancelada. {len(reservas)} reserva(s) liberadas.'}), 200


@clases_bp.route('/<int:clase_id>/inscriptos', methods=['GET'])
@jwt_required()
@require_rol('administrador', 'empleado')
def get_inscriptos(clase_id):
    reservas = Reserva.query.filter_by(clase_id=clase_id, estado='activa').all()
    result = []
    for r in reservas:
        d = r.to_dict()
        d['usuario'] = r.cliente.to_dict()
        d['habilitado'] = not (
            r.tipo == 'abonado'
            and tiene_suspension_abonado_para_clase(r.usuario_id, r.clase)
        )
        if not d['habilitado']:
            d['estado_habilitacion'] = 'suspendido'
        result.append(d)
    return jsonify(result), 200


@clases_bp.route('/<int:clase_id>/lista-espera', methods=['GET'])
@jwt_required()
@require_rol('administrador', 'empleado')
def get_lista_espera(clase_id):
    now = datetime.utcnow()
    lista = ListaEspera.query.filter_by(
        clase_id=clase_id,
        estado='esperando',
        mes=now.month,
        anio=now.year
    ).order_by(ListaEspera.fecha_inscripcion).all()
    return jsonify([l.to_dict() for l in lista]), 200
