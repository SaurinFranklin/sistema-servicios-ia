from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from models import Equipo, HistorialEstado, Orden, Tecnico
from clasificador import sugerir_fallas
from clientes import ClienteRespuesta
from equipos import EquipoRespuesta
from tecnicos import TecnicoRespuesta
from models import ObservacionTecnica
from sqlalchemy import select
from sqlalchemy.orm import Session
from estimador import estimar_servicio

from database import obtener_db
from models import Equipo, HistorialEstado, Orden


router = APIRouter(prefix="/ordenes", tags=["Órdenes"])

class DiagnosticoConfirmar(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    tecnico_id: int = Field(gt=0, strict=True)

    categoria_falla: Literal[
        "bateria",
        "pantalla",
        "placa_madre",
        "fuente_poder",
        "disco_duro",
        "software",
        "sobrecalentamiento",
        "teclado_touchpad",
        "atasco_papel",
        "cabezal_tinta",
        "fusor_laser",
    ]

class ComparacionValores(BaseModel):
    estimado: float | None
    real: float | None
    diferencia: float | None


class ComparacionOrdenRespuesta(BaseModel):
    orden_id: int
    estado: str
    tiempo_dias: ComparacionValores
    costo_soles: ComparacionValores

class CostoRealRegistrar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    costo_real: float = Field(ge=0, allow_inf_nan=False)

class EstimacionSolicitar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    num_repuestos: int = Field(
        ge=0,
        strict=True,
        description="Número de tipos de repuesto previstos para el servicio.",
    )

class OrdenCambiarEstado(BaseModel):
    model_config = ConfigDict(extra="forbid")

    estado: Literal["en_reparacion", "listo", "entregado"]

class HistorialRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    estado: str
    fecha: datetime

class OrdenCrear(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    equipo_id: int = Field(gt=0, strict=True)
    descripcion_falla: str = Field(min_length=1, max_length=2000)
    prioridad: Literal["baja", "media", "alta"] = "media"

class SugerenciaFalla(BaseModel):
    categoria: str
    puntuacion: float = Field(ge=0, le=1)


class SugerenciasOrdenRespuesta(BaseModel):
    orden_id: int
    sugerencias: list[SugerenciaFalla]


class OrdenRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    equipo_id: int
    tecnico_id: int | None
    descripcion_falla: str
    categoria_falla: str | None
    prioridad: str
    estado: str
    fecha_ingreso: datetime
    fecha_entrega: datetime | None
    tiempo_real_dias: float | None
    tiempo_estimado_dias: float | None
    costo_estimado: float | None
    costo_real: float | None


@router.post("", response_model=OrdenRespuesta, status_code=201)
def crear_orden(
    datos: OrdenCrear,
    db: Session = Depends(obtener_db),
):
    equipo = db.get(Equipo, datos.equipo_id)

    if equipo is None:
        raise HTTPException(
            status_code=404,
            detail="No existe el equipo indicado.",
        )

    fecha = datetime.now()

    orden = Orden(
        equipo_id=datos.equipo_id,
        descripcion_falla=datos.descripcion_falla,
        prioridad=datos.prioridad,
        estado="recibido",
        fecha_ingreso=fecha,
    )

    orden.historial.append(
        HistorialEstado(
            estado="recibido",
            fecha=fecha,
        )
    )

    db.add(orden)
    db.commit()
    db.refresh(orden)

    return orden


@router.get("", response_model=list[OrdenRespuesta])
def listar_ordenes(
    equipo_id: int | None = Query(default=None, gt=0),
    estado: Literal[
        "recibido",
        "diagnostico",
        "en_reparacion",
        "listo",
        "entregado",
    ] | None = Query(default=None),
    limite: int = Query(default=20, ge=1, le=100),
    desplazamiento: int = Query(default=0, ge=0),
    db: Session = Depends(obtener_db),
):
    consulta = select(Orden)

    if equipo_id is not None:
        consulta = consulta.where(Orden.equipo_id == equipo_id)

    if estado is not None:
        consulta = consulta.where(Orden.estado == estado)

    consulta = (
        consulta
        .order_by(Orden.id.desc())
        .offset(desplazamiento)
        .limit(limite)
    )

    return db.scalars(consulta).all()

@router.get("/{orden_id}", response_model=OrdenRespuesta)
def obtener_orden(
    orden_id: int,
    db: Session = Depends(obtener_db),
):
    orden = db.get(Orden, orden_id)

    if orden is None:
        raise HTTPException(
            status_code=404,
            detail="Orden no encontrada.",
        )

    return orden

@router.get(
    "/{orden_id}/sugerencias",
    response_model=SugerenciasOrdenRespuesta,
)
def obtener_sugerencias_orden(
    orden_id: int,
    cantidad: int = Query(default=3, ge=1, le=11),
    db: Session = Depends(obtener_db),
):
    orden = db.get(Orden, orden_id)

    if orden is None:
        raise HTTPException(
            status_code=404,
            detail="Orden no encontrada.",
        )

    sugerencias = sugerir_fallas(
        texto=orden.descripcion_falla,
        cantidad=cantidad,
    )

    return {
        "orden_id": orden.id,
        "sugerencias": sugerencias,
    }

@router.patch(
    "/{orden_id}/diagnostico",
    response_model=OrdenRespuesta,
)
def confirmar_diagnostico(
    orden_id: int,
    datos: DiagnosticoConfirmar,
    db: Session = Depends(obtener_db),
):
    orden = db.get(Orden, orden_id)

    if orden is None:
        raise HTTPException(
            status_code=404,
            detail="Orden no encontrada.",
        )

    tecnico = db.get(Tecnico, datos.tecnico_id)

    if tecnico is None:
        raise HTTPException(
            status_code=404,
            detail="Técnico no encontrado.",
        )

    if orden.estado not in {"recibido", "diagnostico"}:
        raise HTTPException(
            status_code=409,
            detail=(
                "Esta operación solo está disponible para órdenes "
                "en estado recibido o diagnostico."
            ),
        )

    cambio_diagnostico = (
        orden.tecnico_id != tecnico.id
        or orden.categoria_falla != datos.categoria_falla
    )

    if cambio_diagnostico:
        orden.tiempo_estimado_dias = None
        orden.costo_estimado = None

    orden.tecnico_id = tecnico.id
    orden.categoria_falla = datos.categoria_falla

    # Registramos el cambio de estado únicamente si corresponde.
    if orden.estado == "recibido":
        orden.estado = "diagnostico"

        orden.historial.append(
            HistorialEstado(
                estado="diagnostico",
                fecha=datetime.now(),
            )
        )

    db.commit()
    db.refresh(orden)

    return orden

@router.get(
    "/{orden_id}/historial",
    response_model=list[HistorialRespuesta],
)
def consultar_historial(
    orden_id: int,
    db: Session = Depends(obtener_db),
):
    orden = db.get(Orden, orden_id)

    if orden is None:
        raise HTTPException(
            status_code=404,
            detail="Orden no encontrada.",
        )

    consulta = (
        select(HistorialEstado)
        .where(HistorialEstado.orden_id == orden_id)
        .order_by(
            HistorialEstado.fecha,
            HistorialEstado.id,
        )
    )

    return db.scalars(consulta).all()

@router.patch(
    "/{orden_id}/estado",
    response_model=OrdenRespuesta,
)
def cambiar_estado(
    orden_id: int,
    datos: OrdenCambiarEstado,
    db: Session = Depends(obtener_db),
):
    orden = db.get(Orden, orden_id)

    if orden is None:
        raise HTTPException(
            status_code=404,
            detail="Orden no encontrada.",
        )

    # Repetir la misma solicitud no duplica el historial
    # ni modifica una fecha de entrega ya registrada.
    if datos.estado == orden.estado:
        return orden

    siguiente_estado = {
        "diagnostico": "en_reparacion",
        "en_reparacion": "listo",
        "listo": "entregado",
    }

    permitido = siguiente_estado.get(orden.estado)

    if datos.estado != permitido:
        raise HTTPException(
            status_code=409,
            detail=(
                f"No se puede pasar de '{orden.estado}' "
                f"a '{datos.estado}'."
            ),
        )

    ahora = datetime.now()

    if datos.estado == "entregado":
        segundos = (ahora - orden.fecha_ingreso).total_seconds()

        if segundos < 0:
            raise HTTPException(
                status_code=409,
                detail="La entrega no puede ser anterior al ingreso.",
            )

        orden.fecha_entrega = ahora
        orden.tiempo_real_dias = round(segundos / 86400, 4)

    orden.estado = datos.estado

    orden.historial.append(
        HistorialEstado(
            estado=datos.estado,
            fecha=ahora,
        )
    )

    db.commit()
    db.refresh(orden)

    return orden

@router.post(
    "/{orden_id}/estimacion",
    response_model=OrdenRespuesta,
)
def estimar_orden(
    orden_id: int,
    datos: EstimacionSolicitar,
    db: Session = Depends(obtener_db),
):
    orden = db.get(Orden, orden_id)

    if orden is None:
        raise HTTPException(
            status_code=404,
            detail="Orden no encontrada.",
        )

    if orden.estado != "diagnostico":
        raise HTTPException(
            status_code=409,
            detail="Solo se puede estimar una orden en diagnóstico.",
        )

    if not orden.categoria_falla or orden.tecnico is None:
        raise HTTPException(
            status_code=409,
            detail="La orden necesita categoría confirmada y técnico asignado.",
        )

    equipo = orden.equipo
    tecnico = orden.tecnico

    if equipo is None:
        raise HTTPException(
            status_code=409,
            detail="La orden no tiene un equipo válido asociado.",
        )

    resultado = estimar_servicio(
        tipo_equipo=equipo.tipo,
        marca=equipo.marca,
        categoria_falla=orden.categoria_falla,
        tecnico=tecnico.nombre,
        anios_experiencia=tecnico.anios_experiencia,
        num_repuestos=datos.num_repuestos,
        prioridad=orden.prioridad,
    )

    orden.tiempo_estimado_dias = resultado["tiempo_estimado_dias"]
    orden.costo_estimado = resultado["costo_estimado"]

    db.commit()
    db.refresh(orden)

    return orden

@router.patch(
    "/{orden_id}/costo-real",
    response_model=OrdenRespuesta,
)
def registrar_costo_real(
    orden_id: int,
    datos: CostoRealRegistrar,
    db: Session = Depends(obtener_db),
):
    orden = db.get(Orden, orden_id)

    if orden is None:
        raise HTTPException(
            status_code=404,
            detail="Orden no encontrada.",
        )

    if orden.estado not in {"listo", "entregado"}:
        raise HTTPException(
            status_code=409,
            detail=(
                "El costo real se registra cuando el servicio "
                "está listo o entregado."
            ),
        )

    orden.costo_real = round(datos.costo_real, 2)

    db.commit()
    db.refresh(orden)

    return orden

def comparar_valores(estimado, real, decimales):
    diferencia = None

    if estimado is not None and real is not None:
        diferencia = round(real - estimado, decimales)

    return {
        "estimado": estimado,
        "real": real,
        "diferencia": diferencia,
    }


@router.get(
    "/{orden_id}/comparacion",
    response_model=ComparacionOrdenRespuesta,
)
def consultar_comparacion(
    orden_id: int,
    db: Session = Depends(obtener_db),
):
    orden = db.get(Orden, orden_id)

    if orden is None:
        raise HTTPException(
            status_code=404,
            detail="Orden no encontrada.",
        )

    return {
        "orden_id": orden.id,
        "estado": orden.estado,
        "tiempo_dias": comparar_valores(
            orden.tiempo_estimado_dias,
            orden.tiempo_real_dias,
            decimales=4,
        ),
        "costo_soles": comparar_valores(
            orden.costo_estimado,
            orden.costo_real,
            decimales=2,
        ),
    }

class ObservacionCrear(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    texto: str = Field(min_length=1, max_length=3000)


class ObservacionRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    orden_id: int
    tecnico_id: int
    texto: str
    fecha: datetime


@router.post(
    "/{orden_id}/observaciones",
    response_model=ObservacionRespuesta,
    status_code=201,
)
def registrar_observacion(
    orden_id: int,
    datos: ObservacionCrear,
    db: Session = Depends(obtener_db),
):
    orden = db.get(Orden, orden_id)

    if orden is None:
        raise HTTPException(
            status_code=404,
            detail="Orden no encontrada.",
        )

    if orden.estado not in {"diagnostico", "en_reparacion", "listo"}:
        raise HTTPException(
            status_code=409,
            detail=(
                "Las observaciones se registran durante el diagnóstico, "
                "la reparación o cuando el servicio está listo."
            ),
        )

    if orden.tecnico_id is None:
        raise HTTPException(
            status_code=409,
            detail="La orden necesita un técnico asignado.",
        )

    tecnico = db.get(Tecnico, orden.tecnico_id)

    if tecnico is None:
        raise HTTPException(
            status_code=409,
            detail="El técnico asignado no existe.",
        )

    observacion = ObservacionTecnica(
        orden_id=orden.id,
        tecnico_id=tecnico.id,
        texto=datos.texto,
    )

    db.add(observacion)
    db.commit()
    db.refresh(observacion)

    return observacion


@router.get(
    "/{orden_id}/observaciones",
    response_model=list[ObservacionRespuesta],
)
def listar_observaciones(
    orden_id: int,
    limite: int = Query(default=20, ge=1, le=100),
    desplazamiento: int = Query(default=0, ge=0),
    db: Session = Depends(obtener_db),
):
    orden = db.get(Orden, orden_id)

    if orden is None:
        raise HTTPException(
            status_code=404,
            detail="Orden no encontrada.",
        )

    consulta = (
        select(ObservacionTecnica)
        .where(ObservacionTecnica.orden_id == orden_id)
        .order_by(
            ObservacionTecnica.fecha,
            ObservacionTecnica.id,
        )
        .offset(desplazamiento)
        .limit(limite)
    )

    return db.scalars(consulta).all()

class OrdenDetalleRespuesta(BaseModel):
    orden: OrdenRespuesta
    cliente: ClienteRespuesta
    equipo: EquipoRespuesta
    tecnico: TecnicoRespuesta | None
    observaciones: list[ObservacionRespuesta]
    historial: list[HistorialRespuesta]


@router.get(
    "/{orden_id}/detalle",
    response_model=OrdenDetalleRespuesta,
)
def obtener_detalle_orden(
    orden_id: int,
    db: Session = Depends(obtener_db),
):
    orden = db.get(Orden, orden_id)

    if orden is None:
        raise HTTPException(
            status_code=404,
            detail="Orden no encontrada.",
        )

    equipo = orden.equipo

    if equipo is None:
        raise HTTPException(
            status_code=409,
            detail="La orden no tiene un equipo válido asociado.",
        )

    cliente = equipo.cliente

    if cliente is None:
        raise HTTPException(
            status_code=409,
            detail="El equipo no tiene un cliente válido asociado.",
        )

    consulta_observaciones = (
        select(ObservacionTecnica)
        .where(ObservacionTecnica.orden_id == orden.id)
        .order_by(
            ObservacionTecnica.fecha,
            ObservacionTecnica.id,
        )
    )

    consulta_historial = (
        select(HistorialEstado)
        .where(HistorialEstado.orden_id == orden.id)
        .order_by(
            HistorialEstado.fecha,
            HistorialEstado.id,
        )
    )

    observaciones = db.scalars(consulta_observaciones).all()
    historial = db.scalars(consulta_historial).all()

    return {
        "orden": orden,
        "cliente": cliente,
        "equipo": equipo,
        "tecnico": orden.tecnico,
        "observaciones": observaciones,
        "historial": historial,
    }