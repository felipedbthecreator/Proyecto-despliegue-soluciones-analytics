"""Limpieza y transformación reproducible de la base agrícola EVA."""

from pathlib import Path
from typing import List

import numpy as np
import pandas as pd


ENTRADA = Path("data/raw/eva_2019_2025.json")
SALIDA = Path("data/processed/eva_modelo.csv")
NUMERICAS: List[str] = [
    "a_o",
    "rea_sembrada",
    "rea_cosechada",
    "producci_n",
    "rendimiento",
]
LLAVE = ["c_digo_dane_municipio", "periodo"]


def leer_datos() -> pd.DataFrame:
    """Lee el archivo crudo y convierte las columnas cuantitativas."""
    datos = pd.read_json(ENTRADA)
    for columna in NUMERICAS:
        datos[columna] = pd.to_numeric(datos[columna], errors="coerce")
    datos["municipio"] = datos["municipio"].str.strip()
    return datos


def agregar_variante(datos: pd.DataFrame, variante: str) -> pd.DataFrame:
    """Agrega una variante sin sumar filas que representan el mismo total."""
    columnas = [
        "c_digo_dane_departamento",
        "departamento",
        "c_digo_dane_municipio",
        "municipio",
        "cultivo",
        "periodo",
        "a_o",
        "ciclo_del_cultivo",
        "variante",
    ]
    grupo = datos.groupby(columnas, as_index=False, dropna=False).agg(
        rea_sembrada=("rea_sembrada", "sum"),
        rea_cosechada=("rea_cosechada", "sum"),
        producci_n=("producci_n", "sum"),
    )
    grupo["rendimiento"] = np.where(
        grupo["rea_cosechada"] > 0,
        grupo["producci_n"] / grupo["rea_cosechada"],
        np.nan,
    )
    return grupo


def preparar(datos: pd.DataFrame) -> pd.DataFrame:
    """Filtra cultivos, normaliza periodos y deriva la papa no criolla."""
    cultivos = datos[datos["cultivo"].isin(["Arroz", "Papa", "Caña"])].copy()
    cultivos = cultivos[
        ~cultivos["desagregaci_n_cultivo"].isin(["Caña miel"])
    ].copy()

    transitorios = cultivos[
        (cultivos["cultivo"].isin(["Arroz", "Papa"]))
        & cultivos["periodo"].astype(str).str.match(r"^\d{4}[AB]$")
    ].copy()
    permanentes = cultivos[
        (cultivos["cultivo"] == "Caña")
        & cultivos["periodo"].astype(str).str.match(r"^\d{4}$")
    ].copy()

    transitorios["variante"] = transitorios["desagregaci_n_cultivo"]
    permanentes["variante"] = permanentes["desagregaci_n_cultivo"]
    base = pd.concat(
        [
            agregar_variante(transitorios, "variante"),
            agregar_variante(permanentes, "variante"),
        ],
        ignore_index=True,
    )

    return separar_papa(base)


def separar_papa(base: pd.DataFrame) -> pd.DataFrame:
    """Deriva 'Papa todas menos criolla' conservando todas las llaves del total.

    La criolla es un subconjunto del total. Donde no hay criolla, el total ya
    es el resto (se resta cero). Donde la criolla supera al total en alguna
    medida, la fila es inconsistente: se conserva solo el total.
    """
    medidas = ["rea_sembrada", "rea_cosechada", "producci_n"]
    papa = base[base["cultivo"] == "Papa"]
    resto_base = base[base["cultivo"] != "Papa"]
    criolla = papa[papa["variante"] == "Papa criolla"]
    total = papa[papa["variante"] == "Papa todas las variedades"]

    union = total.merge(
        criolla[LLAVE + medidas], on=LLAVE, how="outer",
        suffixes=("", "_criolla"), indicator=True,
    )
    for m in medidas:
        union[f"{m}_criolla"] = union[f"{m}_criolla"].fillna(0)

    # Criolla sin total: se conserva como criolla, sin fila derivada.
    sin_total = union["_merge"] == "right_only"
    solo_criolla = criolla.merge(
        union.loc[sin_total, LLAVE], on=LLAVE, how="inner"
    )

    con_total = union[~sin_total].copy()
    inconsistente = (
        (con_total["producci_n_criolla"] > con_total["producci_n"])
        | (con_total["rea_sembrada_criolla"] > con_total["rea_sembrada"])
        | (con_total["rea_cosechada_criolla"] > con_total["rea_cosechada"])
    )
    print(f"Papa: {inconsistente.sum()} llaves inconsistentes de {len(con_total)}; "
          f"{sin_total.sum()} criolla sin total.")

    # Inconsistentes: solo el total, sin criolla.
    total_inc = con_total.loc[inconsistente, total.columns]

    # Consistentes: criolla (si existe) y resto = total - criolla.
    ok = con_total[~inconsistente].copy()
    criolla_ok = criolla.merge(ok[LLAVE], on=LLAVE, how="inner")
    resto = ok[total.columns].copy()
    resto["variante"] = "Papa todas menos criolla"
    for m in medidas:
        resto[m] = ok[m].to_numpy() - ok[f"{m}_criolla"].to_numpy()
    resto["rendimiento"] = np.where(
        resto["rea_cosechada"] > 0,
        resto["producci_n"] / resto["rea_cosechada"],
        np.nan,
    )

    return pd.concat(
        [resto_base, criolla_ok, solo_criolla, resto, total_inc],
        ignore_index=True,
    ).sort_values(["cultivo", "municipio", "periodo", "variante"])


def main() -> None:
    datos = preparar(leer_datos())
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    datos.to_csv(SALIDA, index=False)
    print(f"Archivo guardado en {SALIDA}: {len(datos)} filas")


if __name__ == "__main__":
    main()
