from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Ruta de la base de datos: un archivo llamado servicios.db
DATABASE_URL = "sqlite:///./servicios.db"

# El "engine" es el motor que se comunica con la base de datos
engine = create_engine(DATABASE_URL, echo=False)

# Cada vez que necesitemos hablar con la BD, abrimos una "sesión"
SessionLocal = sessionmaker(bind=engine)


# Todas nuestras tablas heredarán de esta clase base
class Base(DeclarativeBase):
    pass