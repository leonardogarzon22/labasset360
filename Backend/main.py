from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session, joinedload
from database import SessionLocal, engine
import models, schemas
from fastapi.middleware.cors import CORSMiddleware
from datetime import date, datetime
import os
import shutil
from typing import Optional
from uuid import UUID
from fastapi import Form, File, UploadFile
from pydantic import BaseModel
from typing import Optional, List
import math
from sqlalchemy import func
from datetime import timedelta
from fastapi import Query
from dotenv import load_dotenv
from passlib.context import CryptContext
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from database import get_db
from models import Usuario
from schemas import UsuarioLogin
from schemas import UbicacionCreate, UbicacionResponse
from schemas import FallaCreate, FallaResponse
from models import Equipo, HistorialUbicacion
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# Crear carpeta de subidas si no existe
if not os.path.exists("uploads"):
    os.makedirs("uploads")

load_dotenv()
models.Base.metadata.create_all(bind=engine)

app = FastAPI()
@app.get("/")
def home():
    return {"mensaje": "Backend funcionando correctamente"}

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static", StaticFiles(directory="../Frontend"), name="static")

# Página de registro
@app.get("/registro")
def registro_page():
    return FileResponse("Frontend/registrar.html")

# Página login
@app.get("/login")
def login_page():
    return FileResponse("Frontend/login.html")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def actualizar_estados_vencidos(equipo_id: str, db: Session):

    hoy = date.today()

    # 🔧 MANTENIMIENTOS
    mantenimientos = db.query(models.Mantenimiento).filter(
        models.Mantenimiento.equipo_id == equipo_id,
        models.Mantenimiento.estado != "completado"
    ).all()

    for m in mantenimientos:
        if m.fecha_programada and m.fecha_programada < hoy:
            m.estado = "vencido"

    # 🧪 CALIBRACIONES
    calibraciones = db.query(models.Calibracion).filter(
        models.Calibracion.equipo_id == equipo_id,
        models.Calibracion.estado != "completado"
    ).all()

    for c in calibraciones:
        if c.fecha_programada and c.fecha_programada < hoy:
            c.estado = "vencida"

    db.commit()

def calcular_weibull(equipo, db, hoy):

    # 1️⃣ Validación básica
    if not equipo.fecha_inicio_operacion:
        return 100

    # 2️⃣ Tiempo calendario en días
    t = (hoy - equipo.fecha_inicio_operacion).days

    if t <= 0:
        return 100

    # 3️⃣ Calcular horas acumuladas automáticamente (8h promedio/día)
    equipo.horas_acumuladas = t * 8

    # 4️⃣ Obtener mantenimientos correctivos completados
    correctivos = db.query(models.Mantenimiento).filter(
        models.Mantenimiento.equipo_id == equipo.id,
        models.Mantenimiento.tipo == "correctivo",
        models.Mantenimiento.estado == "completado"
    ).all()

    # 5️⃣ Si nunca ha fallado → confiabilidad alta
    if len(correctivos) == 0:
        return 100

    # 6️⃣ Calcular impacto ponderado real
    impacto_total = 0
    tiempo_total_paro = 0

    for c in correctivos:
        severidad = c.severidad or 1
        dias_paro = c.tiempo_fuera_servicio or 0

        # Impacto ponderado industrial
        impacto = severidad * (1 + dias_paro * 0.05)

        impacto_total += impacto
        tiempo_total_paro += dias_paro

    # 7️⃣ Parámetro beta dinámico
    frecuencia = impacto_total / t

    if frecuencia < 0.001:
        beta = 1.2
    elif frecuencia < 0.005:
        beta = 1.8
    else:
        beta = 2.5

    # 8️⃣ Parámetro eta (vida característica ajustada)
    eta = t / impacto_total
    eta = max(eta, 1)

    # 9️⃣ Función Weibull
    R_t = math.exp(-((t / eta) ** beta))

    # 🔟 Penalización adicional por tiempo total parado
    penalizacion_disponibilidad = min(tiempo_total_paro * 0.2, 20)

    salud = (R_t * 100) - penalizacion_disponibilidad

    return max(min(salud, 100), 0)

