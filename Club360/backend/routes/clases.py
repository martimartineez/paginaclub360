from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Clase, Actividad, Reserva, ListaEspera, Usuario
from datetime import datetime

clases_bp = Blueprint('clases', __name__)

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
    desde = request.args.get('desde')   # fecha YYYY-MM-DD
    hasta = request.args.get('hasta')
    solo_activas = request.args.get('solo_activas', 'true') == 'true'

    query = Clase.query.filter_by(activa=True)
    if solo_activas:
        query = query.filter_by(cancelada=False)
    if actividad_id:
        query = query.filter_by(actividad_id=actividad_id)
    if desde:
        fecha_desde = datetime.strptime(desde, '%Y-%m-%d').date()
        query = query.filter(Clase.fecha >= fecha_desde)
    if hasta:
        fecha_hasta = datetime.strptime(hasta, '%Y-%m-%d').date()
        query = query.filter(Clase.fecha <= fecha_hasta)

    clases = query.order_by(Clase.fecha, Clase.hora_inicio).all()
    return jsonify([c.to_dict() for c in clases]), 200


@clases_bp.route('/<int:clase_id>', methods=['GET'])
def get_clase(clase_id):
    clase = Clase.query.get_or_404(clase_id)
    return jsonify(clase.to_dict()), 200


@clases_bp.route('/', methods=['POST'])
@jwt_required()
@require_rol('administrador')
def create_clase():
    data = request.get_json()
    fecha_str = data.get('fecha')  # YYYY-MM-DD
    if not fecha_str:
        return jsonify({'error': 'La fecha es requerida'}), 400
    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Formato de fecha inválido (YYYY-MM-DD)'}), 400

    clase = Clase(
        actividad_id=data['actividad_id'],
        fecha=fecha,
        hora_inicio=datetime.strptime(data['hora_inicio'], '%H:%M').time(),
        cupo_maximo=data['cupo_maximo']
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
    # Solo se puede modificar el cupo
    if 'cupo_maximo' in data:
        nuevo_cupo = int(data['cupo_maximo'])
        inscriptos = Reserva.query.filter_by(clase_id=clase_id, estado='activa').count()
        if nuevo_cupo < inscriptos:
            return jsonify({'error': f'No podés bajar el cupo por debajo de los inscriptos actuales ({inscriptos})'}), 400
        clase.cupo_maximo = nuevo_cupo
    db.session.commit()
    return jsonify(clase.to_dict()), 200


@clases_bp.route('/<int:clase_id>/cancelar', methods=['POST'])
@jwt_required()
@require_rol('administrador')
def cancelar_clase(clase_id):
    clase = Clase.query.get_or_404(clase_id)
    if clase.cancelada:
        return jsonify({'error': 'La clase ya está cancelada'}), 400
    clase.cancelada = True
    # Liberar todas las reservas activas de esta clase
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
