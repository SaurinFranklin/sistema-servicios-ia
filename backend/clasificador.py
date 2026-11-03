import argparse
import json
from functools import lru_cache
from pathlib import Path

import joblib
import torch
from transformers import AutoModel, AutoTokenizer


RAIZ = Path(__file__).resolve().parents[1]
CARPETA_MODELO = RAIZ / "ml/models/clasificador_beto_v1"


@lru_cache(maxsize=1)
def cargar_modelos():
    """Carga los modelos una sola vez por proceso."""
    with (CARPETA_MODELO / "configuracion.json").open(
        encoding="utf-8"
    ) as archivo:
        configuracion = json.load(archivo)

    tokenizador = AutoTokenizer.from_pretrained(
        CARPETA_MODELO / "beto",
        local_files_only=True,
    )

    extractor = AutoModel.from_pretrained(
        CARPETA_MODELO / "beto",
        local_files_only=True,
    )
    extractor.eval()

    clasificador = joblib.load(
        CARPETA_MODELO / "clasificador.joblib"
    )

    return configuracion, tokenizador, extractor, clasificador


def sugerir_fallas(texto: str, cantidad: int = 3) -> list[dict]:
    """Devuelve las categorías con mayor puntuación."""
    if not isinstance(texto, str) or not texto.strip():
        raise ValueError("La descripción no puede estar vacía.")

    configuracion, tokenizador, extractor, clasificador = cargar_modelos()

    if not isinstance(cantidad, int) or not (
        1 <= cantidad <= len(clasificador.classes_)
    ):
        raise ValueError("La cantidad de sugerencias está fuera de rango.")

    entradas = tokenizador(
        texto.strip(),
        return_tensors="pt",
        truncation=True,
        max_length=configuracion["max_length"],
    )

    with torch.inference_mode():
        tokens = extractor(**entradas).last_hidden_state

        mascara = entradas["attention_mask"].unsqueeze(-1)
        mascara = mascara.to(tokens.dtype)

        vector = (
            (tokens * mascara).sum(dim=1)
            / mascara.sum(dim=1).clamp(min=1)
        )

    puntuaciones = clasificador.predict_proba(
        vector.cpu().numpy()
    )[0]

    mejores = puntuaciones.argsort()[::-1][:cantidad]

    return [
        {
            "categoria": str(clasificador.classes_[indice]),
            "puntuacion": round(float(puntuaciones[indice]), 4),
        }
        for indice in mejores
    ]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sugiere categorías para una descripción de falla."
    )
    parser.add_argument("texto", help="Descripción de la falla")
    argumentos = parser.parse_args()

    resultado = sugerir_fallas(argumentos.texto)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))