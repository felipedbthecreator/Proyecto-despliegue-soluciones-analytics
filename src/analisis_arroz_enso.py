"""Relaciona el rendimiento del arroz con fases ENSO por semestre."""

from pathlib import Path

import pandas as pd


ENTRADA = Path("data/processed/eva_modelo.csv")
SALIDA = Path("data/processed/eda")


# Clasificación exploratoria por semestre.
# Las etiquetas deben contrastarse con la serie histórica oficial de NOAA.
# Las categorías de transición representan períodos semestrales mixtos.
FASE_POR_PERIODO = {
    "2019A": "Neutral",
    "2019B": "Neutral",
    "2020A": "Neutral / transición a La Niña",
    "2020B": "La Niña",
    "2021A": "La Niña",
    "2021B": "La Niña",
    "2022A": "La Niña",
    "2022B": "La Niña",
    "2023A": "La Niña / transición a neutral",
    "2023B": "El Niño",
    "2024A": "El Niño / transición a neutral",
    "2024B": "La Niña",
    "2025A": "La Niña / transición a neutral",
    "2025B": "La Niña",
}


def main():
    # Crear la carpeta de salida si no existe.
    SALIDA.mkdir(parents=True, exist_ok=True)

    # Leer los datos procesados.
    datos = pd.read_csv(
        ENTRADA,
        dtype={"periodo": str},
    )

    # Comprobar que estén presentes las columnas necesarias.
    columnas_requeridas = {
        "cultivo",
        "periodo",
        "variante",
        "rendimiento",
        "c_digo_dane_municipio",
    }

    faltantes = columnas_requeridas - set(datos.columns)

    if faltantes:
        raise ValueError(
            f"Faltan columnas requeridas en {ENTRADA}: "
            f"{sorted(faltantes)}"
        )

    # Seleccionar arroz y períodos semestrales con formato 2019A, 2019B...
    arroz = datos[
        datos["cultivo"].eq("Arroz")
        & datos["periodo"].str.match(r"^\d{4}[AB]$", na=False)
    ].copy()

    if arroz.empty:
        raise ValueError(
            "No se encontraron registros de arroz con períodos semestrales."
        )

    # Asignar las categorías exploratorias de ENSO.
    arroz["fase_enso"] = arroz["periodo"].map(FASE_POR_PERIODO)

    # Verificar que todos los períodos tengan una categoría.
    periodos_sin_clasificar = sorted(
        arroz.loc[
            arroz["fase_enso"].isna(),
            "periodo",
        ].unique()
    )

    if periodos_sin_clasificar:
        raise ValueError(
            "Faltan fases ENSO para estos períodos: "
            f"{periodos_sin_clasificar}"
        )

    # Convertir el rendimiento a formato numérico.
    arroz["rendimiento"] = pd.to_numeric(
        arroz["rendimiento"],
        errors="coerce",
    )

    # Excluir rendimientos faltantes del cálculo.
    arroz = arroz.dropna(subset=["rendimiento"])

    if arroz.empty:
        raise ValueError(
            "No hay rendimientos válidos para realizar el análisis."
        )

    # ---------------------------------------------------------
    # 1. Rendimiento mediano por período y variante de arroz
    # ---------------------------------------------------------
    por_periodo = (
        arroz.groupby(
            ["periodo", "fase_enso", "variante"],
            as_index=False,
        )
        .agg(
            registros=("rendimiento", "count"),
            municipios=("c_digo_dane_municipio", "nunique"),
            rendimiento_mediano=("rendimiento", "median"),
        )
        .sort_values(["periodo", "variante"])
    )

    archivo_periodos = (
        SALIDA / "arroz_rendimiento_por_periodo_enso.csv"
    )

    por_periodo.to_csv(
        archivo_periodos,
        index=False,
        encoding="utf-8-sig",
    )

    # ---------------------------------------------------------
    # 2. Resumen por fase exploratoria y variante de arroz
    # ---------------------------------------------------------
    resumen = (
        por_periodo.groupby(
            ["fase_enso", "variante"],
            as_index=False,
        )
        .agg(
            semestres=("periodo", "nunique"),
            rendimiento_mediano_entre_semestres=(
                "rendimiento_mediano",
                "median",
            ),
        )
        .sort_values(["fase_enso", "variante"])
    )

    archivo_resumen = (
        SALIDA / "arroz_resumen_por_fase_enso.csv"
    )

    resumen.to_csv(
        archivo_resumen,
        index=False,
        encoding="utf-8-sig",
    )

    # ---------------------------------------------------------
    # 3. Mostrar resultados en la terminal
    # ---------------------------------------------------------
    print(
        "Semestres de arroz analizados:",
        arroz["periodo"].nunique(),
    )

    print(
        "Variantes de arroz:",
        arroz["variante"].nunique(),
    )

    print(f"Archivo por período: {archivo_periodos}")
    print(f"Resumen por fase: {archivo_resumen}")

    print("\nResumen generado:")

    print(
        resumen.to_string(index=False)
    )

    print(
        "\nNota: las categorías ENSO son exploratorias y deben "
        "validarse con los registros históricos oficiales."
    )


if __name__ == "__main__":
    main()