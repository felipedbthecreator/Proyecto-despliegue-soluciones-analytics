"""Genera tablas y graficas EDA por cultivo y variante."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ENTRADA = Path("data/processed/eva_modelo.csv")
SALIDA = Path("data/processed/eda")


def main() -> None:
    datos = pd.read_csv(ENTRADA, dtype={"periodo": str})
    SALIDA.mkdir(parents=True, exist_ok=True)

    # Resumen general por cultivo y variante.
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

    # Historico separado por cultivo, variante y periodo.
    historico = (
        datos.groupby(
            ["cultivo", "variante", "periodo"], as_index=False
        )
        .agg(rendimiento_mediano=("rendimiento", "median"))
        .sort_values(["cultivo", "variante", "periodo"])
    )
    historico.to_csv(
        SALIDA / "historico_rendimiento.csv", index=False
    )

    # Graficas independientes para no mezclar escalas temporales.
    archivos = {
        "Arroz": "rendimiento_arroz_por_variante.png",
        "Papa": "rendimiento_papa_por_variante.png",
        "Caña": "rendimiento_cana_por_variante.png",
    }

    for cultivo, archivo in archivos.items():
        grupo_cultivo = historico[
            historico["cultivo"] == cultivo
        ]

        if grupo_cultivo.empty:
            print(f"No hay datos para: {cultivo}")
            continue

        fig, ax = plt.subplots(figsize=(11, 5))

        for variante, grupo in grupo_cultivo.groupby("variante"):
            grupo = grupo.sort_values("periodo")
            ax.plot(
                grupo["periodo"],
                grupo["rendimiento_mediano"],
                marker="o",
                label=variante,
            )

        ax.set_title(
            f"Rendimiento mediano de {cultivo} por variante y periodo"
        )
        ax.set_xlabel("Periodo")
        ax.set_ylabel("Rendimiento (t/ha)")
        ax.tick_params(axis="x", rotation=45)
        ax.legend(title="Variante")
        fig.tight_layout()
        fig.savefig(SALIDA / archivo, dpi=160)
        plt.close(fig)

        print(f"Grafica guardada: {SALIDA / archivo}")

    print(f"Resultados EDA guardados en {SALIDA}")


if __name__ == "__main__":
    main()