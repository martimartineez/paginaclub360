from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Turno, Clase, Actividad, Usuario
from datetime import datetime, date, timedelta
import calendar

turnos_bp = Blueprint('turnos', __name__)

# Feriados nacionales Argentina 2026 (formato MM-DD)
FERIADOS_2026 = {
    '01-01', '02-16', '02-17', '03-24', '04-02', '04-03', '04-06',
    '05-01', '05-25', '06-19', '06-20', '07-09', '08-17',
    '10-12', '11-20', '12-08', '12-25'
}

def es_feriado(fecha):
    return fecha.strftime('%m-%d') in FERIADOS_2026

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


def generar_clases_para_turno(turno, desde=None, hasta=None):
    """Genera todas las clases del año para un turno dado, saltando feriados."""
    hoy = date.today()
    inicio = desde or hoy
    fin = hasta or date(hoy.year, 12, 31)

    clases_generadas = 0
    clases_existentes = 0
    fecha = inicio

    while fecha <= fin:
        if fecha.weekday() == turno.dia_semana and not es_feriado(fecha):
            # Verificar si ya existe una clase para este turno en esta fecha
            existente = Clase.query.filter_by(
                turno_id=turno.id,
                fecha=fecha
            ).first()
            if not existente:
                clase = Clase(
                    actividad_id=turno.actividad_id,
                    turno_id=turno.id,
                    fecha=fecha,
                    hora_inicio=turno.hora_inicio,
                    cupo_maximo=turno.cupo_maximo,
                    precio_clase=turno.precio_clase
                )
                db.session.add(clase)
                clases_generadas += 1
            else:
                clases_existentes += 1
        fecha += timedelta(days=1)

    db.session.commit()
    return clases_generadas, clases_existentes


@turnos_bp.route('/', methods=['GET'])
@jwt_required()
@require_rol('administrador', 'empleado')
def listar_turnos():
    activos = request.args.get('activos', 'true') == 'true'
    actividad_id = request.args.get('actividad_id', type=int)

    query = Turno.query
    if activos:
        query = query.filter_by(activo=True)
    if actividad_id:
        query = query.filter_by(actividad_id=actividad_id)

    turnos = query.order_by(Turno.dia_semana, Turno.hora_inicio).all()
    return jsonify([t.to_dict() for t in turnos]), 200


@turnos_bp.route('/<int:turno_id>', methods=['GET'])
@jwt_required()
@require_rol('administrador', 'empleado')
def get_turno(turno_id):
    turno = Turno.query.get_or_404(turno_id)
    data = turno.to_dict()
    # Contar clases futuras activas
    hoy = date.today()
    data['clases_futuras'] = Clase.query.filter_by(
        turno_id=turno_id, activa=True, cancelada=False
    ).filter(Clase.fecha >= hoy).count()
    data['clases_pasadas'] = Clase.query.filter_by(
        turno_id=turno_id
    ).filter(Clase.fecha < hoy).count()
    return jsonify(data), 200


