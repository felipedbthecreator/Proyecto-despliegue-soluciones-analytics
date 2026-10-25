"""Grafica la serie RONI 2018-actual con los umbrales y resume la fase por semestre."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ENTRADA_CRUDA = Path("data/raw/roni.txt")
ENTRADA_PERIODOS = Path("data/processed/roni_periodos.csv")
SALIDA = Path("data/processed/eda")
MES_CENTRAL = {"DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
               "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12}


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)

    serie = pd.read_csv(ENTRADA_CRUDA, sep=r"\s+")
    serie = serie[serie["YR"] >= 2018].copy()
    serie["fecha"] = pd.to_datetime(dict(year=serie["YR"], month=serie["SEAS"].map(MES_CENTRAL), day=15))

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(serie["fecha"], serie["ANOM"], color="black", linewidth=1.5)
    ax.fill_between(serie["fecha"], serie["ANOM"], 0.5, where=serie["ANOM"] >= 0.5, interpolate=True, color="tab:red", alpha=0.4, label="El Niño")
    ax.fill_between(serie["fecha"], serie["ANOM"], -0.5, where=serie["ANOM"] <= -0.5, interpolate=True, color="tab:blue", alpha=0.4, label="La Niña")
    ax.axhline(0.5, color="tab:red", linestyle="--", linewidth=0.8)
    ax.axhline(-0.5, color="tab:blue", linestyle="--", linewidth=0.8)
    ax.axhline(0, color="grey", linewidth=0.5)
    ax.set_title("RONI 2018–actual (NOAA/CPC)")
    ax.set_ylabel("Anomalía relativa (°C)")
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(SALIDA / "roni_serie.png", dpi=150)

    periodos = pd.read_csv(ENTRADA_PERIODOS, dtype={"periodo": str})
    semestres = periodos[periodos["frecuencia"] == "semestral"]
    print(semestres[["periodo", "roni_medio", "fase", "completo"]].to_string(index=False))
    print(f"\nGráfica guardada en {SALIDA / 'roni_serie.png'}")


if __name__ == "__main__":
    main()