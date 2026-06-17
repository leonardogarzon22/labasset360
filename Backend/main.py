import os
import shutil
import math
from datetime import date, datetime, timedelta, timezone
from typing import Optional, List
from uuid import UUID

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
from passlib.context import CryptContext
from jose import JWTError, jwt

# 1. MOVIDO ARRIBA: Cargar variables de entorno antes de usarlas
load_dotenv()

import models, schemas
from database import SessionLocal, engine, get_db

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY")

# Validación crítica para producción
if not SECRET_KEY:
    raise RuntimeError("CRÍTICO: La variable de entorno 'SECRET_KEY' no está configurada.")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

def crear_token_acceso(data: dict):
    to_encode = data.copy()
    # 2. ACTUALIZADO: Uso de timezone (buenas prácticas en Python moderno)
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(models.Usuario).filter(models.Usuario.email == email).first()
    if user is None:
        raise credentials_exception
    return user

# Crear carpeta de subidas si no existe
if not os.path.exists("uploads"):
    os.makedirs("uploads")

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static", StaticFiles(directory="../Frontend"), name="static")


@app.get("/")
def home():
    return {"mensaje": "Backend funcionando correctamente"}

@app.get("/registro")
def registro_page():
    return FileResponse("Frontend/registrar.html")

@app.get("/login")
def login_page():
    return FileResponse("Frontend/login.html")


# =====================================
# LÓGICA DE NEGOCIO (SALUD Y ESTADOS)
# =====================================

def actualizar_estados_vencidos(equipo_id: str, db: Session):
    hoy = date.today()

    mantenimientos = db.query(models.Mantenimiento).filter(
        models.Mantenimiento.equipo_id == equipo_id,
        models.Mantenimiento.estado != "completado"
    ).all()
    for m in mantenimientos:
        if m.fecha_programada and m.fecha_programada < hoy:
            m.estado = "vencido"

    calibraciones = db.query(models.Calibracion).filter(
        models.Calibracion.equipo_id == equipo_id,
        models.Calibracion.estado != "completado"
    ).all()
    for c in calibraciones:
        if c.fecha_programada and c.fecha_programada < hoy:
            c.estado = "vencida"
    db.commit()

def calcular_weibull(equipo, db, hoy):
    if not equipo.fecha_inicio_operacion: return 100
    t = (hoy - equipo.fecha_inicio_operacion).days
    if t <= 0: return 100
    equipo.horas_acumuladas = t * 8
    correctivos = db.query(models.Mantenimiento).filter(
        models.Mantenimiento.equipo_id == equipo.id,
        models.Mantenimiento.tipo == "correctivo",
        models.Mantenimiento.estado == "completado"
    ).all()
    if len(correctivos) == 0: return 100

    impacto_total = 0
    tiempo_total_paro = 0
    for c in correctivos:
        severidad = c.severidad or 1
        dias_paro = c.tiempo_fuera_servicio or 0
        impacto = severidad * (1 + dias_paro * 0.05)
        impacto_total += impacto
        tiempo_total_paro += dias_paro

    frecuencia = impacto_total / t
    beta = 1.2 if frecuencia < 0.001 else 1.8 if frecuencia < 0.005 else 2.5
    eta = max(t / impacto_total, 1)
    R_t = math.exp(-((t / eta) ** beta))
    penalizacion_disponibilidad = min(tiempo_total_paro * 0.2, 20)
    salud = (R_t * 100) - penalizacion_disponibilidad
    return max(min(salud, 100), 0)

def recalcular_indice_salud(equipo_id: str, db: Session):
    equipo = db.query(models.Equipo).filter(models.Equipo.id == equipo_id).first()
    if not equipo: return

    actualizar_estados_vencidos(equipo_id, db)
    hoy = date.today()

    score_weibull = calcular_weibull(equipo, db, hoy) * 0.40
    mantenimientos_vencidos = db.query(models.Mantenimiento).filter(
        models.Mantenimiento.equipo_id == equipo_id, models.Mantenimiento.estado == "vencido"
    ).count()
    score_mantenimiento = max(0, 20 - (mantenimientos_vencidos * 5))

    calibraciones_vencidas = db.query(models.Calibracion).filter(
        models.Calibracion.equipo_id == equipo_id, models.Calibracion.estado == "vencida"
    ).count()
    score_calibracion = max(0, 20 - (calibraciones_vencidas * 10))

    ultima_eval = db.query(models.EvaluacionEquipo).filter(
        models.EvaluacionEquipo.equipo_id == equipo_id
    ).order_by(models.EvaluacionEquipo.fecha.desc()).first()
    score_iso = 0 if ultima_eval and ultima_eval.resultado_global.lower() == "no cumple" else 10

    score_estado = 10
    if equipo.estado:
        estado = equipo.estado.lower()
        if estado == "no operativo": score_estado = 0
        elif estado == "en revisión": score_estado = 5
        elif estado == "en prestamo": score_estado = 8

    salud = score_weibull + score_mantenimiento + score_calibracion + score_iso + score_estado
    equipo.indice_salud = round(max(0, min(100, salud)), 2)
    db.commit()

