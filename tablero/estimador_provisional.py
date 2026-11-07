"""Estimación provisional local, usada solo mientras la API del modelo no está conectada.

Replica el contrato de respuesta de POST /predict para que el tablero funcione igual con
o sin API. NO es el modelo seleccionado (HGB): es la línea base Naive del reporte
(mediana histórica del municipio-variante, suavizada hacia la mediana de la variante)
multiplicada por una sensibilidad lineal al RONI estimada con los mismos datos:

    y(escenario) = mediana_mpio * exp(b * roni_escenario)

donde b es la pendiente de log(rendimiento / mediana_mpio) frente a roni_medio. La
pendiente municipal se contrae hacia la de la variante porque cada municipio tiene
como máximo 14 observaciones. El intervalo del 80% sale de los cuantiles 10 y 90 de
los residuos en escala logarítmica observados en esa fase.
"""
from functools import lru_cache

import numpy as np
import pandas as pd

from config import ESCENARIOS
from datos import cargar_dataset

NOMBRE_MODELO = "linea-base-provisional"
K_MEDIANA = 3    # observaciones "ficticias" para suavizar la mediana municipal
K_PENDIENTE = 20  # contracción de la pendiente municipal hacia la de la variante
FASE_ESC = {"nino": "El Niño", "neutro": "Neutro", "nina": "La Niña"}


@lru_cache(maxsize=1)
def _parametros():
    d = cargar_dataset().copy()
    g = d.groupby(["cod_mpio", "var_cod"])["rendimiento"]
    d["med_mv"] = g.transform("median")
    d["n_mv"] = g.transform("size")
    d["lr"] = np.log(d["rendimiento"] / d["med_mv"])

    nacional = d.groupby("var_cod")["rendimiento"].median()

    pend_var = {v: float(np.polyfit(x["roni_medio"], x["lr"], 1)[0]) for v, x in d.groupby("var_cod")}

    pend_mv = {}
    for (m, v), x in d.groupby(["cod_mpio", "var_cod"]):
        n, b_var = len(x), pend_var[v]
        if n >= 4 and x["roni_medio"].std() > 0.3:
            b_loc = float(np.polyfit(x["roni_medio"], x["lr"], 1)[0])
            w = n / (n + K_PENDIENTE)
            pend_mv[(m, v)] = w * b_loc + (1 - w) * b_var
        else:
            pend_mv[(m, v)] = b_var

    medianas = d.groupby(["cod_mpio", "var_cod"]).agg(med=("rendimiento", "median"), n=("rendimiento", "size"))

    # Cuantiles de residuos por variante y fase; si no hay datos de la fase, se usan todos y se ensancha
    cuantiles = {}
    for v, x in d.groupby("var_cod"):
        todo = x["lr"].quantile([0.1, 0.9]).to_numpy()
        for esc, fase in FASE_ESC.items():
            xf = x[x["fase"] == fase]["lr"]
            if len(xf) >= 50:
                cuantiles[(v, esc)] = (xf.quantile([0.1, 0.9]).to_numpy(), False)
            else:
                cuantiles[(v, esc)] = (todo * 1.5, True)
    return nacional, pend_var, pend_mv, medianas, cuantiles


def predecir(cod_mpio: int, variante: str, periodo: str, escenario: str) -> dict:
    nacional, pend_var, pend_mv, medianas, cuantiles = _parametros()
    nat = float(nacional[variante])
    if (cod_mpio, variante) in medianas.index:
        r = medianas.loc[(cod_mpio, variante)]
        base = (r["n"] * r["med"] + K_MEDIANA * nat) / (r["n"] + K_MEDIANA)
    else:
        base = nat
    b = pend_mv.get((cod_mpio, variante), pend_var[variante])
    y = base * np.exp(b * ESCENARIOS[escenario]["roni_medio"])
    (q10, q90), sin_datos_fase = cuantiles[(variante, escenario)]
    # Se garantiza que el intervalo contenga la estimación puntual
    lo, hi = y * np.exp(min(q10, -0.02)), y * np.exp(max(q90, 0.02))
    return {
        "rendimiento_t_ha": round(float(y), 3),
        "intervalo_80": [round(float(lo), 3), round(float(hi), 3)],
        "modelo": NOMBRE_MODELO,
        "advertencia": "Sin observaciones de esta fase; intervalo ampliado" if sin_datos_fase else None,
    }
