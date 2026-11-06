"""Revisa si las exclusiones de construir_dataset.py esconden señal climática.

1. Filas sin área cosechada: ¿registros vacíos o cosechas perdidas? ¿Se concentran en El Niño?
2. Atípicos excluidos: ¿errores evidentes o valores plausibles?

Entradas: data/processed/eva_modelo.csv, roni_periodos.csv, filas_excluidas_modelo.csv
"""

from pathlib import Path

import pandas as pd

from construir_dataset import FRECUENCIA, leer_eva

RONI = Path("data/processed/roni_periodos.csv")
EXCLUIDAS = Path("data/processed/filas_excluidas_modelo.csv")
SALIDA = Path("data/processed/auditoria_sin_area_por_periodo.csv")


def con_fase(df: pd.DataFrame) -> pd.DataFrame:
    roni = pd.read_csv(RONI, dtype={"periodo": str})[["periodo", "frecuencia", "fase", "prop_nino"]]
    df = df.assign(frecuencia=df["cultivo"].map(FRECUENCIA))
    return df.merge(roni, on=["periodo", "frecuencia"], how="left")


def main() -> None:
    eva = leer_eva()
    eva = eva[eva["variante"] != "Papa todas las variedades"]
    exc = pd.read_csv(EXCLUIDAS, dtype={"cod_mpio": str, "periodo": str})

    # ---- 1. Sin área cosechada
    sin_area = exc[exc["motivo"] == "sin_area_cosechada"]
    sembrada = sin_area["area_sembrada"].fillna(0) > 0
    print("=== 1. FILAS SIN ÁREA COSECHADA ===")
    print(f"Total: {len(sin_area)}  |  con área sembrada > 0 (posible pérdida): {sembrada.sum()}"
          f"  |  sin nada sembrado (registro vacío): {(~sembrada).sum()}")

    perdida = sin_area[sembrada]
    print("\nPosibles pérdidas por cultivo y variante:")
    print(perdida.groupby(["cultivo", "variante"]).size().to_string())

    # Tasa por periodo: posibles pérdidas / filas del periodo con algo sembrado
    base = con_fase(eva[eva["area_sembrada"].fillna(0) > 0])
    tot = base.groupby(["cultivo", "periodo", "fase", "prop_nino"]).size().rename("filas")
    perd = perdida.groupby(["cultivo", "periodo"]).size().rename("perdidas")
    tasa = tot.reset_index().merge(perd.reset_index(), on=["cultivo", "periodo"], how="left")
    tasa["perdidas"] = tasa["perdidas"].fillna(0).astype(int)
    tasa["tasa_pct"] = (100 * tasa["perdidas"] / tasa["filas"]).round(2)
    tasa.to_csv(SALIDA, index=False)

    print("\nTasa de posibles pérdidas por periodo (El Niño: 2019A, 2023B; caña por año):")
    for cultivo, g in tasa.groupby("cultivo"):
        print(f"\n{cultivo}")
        print(g[["periodo", "fase", "prop_nino", "filas", "perdidas", "tasa_pct"]].to_string(index=False))

    print("\nTasa media por fase (promedio simple de periodos):")
    print(tasa.groupby(["cultivo", "fase"])["tasa_pct"].mean().round(2).unstack().to_string())

    # ---- 2. Atípicos
    atip = exc[exc["motivo"] == "atipico_iqr_log"]
    medianas = eva[eva["area_cosechada"] > 0].groupby("variante")["rendimiento"].median()
    print("\n=== 2. ATÍPICOS EXCLUIDOS ===")
    resumen = atip.groupby("variante")["rendimiento"].describe()[["count", "min", "50%", "max"]]
    resumen["mediana_variante"] = medianas.reindex(resumen.index)
    print(resumen.round(1).to_string())

    print("\nCaña de azúcar, detalle:")
    cana = atip[atip["variante"] == "Caña de azúcar"]
    print(cana[["departamento", "municipio", "periodo", "area_cosechada", "rendimiento"]]
          .sort_values("rendimiento").round(1).to_string(index=False))

    print(f"\nTasas por periodo guardadas en {SALIDA}")


if __name__ == "__main__":
    main()
