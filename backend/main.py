from contextlib import asynccontextmanager

from fastapi import FastAPI
from clientes import router as clientes_router
from equipos import router as equipos_router
from ordenes import router as ordenes_router
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from tecnicos import router as tecnicos_router
from pydantic import BaseModel, ConfigDict, Field

from clasificador import cargar_modelos, sugerir_fallas


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Preparamos los modelos antes de aceptar consultas.
    cargar_modelos()
    yield


app = FastAPI(
    title="Sistema de servicios técnicos",
    description="Prototipo de sugerencias de categorías de fallas.",
    version="0.1.0",
    lifespan=lifespan,
)


class SolicitudClasificacion(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    descripcion: str = Field(min_length=1, max_length=2000)
    cantidad: int = Field(default=3, ge=1, le=11, strict=True)


class Sugerencia(BaseModel):
    categoria: str
    puntuacion: float = Field(ge=0, le=1)


@app.get("/")
def inicio():
    return {
        "servicio": "Clasificación de fallas",
        "estado": "disponible",
    }


@app.post("/ia/clasificar", response_model=list[Sugerencia])
def clasificar(solicitud: SolicitudClasificacion):
    return sugerir_fallas(
        texto=solicitud.descripcion,
        cantidad=solicitud.cantidad,
    )

CARPETA_FRONTEND = Path(__file__).resolve().parents[1] / "frontend"

app.mount(
    "/app",
    StaticFiles(directory=str(CARPETA_FRONTEND), html=True),
    name="frontend",
)

app.include_router(clientes_router)
app.include_router(equipos_router)
app.include_router(ordenes_router)
app.include_router(tecnicos_router)