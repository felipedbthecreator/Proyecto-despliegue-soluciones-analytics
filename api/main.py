"""API de inferencia del rendimiento agrícola esperado (arroz, papa y caña).

Sirve los modelos finales que exporta src/tuning.py (models/rendimiento_<cultivo>.pkl y .json)
con el contrato que consume el tablero:

    GET  /health            -> {"status": "ok", "modelo": "...", "modelos": {...}}
    GET  /modelos           -> metadatos de cada modelo (hiperparámetros, métricas, versión)
    POST /predict           <- {"municipio", "cod_mpio", "cultivo", "variante", "periodo", "escenario"}
                            -> {"rendimiento_t_ha", "intervalo_80", "modelo", ...}
    POST /predict/lote      <- lista de peticiones /predict (para el ranking del tablero)

El escenario se traduce a las variables climáticas igual que predecir_escenarios en
src/modelado.py (RONI 1 / 0 / -1 y, en caña, prop_nino / prop_nina). El RONI del periodo
anterior se calcula con el último archivo de NOAA/CPC (roni.txt), porque ese sí se conoce
antes de la cosecha.

Ejecutar en local (desde la raíz del repositorio):
    uvicorn api.main:app --port 8001
"""
import json
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Literal

import cloudpickle
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

RAIZ = Path(__file__).resolve().parents[1]
RUTA_MODELOS = Path(os.getenv("RUTA_MODELOS", RAIZ / "models"))
RUTA_DATASET = Path(os.getenv("RUTA_DATASET", RAIZ / "tablero" / "datos" / "dataset_modelo.csv"))
RUTA_RONI = Path(os.getenv("RUTA_RONI", RAIZ / "tablero" / "datos" / "roni.txt"))

# modelado.py debe ser importable para deserializar los pipelines (HistoricoMunicipio, etc.)
sys.path.insert(0, str(Path(os.getenv("RUTA_SRC", RAIZ / "src"))))
from modelado import ESCENARIOS, columnas  # noqa: E402

