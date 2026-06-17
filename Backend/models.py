from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import date
from database import Base
from datetime import datetime
from sqlalchemy import Index


class TipoEquipo(Base):
    __tablename__ = "tipos_equipos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    categoria = Column(String)
    criticidad_total = Column(Integer)

    equipos = relationship("Equipo", back_populates="tipo_relacion")


class Empresa(Base):
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, index=True, nullable=False)
    fecha_registro = Column(DateTime, default=datetime.utcnow)

    usuarios = relationship("Usuario", back_populates="empresa")
    equipos = relationship("Equipo", back_populates="empresa")
    
    
class Equipo(Base):
    __tablename__ = "equipos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo = Column(String, nullable=False, unique=True)
    tipo_equipo_id = Column(Integer, ForeignKey("tipos_equipos.id"))

    tipo_relacion = relationship("TipoEquipo", back_populates="equipos")
    historial_ubicaciones = relationship("UbicacionEquipo", back_populates="equipo")
    ubicaciones = relationship("HistorialUbicacion", back_populates="equipo", cascade="all, delete")

    marca = Column(String)
    modelo = Column(String)
    serial = Column(String)
    ubicacion = Column(String)
    nivel_uso = Column(String)

    estado = Column(String, default="Operativo")
    responsable = Column(String, nullable=True)

    indice_salud = Column(Float, default=100)
    fecha_inicio_operacion = Column(Date)
    horas_acumuladas = Column(Float, default=0)

    manual_url = Column(String, nullable=True)
    observaciones_iniciales = Column(Text, nullable=True)

    prestamos_relacion = relationship(
        "Prestamo",
        back_populates="equipo",
        cascade="all, delete-orphan"
    )

    mantenimientos = relationship(
        "Mantenimiento",
        back_populates="equipo",
        cascade="all, delete-orphan"
    )

    calibraciones = relationship(
        "Calibracion",
        back_populates="equipo",
        cascade="all, delete-orphan"
    )
    
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    empresa = relationship("Empresa", back_populates="equipos")



class Prestamo(Base):
    __tablename__ = "prestamos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    equipo_id = Column(UUID(as_uuid=True), ForeignKey("equipos.id"))

    fecha_salida = Column(Date, default=date.today)
    responsable_prestamo = Column(String)
    condiciones_salida = Column(Text)
    observaciones_salida = Column(Text, nullable=True)

    fecha_regreso = Column(Date, nullable=True)
    condiciones_regreso = Column(Text, nullable=True)
    observaciones_regreso = Column(Text, nullable=True)

    estado_prestamo = Column(String, default="Activo")

    equipo = relationship("Equipo", back_populates="prestamos_relacion")


class Mantenimiento(Base):
    __tablename__ = "mantenimientos"

    id = Column(Integer, primary_key=True, index=True)
    equipo_id = Column(UUID(as_uuid=True), ForeignKey("equipos.id"))

    tipo = Column(String)
    descripcion = Column(Text, nullable=True)

    fecha_programada = Column(Date)
    fecha_realizada = Column(Date, nullable=True)

    tecnico = Column(String, nullable=True)

    estado = Column(String, default="pendiente")
    costo = Column(Float, nullable=True)
    observaciones_modificacion = Column(Text, nullable=True)

    tiempo_fuera_servicio = Column(Integer, nullable=True)
    severidad = Column(Integer, default=1)

    soporte_url = Column(String, nullable=True)

    creado_en = Column(Date, default=date.today)
    equipo = relationship("Equipo", back_populates="mantenimientos")
    
    mantenimiento_padre_id = Column(
        Integer,
        ForeignKey("mantenimientos.id"),
        nullable=True
    )

class Calibracion(Base):
    __tablename__ = "calibraciones"

    id = Column(Integer, primary_key=True, index=True)
    equipo_id = Column(UUID(as_uuid=True), ForeignKey("equipos.id"))

    tipo = Column(String)
    fecha_programada = Column(Date, nullable=False)
    proveedor = Column(String, nullable=True)

    fecha_realizada = Column(Date, nullable=True)
    resultado = Column(String, nullable=True)
    certificado_url = Column(String, nullable=True)
    observaciones = Column(Text, nullable=True)

    estado = Column(String, default="pendiente")

    equipo = relationship("Equipo", back_populates="calibraciones")
    
    calibracion_padre_id = Column(
        Integer,
        ForeignKey("calibraciones.id"),
        nullable=True
    )

