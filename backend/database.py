from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker


RUTA_BD = Path(__file__).resolve().parent / "servicios.db"

DATABASE_URL = URL.create(
    "sqlite",
    database=str(RUTA_BD),
)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def obtener_db():
    with SessionLocal() as sesion:
        yield sesion