CULTIVOS = {"arroz": "Arroz", "papa": "Papa", "cana": "Caña"}
VARIANTES = {
    "riego": ("arroz", "Arroz riego"),
    "secano_mec": ("arroz", "Arroz secano mecanizado"),
    "secano_man": ("arroz", "Arroz secano manual"),
    "resto": ("papa", "Papa todas menos criolla"),
    "criolla": ("papa", "Papa criolla"),
    "azucar": ("cana", "Caña de azúcar"),
    "panelera": ("cana", "Caña panelera"),
}
MES_CENTRAL = {"DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
               "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12}


# ---------------------------------------------------------------- carga (una vez)
@lru_cache(maxsize=1)
def modelos() -> dict:
    salida = {}
    for cod in CULTIVOS:
        base = RUTA_MODELOS / f"rendimiento_{cod}"
        if not base.with_suffix(".pkl").exists():
            raise RuntimeError(f"No se encontró {base}.pkl: ejecute src/tuning.py")
        salida[cod] = {"modelo": cloudpickle.loads(base.with_suffix(".pkl").read_bytes()),
                       "meta": json.loads(base.with_suffix(".json").read_text(encoding="utf-8"))}
    return salida


@lru_cache(maxsize=1)
def municipios() -> pd.DataFrame:
    """cod_mpio -> cod_depto, con los mismos tipos de texto que usó el entrenamiento."""
    d = pd.read_csv(RUTA_DATASET, dtype={"cod_mpio": str, "cod_depto": str, "periodo": str},
                    usecols=["cod_mpio", "cod_depto", "municipio", "departamento"])
    return d.drop_duplicates("cod_mpio").set_index("cod_mpio")


@lru_cache(maxsize=1)
def roni_periodos() -> dict:
    """RONI medio por semestre (2026A) y por año (2026) a partir de los trimestres publicados."""
    r = pd.read_csv(RUTA_RONI, sep=r"\s+").rename(columns={"SEAS": "t", "YR": "anio", "ANOM": "v"})
    r["mes"] = r["t"].map(MES_CENTRAL)
    r["sem"] = r["anio"].astype(str) + np.where(r["mes"] <= 6, "A", "B")
    sem = r.groupby("sem")["v"].mean().to_dict()
    anio = r.groupby(r["anio"].astype(str))["v"].mean().to_dict()
    return {**sem, **anio, "_ultimo": float(r["v"].iloc[-1])}


def periodo_anterior(periodo: str) -> str:
    if periodo.endswith("A"):
        return f"{int(periodo[:4]) - 1}B"
    if periodo.endswith("B"):
        return f"{periodo[:4]}A"
    return str(int(periodo) - 1)


def nombre_modelo(cod: str) -> str:
    meta = modelos()[cod]["meta"]
    version = meta.get("registro", {}).get("version")
    return f"rendimiento-{cod}-{meta['modelo']}" + (f"-v{version}" if version else "")


# ---------------------------------------------------------------- esquema
class Peticion(BaseModel):
    municipio: str | None = None
    cod_mpio: int = Field(..., examples=[23570])
    cultivo: Literal["arroz", "papa", "cana"]
    variante: Literal["riego", "secano_mec", "secano_man", "resto", "criolla", "azucar", "panelera"]
    periodo: str = Field(..., pattern=r"^\d{4}[AB]?$", examples=["2026B"])
    escenario: Literal["nino", "neutro", "nina"]


class Respuesta(BaseModel):
    rendimiento_t_ha: float
    intervalo_80: list[float]
    modelo: str
    escenario: str
    variables_clima: dict
    advertencia: str | None = None


def construir_fila(p: Peticion) -> tuple[pd.DataFrame, dict, str]:
    cultivo_var, variante_eva = VARIANTES[p.variante]
    if cultivo_var != p.cultivo:
        raise HTTPException(422, f"La variante {p.variante} no corresponde al cultivo {p.cultivo}")
    anual = p.cultivo == "cana"
    if anual == p.periodo[-1].isalpha():
        raise HTTPException(422, "Caña usa periodos anuales (2026); arroz y papa, semestrales (2026B)")
    cod = str(p.cod_mpio)
    if cod not in municipios().index:
        raise HTTPException(404, f"Municipio {cod} no está en la base EVA")

    roni = roni_periodos()
    previo = roni.get(periodo_anterior(p.periodo))
    advertencia = None
    if previo is None:
        previo = roni["_ultimo"]
        advertencia = "RONI del periodo anterior aún no publicado; se usa el último trimestre disponible"

    clima = dict(ESCENARIOS[p.escenario])
    fila = {"cod_mpio": cod, "variante": variante_eva, "cod_depto": municipios().at[cod, "cod_depto"],
            "anio": int(p.periodo[:4]), "roni_medio": clima["roni_medio"],
            "roni_medio_previo": round(float(previo), 3)}
    if anual:
        fila |= {"prop_nino": clima["prop_nino"], "prop_nina": clima["prop_nina"]}
    else:
        fila["semestre"] = p.periodo[-1]
    feats, _ = columnas(CULTIVOS[p.cultivo])
    usadas = {k: fila[k] for k in ("roni_medio", "roni_medio_previo", "prop_nino", "prop_nina") if k in fila}
    return pd.DataFrame([fila])[feats], usadas, advertencia


def predecir(p: Peticion) -> Respuesta:
    X, clima, advertencia = construir_fila(p)
    m = modelos()[p.cultivo]
    y = float(m["modelo"].predict(X)[0])
    factores = m["meta"]["intervalo_80_factores"]
    lo, hi = factores.get(VARIANTES[p.variante][1], factores["_global"])
    return Respuesta(rendimiento_t_ha=round(y, 3),
                     intervalo_80=[round(y * min(lo, 1.0), 3), round(y * max(hi, 1.0), 3)],
                     modelo=nombre_modelo(p.cultivo), escenario=p.escenario,
                     variables_clima=clima, advertencia=advertencia)


# ---------------------------------------------------------------- rutas
app = FastAPI(title="API rendimiento agrícola esperado bajo El Niño",
              description="Modelos finales por cultivo (EVA 2019–2025 + RONI NOAA/CPC).",
              version="1.0.0")


@app.on_event("startup")
def precargar():
    modelos(), municipios(), roni_periodos()


@app.get("/health")
def health():
    return {"status": "ok", "modelo": "rendimiento-v1",
            "modelos": {c: nombre_modelo(c) for c in CULTIVOS}}


@app.get("/modelos")
def info_modelos():
    return {c: {k: m["meta"][k] for k in ("modelo", "target_log", "hiperparametros", "metricas",
                                           "registro", "entrenado_con", "evaluado_en", "sklearn_version")}
            for c, m in modelos().items()}


@app.post("/predict", response_model=Respuesta)
def predict(p: Peticion):
    return predecir(p)


@app.post("/predict/lote", response_model=list[Respuesta])
def predict_lote(peticiones: list[Peticion]):
    if len(peticiones) > 1000:
        raise HTTPException(413, "Máximo 1000 peticiones por lote")
    return [predecir(p) for p in peticiones]