def evaluar_resultado(r):
    try: valor = float(r.valor_obtenido)
    except: return "No cumple"

    if r.valor_min is not None and r.valor_max is not None:
        return "Cumple" if r.valor_min <= valor <= r.valor_max else "No cumple"
    if r.valor_min is not None:
        return "Cumple" if valor >= r.valor_min else "No cumple"
    if r.valor_max is not None:
        return "Cumple" if valor <= r.valor_max else "No cumple"
    return "No cumple"

# =====================================
# ENDPOINTS DE AUTENTICACIÓN
# =====================================

@app.post("/api/registro", response_model=schemas.UsuarioResponse)
def registrar_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.Usuario).filter(models.Usuario.email == usuario.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    # Búsqueda o creación de empresa basada en "laboratorio"
    empresa = db.query(models.Empresa).filter(models.Empresa.nombre == usuario.laboratorio.strip()).first()
    if not empresa:
        empresa = models.Empresa(nombre=usuario.laboratorio.strip())
        db.add(empresa)
        db.flush() 

    areas_criticas = ['Calidad', 'Dirección Laboratorio', 'Coordinación Laboratorio']
    if usuario.area in areas_criticas:
        existe_area = db.query(models.Usuario).filter(
            models.Usuario.area == usuario.area,
            models.Usuario.empresa_id == empresa.id
        ).first()
        if existe_area:
            raise HTTPException(status_code=400, detail=f"Ya existe un responsable para {usuario.area} en esta empresa")

    hashed_pw = pwd_context.hash(usuario.password)
    nuevo_usuario = models.Usuario(
        nombre=usuario.nombre,
        apellido=usuario.apellido,
        laboratorio=usuario.laboratorio,
        area=usuario.area,
        email=usuario.email,
        hashed_password=hashed_pw,
        empresa_id=empresa.id
    )

    try:
        db.add(nuevo_usuario)
        db.commit()
        db.refresh(nuevo_usuario)
        return nuevo_usuario
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar en la base de datos")

@app.post("/api/login")
def login(usuario: schemas.UsuarioLogin, db: Session = Depends(get_db)):
    user = db.query(models.Usuario).filter(models.Usuario.email == usuario.email).first()
    if not user or not pwd_context.verify(usuario.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    access_token = crear_token_acceso(data={"sub": user.email})
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "empresa_id": user.empresa_id,
        "usuario_nombre": user.nombre
    }

# =====================================
# ENDPOINTS DE EQUIPOS (MULTI-TENANT)
# =====================================

@app.get("/api/tipos-equipos")
def listar_tipos(db: Session = Depends(get_db), usuario_actual: models.Usuario = Depends(get_current_user)):
    # Asumiendo que TipoEquipo es un catálogo global. Si es por empresa, añadir filtro.
    return db.query(models.TipoEquipo).all()

@app.get("/api/equipos")
def listar_equipos(db: Session = Depends(get_db), usuario_actual: models.Usuario = Depends(get_current_user)):
    return db.query(models.Equipo).filter(models.Equipo.empresa_id == usuario_actual.empresa_id).all()

@app.get("/api/equipos/{equipo_id}")
def obtener_equipo(equipo_id: UUID, db: Session = Depends(get_db), usuario_actual: models.Usuario = Depends(get_current_user)):
    equipo = db.query(models.Equipo).options(joinedload(models.Equipo.tipo_relacion)).filter(
        models.Equipo.id == equipo_id,
        models.Equipo.empresa_id == usuario_actual.empresa_id
    ).first()

    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado o acceso denegado")

    recalcular_indice_salud(str(equipo.id), db)
    db.refresh(equipo)

    return {
        "id": str(equipo.id),
        "codigo": equipo.codigo,
        "marca": equipo.marca,
        "modelo": equipo.modelo,
        "serial": equipo.serial,
        "ubicacion": equipo.ubicacion,
        "estado": equipo.estado or "Operativo",
        "indice_salud": float(equipo.indice_salud) if equipo.indice_salud else 0,
        "responsable": equipo.responsable,
        "manual_url": equipo.manual_url,
        "tipo_nombre": equipo.tipo_relacion.nombre if equipo.tipo_relacion else "No definido",
        "observaciones_iniciales": equipo.observaciones_iniciales,
        "fecha_inicio_operacion": equipo.fecha_inicio_operacion,
        "tipo_equipo_id": equipo.tipo_equipo_id,
    }

@app.post("/api/equipos")
def crear_equipo(data: schemas.EquipoCreate, db: Session = Depends(get_db), usuario_actual: models.Usuario = Depends(get_current_user)):
    nuevo = models.Equipo(
        codigo=data.codigo,
        tipo_equipo_id=data.tipo_equipo_id,
        marca=data.marca,
        modelo=data.modelo,
        serial=data.serial,
        ubicacion=data.ubicacion,
        nivel_uso=data.nivel_uso,
        observaciones_iniciales=data.observaciones_iniciales,
        indice_salud=100,
        estado="Operativo",
        fecha_inicio_operacion=data.fecha_inicio_operacion,
        empresa_id=usuario_actual.empresa_id  # <--- Vinculación Automática
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    recalcular_indice_salud(str(nuevo.id), db)
    db.refresh(nuevo)
    return nuevo

@app.patch("/api/equipos/{equipo_id}")
async def actualizar_equipo(
    equipo_id: str,
    ubicacion: str = Form(...),
    responsable: Optional[str] = Form(None),
    estado: str = Form(...),
    manual_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    usuario_actual: models.Usuario = Depends(get_current_user)
):
    equipo = db.query(models.Equipo).filter(
        models.Equipo.id == equipo_id,
        models.Equipo.empresa_id == usuario_actual.empresa_id
    ).first()
    
    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    if manual_file:
        nombre_manual = f"manual_{equipo_id}_{manual_file.filename}".replace(" ", "_")
        ruta_manual = os.path.join("uploads", nombre_manual)
        with open(ruta_manual, "wb") as buffer:
            shutil.copyfileobj(manual_file.file, buffer)
        equipo.manual_url = f"/uploads/{nombre_manual}"

    equipo.ubicacion = ubicacion
    equipo.responsable = responsable
    equipo.estado = estado

    db.commit()
    db.refresh(equipo)
    return equipo

# =====================================
# DASHBOARD
# =====================================

@app.get("/api/dashboard")
def obtener_dashboard_stats(db: Session = Depends(get_db), usuario_actual: models.Usuario = Depends(get_current_user)):
    hoy = date.today()
    proximos_7_dias = hoy + timedelta(days=7)
    
    filtro_empresa = models.Equipo.empresa_id == usuario_actual.empresa_id

    total_equipos = db.query(models.Equipo).filter(filtro_empresa).count()
    equipos_operativos = db.query(models.Equipo).filter(func.lower(models.Equipo.estado) == "operativo", filtro_empresa).count()
    porcentaje_operativos = round((equipos_operativos / total_equipos * 100)) if total_equipos > 0 else 0

    conteo_estados = db.query(models.Equipo.estado, func.count(models.Equipo.id)).filter(filtro_empresa).group_by(models.Equipo.estado).all()
    stats_grafico = {estado: conteo for estado, conteo in conteo_estados}

    equipos_criticos = db.query(models.Equipo).filter(models.Equipo.indice_salud < 50, filtro_empresa).order_by(models.Equipo.indice_salud.asc()).all()

    alertas_lista = []

    mants_vencidos = db.query(models.Mantenimiento).join(models.Equipo).filter(
        models.Mantenimiento.estado != "completado",
        models.Mantenimiento.fecha_programada < hoy,
        filtro_empresa
    ).all()
    for m in mants_vencidos:
        alertas_lista.append({"mensaje": f"MANTENIMIENTO VENCIDO: {m.equipo.codigo}", "id": str(m.equipo_id), "clase": "vencido"})

    cals_vencidas = db.query(models.Calibracion).join(models.Equipo).filter(
        models.Calibracion.estado != "completado",
        models.Calibracion.fecha_programada < hoy,
        filtro_empresa
    ).all()
    for c in cals_vencidas:
        alertas_lista.append({"mensaje": f"CALIBRACIÓN VENCIDA: {c.equipo.codigo}", "id": str(c.equipo_id), "clase": "vencido"})

    mants_prox = db.query(models.Mantenimiento).join(models.Equipo).filter(
        models.Mantenimiento.estado != "completado",
        models.Mantenimiento.fecha_programada >= hoy,
        models.Mantenimiento.fecha_programada <= proximos_7_dias,
        filtro_empresa
    ).all()
    for m in mants_prox:
        alertas_lista.append({"mensaje": f"Mantenimiento próximo: {m.equipo.codigo}", "id": str(m.equipo_id), "clase": "proximo"})

    salud_avg = db.query(func.avg(models.Equipo.indice_salud)).filter(filtro_empresa).scalar() or 0

    return {
        "kpis": {
            "operatividad": porcentaje_operativos,
            "mantenimientos": len(mants_vencidos) + len(mants_prox),
            "calibraciones": len(cals_vencidas),
            "salud_general": round(salud_avg),
            "criticos_count": len(equipos_criticos)
        },
        "grafico": stats_grafico,
        "tabla_criticos": [{
            "id": str(e.id), "codigo": e.codigo, "ubicacion": e.ubicacion or "N/A", "salud": e.indice_salud
        } for e in equipos_criticos[:5]],
        "alertas": alertas_lista[:10]
    }


# =====================================
# MANTENIMIENTOS
# =====================================

@app.post("/api/equipos/{equipo_id}/mantenimientos")
def crear_mantenimiento(equipo_id: str, data: schemas.MantenimientoCreate, db: Session = Depends(get_db), usuario_actual: models.Usuario = Depends(get_current_user)):
    equipo = db.query(models.Equipo).filter(models.Equipo.id == equipo_id, models.Equipo.empresa_id == usuario_actual.empresa_id).first()
    if not equipo: raise HTTPException(status_code=404, detail="Equipo no encontrado")

    nuevo = models.Mantenimiento(
        equipo_id=equipo_id,
        fecha_programada=data.fecha_programada,
        tecnico=data.tecnico,
        descripcion=data.descripcion,
        tipo=data.tipo,
        estado=data.estado
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@app.put("/api/mantenimientos/{mantenimiento_id}/ejecutar")
async def ejecutar_mantenimiento(
    mantenimiento_id: int,
    fecha_realizada: str = Form(...),
    tecnico: str = Form(...),
    costo: float = Form(0.0),
    observaciones: str = Form(""),
    tiempo_fuera_servicio: int = Form(0),
    severidad: int = Form(1),
    soporte: UploadFile = File(None),
    db: Session = Depends(get_db),
    usuario_actual: models.Usuario = Depends(get_current_user)
):
    mant = db.query(models.Mantenimiento).join(models.Equipo).filter(
        models.Mantenimiento.id == mantenimiento_id,
        models.Equipo.empresa_id == usuario_actual.empresa_id
    ).first()
    if not mant: raise HTTPException(status_code=404, detail="Mantenimiento no encontrado")

    if soporte:
        file_path = f"uploads/{mantenimiento_id}_{soporte.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(soporte.file, buffer)
        mant.soporte_url = f"/{file_path}"

    mant.fecha_realizada = datetime.strptime(fecha_realizada, '%Y-%m-%d').date()
    mant.tecnico = tecnico
    mant.descripcion = observaciones
    mant.costo = costo
    mant.estado = "completado"
    mant.tiempo_fuera_servicio = tiempo_fuera_servicio
    mant.severidad = severidad

    db.commit()
    recalcular_indice_salud(str(mant.equipo_id), db)
    return {"message": "Mantenimiento ejecutado con éxito"}

@app.get("/api/equipos/{equipo_id}/mantenimientos")
def listar_mantenimientos(equipo_id: str, db: Session = Depends(get_db), usuario_actual: models.Usuario = Depends(get_current_user)):
    equipo = db.query(models.Equipo).filter(models.Equipo.id == equipo_id, models.Equipo.empresa_id == usuario_actual.empresa_id).first()
    if not equipo: raise HTTPException(status_code=404)
    return db.query(models.Mantenimiento).filter(models.Mantenimiento.equipo_id == equipo_id).order_by(models.Mantenimiento.fecha_programada.desc()).all()

@app.patch("/api/mantenimientos/{mantenimiento_id}/reprogramar")
def reprogramar_mantenimiento(mantenimiento_id: int, data: schemas.ReprogramarMantenimiento, db: Session = Depends(get_db), usuario_actual: models.Usuario = Depends(get_current_user)):
    mant = db.query(models.Mantenimiento).join(models.Equipo).filter(models.Mantenimiento.id == mantenimiento_id, models.Equipo.empresa_id == usuario_actual.empresa_id).first()
    if not mant: raise HTTPException(status_code=404, detail="Mantenimiento no encontrado")

    mant.estado = "reprogramado"
    mant.observaciones_modificacion = data.observaciones_modificacion

    nuevo_mantenimiento = models.Mantenimiento(
        equipo_id=mant.equipo_id, tipo=mant.tipo, descripcion=mant.descripcion,
        fecha_programada=data.fecha_programada, tecnico=mant.tecnico, estado="pendiente", severidad=mant.severidad
    )
    db.add(nuevo_mantenimiento)
    db.commit()
    return {"message": "Mantenimiento reprogramado"}

@app.get("/api/equipos/{equipo_id}/mantenimientos-pendientes")
def listar_mantenimientos_pendientes(equipo_id: str, db: Session = Depends(get_db), usuario_actual: models.Usuario = Depends(get_current_user)):
    equipo = db.query(models.Equipo).filter(models.Equipo.id == equipo_id, models.Equipo.empresa_id == usuario_actual.empresa_id).first()
    if not equipo: raise HTTPException(status_code=404)
    return db.query(models.Mantenimiento).filter(models.Mantenimiento.equipo_id == equipo_id, models.Mantenimiento.estado == "pendiente").order_by(models.Mantenimiento.fecha_programada.asc()).all()


# =====================================
# CALIBRACIONES
# =====================================

@app.get("/api/equipos/{equipo_id}/calibraciones", response_model=List[schemas.CalibracionSchema])
def listar_calibraciones(equipo_id: str, db: Session = Depends(get_db), usuario_actual: models.Usuario = Depends(get_current_user)):
    equipo = db.query(models.Equipo).filter(models.Equipo.id == equipo_id, models.Equipo.empresa_id == usuario_actual.empresa_id).first()
    if not equipo: raise HTTPException(status_code=404)
    return db.query(models.Calibracion).filter(models.Calibracion.equipo_id == equipo_id).order_by(models.Calibracion.id.desc()).all()

@app.post("/api/equipos/{equipo_id}/calibraciones", response_model=schemas.CalibracionSchema)
def crear_calibracion(equipo_id: str, calibracion: schemas.CalibracionCreate, db: Session = Depends(get_db), usuario_actual: models.Usuario = Depends(get_current_user)):
    equipo = db.query(models.Equipo).filter(models.Equipo.id == equipo_id, models.Equipo.empresa_id == usuario_actual.empresa_id).first()
    if not equipo: raise HTTPException(status_code=404, detail="Equipo no encontrado")

    nueva_cal = models.Calibracion(**calibracion.dict(), equipo_id=equipo_id, estado="pendiente")
    db.add(nueva_cal)
    db.commit()
    db.refresh(nueva_cal)
    return nueva_cal

@app.patch("/api/calibraciones/{cal_id}/finalizar")
async def finalizar_calibracion(
    cal_id: int,
    fecha_realizada: date = Form(...),
    resultado: str = Form(...),
    observaciones: str = Form(None),
    certificado: UploadFile = File(None),
    db: Session = Depends(get_db),
    usuario_actual: models.Usuario = Depends(get_current_user)
):
    cal = db.query(models.Calibracion).join(models.Equipo).filter(
        models.Calibracion.id == cal_id, models.Equipo.empresa_id == usuario_actual.empresa_id
    ).first()
    if not cal: raise HTTPException(status_code=404, detail="Calibración no encontrada")

    cal.fecha_realizada = fecha_realizada
    cal.resultado = resultado.strip().lower() # Corrección de la variable `data` fantasma
    cal.observaciones = observaciones
    cal.estado = "completado"

    if certificado:
        file_path = os.path.join(f"uploads/cal_{cal_id}_{certificado.filename}")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(certificado.file, buffer)
        cal.certificado_url = f"/uploads/cal_{cal_id}_{certificado.filename}"

    db.commit()
    db.refresh(cal)
    recalcular_indice_salud(str(cal.equipo_id), db)
    return {"ok": True, "url": cal.certificado_url}

@app.patch("/api/calibraciones/{cal_id}/reprogramar")
def reprogramar_calibracion(cal_id: int, data: dict, db: Session = Depends(get_db), usuario_actual: models.Usuario = Depends(get_current_user)):
    cal = db.query(models.Calibracion).join(models.Equipo).filter(models.Calibracion.id == cal_id, models.Equipo.empresa_id == usuario_actual.empresa_id).first()
    if not cal: raise HTTPException(status_code=404, detail="No encontrada")
    
    fecha_original = cal.fecha_programada
    cal.estado = "reprogramado"
    motivo = data.get("observaciones", "Sin motivo")
    cal.observaciones = f"Reprogramada. Fecha original: {fecha_original}. Motivo: {motivo}"

    nueva_cal = models.Calibracion(
        equipo_id=cal.equipo_id, fecha_programada=data.get("fecha_programada"),
        proveedor=cal.proveedor, estado="pendiente", calibracion_padre_id=cal.id
    )
    db.add(nueva_cal)
    db.commit()
    return {"ok": True, "nueva_calibracion_id": nueva_cal.id}

@app.get("/api/equipos/{equipo_id}/calibraciones-pendientes")
def listar_calibraciones_pendientes(equipo_id: str, db: Session = Depends(get_db), usuario_actual: models.Usuario = Depends(get_current_user)):
    equipo = db.query(models.Equipo).filter(models.Equipo.id == equipo_id, models.Equipo.empresa_id == usuario_actual.empresa_id).first()
    if not equipo: raise HTTPException(status_code=404)
    return db.query(models.Calibracion).filter(models.Calibracion.equipo_id == equipo_id, models.Calibracion.estado == "pendiente").order_by(models.Calibracion.fecha_programada.asc()).all()


# =====================================
# PRÉSTAMOS
# =====================================

@app.post("/api/prestamos/salir")
def registrar_salida(data: schemas.PrestamoSalida, db: Session = Depends(get_db), usuario_actual: models.Usuario = Depends(get_current_user)):
    equipo = db.query(models.Equipo).filter(models.Equipo.id == data.equipo_id, models.Equipo.empresa_id == usuario_actual.empresa_id).first()
    if not equipo: raise HTTPException(status_code=404, detail="Equipo no encontrado")

    nuevo_p = models.Prestamo(
        equipo_id=data.equipo_id, responsable_prestamo=data.responsable,
        condiciones_salida=data.condiciones, observaciones_salida=data.obs,
        fecha_salida=date.today(), estado_prestamo="Activo"
    )
    equipo.estado = "En prestamo"
    db.add(nuevo_p)
    db.commit()
    return {"status": "success", "message": "Salida registrada correctamente"}

@app.post("/api/prestamos/regresar")
def registrar_regreso(data: schemas.PrestamoRegreso, db: Session = Depends(get_db), usuario_actual: models.Usuario = Depends(get_current_user)):
    equipo = db.query(models.Equipo).filter(models.Equipo.id == data.equipo_id, models.Equipo.empresa_id == usuario_actual.empresa_id).first()
    if not equipo: raise HTTPException(status_code=404, detail="Equipo no encontrado")

    prestamo = db.query(models.Prestamo).filter(models.Prestamo.equipo_id == data.equipo_id, models.Prestamo.estado_prestamo == "Activo").first()
    if not prestamo: raise HTTPException(status_code=404, detail="No hay préstamo activo")

    prestamo.fecha_regreso = date.today()
    prestamo.condiciones_regreso = data.condiciones
    prestamo.observaciones_regreso = data.obs
    prestamo.estado_prestamo = "Finalizado"
    equipo.estado = "Operativo"
    db.commit()
    return {"status": "success", "message": "Devolución registrada correctamente"}

@app.get("/api/equipos/{equipo_id}/ultimo-prestamo")
def obtener_ultimo_prestamo(equipo_id: str, db: Session = Depends(get_db), usuario_actual: models.Usuario = Depends(get_current_user)):
    equipo = db.query(models.Equipo).filter(models.Equipo.id == equipo_id, models.Equipo.empresa_id == usuario_actual.empresa_id).first()
    if not equipo: raise HTTPException(status_code=404)
    return db.query(models.Prestamo).filter(models.Prestamo.equipo_id == equipo_id, models.Prestamo.estado_prestamo == "Activo").first()

@app.get("/api/equipos/{equipo_id}/historial-prestamos")
def obtener_historial_prestamos(equipo_id: str, db: Session = Depends(get_db), usuario_actual: models.Usuario = Depends(get_current_user)):
    equipo = db.query(models.Equipo).filter(models.Equipo.id == equipo_id, models.Equipo.empresa_id == usuario_actual.empresa_id).first()
    if not equipo: raise HTTPException(status_code=404)
    return db.query(models.Prestamo).filter(models.Prestamo.equipo_id == equipo_id).order_by(models.Prestamo.fecha_salida.desc()).all()


# =====================================
# EVALUACIONES Y PRUEBAS
# =====================================

@app.get("/api/pruebas-por-equipo/{nombre_equipo}")
def obtener_pruebas_por_equipo(nombre_equipo: str, db: Session = Depends(get_db), usuario_actual: models.Usuario = Depends(get_current_user)):
    return db.query(models.PruebaTecnica).join(models.EquipoPrueba, models.PruebaTecnica.id == models.EquipoPrueba.prueba_id).filter(models.EquipoPrueba.nombre_equipo == nombre_equipo).all()

@app.post("/api/evaluar-equipo")
def evaluar_equipo(data: schemas.EvaluacionEquipoCreate, db: Session = Depends(get_db), usuario_actual: models.Usuario = Depends(get_current_user)):
    equipo = db.query(models.Equipo).filter(models.Equipo.id == data.equipo_id, models.Equipo.empresa_id == usuario_actual.empresa_id).first()
    if not equipo: raise HTTPException(status_code=404, detail="Equipo no encontrado")

    evaluacion = models.EvaluacionEquipo(equipo_id=data.equipo_id, responsable=data.responsable, resultado_global="Cumple")
    db.add(evaluacion)
    db.commit()
    db.refresh(evaluacion)

    cumple_global = True
    resultados_guardados = []

    for r in data.resultados:
        cumple_auto = evaluar_resultado(r)
        resultado = models.ResultadoPrueba(
            evaluacion_id=evaluacion.id, prueba_id=r.prueba_id, valor_obtenido=r.valor_obtenido,
            criterio_aplicado=r.criterio_aplicado, valor_min=r.valor_min, valor_max=r.valor_max,
            cumple="Cumple" if cumple_auto else "No cumple"
        )
        if not cumple_auto: cumple_global = False
        db.add(resultado)
        db.flush()
        resultados_guardados.append({"prueba_nombre": resultado.prueba.nombre, "valor_obtenido": resultado.valor_obtenido, "criterio_aplicado": resultado.criterio_aplicado, "cumple": resultado.cumple})

    evaluacion.resultado_global = "Cumple" if cumple_global else "No cumple"
    db.commit()
    recalcular_indice_salud(str(data.equipo_id), db)
    return {"resultado_global": evaluacion.resultado_global, "resultados": resultados_guardados}

@app.get("/api/equipos/{equipo_id}/evaluaciones")
def obtener_evaluaciones_equipo(equipo_id: str, db: Session = Depends(get_db), usuario_actual: models.Usuario = Depends(get_current_user)):
    equipo = db.query(models.Equipo).filter(models.Equipo.id == equipo_id, models.Equipo.empresa_id == usuario_actual.empresa_id).first()
    if not equipo: raise HTTPException(status_code=404)
    evaluaciones = db.query(models.EvaluacionEquipo).options(joinedload(models.EvaluacionEquipo.resultados).joinedload(models.ResultadoPrueba.prueba)).filter(models.EvaluacionEquipo.equipo_id == equipo_id).order_by(models.EvaluacionEquipo.fecha.desc()).all()
    return [{"id": e.id, "fecha": e.fecha, "responsable": e.responsable, "resultado_global": e.resultado_global, "resultados": [{"prueba_id": r.prueba_id, "prueba_nombre": r.prueba.nombre if r.prueba else "N/A", "valor_obtenido": r.valor_obtenido, "criterio_aplicado": r.criterio_aplicado, "cumple": r.cumple} for r in e.resultados]} for e in evaluaciones]

@app.get("/api/evaluacion-existente/{equipo_id}")
def obtener_evaluacion(equipo_id: str, db: Session = Depends(get_db), usuario_actual: models.Usuario = Depends(get_current_user)):
    equipo = db.query(models.Equipo).filter(models.Equipo.id == equipo_id, models.Equipo.empresa_id == usuario_actual.empresa_id).first()
    if not equipo: return []
    evaluacion = db.query(models.EvaluacionEquipo).filter(models.EvaluacionEquipo.equipo_id == equipo_id).order_by(models.EvaluacionEquipo.id.desc()).first()
    if not evaluacion: return []
    return [{"prueba_nombre": r.prueba.nombre if r.prueba else "N/A", "valor_obtenido": r.valor_obtenido, "criterio_aplicado": r.criterio_aplicado, "cumple": r.cumple} for r in evaluacion.resultados]


# =====================================
# FALLAS Y UBICACIONES
# =====================================

@app.post("/api/fallas", response_model=schemas.FallaResponse)
def registrar_falla(falla: schemas.FallaCreate, db: Session = Depends(get_db), usuario_actual: models.Usuario = Depends(get_current_user)):
    equipo = db.query(models.Equipo).filter(models.Equipo.id == falla.equipo_id, models.Equipo.empresa_id == usuario_actual.empresa_id).first()
    if not equipo: raise HTTPException(status_code=404, detail="Equipo no encontrado")
    
    equipo.estado = "En revisión"
    reduccion = {"baja": 5, "media": 10, "alta": 20, "critica": 30}
    equipo.indice_salud = max(0, equipo.indice_salud - reduccion.get(falla.urgencia.lower(), 5))

    nueva_falla = models.Falla(equipo_id=equipo.id, tipo=falla.tipo, urgencia=falla.urgencia, descripcion=falla.descripcion)
    try:
        db.add(nueva_falla)
        db.commit()
        db.refresh(nueva_falla)
        db.refresh(equipo)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al procesar el reporte")
    return nueva_falla

@app.get("/api/equipos/{equipo_id}/fallas", response_model=List[schemas.FallaResponse])
def obtener_historial_fallas(equipo_id: UUID, db: Session = Depends(get_db), usuario_actual: models.Usuario = Depends(get_current_user)):
    equipo = db.query(models.Equipo).filter(models.Equipo.id == equipo_id, models.Equipo.empresa_id == usuario_actual.empresa_id).first()
    if not equipo: raise HTTPException(status_code=404)
    return db.query(models.Falla).filter(models.Falla.equipo_id == equipo_id).order_by(models.Falla.fecha_reporte.desc()).all()

@app.post("/api/equipos/{equipo_id}/ubicacion")
def registrar_ubicacion(equipo_id: UUID, datos: schemas.UbicacionCreate, db: Session = Depends(get_db), usuario_actual: models.Usuario = Depends(get_current_user)):
    equipo = db.query(models.Equipo).filter(models.Equipo.id == equipo_id, models.Equipo.empresa_id == usuario_actual.empresa_id).first()
    if not equipo: raise HTTPException(status_code=404, detail="Equipo no encontrado")

    nueva_ubicacion = models.HistorialUbicacion(
        equipo_id=equipo_id, nombre_personalizado=datos.nombre_personalizado,
        direccion_texto=datos.direccion_texto, latitud=datos.latitud, longitud=datos.longitud
    )
    db.add(nueva_ubicacion)
    db.commit()
    db.refresh(nueva_ubicacion)
    return nueva_ubicacion

@app.get("/api/equipos/{equipo_id}/ubicaciones", response_model=list[schemas.UbicacionResponse])
def obtener_historial_ubicaciones(equipo_id: UUID, db: Session = Depends(get_db), usuario_actual: models.Usuario = Depends(get_current_user)):
    equipo = db.query(models.Equipo).filter(models.Equipo.id == equipo_id, models.Equipo.empresa_id == usuario_actual.empresa_id).first()
    if not equipo: raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return db.query(models.HistorialUbicacion).filter(models.HistorialUbicacion.equipo_id == equipo_id).order_by(models.HistorialUbicacion.fecha_registro.desc()).all()

@app.get("/api/config/mapbox-token")
def get_mapbox_token():
    return {"token": os.getenv("MAPBOX_TOKEN")}

@app.post("/api/equipos/{equipo_id}/recalcular-salud")
def recalcular_salud(equipo_id: str, db: Session = Depends(get_db), usuario_actual: models.Usuario = Depends(get_current_user)):
    equipo = db.query(models.Equipo).filter(models.Equipo.id == equipo_id, models.Equipo.empresa_id == usuario_actual.empresa_id).first()
    if not equipo: raise HTTPException(status_code=404, detail="Equipo no encontrado")
    recalcular_indice_salud(equipo_id, db)
    db.refresh(equipo)
    return {"equipo_id": equipo_id, "indice_salud": equipo.indice_salud}