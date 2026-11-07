"""Corre los modelos base (naive, ridge, hgb) con valores por defecto para los tres cultivos."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from entrenar_base import entrenar  # noqa: E402

for cultivo in ["Arroz", "Papa", "Caña"]:
    for modelo in ["naive", "ridge", "hgb"]:
        entrenar(cultivo, modelo, nombre_run=f"base-{modelo}")
