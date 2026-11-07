"""Agrega el RONI a los periodos de EVA: semestral (arroz, papa) y anual (caña)."""

from pathlib import Path
import pandas as pd


ENTRADA = Path("data/raw/roni.txt")
SALIDA = Path("data/processed/roni_periodos.csv")
UMBRAL = 0.5
ANIO_INICIO = 2018  # un año antes de EVA, para tener el periodo anterior de 2019
MES_CENTRAL = {"DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
               "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12}


def leer_datos() -> pd.DataFrame:
    """Lee el archivo crudo y valida los trimestres."""
    datos = pd.read_csv(ENTRADA, sep=r"\s+")
    datos = datos.rename(columns={"SEAS": "trimestre", "YR": "anio", "ANOM": "anomalia"})
    datos["mes"] = datos["trimestre"].map(MES_CENTRAL)
    if datos["mes"].isna().any():
        raise ValueError("Hay trimestres con nombre inesperado en el archivo RONI")
    return datos[datos["anio"] >= ANIO_INICIO].copy()


def fase(valor: float) -> str:
    if valor >= UMBRAL:
        return "El Niño"
    if valor <= -UMBRAL:
        return "La Niña"
    return "Neutro"


def agregar(datos: pd.DataFrame, columna: str, frecuencia: str, completos: int) -> pd.DataFrame:
    """Resume el RONI por periodo: media, fase y proporción de trimestres en cada fase."""
    grupo = datos.groupby(columna)["anomalia"]
    salida = pd.DataFrame({
        "roni_medio": grupo.mean(),
        "prop_nino": grupo.apply(lambda s: (s >= UMBRAL).mean()),
        "prop_nina": grupo.apply(lambda s: (s <= -UMBRAL).mean()),
        "trimestres": grupo.size(),
    }).reset_index().rename(columns={columna: "periodo"}).sort_values("periodo")
    salida["fase"] = salida["roni_medio"].apply(fase)
    for variable in ["roni_medio", "prop_nino", "prop_nina"]:
        salida[f"{variable}_previo"] = salida[variable].shift(1)
    salida["completo"] = salida["trimestres"] == completos
    salida["frecuencia"] = frecuencia
    return salida


def main() -> None:
    datos = leer_datos()
    datos["semestre"] = datos["anio"].astype(str) + datos["mes"].le(6).map({True: "A", False: "B"})
    datos["anio_txt"] = datos["anio"].astype(str)
    salida = pd.concat([
        agregar(datos, "semestre", "semestral", 6),
        agregar(datos, "anio_txt", "anual", 12),
    ], ignore_index=True)
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    salida.round(3).to_csv(SALIDA, index=False)
    print(f"Archivo guardado en {SALIDA}: {len(salida)} periodos")


if __name__ == "__main__":
    main()