from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


RAIZ = Path(__file__).resolve().parents[1]
CARPETA_MODELOS = RAIZ / "ml/models"


@lru_cache(maxsize=1)
def cargar_estimadores():
    modelo_tiempo = joblib.load(
        CARPETA_MODELOS / "modelo_tiempo.pkl"
    )
    modelo_costo = joblib.load(
        CARPETA_MODELOS / "modelo_costo.pkl"
    )

    return modelo_tiempo, modelo_costo


def estimar_servicio(
    *,
    tipo_equipo: str,
    marca: str,
    categoria_falla: str,
    tecnico: str,
    anios_experiencia: int,
    num_repuestos: int,
    prioridad: str,
) -> dict:
    entrada = pd.DataFrame([{
        "tipo_equipo": tipo_equipo,
        "marca": marca,
        "categoria_falla": categoria_falla,
        "tecnico": tecnico,
        "anios_experiencia": anios_experiencia,
        "num_repuestos": num_repuestos,
        "prioridad": prioridad,
    }])

    modelo_tiempo, modelo_costo = cargar_estimadores()

    tiempo_log = modelo_tiempo.predict(entrada)[0]
    tiempo_dias = float(np.exp(tiempo_log))
    costo = float(modelo_costo.predict(entrada)[0])

    if (
        not np.isfinite(tiempo_dias)
        or not np.isfinite(costo)
        or tiempo_dias <= 0
        or costo < 0
    ):
        raise ValueError("Los modelos devolvieron una estimación inválida.")

    return {
        "tiempo_estimado_dias": round(tiempo_dias, 2),
        "costo_estimado": round(costo, 2),
    }


if __name__ == "__main__":
    resultado = estimar_servicio(
        tipo_equipo="laptop",
        marca="Apple",
        categoria_falla="pantalla",
        tecnico="Miguel Salazar",
        anios_experiencia=1,
        num_repuestos=2,
        prioridad="alta",
    )

    print(
        f"Tiempo estimado: "
        f"{resultado['tiempo_estimado_dias']:.1f} días"
    )
    print(
        f"Costo estimado: "
        f"S/ {resultado['costo_estimado']:.0f}"
    )