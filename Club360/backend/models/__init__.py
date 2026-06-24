from datetime import datetime, date, timedelta
from flask_sqlalchemy import SQLAlchemy
import bcrypt

db = SQLAlchemy()

DIAS_ES = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

ASISTENCIA_TOLERANCIA_MINUTOS = 15

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
    fecha_nacimiento = db.Column(db.Date, nullable=True)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    reservas = db.relationship('Reserva', backref='cliente', lazy=True, foreign_keys='Reserva.usuario_id')
    listas_espera = db.relationship('ListaEspera', backref='cliente', lazy=True)
    creditos = db.relationship('Credito', backref='usuario', lazy=True)

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
            'fecha_registro': self.fecha_registro.isoformat() if self.fecha_registro else None,
            'fecha_nacimiento': self.fecha_nacimiento.isoformat() if self.fecha_nacimiento else None
        }


class Actividad(db.Model):
    __tablename__ = 'actividades'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    precio_clase = db.Column(db.Numeric(10, 2), nullable=False)
    activa = db.Column(db.Boolean, default=True)

    clases = db.relationship('Clase', backref='actividad', lazy=True)
    creditos = db.relationship('Credito', backref='actividad', lazy=True)

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
    turno_id = db.Column(db.Integer, db.ForeignKey('turnos.id'), nullable=True)
    fecha = db.Column(db.Date, nullable=False)
    hora_inicio = db.Column(db.Time, nullable=False)
    cupo_maximo = db.Column(db.Integer, nullable=False)
    precio_clase = db.Column(db.Numeric(10, 2), nullable=True)
    cancelada = db.Column(db.Boolean, default=False)
    cancelada_fecha = db.Column(db.DateTime, nullable=True)
    cancelada_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
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

    def get_precio(self):
        if self.precio_clase:
            return float(self.precio_clase)
        if self.turno and self.turno.precio_clase:
            return float(self.turno.precio_clase)
        if self.actividad:
            return float(self.actividad.precio_clase)
        return 0

    def to_dict(self):
        return {
            'id': self.id,
            'actividad_id': self.actividad_id,
            'turno_id': self.turno_id,
            'actividad': self.actividad.nombre if self.actividad else None,
            'precio_clase': self.get_precio(),
            'fecha': self.fecha.isoformat() if self.fecha else None,
            'dia_semana': self.dia_semana_str(),
            'hora_inicio': self.hora_inicio.strftime('%H:%M') if self.hora_inicio else None,
            'cupo_maximo': self.cupo_maximo,
            'cupos_disponibles': self.cupos_disponibles(),
            'cancelada': self.cancelada,
            'cancelada_fecha': self.cancelada_fecha.isoformat() if self.cancelada_fecha else None,
            'cancelada_por': self.cancelada_por,
            'activa': self.activa
        }


