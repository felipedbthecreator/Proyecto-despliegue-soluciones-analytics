"""Faltantes por columna y diferencias de rendimiento entre municipios y departamentos.

Entradas: data/processed/eva_modelo.csv, data/processed/dataset_modelo.csv
Salidas : data/processed/eda/faltantes_por_columna.csv
          data/processed/eda/varianza_municipio.csv
          data/processed/eda/rendimiento_departamento.csv
"""

from pathlib import Path

import numpy as np
import pandas as pd

from construir_dataset import leer_eva

DATOS = Path("data/processed/dataset_modelo.csv")
SALIDA = Path("data/processed/eda")


def faltantes() -> pd.DataFrame:
    eva = leer_eva()
    tabla = pd.DataFrame({
        "faltantes": eva.isna().sum(),
        "ceros": (eva.select_dtypes("number") == 0).sum(),
    }).fillna(0).astype(int)
    tabla["pct_faltantes"] = (100 * tabla["faltantes"] / len(eva)).round(2)
    return tabla[(tabla["faltantes"] > 0) | (tabla["ceros"] > 0)]


def varianza_municipio(df: pd.DataFrame) -> pd.DataFrame:
    """Qué parte de la variación del log-rendimiento se explica por el municipio y el departamento."""
    filas = []
    for v, g in df.groupby("variante"):
        y = np.log(g["rendimiento"])
        total = y.var(ddof=0)
        entre_mpio = g.assign(y=y).groupby("cod_mpio")["y"].transform("mean").var(ddof=0)
        entre_depto = g.assign(y=y).groupby("cod_depto")["y"].transform("mean").var(ddof=0)
        filas.append({
            "variante": v, "municipios": g["cod_mpio"].nunique(),
            "pct_entre_municipios": round(100 * entre_mpio / total, 1),
            "pct_entre_departamentos": round(100 * entre_depto / total, 1),
            "pct_dentro_municipio": round(100 * (1 - entre_mpio / total), 1),
        })
    return pd.DataFrame(filas)


def rendimiento_departamento(df: pd.DataFrame) -> pd.DataFrame:
    """Mediana por departamento y variante (departamentos con al menos 3 municipios)."""
    g = df.groupby(["variante", "departamento"]).agg(
        municipios=("cod_mpio", "nunique"), mediana=("rendimiento", "median"))
    g = g[g["municipios"] >= 3].reset_index()
    return g.sort_values(["variante", "mediana"], ascending=[True, False])


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(DATOS, dtype={"cod_mpio": str, "cod_depto": str, "periodo": str})

    f = faltantes()
    f.to_csv(SALIDA / "faltantes_por_columna.csv")
    print("Faltantes y ceros por columna (EVA limpia, antes de filtros)")
    print(f.to_string())

    v = varianza_municipio(df)
    v.to_csv(SALIDA / "varianza_municipio.csv", index=False)
    print("\n¿De dónde viene la variación del rendimiento? (log, % de la varianza)")
    print(v.to_string(index=False))

    d = rendimiento_departamento(df)
    d.to_csv(SALIDA / "rendimiento_departamento.csv", index=False)
    print("\nMediana por departamento: 3 más altos y 3 más bajos por variante")
    for var, g in d.groupby("variante"):
        ext = pd.concat([g.head(3), g.tail(3)]).drop_duplicates()
        print(f"\n{var}")
        print(ext[["departamento", "municipios", "mediana"]].round(1).to_string(index=False))


if __name__ == "__main__":
    main()
