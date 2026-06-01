from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Union



# =====================================
# EQUIPOS
# =====================================

class EquipoBase(BaseModel):
    codigo: str
    tipo_equipo_id: int
    marca: Optional[str] = None
    modelo: Optional[str] = None
    serial: Optional[str] = None
    ubicacion: Optional[str] = None
    nivel_uso: str
    fecha_inicio_operacion: Optional[date] = None
    observaciones_iniciales: Optional[str] = None


class EquipoCreate(EquipoBase):
    pass


class EquipoResponse(EquipoBase):
    id: str
    estado: str
    indice_salud: float
    responsable: Optional[str] = None
    horas_acumuladas: Optional[float] = 0
    fecha_inicio_operacion: Optional[date] = None
    manual_url: Optional[str] = None

    class Config:
        from_attributes = True


# =====================================
# MANTENIMIENTOS
# =====================================

# schemas.py
class MantenimientoBase(BaseModel):
    tipo: str
    descripcion: Optional[str] = None
    fecha_programada: date
    tiempo_fuera_servicio: Optional[int] = None
    severidad: Optional[int] = 1
    fecha_realizada: Optional[date] = None
    tecnico: Optional[str] = None
    estado: Optional[str] = "pendiente"
    costo: Optional[float] = None

class MantenimientoCreate(BaseModel):
    fecha_programada: date
    tecnico: str
    descripcion: Optional[str] = "Sin descripción"
    tipo: str = "preventivo"
    severidad: int = 1
    estado: str = "pendiente"

class MantenimientoResponse(MantenimientoBase):
    id: int
    equipo_id: str
    soporte_url: Optional[str] = None

    class Config:
        from_attributes = True

class ReprogramarMantenimiento(BaseModel):
    fecha_programada: date
    observaciones_modificacion: Optional[str] = None

# =====================================
# PRÉSTAMOS
# =====================================

class PrestamoSalida(BaseModel):
    equipo_id: str
    responsable: str
    condiciones: str
    obs: Optional[str] = None


class PrestamoRegreso(BaseModel):
    equipo_id: str
    condiciones: str
    obs: Optional[str] = None


class PrestamoResponse(BaseModel):
    id: str
    equipo_id: str
    responsable_prestamo: str
    fecha_salida: date
    fecha_regreso: Optional[date] = None
    estado_prestamo: str

    class Config:
        from_attributes = True
# =====================================
# CONFIRMACION DE APTITUD ISO 17025
# =====================================

class ResultadoPruebaCreate(BaseModel):
    prueba_id: int
    valor_obtenido: str

    criterio_aplicado: str | None = None
    valor_min: float | None = None
    valor_max: float | None = None

    cumple: bool


class EvaluacionEquipoCreate(BaseModel):
    equipo_id: str
    responsable: Optional[str] = "Sistema"
    resultados: List[ResultadoPruebaCreate]


class ResultadoPruebaResponse(BaseModel):
    id: int
    prueba_id: int
    valor_obtenido: str
    criterio_aplicado: str
    cumple: bool

    class Config:
        from_attributes = True


class EvaluacionEquipoResponse(BaseModel):
    id: int
    equipo_id: str
    fecha: date
    responsable: str
    resultado_global: str
    resultados: List[ResultadoPruebaResponse]

    class Config:
        from_attributes = True

# =====================================
# CALIBRACIONES
# =====================================

class CalibracionCreate(BaseModel):
    fecha_programada: date
    proveedor: Optional[str] = None


class CalibracionSchema(BaseModel):
    id: int
    equipo_id: UUID
    fecha_programada: date
    fecha_realizada: Optional[date] = None
    proveedor: Optional[str] = None
    resultado: Optional[str] = None
    certificado_url: Optional[str] = None
    estado: str
    observaciones: Optional[str] = None

    class Config:
        from_attributes = True


class ReprogramarCalibracion(BaseModel):
    fecha_programada: date
    observaciones: Optional[str] = None

class UbicacionCreate(BaseModel):
    nombre_personalizado: str
    direccion_texto: str
    latitud: float
    longitud: float

class UbicacionResponse(UbicacionCreate):
    id: int
    fecha_registro: datetime

    class Config:
        orm_mode = True


class UsuarioCreate(BaseModel):
    nombre: str
    apellido: str
    laboratorio: str
    area: str
    email: str
    password: str

class UsuarioResponse(BaseModel):
    id: UUID
    email: str
    area: str

    class Config:
        from_attributes = True

class UsuarioLogin(BaseModel):
    email: EmailStr
    password: str
    
# En schemas.py, asegúrate de tener esto:

class FallaCreate(BaseModel):
    equipo_id: Union[str, UUID]
    tipo: str
    urgencia: str
    descripcion: str
    

class FallaResponse(BaseModel):
    id: int
    equipo_id: Union[str, UUID] 
    tipo: str
    urgencia: str
    descripcion: str
    fecha_reporte: datetime

    class Config:
        from_attributes = True