class Turno(db.Model):
    __tablename__ = 'turnos'
    id = db.Column(db.Integer, primary_key=True)
    actividad_id = db.Column(db.Integer, db.ForeignKey('actividades.id'), nullable=False)
    dia_semana = db.Column(db.Integer, nullable=False)
    hora_inicio = db.Column(db.Time, nullable=False)
    cupo_maximo = db.Column(db.Integer, nullable=False)
    precio_clase = db.Column(db.Numeric(10, 2), nullable=False)
    activo = db.Column(db.Boolean, default=True)
    cancelado_fecha = db.Column(db.DateTime, nullable=True)
    cancelado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    motivo_cancelacion = db.Column(db.Text, nullable=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    actividad = db.relationship('Actividad', backref='turnos')
    clases = db.relationship('Clase', backref='turno', lazy=True)

    DIAS_ES = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']

    def dia_semana_str(self):
        return self.DIAS_ES[self.dia_semana] if 0 <= self.dia_semana <= 5 else ''

    def to_dict(self):
        return {
            'id': self.id,
            'actividad_id': self.actividad_id,
            'actividad': self.actividad.nombre if self.actividad else None,
            'dia_semana': self.dia_semana,
            'dia_semana_str': self.dia_semana_str(),
            'hora_inicio': self.hora_inicio.strftime('%H:%M') if self.hora_inicio else None,
            'cupo_maximo': self.cupo_maximo,
            'precio_clase': float(self.precio_clase),
            'activo': self.activo,
            'cancelado_fecha': self.cancelado_fecha.isoformat() if self.cancelado_fecha else None,
            'cancelado_por': self.cancelado_por,
            'motivo_cancelacion': self.motivo_cancelacion,
            'total_clases': len(self.clases)
        }


class Abono(db.Model):
    __tablename__ = 'abonos'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    actividad_id = db.Column(db.Integer, db.ForeignKey('actividades.id'), nullable=False)
    mes = db.Column(db.Integer, nullable=False)
    anio = db.Column(db.Integer, nullable=False)
    monto_total = db.Column(db.Numeric(10, 2), nullable=False)
    monto_pagado = db.Column(db.Numeric(10, 2), default=0)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    actividad = db.relationship('Actividad', backref='abonos')
    usuario = db.relationship('Usuario', backref='abonos')
    reservas = db.relationship('Reserva', backref='abono', lazy=True)
    pagos = db.relationship('Pago', backref='abono', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'actividad_id': self.actividad_id,
            'actividad': self.actividad.nombre if self.actividad else None,
            'mes': self.mes,
            'anio': self.anio,
            'monto_total': float(self.monto_total),
            'monto_pagado': float(self.monto_pagado),
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            'cantidad_clases': len(self.reservas)
        }


class Reserva(db.Model):
    __tablename__ = 'reservas'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    clase_id = db.Column(db.Integer, db.ForeignKey('clases.id'), nullable=False)
    abono_id = db.Column(db.Integer, db.ForeignKey('abonos.id'), nullable=True)  # <-- Relación añadida
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
    cancelada_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    motivo_cancelacion = db.Column(db.Text, nullable=True)
    fecha_cancelacion = db.Column(db.DateTime, nullable=True)

    pagos = db.relationship('Pago', backref='reserva', lazy=True)
    asistencias = db.relationship('Asistencia', backref='reserva', lazy=True)

    def limite_asistencia(self):
        if not self.clase or not self.clase.fecha or not self.clase.hora_inicio:
            return None
        inicio = datetime.combine(self.clase.fecha, self.clase.hora_inicio)
        return inicio + timedelta(minutes=ASISTENCIA_TOLERANCIA_MINUTOS)

    def asistencia_vencida(self, ahora=None):
        if self.estado != 'activa':
            return False
        if not self.clase or self.clase.cancelada or not self.clase.activa:
            return False
        limite = self.limite_asistencia()
        if not limite:
            return False
        return (ahora or datetime.now()) >= limite

    def asistencia_estado(self, ahora=None):
        presente = next((a for a in self.asistencias if a.presente), None)
        if presente:
            return 'asistida', presente
        ausente = next((a for a in self.asistencias if not a.presente), None)
        if ausente or self.asistencia_vencida(ahora):
            return 'falto', ausente
        return 'pendiente', None

    def to_dict(self):
        estado_asistencia, asistencia = self.asistencia_estado()
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'clase_id': self.clase_id,
            'abono_id': self.abono_id,  # <-- Expuesto en el dict
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
            'qr_code': self.qr_code,
            'cancelada_por': self.cancelada_por,
            'motivo_cancelacion': self.motivo_cancelacion,
            'fecha_cancelacion': self.fecha_cancelacion.isoformat() if self.fecha_cancelacion else None,
            'asistida': estado_asistencia == 'asistida',
            'falto': estado_asistencia == 'falto',
            'estado_asistencia': estado_asistencia,
            'fecha_asistencia': asistencia.fecha.isoformat() if asistencia and asistencia.fecha else None
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
    # Tipo de reserva que origino la notificacion actual ('abonado' o 'no_abonado').
    # Se usa para saber, si esta persona rechaza, con que criterio seguir
    # la cadena (lista de abonados, no_abonados o la general combinada).
    # String simple (no Enum) para que el ALTER TABLE de compatibilidad
    # funcione igual en sqlite y en postgres.
    origen_cancelacion = db.Column(db.String(20), nullable=True)

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
            'anio': self.anio,
            'origen_cancelacion': self.origen_cancelacion
        }