def recalcular_indice_salud(equipo_id: str, db: Session):

    equipo = db.query(models.Equipo).filter(
        models.Equipo.id == equipo_id
    ).first()

    if not equipo:
        return

    # 1️⃣ Actualizar vencidos
    actualizar_estados_vencidos(equipo_id, db)

    hoy = date.today()

    # 2️⃣ WEIBULL (40%)
    score_weibull = calcular_weibull(equipo, db, hoy) * 0.40

    # 3️⃣ MANTENIMIENTOS VENCIDOS (20%)
    mantenimientos_vencidos = db.query(models.Mantenimiento).filter(
        models.Mantenimiento.equipo_id == equipo_id,
        models.Mantenimiento.estado == "vencido"
    ).count()

    score_mantenimiento = max(0, 20 - (mantenimientos_vencidos * 5))

    # 4️⃣ CALIBRACIONES VENCIDAS (20%)
    calibraciones_vencidas = db.query(models.Calibracion).filter(
        models.Calibracion.equipo_id == equipo_id,
        models.Calibracion.estado == "vencida"
    ).count()

    score_calibracion = max(0, 20 - (calibraciones_vencidas * 10))

    # 5️⃣ EVALUACIÓN ISO (10%)
    ultima_eval = db.query(models.EvaluacionEquipo).filter(
        models.EvaluacionEquipo.equipo_id == equipo_id
    ).order_by(models.EvaluacionEquipo.fecha.desc()).first()

    score_iso = 10
    if ultima_eval and ultima_eval.resultado_global.lower() == "no cumple":
        score_iso = 0

    # 6️⃣ DISPONIBILIDAD / ESTADO (10%)
    score_estado = 10

    if equipo.estado:
        estado = equipo.estado.lower()

        if estado == "no operativo":
            score_estado = 0
        elif estado == "en revisión":
            score_estado = 5
        elif estado == "en prestamo":
            score_estado = 8

    # 7️⃣ SUMATORIA FINAL
    salud = (
        score_weibull +
        score_mantenimiento +
        score_calibracion +
        score_iso +
        score_estado
    )

    salud = max(0, min(100, salud))

    equipo.indice_salud = round(salud, 2)

    db.commit()

def evaluar_resultado(r):

    try:
        valor = float(r.valor_obtenido)
    except:
        return "No cumple"

    if r.valor_min is not None and r.valor_max is not None:
        if r.valor_min <= valor <= r.valor_max:
            return "Cumple"
        else:
            return "No cumple"

    if r.valor_min is not None:
        if valor >= r.valor_min:
            return "Cumple"
        else:
            return "No cumple"

    if r.valor_max is not None:
        if valor <= r.valor_max:
            return "Cumple"
        else:
            return "No cumple"

    return "No cumple"
# =====================================
# ENDPOINTS DE EQUIPOS
# =====================================

@app.get("/api/tipos-equipos")
def listar_tipos(db: Session = Depends(get_db)):
    return db.query(models.TipoEquipo).all()

@app.get("/api/equipos")
def listar_equipos(db: Session = Depends(get_db)):
    return db.query(models.Equipo).all()

@app.get("/api/equipos/{equipo_id}")
def obtener_equipo(equipo_id: UUID, db: Session = Depends(get_db)):
    equipo = db.query(models.Equipo).options(
        joinedload(models.Equipo.tipo_relacion)
    ).filter(models.Equipo.id == equipo_id).first()

    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

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
def crear_equipo(data: schemas.EquipoCreate, db: Session = Depends(get_db)):
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
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    recalcular_indice_salud(nuevo.id, db)
    db.refresh(nuevo)
    return nuevo

