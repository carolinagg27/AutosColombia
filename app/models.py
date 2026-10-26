"""Las ocho entidades del modelo de datos del parqueadero Autos Colombia."""
from datetime import date, datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, Index, text


db = SQLAlchemy()


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuario"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    usuario = db.Column(db.String(60), nullable=False, unique=True)
    contrasena_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    __table_args__ = (CheckConstraint("rol IN ('Administrador','Operario')"),)

    @property
    def is_active(self):
        return self.activo


class Cliente(db.Model):
    __tablename__ = "cliente"
    id = db.Column(db.Integer, primary_key=True)
    documento = db.Column(db.String(25), nullable=False, unique=True)
    nombre = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(30))
    vehiculos = db.relationship("Vehiculo", back_populates="cliente")


class Vehiculo(db.Model):
    __tablename__ = "vehiculo"
    id = db.Column(db.Integer, primary_key=True)
    placa = db.Column(db.String(12), nullable=False, unique=True)
    tipo = db.Column(db.String(12), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey("cliente.id"), nullable=False)
    cliente = db.relationship("Cliente", back_populates="vehiculos")
    __table_args__ = (CheckConstraint("tipo IN ('Carro','Moto')"),)


class Celda(db.Model):
    __tablename__ = "celda"
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(12), nullable=False, unique=True)
    tipo = db.Column(db.String(12), nullable=False)
    estado = db.Column(db.String(25), nullable=False, default="Disponible")
    __table_args__ = (
        CheckConstraint("tipo IN ('Carro','Moto')"),
        CheckConstraint("estado IN ('Disponible','Ocupada','Fuera de servicio')"),
    )

    def esta_disponible(self):
        return self.estado == "Disponible"


class Mensualidad(db.Model):
    __tablename__ = "mensualidad"
    id = db.Column(db.Integer, primary_key=True)
    vehiculo_id = db.Column(db.Integer, db.ForeignKey("vehiculo.id"), nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=False)
    valor_cop = db.Column(db.Integer, nullable=False)
    vehiculo = db.relationship("Vehiculo")
    pago = db.relationship("Pago", back_populates="mensualidad", uselist=False)
    __table_args__ = (
        CheckConstraint("valor_cop > 0"),
        CheckConstraint("fecha_fin >= fecha_inicio"),
    )

    def esta_vigente(self, hoy=None):
        hoy = hoy or date.today()
        return self.fecha_inicio <= hoy <= self.fecha_fin and self.pago is not None


class Pago(db.Model):
    __tablename__ = "pago"
    id = db.Column(db.Integer, primary_key=True)
    mensualidad_id = db.Column(db.Integer, db.ForeignKey("mensualidad.id"), nullable=False, unique=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    fecha_pago = db.Column(db.DateTime, nullable=False)
    valor_cop = db.Column(db.Integer, nullable=False)
    metodo = db.Column(db.String(20), nullable=False)
    mensualidad = db.relationship("Mensualidad", back_populates="pago")
    usuario = db.relationship("Usuario")
    __table_args__ = (
        CheckConstraint("valor_cop > 0"),
        CheckConstraint("metodo IN ('Efectivo','Transferencia')"),
    )


class Movimiento(db.Model):
    __tablename__ = "movimiento"
    id = db.Column(db.Integer, primary_key=True)
    vehiculo_id = db.Column(db.Integer, db.ForeignKey("vehiculo.id"), nullable=False)
    celda_id = db.Column(db.Integer, db.ForeignKey("celda.id"), nullable=False)
    usuario_entrada_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    usuario_salida_id = db.Column(db.Integer, db.ForeignKey("usuario.id"))
    fecha_entrada = db.Column(db.DateTime, nullable=False)
    fecha_salida = db.Column(db.DateTime)
    estado = db.Column(db.String(12), nullable=False, default="Activo")
    vehiculo = db.relationship("Vehiculo")
    celda = db.relationship("Celda")
    usuario_entrada = db.relationship("Usuario", foreign_keys=[usuario_entrada_id])
    usuario_salida = db.relationship("Usuario", foreign_keys=[usuario_salida_id])
    novedades = db.relationship("Novedad", back_populates="movimiento")
    __table_args__ = (
        CheckConstraint("estado IN ('Activo','Cerrado')"),
        CheckConstraint("(estado = 'Activo' AND fecha_salida IS NULL AND usuario_salida_id IS NULL) OR (estado = 'Cerrado' AND fecha_salida IS NOT NULL AND usuario_salida_id IS NOT NULL AND fecha_salida >= fecha_entrada)"),
        # Índices únicos parciales, soportados por SQLite.
        Index("idx_vehiculo_activo", "vehiculo_id", unique=True, sqlite_where=text("estado = 'Activo'")),
        Index("idx_celda_ocupada", "celda_id", unique=True, sqlite_where=text("estado = 'Activo'")),
    )

    def cerrar_salida(self, usuario_id, fecha):
        self.usuario_salida_id = usuario_id
        self.fecha_salida = fecha
        self.estado = "Cerrado"


class Novedad(db.Model):
    __tablename__ = "novedad"
    id = db.Column(db.Integer, primary_key=True)
    movimiento_id = db.Column(db.Integer, db.ForeignKey("movimiento.id"), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, nullable=False)
    movimiento = db.relationship("Movimiento", back_populates="novedades")
    usuario = db.relationship("Usuario")
    __table_args__ = (CheckConstraint("length(trim(descripcion)) > 0"),)
