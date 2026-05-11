from flask import Blueprint, request, jsonify
from extensions import db
from models import Clase, Reserva

reservas_bp = Blueprint('reservas', __name__)

@reservas_bp.route('/api/reservar', methods=['POST'])
def reservar_clase():
    datos = request.get_json()
    clase = Clase.query.filter_by(actividad=datos['sport'], dia=datos['day'], hora=datos['hour']).first()
    
    if not clase:
        return jsonify({'mensaje': 'La clase no existe'}), 404

    reservas_actuales = Reserva.query.filter_by(clase_id=clase.id, estado='confirmada').count()
    es_abonado = True if datos['planType'] == 'mensual' else False

    if reservas_actuales >= clase.cupo_maximo:
        # Inscripción automática en lista de espera [cite: 39, 89]
        nueva = Reserva(usuario_id=1, clase_id=clase.id, es_abonado=es_abonado, estado='espera')
        db.session.add(nueva)
        db.session.commit()
        return jsonify({'mensaje': 'Turno lleno. Anotado en lista de espera.', 'estado': 'espera'}), 200

    nueva = Reserva(usuario_id=1, clase_id=clase.id, es_abonado=es_abonado, estado='confirmada')
    db.session.add(nueva)
    db.session.commit()
    return jsonify({'mensaje': 'Reserva confirmada', 'estado': 'confirmada'}), 201