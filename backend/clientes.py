from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import obtener_db
from models import Cliente


router = APIRouter(prefix="/clientes", tags=["Clientes"])


class ClienteCrear(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    nombre: str = Field(min_length=1, max_length=100)
    dni: str = Field(pattern=r"^[0-9]{8}$")
    telefono: str = Field(min_length=1, max_length=20)
    email: EmailStr | None = Field(default=None, max_length=100)


class ClienteRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    dni: str
    telefono: str
    email: str | None
    creado_en: datetime


@router.post("", response_model=ClienteRespuesta, status_code=201)
def crear_cliente(
    datos: ClienteCrear,
    db: Session = Depends(obtener_db),
):
    cliente = Cliente(**datos.model_dump())
    db.add(cliente)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()

        existente = db.scalar(
            select(Cliente.id).where(Cliente.dni == datos.dni)
        )

        if existente is not None:
            raise HTTPException(
                status_code=409,
                detail="Ya existe un cliente con ese DNI.",
            )

        raise

    db.refresh(cliente)
    return cliente


@router.get("", response_model=list[ClienteRespuesta])
def listar_clientes(
    dni: str | None = Query(
        default=None,
        pattern=r"^[0-9]{8}$",
    ),
    limite: int = Query(default=20, ge=1, le=100),
    desplazamiento: int = Query(default=0, ge=0),
    db: Session = Depends(obtener_db),
):
    consulta = select(Cliente)

    if dni is not None:
        consulta = consulta.where(Cliente.dni == dni)

    consulta = (
        consulta
        .order_by(Cliente.id)
        .offset(desplazamiento)
        .limit(limite)
    )

    return db.scalars(consulta).all()


@router.get("/{cliente_id}", response_model=ClienteRespuesta)
def obtener_cliente(
    cliente_id: int,
    db: Session = Depends(obtener_db),
):
    cliente = db.get(Cliente, cliente_id)

    if cliente is None:
        raise HTTPException(
            status_code=404,
            detail="Cliente no encontrado.",
        )

    return cliente