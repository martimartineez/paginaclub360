from flask import Blueprint, request, jsonify
from extensions import db
from models import Clase

clases_bp = Blueprint('clases', __name__)

@clases_bp.route('/api/clases', methods=['GET'])
def obtener_clases():
    clases = Clase.query.all()
    return jsonify([{"id": c.id, "actividad": c.actividad, "dia": c.dia, "hora": c.hora, "precio": c.precio} for c in clases])

@clases_bp.route('/api/clases', methods=['POST'])
def crear_clase():
    datos = request.get_json()
    nueva = Clase(
        actividad=datos['actividad'], 
        dia=datos['dia'], 
        hora=datos['hora'], 
        cupo_maximo=int(datos['cupo_maximo']), 
        precio=float(datos['precio'])
    )
    db.session.add(nueva)
    db.session.commit()
    return jsonify({'mensaje': 'Clase creada exitosamente'}), 201