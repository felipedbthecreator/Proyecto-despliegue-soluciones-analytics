"""Une EVA y RONI en la tabla de modelado y deja trazabilidad de cada filtro.
 
Entradas : data/processed/eva_modelo.csv, data/processed/roni_periodos.csv
Salidas  : data/processed/dataset_modelo.csv        (tabla para entrenar)
           data/processed/trazabilidad_modelo.csv   (filas excluidas por paso)
           data/processed/filas_excluidas_modelo.csv (detalle de cada fila excluida)
"""
 
import hashlib
from pathlib import Path
 
import numpy as np
import pandas as pd
 
EVA = Path("data/processed/eva_modelo.csv")
RONI = Path("data/processed/roni_periodos.csv")
SALIDA = Path("data/processed/dataset_modelo.csv")
TRAZA = Path("data/processed/trazabilidad_modelo.csv")
EXCLUIDAS = Path("data/processed/filas_excluidas_modelo.csv")
 
K_IQR = 3.0     
IQR_MIN = 0.3    # piso del IQR en log: evita excluir todo si muchos municipios reportan el mismo valor
FRECUENCIA = {"Arroz": "semestral", "Papa": "semestral", "Caña": "anual"}
LLAVE = ["cod_mpio", "cultivo", "variante", "periodo"]
RENOMBRAR = {
    "c_digo_dane_departamento": "cod_depto",
    "c_digo_dane_municipio": "cod_mpio",
    "a_o": "anio",
    "rea_sembrada": "area_sembrada",
    "rea_cosechada": "area_cosechada",
    "producci_n": "produccion",
}
COLS_RONI = ["periodo", "frecuencia", "roni_medio", "prop_nino", "prop_nina",
             "roni_medio_previo", "fase"]
 
 
def leer_eva() -> pd.DataFrame:
    eva = pd.read_csv(
        EVA,
        dtype={"c_digo_dane_municipio": str, "c_digo_dane_departamento": str, "periodo": str},
    ).rename(columns=RENOMBRAR)
    eva["cod_mpio"] = eva["cod_mpio"].str.zfill(5)
    eva["cod_depto"] = eva["cod_depto"].str.zfill(2)
    eva["anio"] = eva["anio"].astype(int)
    return eva
 
 
def filtrar(df: pd.DataFrame):
    """Aplica los filtros en orden y registra cuántas filas excluye cada uno."""
    traza, excluidas = [], []
 
    def paso(df, excluir, nombre, detalle):
        excluir = excluir.fillna(True)
        traza.append({"paso": nombre, "filas_antes": len(df),
                      "excluidas": int(excluir.sum()), "detalle": detalle})
        excluidas.append(df[excluir].assign(motivo=nombre))
        return df[~excluir].copy()
 
    df = paso(df, df["variante"].eq("Papa todas las variedades"), "papa_total_inconsistente",
              "Total de papa donde la criolla supera al total; no es una variante comparable")
    df = paso(df, ~(df["area_cosechada"] > 0), "sin_area_cosechada",
              "Sin área cosechada: el rendimiento no está definido")
    df = paso(df, df["produccion"].le(0), "produccion_cero",
              "Área cosechada con producción cero; revisar si se concentra en El Niño")
    df = paso(df, df.duplicated(LLAVE, keep="first"), "duplicado_llave",
              "Más de una fila por municipio-cultivo-variante-periodo")
 
    log_r = np.log(df["rendimiento"])
    q1 = log_r.groupby(df["variante"]).transform(lambda s: s.quantile(0.25))
    q3 = log_r.groupby(df["variante"]).transform(lambda s: s.quantile(0.75))
    iqr = np.maximum(q3 - q1, IQR_MIN)
    atipico = (log_r < q1 - K_IQR * iqr) | (log_r > q3 + K_IQR * iqr)
    df = paso(df, atipico, "atipico_iqr_log",
              f"Fuera de Q1/Q3 ± {K_IQR}·IQR del log-rendimiento por variante")
 
    return df, pd.DataFrame(traza), pd.concat(excluidas, ignore_index=True)
 
 
def unir_roni(df: pd.DataFrame) -> pd.DataFrame:
    roni = pd.read_csv(RONI, dtype={"periodo": str})[COLS_RONI]
    df["frecuencia"] = df["cultivo"].map(FRECUENCIA)
    df = df.merge(roni, on=["periodo", "frecuencia"], how="left", validate="many_to_one")
    faltan = df["roni_medio"].isna().sum()
    if faltan:
        raise ValueError(f"{faltan} filas sin RONI: revisar formato de 'periodo'")
    return df
 
 
def main() -> None:
    df, traza, excluidas = filtrar(leer_eva())
    df = unir_roni(df)
    df["semestre"] = np.where(df["frecuencia"] == "semestral", df["periodo"].str[-1], "anual")
    df["log_area_sembrada"] = np.log1p(df["area_sembrada"])
    df["rend_redondo"] = np.isclose(df["rendimiento"], df["rendimiento"].round())
 
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(SALIDA, index=False)
    traza.to_csv(TRAZA, index=False)
    excluidas.to_csv(EXCLUIDAS, index=False)
 
    print(traza.to_string(index=False))
    atip = excluidas[excluidas["motivo"] == "atipico_iqr_log"]
    print("\nAtípicos excluidos por variante:")
    print(atip.groupby("variante").size().to_string() if len(atip) else "  ninguno")
    print(f"\nFilas para modelar: {len(df)}")
    print(df.groupby(["cultivo", "variante"]).size().to_string())
    print(f"\nMD5 {SALIDA}: {hashlib.md5(SALIDA.read_bytes()).hexdigest()}")
 
 
if __name__ == "__main__":
    main()
 