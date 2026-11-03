from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import obtener_db
from models import Tecnico


router = APIRouter(prefix="/tecnicos", tags=["Técnicos"])


class TecnicoRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    especialidad: str
    anios_experiencia: int


@router.get("", response_model=list[TecnicoRespuesta])
def listar_tecnicos(
    limite: int = Query(default=20, ge=1, le=100),
    desplazamiento: int = Query(default=0, ge=0),
    db: Session = Depends(obtener_db),
):
    consulta = (
        select(Tecnico)
        .order_by(Tecnico.id)
        .offset(desplazamiento)
        .limit(limite)
    )

    return db.scalars(consulta).all()