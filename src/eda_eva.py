"""Genera tablas y gráficas básicas para la exploración de EVA."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ENTRADA = Path("data/processed/eva_modelo.csv")
SALIDA = Path("data/processed/eda")


def main() -> None:
    datos = pd.read_csv(ENTRADA)
    SALIDA.mkdir(parents=True, exist_ok=True)

    resumen = (
        datos.groupby(["cultivo", "variante"], as_index=False)
        .agg(
            filas=("cultivo", "size"),
            municipios=("c_digo_dane_municipio", "nunique"),
            produccion_total=("producci_n", "sum"),
            area_cosechada_total=("rea_cosechada", "sum"),
            rendimiento_mediano=("rendimiento", "median"),
        )
        .sort_values(["cultivo", "variante"])
    )
    resumen.to_csv(SALIDA / "resumen_cultivos.csv", index=False)

    historico = (
        datos.groupby(["cultivo", "periodo"], as_index=False)
        .agg(rendimiento_mediano=("rendimiento", "median"))
        .sort_values("periodo")
    )
    historico.to_csv(SALIDA / "historico_rendimiento.csv", index=False)

    fig, ax = plt.subplots(figsize=(10, 5))
    for cultivo, grupo in historico.groupby("cultivo"):
        ax.plot(
            grupo["periodo"],
            grupo["rendimiento_mediano"],
            marker="o",
            label=cultivo,
        )
    ax.set_title("Rendimiento mediano por cultivo y periodo")
    ax.set_xlabel("Periodo")
    ax.set_ylabel("Rendimiento (t/ha)")
    ax.tick_params(axis="x", rotation=45)
    ax.legend(title="Cultivo")
    fig.tight_layout()
    fig.savefig(SALIDA / "rendimiento_por_periodo.png", dpi=160)
    plt.close(fig)

    print(f"Resultados EDA guardados en {SALIDA}")


if __name__ == "__main__":
    main()
