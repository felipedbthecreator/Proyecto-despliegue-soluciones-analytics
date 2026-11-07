"""Carga y consultas descriptivas sobre EVA 2019-2025 + RONI."""
from functools import lru_cache

import pandas as pd

from config import EVA_A_CODIGO, RUTA_DATASET, RUTA_RONI, UMBRAL_RONI, VARIANTES


def _orden_periodo(p: str) -> float:
    """2019A -> 2019.0, 2019B -> 2019.5, 2019 -> 2019.0"""
    p = str(p)
    return int(p[:4]) + (0.5 if p.endswith("B") else 0.0)


@lru_cache(maxsize=1)
def cargar_dataset() -> pd.DataFrame:
    df = pd.read_csv(RUTA_DATASET)
    df = df[df["rendimiento"] > 0].copy()
    df["var_cod"] = df["variante"].map(EVA_A_CODIGO)
    df = df.dropna(subset=["var_cod"])
    df["cultivo_cod"] = df["var_cod"].map(lambda v: VARIANTES[v]["cultivo"])
    df["orden"] = df["periodo"].map(_orden_periodo)
    df["cod_mpio"] = df["cod_mpio"].astype(int)
    return df.sort_values(["cod_mpio", "var_cod", "orden"]).reset_index(drop=True)


def clasificar_fase(valor: float) -> str:
    if valor >= UMBRAL_RONI:
        return "nino"
    if valor <= -UMBRAL_RONI:
        return "nina"
    return "neutro"


@lru_cache(maxsize=1)
def cargar_roni() -> pd.DataFrame:
    return pd.read_csv(RUTA_RONI, sep=r"\s+")


def fase_actual() -> dict:
    """Último trimestre publicado del RONI y su fase."""
    r = cargar_roni().iloc[-1]
    return {"trimestre": r["SEAS"], "anio": int(r["YR"]), "valor": float(r["ANOM"]),
            "fase": clasificar_fase(float(r["ANOM"]))}


# ---------------- Consultas para los filtros ----------------
def departamentos() -> list[str]:
    return sorted(cargar_dataset()["departamento"].unique())


def municipios(depto: str) -> list[dict]:
    d = cargar_dataset()
    d = d[d["departamento"] == depto][["cod_mpio", "municipio"]].drop_duplicates()
    return [{"label": r.municipio, "value": int(r.cod_mpio)} for r in d.sort_values("municipio").itertuples()]


def nombre_municipio(cod_mpio: int) -> tuple[str, str]:
    d = cargar_dataset()
    r = d[d["cod_mpio"] == cod_mpio].iloc[0]
    return r["municipio"], r["departamento"]


def variantes_municipio(cod_mpio: int, cultivo: str | None = None) -> list[str]:
    d = cargar_dataset()
    d = d[d["cod_mpio"] == cod_mpio]
    if cultivo:
        d = d[d["cultivo_cod"] == cultivo]
    orden = list(VARIANTES)
    return sorted(d["var_cod"].unique(), key=orden.index)


def cultivos_municipio(cod_mpio: int) -> list[str]:
    return sorted({VARIANTES[v]["cultivo"] for v in variantes_municipio(cod_mpio)},
                  key=["arroz", "papa", "cana"].index)


def municipios_con_variante(depto: str, variante: str) -> list[tuple[int, str]]:
    d = cargar_dataset()
    d = d[(d["departamento"] == depto) & (d["var_cod"] == variante)]
    return sorted({(int(r.cod_mpio), r.municipio) for r in d.itertuples()}, key=lambda x: x[1])


# ---------------- Consultas descriptivas ----------------
def historia(cod_mpio: int, variante: str) -> pd.DataFrame:
    d = cargar_dataset()
    d = d[(d["cod_mpio"] == cod_mpio) & (d["var_cod"] == variante)]
    return d[["periodo", "orden", "fase", "rendimiento", "area_sembrada", "roni_medio"]].sort_values("orden")


def mediana_nacional(variante: str) -> float:
    d = cargar_dataset()
    return float(d.loc[d["var_cod"] == variante, "rendimiento"].median())


def ultima_area_sembrada(cod_mpio: int, variante: str) -> tuple[float, str]:
    h = historia(cod_mpio, variante)
    r = h.iloc[-1]
    return float(r["area_sembrada"]), str(r["periodo"])