@turnos_bp.route('/', methods=['POST'])
@jwt_required()
@require_rol('administrador')
def crear_turno():
    data = request.get_json()

    actividad_id = int(data.get('actividad_id'))
    dia_semana = int(data.get('dia_semana'))  # 0=lunes..5=sabado
    hora_str = data.get('hora_inicio')
    cupo_maximo = int(data.get('cupo_maximo', 10))
    precio_clase = float(data.get('precio_clase'))

    if dia_semana < 0 or dia_semana > 5:
        return jsonify({'error': 'Día inválido (0=Lunes, 5=Sábado)'}), 400

    hora = datetime.strptime(hora_str, '%H:%M').time()

    # Verificar si ya existe un turno activo con esos datos
    existente = Turno.query.filter_by(
        actividad_id=actividad_id,
        dia_semana=dia_semana,
        hora_inicio=hora,
        activo=True
    ).first()

    if existente:
        return jsonify({'error': 'Ya existe un turno activo con esa actividad, día y horario'}), 409

    # Verificar turno inactivo para reactivar
    inactivo = Turno.query.filter_by(
        actividad_id=actividad_id,
        dia_semana=dia_semana,
        hora_inicio=hora,
        activo=False
    ).first()

    if inactivo:
        inactivo.activo = True
        inactivo.cupo_maximo = cupo_maximo
        inactivo.precio_clase = precio_clase
        db.session.commit()
        generadas, existentes = generar_clases_para_turno(inactivo)
        return jsonify({
            'turno': inactivo.to_dict(),
            'reactivado': True,
            'mensaje': f'Turno reactivado. {generadas} clase(s) generadas, {existentes} ya existían.'
        }), 200

    turno = Turno(
        actividad_id=actividad_id,
        dia_semana=dia_semana,
        hora_inicio=hora,
        cupo_maximo=cupo_maximo,
        precio_clase=precio_clase
    )
    db.session.add(turno)
    db.session.flush()

    generadas, _ = generar_clases_para_turno(turno)

    db.session.commit()
    return jsonify({
        'turno': turno.to_dict(),
        'clases_generadas': generadas,
        'mensaje': f'Turno creado. {generadas} clase(s) generadas hasta fin de año (sin feriados).'
    }), 201


@turnos_bp.route('/<int:turno_id>', methods=['PUT'])
@jwt_required()
@require_rol('administrador')
def editar_turno(turno_id):
    turno = Turno.query.get_or_404(turno_id)
    data = request.get_json()

    actualizar_clases = False

    if 'cupo_maximo' in data:
        turno.cupo_maximo = int(data['cupo_maximo'])
        actualizar_clases = True
    if 'precio_clase' in data:
        turno.precio_clase = float(data['precio_clase'])
        actualizar_clases = True

    if actualizar_clases:
        # Actualizar clases futuras sin inscriptos
        hoy = date.today()
        clases_futuras = Clase.query.filter_by(
            turno_id=turno_id, activa=True, cancelada=False
        ).filter(Clase.fecha >= hoy).all()

        actualizadas = 0
        for clase in clases_futuras:
            from models import Reserva
            inscriptos = Reserva.query.filter_by(clase_id=clase.id, estado='activa').count()
            if inscriptos == 0:
                if 'cupo_maximo' in data:
                    clase.cupo_maximo = turno.cupo_maximo
                if 'precio_clase' in data:
                    clase.precio_clase = turno.precio_clase
                actualizadas += 1

    db.session.commit()
    return jsonify({
        'turno': turno.to_dict(),
        'clases_actualizadas': actualizadas if actualizar_clases else 0
    }), 200


@turnos_bp.route('/<int:turno_id>/desactivar', methods=['POST'])
@jwt_required()
@require_rol('administrador')
def desactivar_turno(turno_id):
    """Borrado lógico del turno — cancela clases futuras sin inscriptos"""
    turno = Turno.query.get_or_404(turno_id)
    if not turno.activo:
        return jsonify({'error': 'El turno ya está desactivado'}), 400

    turno.activo = False

    # Cancelar clases futuras sin inscriptos
    hoy = date.today()
    clases_futuras = Clase.query.filter_by(
        turno_id=turno_id, activa=True, cancelada=False
    ).filter(Clase.fecha >= hoy).all()

    canceladas = 0
    with_inscriptos = 0
    for clase in clases_futuras:
        from models import Reserva
        inscriptos = Reserva.query.filter_by(clase_id=clase.id, estado='activa').count()
        if inscriptos == 0:
            clase.activa = False
            canceladas += 1
        else:
            with_inscriptos += 1

    db.session.commit()
    return jsonify({
        'mensaje': f'Turno desactivado. {canceladas} clase(s) futuras canceladas.',
        'clases_con_inscriptos': with_inscriptos
    }), 200
