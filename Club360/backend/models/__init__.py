from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
import bcrypt

db = SQLAlchemy()

DIAS_ES = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    dni = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.Enum('cliente', 'empleado', 'administrador', name='rol_enum'), default='cliente', nullable=False)
    activo = db.Column(db.Boolean, default=True)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    reservas = db.relationship('Reserva', backref='cliente', lazy=True, foreign_keys='Reserva.usuario_id')
    listas_espera = db.relationship('ListaEspera', backref='cliente', lazy=True)

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'apellido': self.apellido,
            'dni': self.dni,
            'email': self.email,
            'rol': self.rol,
            'activo': self.activo,
            'fecha_registro': self.fecha_registro.isoformat() if self.fecha_registro else None
        }


class Actividad(db.Model):
    __tablename__ = 'actividades'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    precio_clase = db.Column(db.Numeric(10, 2), nullable=False)
    activa = db.Column(db.Boolean, default=True)

    clases = db.relationship('Clase', backref='actividad', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'precio_clase': float(self.precio_clase),
            'activa': self.activa
        }


class Clase(db.Model):
    __tablename__ = 'clases'
    id = db.Column(db.Integer, primary_key=True)
    actividad_id = db.Column(db.Integer, db.ForeignKey('actividades.id'), nullable=False)
    fecha = db.Column(db.Date, nullable=False)           # fecha exacta de la clase
    hora_inicio = db.Column(db.Time, nullable=False)
    cupo_maximo = db.Column(db.Integer, nullable=False)
    cancelada = db.Column(db.Boolean, default=False)     # cancelada por admin para este dia
    activa = db.Column(db.Boolean, default=True)

    reservas = db.relationship('Reserva', backref='clase', lazy=True)
    listas_espera = db.relationship('ListaEspera', backref='clase', lazy=True)

    def cupos_disponibles(self):
        reservas_activas = Reserva.query.filter_by(
            clase_id=self.id,
            estado='activa'
        ).count()
        return self.cupo_maximo - reservas_activas

    def dia_semana_str(self):
        if self.fecha:
            return DIAS_ES[self.fecha.weekday()]
        return ''

    def to_dict(self):
        return {
            'id': self.id,
            'actividad_id': self.actividad_id,
            'actividad': self.actividad.nombre if self.actividad else None,
            'precio_clase': float(self.actividad.precio_clase) if self.actividad else 0,
            'fecha': self.fecha.isoformat() if self.fecha else None,
            'dia_semana': self.dia_semana_str(),
            'hora_inicio': self.hora_inicio.strftime('%H:%M') if self.hora_inicio else None,
            'cupo_maximo': self.cupo_maximo,
            'cupos_disponibles': self.cupos_disponibles(),
            'cancelada': self.cancelada,
            'activa': self.activa
        }


class Reserva(db.Model):
    __tablename__ = 'reservas'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    clase_id = db.Column(db.Integer, db.ForeignKey('clases.id'), nullable=False)
    tipo = db.Column(db.Enum('abonado', 'no_abonado', name='tipo_reserva_enum'), nullable=False)
    estado = db.Column(db.Enum('activa', 'cancelada', 'suspendida', name='estado_reserva_enum'), default='activa')
    mes = db.Column(db.Integer, nullable=False)
    anio = db.Column(db.Integer, nullable=False)
    monto_total = db.Column(db.Numeric(10, 2))
    monto_pagado = db.Column(db.Numeric(10, 2), default=0)
    senia_pagada = db.Column(db.Boolean, default=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    cancelaciones_mes = db.Column(db.Integer, default=0)
    credito_a_favor = db.Column(db.Boolean, default=False)
    inasistencias_pendientes = db.Column(db.Integer, default=0)
    qr_code = db.Column(db.Text)

    pagos = db.relationship('Pago', backref='reserva', lazy=True)
    asistencias = db.relationship('Asistencia', backref='reserva', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'clase_id': self.clase_id,
            'clase': self.clase.to_dict() if self.clase else None,
            'tipo': self.tipo,
            'estado': self.estado,
            'mes': self.mes,
            'anio': self.anio,
            'monto_total': float(self.monto_total) if self.monto_total else 0,
            'monto_pagado': float(self.monto_pagado) if self.monto_pagado else 0,
            'senia_pagada': self.senia_pagada,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            'cancelaciones_mes': self.cancelaciones_mes,
            'credito_a_favor': self.credito_a_favor,
            'qr_code': self.qr_code
        }


class ListaEspera(db.Model):
    __tablename__ = 'lista_espera'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    clase_id = db.Column(db.Integer, db.ForeignKey('clases.id'), nullable=False)
    tipo_preferencia = db.Column(db.Enum('abonado', 'no_abonado', name='tipo_espera_enum'), nullable=False)
    fecha_inscripcion = db.Column(db.DateTime, default=datetime.utcnow)
    estado = db.Column(db.Enum('esperando', 'notificado', 'aceptado', 'rechazado', name='estado_espera_enum'), default='esperando')
    mes = db.Column(db.Integer, nullable=False)
    anio = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'usuario': self.cliente.to_dict() if self.cliente else None,
            'clase_id': self.clase_id,
            'clase': self.clase.to_dict() if self.clase else None,
            'tipo_preferencia': self.tipo_preferencia,
            'fecha_inscripcion': self.fecha_inscripcion.isoformat() if self.fecha_inscripcion else None,
            'estado': self.estado,
            'mes': self.mes,
            'anio': self.anio
        }


