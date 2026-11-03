from datetime import datetime
from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    dni: Mapped[str] = mapped_column(String(15), unique=True)
    telefono: Mapped[str] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(100), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    equipos: Mapped[list["Equipo"]] = relationship(back_populates="cliente")


class Equipo(Base):
    __tablename__ = "equipos"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"))
    tipo: Mapped[str] = mapped_column(String(30))      # laptop, pc, impresora
    marca: Mapped[str] = mapped_column(String(50))     # HP, Lenovo, Epson...
    modelo: Mapped[str] = mapped_column(String(80))
    serie: Mapped[str | None] = mapped_column(String(80), nullable=True)

    cliente: Mapped["Cliente"] = relationship(back_populates="equipos")
    ordenes: Mapped[list["Orden"]] = relationship(back_populates="equipo")


class Tecnico(Base):
    __tablename__ = "tecnicos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    especialidad: Mapped[str] = mapped_column(String(50))  # hardware, software, impresoras
    anios_experiencia: Mapped[int] = mapped_column(Integer, default=0)

    ordenes: Mapped[list["Orden"]] = relationship(back_populates="tecnico")


class Orden(Base):
    __tablename__ = "ordenes"

    id: Mapped[int] = mapped_column(primary_key=True)
    equipo_id: Mapped[int] = mapped_column(ForeignKey("equipos.id"))
    tecnico_id: Mapped[int | None] = mapped_column(ForeignKey("tecnicos.id"), nullable=True)

    # --- Lo que describe el cliente ---
    descripcion_falla: Mapped[str] = mapped_column(Text)

    # --- Clasificación (la IA sugerirá estos dos campos) ---
    categoria_falla: Mapped[str | None] = mapped_column(String(50), nullable=True)
    prioridad: Mapped[str] = mapped_column(String(10), default="media")  # baja/media/alta

    # --- Flujo ---
    estado: Mapped[str] = mapped_column(String(20), default="recibido")
    fecha_ingreso: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    fecha_entrega: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # --- Estimado (IA) vs. real: así medimos qué tan buena es la predicción ---
    tiempo_estimado_dias: Mapped[float | None] = mapped_column(Float, nullable=True)
    tiempo_real_dias: Mapped[float | None] = mapped_column(Float, nullable=True)
    costo_estimado: Mapped[float | None] = mapped_column(Float, nullable=True)
    costo_real: Mapped[float | None] = mapped_column(Float, nullable=True)

    equipo: Mapped["Equipo"] = relationship(back_populates="ordenes")
    tecnico: Mapped["Tecnico | None"] = relationship(back_populates="ordenes")
    historial: Mapped[list["HistorialEstado"]] = relationship(back_populates="orden")
    repuestos_usados: Mapped[list["OrdenRepuesto"]] = relationship(back_populates="orden")


class HistorialEstado(Base):
    __tablename__ = "historial_estados"

    id: Mapped[int] = mapped_column(primary_key=True)
    orden_id: Mapped[int] = mapped_column(ForeignKey("ordenes.id"))
    estado: Mapped[str] = mapped_column(String(20))
    fecha: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    orden: Mapped["Orden"] = relationship(back_populates="historial")


class Repuesto(Base):
    __tablename__ = "repuestos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    categoria: Mapped[str] = mapped_column(String(50))
    precio: Mapped[float] = mapped_column(Float)
    stock: Mapped[int] = mapped_column(Integer, default=0)

    usos: Mapped[list["OrdenRepuesto"]] = relationship(back_populates="repuesto")


class OrdenRepuesto(Base):
    """Tabla intermedia: una orden puede usar varios repuestos,
    y un repuesto puede usarse en muchas órdenes."""
    __tablename__ = "orden_repuestos"

    id: Mapped[int] = mapped_column(primary_key=True)
    orden_id: Mapped[int] = mapped_column(ForeignKey("ordenes.id"))
    repuesto_id: Mapped[int] = mapped_column(ForeignKey("repuestos.id"))
    cantidad: Mapped[int] = mapped_column(Integer, default=1)

    orden: Mapped["Orden"] = relationship(back_populates="repuestos_usados")
    repuesto: Mapped["Repuesto"] = relationship(back_populates="usos")

class ObservacionTecnica(Base):
    __tablename__ = "observaciones_tecnicas"

    id: Mapped[int] = mapped_column(primary_key=True)

    orden_id: Mapped[int] = mapped_column(
        ForeignKey("ordenes.id"),
        index=True,
    )

    tecnico_id: Mapped[int] = mapped_column(
        ForeignKey("tecnicos.id"),
    )

    texto: Mapped[str] = mapped_column(Text)

    fecha: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
    )