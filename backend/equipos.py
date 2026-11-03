from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import obtener_db
from models import Cliente, Equipo


router = APIRouter(prefix="/equipos", tags=["Equipos"])


class EquipoCrear(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    cliente_id: int = Field(gt=0, strict=True)
    tipo: Literal["laptop", "pc", "impresora"]
    marca: str = Field(min_length=1, max_length=50)
    modelo: str = Field(min_length=1, max_length=80)
    serie: str | None = Field(default=None, min_length=1, max_length=80)


class EquipoRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int
    tipo: str
    marca: str
    modelo: str
    serie: str | None


@router.post("", response_model=EquipoRespuesta, status_code=201)
def crear_equipo(
    datos: EquipoCrear,
    db: Session = Depends(obtener_db),
):
    cliente = db.get(Cliente, datos.cliente_id)

    if cliente is None:
        raise HTTPException(
            status_code=404,
            detail="No existe el cliente indicado.",
        )

    equipo = Equipo(**datos.model_dump())

    db.add(equipo)
    db.commit()
    db.refresh(equipo)

    return equipo


@router.get("", response_model=list[EquipoRespuesta])
def listar_equipos(
    cliente_id: int | None = Query(default=None, gt=0),
    limite: int = Query(default=20, ge=1, le=100),
    desplazamiento: int = Query(default=0, ge=0),
    db: Session = Depends(obtener_db),
):
    consulta = select(Equipo)

    if cliente_id is not None:
        consulta = consulta.where(Equipo.cliente_id == cliente_id)

    consulta = (
        consulta
        .order_by(Equipo.id)
        .offset(desplazamiento)
        .limit(limite)
    )

    return db.scalars(consulta).all()


@router.get("/{equipo_id}", response_model=EquipoRespuesta)
def obtener_equipo(
    equipo_id: int,
    db: Session = Depends(obtener_db),
):
    equipo = db.get(Equipo, equipo_id)

    if equipo is None:
        raise HTTPException(
            status_code=404,
            detail="Equipo no encontrado.",
        )

    return equipo