class Pago(db.Model):
    __tablename__ = 'pagos'
    id = db.Column(db.Integer, primary_key=True)
    reserva_id = db.Column(db.Integer, db.ForeignKey('reservas.id'), nullable=True)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    metodo = db.Column(db.Enum('efectivo', 'tarjeta_credito', name='metodo_pago_enum'), nullable=False)
    tipo_pago = db.Column(db.Enum('senia', 'mensualidad', 'suspension', name='tipo_pago_enum'), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    registrado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'))

    def to_dict(self):
        return {
            'id': self.id,
            'reserva_id': self.reserva_id,
            'monto': float(self.monto),
            'metodo': self.metodo,
            'tipo_pago': self.tipo_pago,
            'fecha': self.fecha.isoformat() if self.fecha else None
        }


class Asistencia(db.Model):
    __tablename__ = 'asistencias'
    id = db.Column(db.Integer, primary_key=True)
    reserva_id = db.Column(db.Integer, db.ForeignKey('reservas.id'), nullable=False)
    fecha = db.Column(db.Date, default=date.today)
    presente = db.Column(db.Boolean, default=True)
    registrado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'))

    def to_dict(self):
        return {
            'id': self.id,
            'reserva_id': self.reserva_id,
            'fecha': self.fecha.isoformat() if self.fecha else None,
            'presente': self.presente
        }


class Suspension(db.Model):
    __tablename__ = 'suspensiones'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    clase_id = db.Column(db.Integer, db.ForeignKey('clases.id'), nullable=True)
    tipo = db.Column(db.Enum('abonado', 'no_abonado', name='tipo_susp_enum'), nullable=False)
    motivo = db.Column(db.Text)
    monto_deuda = db.Column(db.Numeric(10, 2), default=0)
    activa = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_levantamiento = db.Column(db.DateTime)

    usuario = db.relationship('Usuario', backref='suspensiones')
    clase = db.relationship('Clase', backref='suspensiones')

    def to_dict(self):
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'clase_id': self.clase_id,
            'tipo': self.tipo,
            'motivo': self.motivo,
            'monto_deuda': float(self.monto_deuda) if self.monto_deuda else 0,
            'activa': self.activa,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None
        }


class TarjetaCredito(db.Model):
    __tablename__ = 'tarjetas_credito'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    ultimos_4 = db.Column(db.String(4), nullable=False)
    titular = db.Column(db.String(150), nullable=False)
    vencimiento = db.Column(db.String(7), nullable=False)  # MM/AAAA
    activa = db.Column(db.Boolean, default=True)
    fecha_agregada = db.Column(db.DateTime, default=datetime.utcnow)

    usuario = db.relationship('Usuario', backref='tarjetas')

    def to_dict(self):
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'ultimos_4': self.ultimos_4,
            'titular': self.titular,
            'vencimiento': self.vencimiento,
            'activa': self.activa
        }