class Pago(db.Model):
    __tablename__ = 'pagos'
    id = db.Column(db.Integer, primary_key=True)
    reserva_id = db.Column(db.Integer, db.ForeignKey('reservas.id'), nullable=True)  # <-- Ahora admite NULL
    abono_id = db.Column(db.Integer, db.ForeignKey('abonos.id'), nullable=True)      # <-- Nueva columna
    suspension_id = db.Column(db.Integer, db.ForeignKey('suspensiones.id'), nullable=True)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    metodo = db.Column(db.Enum('efectivo', 'tarjeta_credito', name='metodo_pago_enum'), nullable=False)
    tipo_pago = db.Column(db.Enum('senia', 'mensualidad', 'suspension', name='tipo_pago_enum'), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    registrado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'))

    def to_dict(self):
        return {
            'id': self.id,
            'reserva_id': self.reserva_id,
            'abono_id': self.abono_id,  # <-- Expuesto en el dict
            'suspension_id': self.suspension_id,
            'monto': float(self.monto),
            'metodo': self.metodo,
            'tipo_pago': self.tipo_pago,
            'fecha': self.fecha.isoformat() if self.fecha else None
        }


class Credito(db.Model):
    __tablename__ = 'creditos'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    actividad_id = db.Column(db.Integer, db.ForeignKey('actividades.id'), nullable=False)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    monto_restante = db.Column(db.Numeric(10, 2), nullable=False)
    origen = db.Column(
        db.Enum('abono_cancelacion', 'clase_suelta_cancelacion', name='origen_credito_enum'),
        nullable=False
    )
    reserva_origen_id = db.Column(db.Integer, db.ForeignKey('reservas.id'), nullable=True)
    reserva_uso_id = db.Column(db.Integer, db.ForeignKey('reservas.id'), nullable=True)
    estado = db.Column(db.Enum('disponible', 'usado', 'vencido', name='estado_credito_enum'), default='disponible')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_uso = db.Column(db.DateTime)
    motivo = db.Column(db.Text, nullable=True)

    reserva_origen = db.relationship('Reserva', foreign_keys=[reserva_origen_id], backref='creditos_generados')
    reserva_uso = db.relationship('Reserva', foreign_keys=[reserva_uso_id], backref='creditos_usados')

    def to_dict(self):
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'actividad_id': self.actividad_id,
            'actividad': self.actividad.nombre if self.actividad else None,
            'monto': float(self.monto) if self.monto else 0,
            'monto_restante': float(self.monto_restante) if self.monto_restante else 0,
            'origen': self.origen,
            'origen_label': 'Cancelacion de abono' if self.origen == 'abono_cancelacion' else 'Cancelacion de clase suelta',
            'reserva_origen_id': self.reserva_origen_id,
            'reserva_uso_id': self.reserva_uso_id,
            'estado': self.estado,
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            'fecha_uso': self.fecha_uso.isoformat() if self.fecha_uso else None,
            'motivo': self.motivo
        }


class MovimientoFinanciero(db.Model):
    __tablename__ = 'movimientos_financieros'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    clase_id = db.Column(db.Integer, db.ForeignKey('clases.id'), nullable=True)
    reserva_id = db.Column(db.Integer, db.ForeignKey('reservas.id'), nullable=True)
    abono_id = db.Column(db.Integer, db.ForeignKey('abonos.id'), nullable=True)
    credito_id = db.Column(db.Integer, db.ForeignKey('creditos.id'), nullable=True)
    tipo = db.Column(db.String(40), nullable=False)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    motivo = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    registrado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)

    usuario = db.relationship('Usuario', foreign_keys=[usuario_id], backref='movimientos_financieros')
    clase = db.relationship('Clase', backref='movimientos_financieros')
    reserva = db.relationship('Reserva', backref='movimientos_financieros')
    abono = db.relationship('Abono', backref='movimientos_financieros')
    credito = db.relationship('Credito', backref='movimientos_financieros')

    def to_dict(self):
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'clase_id': self.clase_id,
            'reserva_id': self.reserva_id,
            'abono_id': self.abono_id,
            'credito_id': self.credito_id,
            'tipo': self.tipo,
            'monto': float(self.monto) if self.monto else 0,
            'motivo': self.motivo,
            'fecha': self.fecha.isoformat() if self.fecha else None,
            'registrado_por': self.registrado_por
        }