@app.patch("/api/equipos/{equipo_id}")
async def actualizar_equipo(
    equipo_id: str,
    ubicacion: str = Form(...),
    responsable: Optional[str] = Form(None),
    estado: str = Form(...),
    manual_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    equipo = db.query(models.Equipo).filter(models.Equipo.id == equipo_id).first()
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
# GESTIÓN DE PRÉSTAMOS (AHORA USANDO JSON)
# =====================================

@app.post("/api/prestamos/salir")
def registrar_salida(
    data: schemas.PrestamoSalida,
    db: Session = Depends(get_db)
):
    nuevo_p = models.Prestamo(
        equipo_id=data.equipo_id,
        responsable_prestamo=data.responsable,
        condiciones_salida=data.condiciones,
        observaciones_salida=data.obs,
        fecha_salida=date.today(),
        estado_prestamo="Activo"
    )

    equipo = db.query(models.Equipo).filter(
        models.Equipo.id == data.equipo_id
    ).first()

    if equipo:
        equipo.estado = "En prestamo"

    db.add(nuevo_p)
    db.commit()

    return {"status": "success", "message": "Salida registrada correctamente"}

@app.post("/api/prestamos/regresar")
def registrar_regreso(
    data: schemas.PrestamoRegreso,
    db: Session = Depends(get_db)
):
    prestamo = db.query(models.Prestamo).filter(
        models.Prestamo.equipo_id == data.equipo_id,
        models.Prestamo.estado_prestamo == "Activo"
    ).first()

    if not prestamo:
        raise HTTPException(status_code=404, detail="No hay un préstamo activo para este equipo")

    prestamo.fecha_regreso = date.today()
    prestamo.condiciones_regreso = data.condiciones
    prestamo.observaciones_regreso = data.obs
    prestamo.estado_prestamo = "Finalizado"

    equipo = db.query(models.Equipo).filter(
        models.Equipo.id == data.equipo_id
    ).first()

    if equipo:
        equipo.estado = "Operativo"

    db.commit()

    return {"status": "success", "message": "Devolución registrada correctamente"}

# =====================================
# CONSULTAS DE PRÉSTAMOS
# =====================================

@app.get("/api/equipos/{equipo_id}/ultimo-prestamo")
def obtener_ultimo_prestamo(equipo_id: str, db: Session = Depends(get_db)):
    return db.query(models.Prestamo).filter(
        models.Prestamo.equipo_id == equipo_id,
        models.Prestamo.estado_prestamo == "Activo"
    ).first()

@app.get("/api/equipos/{equipo_id}/historial-prestamos")
def obtener_historial_prestamos(equipo_id: str, db: Session = Depends(get_db)):
    return db.query(models.Prestamo).filter(
        models.Prestamo.equipo_id == equipo_id
    ).order_by(models.Prestamo.fecha_salida.desc()).all()

# =====================================
# FINALIZAR ACTIVIDADES TÉCNICAS
# =====================================

# =====================================
# CONFIRMACION DE APTITUD ISO 17025
# =====================================

@app.get("/api/pruebas-por-equipo/{nombre_equipo}")
def obtener_pruebas_por_equipo(nombre_equipo: str, db: Session = Depends(get_db)):
    pruebas = db.query(models.PruebaTecnica).join(
        models.EquipoPrueba,
        models.PruebaTecnica.id == models.EquipoPrueba.prueba_id
    ).filter(
        models.EquipoPrueba.nombre_equipo == nombre_equipo
    ).all()

    return pruebas

@app.post("/api/evaluar-equipo")
def evaluar_equipo(data: schemas.EvaluacionEquipoCreate, db: Session = Depends(get_db)):

    evaluacion = models.EvaluacionEquipo(
        equipo_id=data.equipo_id,
        responsable=data.responsable,
        resultado_global="Cumple"
    )

    db.add(evaluacion)
    db.commit()
    db.refresh(evaluacion)

    cumple_global = True
    resultados_guardados = []

    for r in data.resultados:

        cumple_auto = evaluar_resultado(r)

        resultado = models.ResultadoPrueba(
            evaluacion_id = evaluacion.id,
            prueba_id = r.prueba_id,
            valor_obtenido = r.valor_obtenido,
            criterio_aplicado = r.criterio_aplicado,
            valor_min = r.valor_min,
            valor_max = r.valor_max,
            cumple = "Cumple" if cumple_auto else "No cumple"
        )

        if not cumple_auto:
            cumple_global = False

        db.add(resultado)
        db.flush()  # 👈 permite acceder a la relación sin commit

        resultados_guardados.append({
            "prueba_nombre": resultado.prueba.nombre,
            "valor_obtenido": resultado.valor_obtenido,
            "criterio_aplicado": resultado.criterio_aplicado,
            "cumple": resultado.cumple
        })

    evaluacion.resultado_global = "Cumple" if cumple_global else "No cumple"

    equipo = db.query(models.Equipo).filter(
        models.Equipo.id == data.equipo_id
    ).first()

    if equipo:
            db.commit()

    recalcular_indice_salud(str(data.equipo_id), db)
    return {
        "resultado_global": evaluacion.resultado_global,
        "resultados": resultados_guardados
    }


@app.get("/api/equipos/{equipo_id}/evaluaciones")
def obtener_evaluaciones_equipo(equipo_id: str, db: Session = Depends(get_db)):

    evaluaciones = db.query(models.EvaluacionEquipo).options(
        joinedload(models.EvaluacionEquipo.resultados).joinedload(
            models.ResultadoPrueba.prueba
        )
    ).filter(
        models.EvaluacionEquipo.equipo_id == equipo_id
    ).order_by(
        models.EvaluacionEquipo.fecha.desc()
    ).all()

    resultado = []

    for e in evaluaciones:
        resultado.append({
            "id": e.id,
            "fecha": e.fecha,
            "responsable": e.responsable,
            "resultado_global": e.resultado_global,
            "resultados": [
                {
                    "prueba_id": r.prueba_id,
                    "prueba_nombre": r.prueba.nombre if r.prueba else "N/A",
                    "valor_obtenido": r.valor_obtenido,
                    "criterio_aplicado": r.criterio_aplicado,
                    "cumple": r.cumple
                }
                for r in e.resultados
            ]
        })

    return resultado
# =====================================
# MANTENIMIENTOS
# =====================================

# main.py

# 1. Endpoint para PROGRAMAR (Modal 1)
@app.post("/api/equipos/{equipo_id}/mantenimientos")
def crear_mantenimiento(
    equipo_id: str,
    data: schemas.MantenimientoCreate,
    db: Session = Depends(get_db)
):
    nuevo = models.Mantenimiento(
        equipo_id=equipo_id,
        fecha_programada=data.fecha_programada,
        # ASIGNACIÓN CORRECTA:
        tecnico=data.tecnico,      # El técnico va a la columna tecnico
        descripcion=data.descripcion, # La descripción va a la columna descripcion
        tipo=data.tipo,
        estado=data.estado
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

# 2. Endpoint para EJECUTAR y cargar archivo (Modal 2)
@app.put("/api/mantenimientos/{mantenimiento_id}/ejecutar")
async def ejecutar_mantenimiento(
    mantenimiento_id: int,
    fecha_realizada: str = Form(...),
    tecnico: str = Form(...),        # Nombre del técnico
    costo: float = Form(0.0),
    observaciones: str = Form(""),   # Lo que hizo el técnico
    tiempo_fuera_servicio: int = Form(0),
    severidad: int = Form(1),
    soporte: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    mant = db.query(models.Mantenimiento).filter(models.Mantenimiento.id == mantenimiento_id).first()
    if not mant:
        raise HTTPException(status_code=404, detail="Mantenimiento no encontrado")

    if soporte:
        file_path = f"uploads/{mantenimiento_id}_{soporte.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(soporte.file, buffer)
        mant.soporte_url = f"/{file_path}"

    # --- CORRECCIÓN DE COLUMNAS ---
    mant.fecha_realizada = datetime.strptime(fecha_realizada, '%Y-%m-%d').date()
    mant.tecnico = tecnico          # Se guarda en la columna tecnico
    mant.descripcion = observaciones # Las observaciones van a descripcion
    # ------------------------------

    mant.costo = costo
    mant.estado = "completado"
    mant.tiempo_fuera_servicio = tiempo_fuera_servicio
    mant.severidad = severidad

    db.commit()
    recalcular_indice_salud(str(mant.equipo_id), db)
    return {"message": "Mantenimiento ejecutado con éxito"}

@app.get("/api/equipos/{equipo_id}/mantenimientos")
def listar_mantenimientos(
    equipo_id: str,
    db: Session = Depends(get_db)
):
    return db.query(models.Mantenimiento).filter(
        models.Mantenimiento.equipo_id == equipo_id
    ).order_by(models.Mantenimiento.fecha_programada.desc()).all()

# =====================================
# ENDPOINT PARA EVALUACIÓN EXISTENTE
# =====================================

@app.get("/api/evaluacion-existente/{equipo_id}")
def obtener_evaluacion(equipo_id: str, db: Session = Depends(get_db)):
    # Buscamos la última evaluación registrada para este equipo
    evaluacion = db.query(models.EvaluacionEquipo).filter(
        models.EvaluacionEquipo.equipo_id == equipo_id
    ).order_by(models.EvaluacionEquipo.id.desc()).first()

    # Si no hay evaluación, devolvemos una lista vacía para que el frontend no de error
    if not evaluacion:
        return []

    # Devolvemos los resultados de las pruebas de esa evaluación
    return [
        {
            "prueba_nombre": r.prueba.nombre if r.prueba else "N/A",
            "valor_obtenido": r.valor_obtenido,
            "criterio_aplicado": r.criterio_aplicado,
            "cumple": r.cumple
        }
        for r in evaluacion.resultados
    ]



# =====================================
# CALIBRACIONES (VERSIÓN CORREGIDA)
# =====================================

@app.get("/api/equipos/{equipo_id}/calibraciones", response_model=List[schemas.CalibracionSchema])
def listar_calibraciones(equipo_id: str, db: Session = Depends(get_db)):
    try:
        # Usamos una consulta que evita errores si faltan columnas en la BD
        return db.query(models.Calibracion).filter(
            models.Calibracion.equipo_id == equipo_id
        ).order_by(models.Calibracion.id.desc()).all()
    except Exception as e:
        print(f"Error en listar_calibraciones: {e}")
        return []


@app.post("/api/calibraciones/{cal_id}/completar")
async def finalizar_calibracion(
    cal_id: int,
    resultado: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    cal = db.query(models.Calibracion).filter(models.Calibracion.id == cal_id).first()
    if not cal:
        raise HTTPException(status_code=404, detail="Calibración no encontrada")

    nombre_archivo = f"cert_{cal_id}_{file.filename}".replace(" ", "_")
    file_path = os.path.join("uploads", nombre_archivo)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    cal.resultado = data.resultado.lower()
    cal.certificado_url = f"/uploads/{nombre_archivo}"
    cal.estado = "completado"
    cal.fecha_realizada = date.today()

    db.commit()
    recalcular_indice_salud(str(cal.equipo_id), db)
    return {"message": "Éxito", "url": cal.certificado_url}


# Cambia schemas.Calibracion por schemas.CalibracionSchema
@app.post("/api/equipos/{equipo_id}/calibraciones", response_model=schemas.CalibracionSchema)
def crear_calibracion(
    equipo_id: str,
    calibracion: schemas.CalibracionCreate, # Este nombre sí existe en tu schemas.py
    db: Session = Depends(get_db)
):
    db_equipo = db.query(models.Equipo).filter(models.Equipo.id == equipo_id).first()
    if not db_equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    # Se crea la instancia usando los datos validados
    nueva_cal = models.Calibracion(
        **calibracion.dict(),
        equipo_id=equipo_id,
        estado="pendiente"
    )

    db.add(nueva_cal)
    db.commit()
    db.refresh(nueva_cal)
    return nueva_cal

@app.patch("/api/calibraciones/{cal_id}/reprogramar")
def reprogramar_calibracion(
    cal_id: int,
    data: dict,
    db: Session = Depends(get_db)
):

    cal = db.query(models.Calibracion).filter(
        models.Calibracion.id == cal_id
    ).first()

    if not cal:
        raise HTTPException(status_code=404, detail="No encontrada")

    try:


        fecha_original = cal.fecha_programada

        cal.estado = "reprogramado"

        motivo = data.get("observaciones", "Sin motivo")

        cal.observaciones = (
            f"Reprogramada. "
            f"Fecha original: {fecha_original}. "
            f"Motivo: {motivo}"
        )


        nueva_cal = models.Calibracion(
            equipo_id=cal.equipo_id,
            fecha_programada=data.get("fecha_programada"),
            proveedor=cal.proveedor,
            estado="pendiente",
            calibracion_padre_id=cal.id
        )

        db.add(nueva_cal)

        db.commit()

        db.refresh(nueva_cal)

        return {
            "ok": True,
            "nueva_calibracion_id": nueva_cal.id
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# =====================================
# RECALCULAR INDICE DE SALUD
# =====================================

@app.post("/api/equipos/{equipo_id}/recalcular-salud")
def recalcular_salud(equipo_id: str, db: Session = Depends(get_db)):

    equipo = db.query(models.Equipo).filter(
        models.Equipo.id == equipo_id
    ).first()

    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    recalcular_indice_salud(equipo_id, db)

    db.refresh(equipo)

    return {
        "equipo_id": equipo_id,
        "indice_salud": equipo.indice_salud
    }

@app.post("/api/fallas", response_model=schemas.FallaResponse)
def registrar_falla(falla: schemas.FallaCreate, db: Session = Depends(get_db)):
    # 1. Buscar el equipo
    equipo = db.query(models.Equipo).filter(models.Equipo.id == falla.equipo_id).first()
    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    
    # 2. Lógica de negocio: Estado y Salud
    # Pasamos a "En revisión" automáticamente
    equipo.estado = "En revisión"
    
    # Penalización de salud: Baja(5), Media(10), Alta(20), Crítica(30)
    reduccion = {"baja": 5, "media": 10, "alta": 20, "critica": 30}
    equipo.indice_salud = max(0, equipo.indice_salud - reduccion.get(falla.urgencia.lower(), 5))

    # 3. Registrar en la tabla 'fallas' (sin tocar mantenimientos)
    nueva_falla = models.Falla(
        equipo_id=equipo.id,
        tipo=falla.tipo,
        urgencia=falla.urgencia,
        descripcion=falla.descripcion
    )
    
    # 4. Transacción atómica
    try:
        db.add(nueva_falla)
        db.commit()
        db.refresh(nueva_falla)
        db.refresh(equipo) # Actualizamos el equipo para reflejar cambios
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al procesar el reporte")
    
    return nueva_falla

@app.get("/api/equipos/{equipo_id}/fallas", response_model=List[schemas.FallaResponse])
def obtener_historial_fallas(equipo_id: UUID, db: Session = Depends(get_db)):
    fallas = db.query(models.Falla)\
               .filter(models.Falla.equipo_id == equipo_id)\
               .order_by(models.Falla.fecha_reporte.desc())\
               .all()
    return fallas

@app.patch("/api/calibraciones/{cal_id}/finalizar")
async def finalizar_calibracion(
    cal_id: int,
    fecha_realizada: date = Form(...),
    resultado: str = Form(...),
    observaciones: str = Form(None),
    certificado: UploadFile = File(None),
    db: Session = Depends(get_db)
):

    cal = db.query(models.Calibracion).filter(
        models.Calibracion.id == cal_id
    ).first()

    if not cal:
        raise HTTPException(status_code=404, detail="No encontrada")

    cal.fecha_realizada = fecha_realizada
    cal.resultado = resultado.strip().lower()
    cal.observaciones = observaciones
    cal.estado = "completado"

    if certificado:
        file_path = os.path.join( f"uploads/cal_{cal_id}_{certificado.filename}")

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(certificado.file, buffer)

        # Guardamos la ruta en base de datos
        cal.certificado_url = f"/uploads/cal_{cal_id}_{certificado.filename}"


    db.commit()
    db.refresh(cal)
    recalcular_indice_salud(str(cal.equipo_id), db)
    return {"ok": True}

@app.get("/api/dashboard")
def obtener_dashboard_stats(db: Session = Depends(get_db)):
    hoy = date.today()
    proximos_7_dias = hoy + timedelta(days=7)

    # 1. KPIs de cabecera
    total_equipos = db.query(models.Equipo).count()
    equipos_operativos = db.query(models.Equipo).filter(func.lower(models.Equipo.estado) == "operativo").count()
    porcentaje_operativos = round((equipos_operativos / total_equipos * 100)) if total_equipos > 0 else 0

    # 2. Distribución para el Gráfico (Dona)
    conteo_estados = db.query(models.Equipo.estado, func.count(models.Equipo.id)).group_by(models.Equipo.estado).all()
    stats_grafico = {estado: conteo for estado, conteo in conteo_estados}

    # 3. Equipos Críticos (Salud < 50%)
    equipos_criticos = db.query(models.Equipo).filter(models.Equipo.indice_salud < 50).order_by(models.Equipo.indice_salud.asc()).all()

    # --- 4. LÓGICA DE ALERTAS DISPARADAS ---
    alertas_lista = []

    # A. Mantenimientos Vencidos (Urgencia Máxima)
    mants_vencidos = db.query(models.Mantenimiento).filter(
        models.Mantenimiento.estado != "completado",
        models.Mantenimiento.fecha_programada < hoy
    ).join(models.Equipo).all()
    for m in mants_vencidos:
        alertas_lista.append({
            "mensaje": f"MANTENIMIENTO VENCIDO: {m.equipo.codigo}",
            "id": str(m.equipo_id),
            "clase": "vencido"
        })

    # B. Calibraciones Vencidas (Urgencia Máxima)
    cals_vencidas = db.query(models.Calibracion).filter(
        models.Calibracion.estado != "completado",
        models.Calibracion.fecha_programada < hoy
    ).join(models.Equipo).all()
    for c in cals_vencidas:
        alertas_lista.append({
            "mensaje": f"CALIBRACIÓN VENCIDA: {c.equipo.codigo}",
            "id": str(c.equipo_id),
            "clase": "vencido"
        })

    # C. Mantenimientos Próximos (Próximos 7 días)
    mants_prox = db.query(models.Mantenimiento).filter(
        models.Mantenimiento.estado != "completado",
        models.Mantenimiento.fecha_programada >= hoy,
        models.Mantenimiento.fecha_programada <= proximos_7_dias
    ).join(models.Equipo).all()
    for m in mants_prox:
        alertas_lista.append({
            "mensaje": f"Mantenimiento próximo: {m.equipo.codigo}",
            "id": str(m.equipo_id),
            "clase": "proximo"
        })

    salud_avg = db.query(func.avg(models.Equipo.indice_salud)).scalar() or 0

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
            "id": str(e.id),
            "codigo": e.codigo,
            "ubicacion": e.ubicacion or "N/A",
            "salud": e.indice_salud
        } for e in equipos_criticos[:5]],
        "alertas": alertas_lista[:10]  # Mostramos hasta 10 alertas mezcladas
    }


@app.patch("/api/mantenimientos/{mantenimiento_id}/reprogramar")
def reprogramar_mantenimiento(
    mantenimiento_id: int,
    data: schemas.ReprogramarMantenimiento,
    db: Session = Depends(get_db)
):

    mant = db.query(models.Mantenimiento).filter(
        models.Mantenimiento.id == mantenimiento_id
    ).first()

    if not mant:
        raise HTTPException(status_code=404, detail="Mantenimiento no encontrado")


    mant.estado = "reprogramado"
    mant.observaciones_modificacion = data.observaciones_modificacion


    nuevo_mantenimiento = models.Mantenimiento(
        equipo_id=mant.equipo_id,
        tipo=mant.tipo,
        descripcion=mant.descripcion,
        fecha_programada=data.fecha_programada,
        tecnico=mant.tecnico,
        estado="pendiente",
        severidad=mant.severidad
    )

    db.add(nuevo_mantenimiento)

    db.commit()

    return {
        "message": "Mantenimiento reprogramado correctamente"
    }

@app.get("/api/equipos/{equipo_id}/mantenimientos-pendientes")
def listar_mantenimientos_pendientes(
    equipo_id: str,
    db: Session = Depends(get_db)
):

    return db.query(models.Mantenimiento).filter(
        models.Mantenimiento.equipo_id == equipo_id,
        models.Mantenimiento.estado == "pendiente"
    ).order_by(
        models.Mantenimiento.fecha_programada.asc()
    ).all()
    
@app.get("/api/equipos/{equipo_id}/calibraciones-pendientes")
def listar_calibraciones_pendientes(
    equipo_id: str,
    db: Session = Depends(get_db)
):

    return db.query(models.Calibracion).filter(
        models.Calibracion.equipo_id == equipo_id,
        models.Calibracion.estado == "pendiente"
    ).order_by(
        models.Calibracion.fecha_programada.asc()
    ).all()

@app.get("/api/config/mapbox-token")
def get_mapbox_token():
    return {"token": os.getenv("MAPBOX_TOKEN")}


@app.get("/api/equipos/{equipo_id}/historial-ubicaciones", response_model=List[schemas.UbicacionResponse])
def obtener_historial_ubicaciones(equipo_id: UUID, db: Session = Depends(get_db)):
    return (
        db.query(models.HistorialUbicacion)
        .filter(models.HistorialUbicacion.equipo_id == equipo_id)
        .order_by(models.HistorialUbicacion.fecha_registro.desc())
        .all()
    )

# @app.get("/api/equipos/{equipo_id}/ubicaciones")
# def listar_ubicaciones(equipo_id: str, db: Session = Depends(get_db)):
    # return db.query(models.UbicacionEquipo).filter(
        # models.UbicacionEquipo.equipo_id == equipo_id
    # ).order_by(models.UbicacionEquipo.fecha_registro.desc()).all()

@app.post("/api/registro", response_model=schemas.UsuarioResponse)
def registrar_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    # 1. Verificar si el email ya existe
    db_user = db.query(models.Usuario).filter(models.Usuario.email == usuario.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    # 2. Verificar áreas críticas
    areas_criticas = ['Calidad', 'Dirección Laboratorio', 'Coordinación Laboratorio']
    if usuario.area in areas_criticas:
        existe_area = db.query(models.Usuario).filter(models.Usuario.area == usuario.area).first()
        if existe_area:
            raise HTTPException(status_code=400, detail=f"Ya existe un responsable para el área de {usuario.area}")

    # 3. Crear usuario
    hashed_pw = pwd_context.hash(usuario.password)
    nuevo_usuario = models.Usuario(
        nombre=usuario.nombre,
        apellido=usuario.apellido,
        laboratorio=usuario.laboratorio,
        area=usuario.area,
        email=usuario.email,
        hashed_password=hashed_pw
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
def login(usuario: UsuarioLogin, db: Session = Depends(get_db)):

    user = db.query(Usuario).filter(Usuario.email == usuario.email).first()

    if not user:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    if not pwd_context.verify(usuario.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    return {"message": "Login exitoso"}

@app.post("/api/equipos/{equipo_id}/ubicacion")
def registrar_ubicacion(equipo_id: UUID, datos: UbicacionCreate, db: Session = Depends(get_db)):

    equipo = db.query(Equipo).filter(Equipo.id == equipo_id).first()

    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    nueva_ubicacion = HistorialUbicacion(
        equipo_id=equipo_id,
        nombre_personalizado=datos.nombre_personalizado,
        direccion_texto=datos.direccion_texto,
        latitud=datos.latitud,
        longitud=datos.longitud
    )

    db.add(nueva_ubicacion)
    db.commit()
    db.refresh(nueva_ubicacion)

    return nueva_ubicacion
@app.get("/api/equipos/{equipo_id}/ubicaciones", response_model=list[UbicacionResponse])
def obtener_historial(equipo_id: UUID, db: Session = Depends(get_db)):

    return db.query(HistorialUbicacion)\
        .filter(HistorialUbicacion.equipo_id == equipo_id)\
        .order_by(HistorialUbicacion.fecha_registro.desc())\
        .all()
