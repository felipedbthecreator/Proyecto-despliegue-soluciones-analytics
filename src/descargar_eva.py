"""Descarga paginada de la base agrícola EVA desde datos.gov.co."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List

import requests


URL = "https://www.datos.gov.co/resource/uejq-wxrr.json"
SALIDA = Path("data/raw/eva_2019_2025.json")
TAMANO_PAGINA = 50000


def descargar() -> List[Dict[str, Any]]:
    """Descarga todas las filas, respetando la paginación de Socrata."""
    filas: List[Dict[str, Any]] = []
    offset = 0
    headers = {}
    token = os.getenv("SOCRATA_TOKEN")
    if token:
        headers["X-App-Token"] = token

    while True:
        parametros = {
            "$limit": TAMANO_PAGINA,
            "$offset": offset,
            "$order": ":id",
        }
        respuesta = requests.get(
            URL, params=parametros, headers=headers, timeout=120
        )
        respuesta.raise_for_status()
        pagina = respuesta.json()
        if not pagina:
            break
        filas.extend(pagina)
        print(f"Filas descargadas: {len(filas)}")
        if len(pagina) < TAMANO_PAGINA:
            break
        offset += TAMANO_PAGINA
    return filas


def main() -> None:
    filas = descargar()
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(filas, ensure_ascii=False), encoding="utf-8")
    print(f"Archivo guardado en {SALIDA}: {len(filas)} filas")


if __name__ == "__main__":
    main()