class PruebaTecnica(Base):
    __tablename__ = "prueba_tecnica"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False, unique=True)

    equipos = relationship("EquipoPrueba", back_populates="prueba")
    resultados = relationship("ResultadoPrueba", back_populates="prueba")


class EquipoPrueba(Base):
    __tablename__ = "equipo_prueba"

    id = Column(Integer, primary_key=True, index=True)
    nombre_equipo = Column(String, nullable=False)
    prueba_id = Column(Integer, ForeignKey("prueba_tecnica.id", ondelete="CASCADE"))

    prueba = relationship("PruebaTecnica", back_populates="equipos")


class EvaluacionEquipo(Base):
    __tablename__ = "evaluacion_equipo"

    id = Column(Integer, primary_key=True, index=True)
    equipo_id = Column(UUID(as_uuid=True), ForeignKey("equipos.id"))

    fecha = Column(Date, default=date.today)
    responsable = Column(String, nullable=False)
    resultado_global = Column(String)
    observaciones = Column(Text, nullable=True)

    resultados = relationship(
        "ResultadoPrueba",
        back_populates="evaluacion",
        cascade="all, delete-orphan"
    )


class ResultadoPrueba(Base):
    __tablename__ = "resultado_prueba"

    id = Column(Integer, primary_key=True, index=True)
    evaluacion_id = Column(Integer, ForeignKey("evaluacion_equipo.id", ondelete="CASCADE"))
    prueba_id = Column(Integer, ForeignKey("prueba_tecnica.id", ondelete="CASCADE"))

    valor_obtenido = Column(String)

    criterio_aplicado = Column(Text)
    valor_min = Column(Float, nullable=True)
    valor_max = Column(Float, nullable=True)

    cumple = Column(String)

    evaluacion = relationship("EvaluacionEquipo", back_populates="resultados")
    prueba = relationship("PruebaTecnica", back_populates="resultados")

class UbicacionEquipo(Base):
    __tablename__ = "ubicaciones_equipos"

    id = Column(Integer, primary_key=True, index=True)
    equipo_id = Column(UUID(as_uuid=True), ForeignKey("equipos.id"))
    nombre_personalizado = Column(String)
    direccion_texto = Column(String) 
    latitud = Column(Float)
    longitud = Column(Float)
    fecha_registro = Column(DateTime, default=datetime.utcnow)

    equipo = relationship("Equipo", back_populates="historial_ubicaciones")

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String, nullable=False)
    apellido = Column(String, nullable=False)
    laboratorio = Column(String, nullable=False)
    area = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    fecha_registro = Column(DateTime, default=datetime.utcnow)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    empresa = relationship("Empresa", back_populates="usuarios")

Index(
    "idx_unico_area_critica",
    Usuario.area,
    unique=True,
    postgresql_where=(Usuario.area.in_(['Calidad', 'Dirección Laboratorio', 'Coordinación Laboratorio']))
)

class HistorialUbicacion(Base):
    __tablename__ = "historial_ubicaciones"

    id = Column(Integer, primary_key=True, index=True)

    equipo_id = Column(
        UUID(as_uuid=True),
        ForeignKey("equipos.id", ondelete="CASCADE"),
        nullable=False
    )

    nombre_personalizado = Column(String)
    direccion_texto = Column(String)
    latitud = Column(Float)
    longitud = Column(Float)
    fecha_registro = Column(DateTime, default=datetime.utcnow)

    equipo = relationship("Equipo", back_populates="ubicaciones")
    
class Falla(Base):
    __tablename__ = "fallas"
    id = Column(Integer, primary_key=True, index=True)
    equipo_id = Column(UUID(as_uuid=True), ForeignKey("equipos.id"), nullable=False)
    tipo = Column(String)
    urgencia = Column(String)
    descripcion = Column(Text)
    fecha_reporte = Column(DateTime, default=datetime.utcnow)
