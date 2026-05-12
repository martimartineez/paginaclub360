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
    actividad_id = request.args.get('actividad_id')
    dia = request.args.get('dia')
    query = Clase.query.filter_by(activa=True)
    if actividad_id:
        query = query.filter_by(actividad_id=actividad_id)
    if dia:
        query = query.filter_by(dia_semana=dia)
    clases = query.all()
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
    clase = Clase(
        actividad_id=data['actividad_id'],
        dia_semana=data['dia_semana'],
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
    if 'cupo_maximo' in data:
        clase.cupo_maximo = data['cupo_maximo']
    if 'hora_inicio' in data:
        clase.hora_inicio = datetime.strptime(data['hora_inicio'], '%H:%M').time()
    if 'activa' in data:
        clase.activa = data['activa']
    db.session.commit()
    return jsonify(clase.to_dict()), 200


@clases_bp.route('/<int:clase_id>/inscriptos', methods=['GET'])
@jwt_required()
@require_rol('administrador', 'empleado')
def get_inscriptos(clase_id):
    now = datetime.utcnow()
    reservas = Reserva.query.filter_by(
        clase_id=clase_id,
        estado='activa',
        mes=now.month,
        anio=now.year
    ).all()
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