class Asistencia(db.Model):
    __tablename__ = 'asistencias'
    __table_args__ = (
        db.UniqueConstraint('reserva_id', name='uq_asistencia_reserva'),
    )

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
    turno_id = db.Column(db.Integer, db.ForeignKey('turnos.id'), nullable=True)
    abono_id = db.Column(db.Integer, db.ForeignKey('abonos.id'), nullable=True)
    tipo = db.Column(db.Enum('abonado', 'no_abonado', name='tipo_susp_enum'), nullable=False)
    motivo = db.Column(db.Text)
    cantidad_clases = db.Column(db.Integer, default=0)
    monto_original = db.Column(db.Numeric(10, 2), default=0)
    recargo = db.Column(db.Numeric(10, 2), default=0)
    monto_deuda = db.Column(db.Numeric(10, 2), default=0)
    activa = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_levantamiento = db.Column(db.DateTime)

    usuario = db.relationship('Usuario', backref='suspensiones')
    clase = db.relationship('Clase', backref='suspensiones')
    turno = db.relationship('Turno', backref='suspensiones')
    abono = db.relationship('Abono', backref='suspensiones')
    pagos = db.relationship('Pago', backref='suspension', lazy=True)

    def to_dict(self):
        clase = self.clase
        turno = self.turno
        actividad = None
        turno_label = None
        clase_label = None

        if turno:
            actividad = turno.actividad.nombre if turno.actividad else None
            turno_label = f"{turno.dia_semana_str()} {turno.hora_inicio.strftime('%H:%M')} hs"
        elif clase:
            actividad = clase.actividad.nombre if clase.actividad else None
            turno_label = f"{clase.dia_semana_str()} {clase.hora_inicio.strftime('%H:%M')} hs"
            clase_label = f"{clase.dia_semana_str()} {clase.fecha.isoformat()} {clase.hora_inicio.strftime('%H:%M')} hs"

        tipo_suspension = 'abonado_turno' if self.tipo == 'abonado' else 'clase_suelta'

        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'clase_id': self.clase_id,
            'turno_id': self.turno_id,
            'abono_id': self.abono_id,
            'tipo': self.tipo,
            'tipo_suspension': tipo_suspension,
            'tipo_label': 'Abonado en turno' if self.tipo == 'abonado' else 'Clase suelta',
            'motivo': self.motivo,
            'actividad': actividad,
            'turno_label': turno_label,
            'clase_label': clase_label,
            'cantidad_clases': self.cantidad_clases or 0,
            'monto_original': float(self.monto_original) if self.monto_original else 0,
            'recargo': float(self.recargo) if self.recargo else 0,
            'monto_deuda': float(self.monto_deuda) if self.monto_deuda else 0,
            'total_pagar': float(self.monto_deuda) if self.monto_deuda else 0,
            'activa': self.activa,
            'estado': 'activa' if self.activa else 'resuelta',
            'fecha_creacion': self.fecha_creacion.isoformat() if self.fecha_creacion else None,
            'fecha_levantamiento': self.fecha_levantamiento.isoformat() if self.fecha_levantamiento else None
        }


class TarjetaCredito(db.Model):
    __tablename__ = 'tarjetas_credito'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    ultimos_4 = db.Column(db.String(4), nullable=False)
    titular = db.Column(db.String(150), nullable=False)
    vencimiento = db.Column(db.String(7), nullable=False)
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
