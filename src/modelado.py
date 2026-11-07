"""Piezas del modelo de rendimiento: variables, particiones, pipelines, métricas y escenarios.

Un modelo por cultivo (Arroz, Papa, Caña): las escalas de rendimiento son muy distintas
(arroz ~2-7 t/ha, caña ~50-115 t/ha) y la caña es anual con su propia medida de clima.
"""

import unicodedata

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin, TransformerMixin
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor, make_column_selector
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

FRECUENCIA = {"Arroz": "semestral", "Papa": "semestral", "Caña": "anual"}
CLIMA = {
    "semestral": ["roni_medio", "roni_medio_previo"],
    "anual": ["roni_medio", "prop_nino", "prop_nina", "roni_medio_previo"],
}
# Supuesto de cada escenario (documentarlo en el reporte): RONI del periodo a estimar.
ESCENARIOS = {
    "nino": {"roni_medio": 1.0, "prop_nino": 1.0, "prop_nina": 0.0},
    "neutro": {"roni_medio": 0.0, "prop_nino": 0.0, "prop_nina": 0.0},
    "nina": {"roni_medio": -1.0, "prop_nino": 0.0, "prop_nina": 1.0},
}
ANIO_VAL, ANIO_TEST = 2024, 2025
PERIODO_NINO = {"semestral": "2023B", "anual": "2023"}


def slug(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return "".join(c if c.isalnum() else "_" for c in sin_tildes.lower()).strip("_")


def columnas(cultivo: str, usar_area: bool = False):
    """Variables conocidas antes de la cosecha. cod_mpio entra y se codifica en el pipeline."""
    frec = FRECUENCIA[cultivo]
    cat = ["variante", "cod_depto"] + (["semestre"] if frec == "semestral" else [])
    num = ["anio"] + CLIMA[frec] + (["log_area_sembrada"] if usar_area else [])
    return ["cod_mpio"] + cat + num, cat


# ---------------------------------------------------------------- particiones
def particiones(df: pd.DataFrame, cultivo: str):
    """Temporal: entrenamiento <= 2023, validación 2024, prueba 2025."""
    d = df[df["cultivo"] == cultivo]
    return d[d["anio"] < ANIO_VAL], d[d["anio"] == ANIO_VAL], d[d["anio"] == ANIO_TEST]


def backtest_nino(df: pd.DataFrame, cultivo: str):
    """Entrena con todo lo anterior a El Niño 2023 y evalúa en ese periodo."""
    d = df[df["cultivo"] == cultivo]
    p = PERIODO_NINO[FRECUENCIA[cultivo]]
    return d[d["periodo"] < p], d[d["periodo"] == p]


# ---------------------------------------------------------------- transformadores
class HistoricoMunicipio(BaseEstimator, TransformerMixin):
    """Reemplaza cod_mpio por el rendimiento histórico del municipio-variante.

    Se calcula solo con los datos de fit (sin fuga) y se encoge hacia la mediana de la
    variante según `suavizado`: municipios con pocas observaciones pesan menos.
    """

    def __init__(self, suavizado: float = 5.0):
        self.suavizado = suavizado

    def fit(self, X, y):
        d = X[["cod_mpio", "variante"]].assign(y=np.asarray(y, dtype=float))
        self.base_ = d.groupby("variante")["y"].median()
        self.global_ = float(d["y"].median())
        self.tabla_ = d.groupby(["cod_mpio", "variante"])["y"].agg(["median", "size"])
        return self

    def transform(self, X):
        X = X.copy()
        llave = pd.MultiIndex.from_frame(X[["cod_mpio", "variante"]])
        med = self.tabla_["median"].reindex(llave).to_numpy()
        n = self.tabla_["size"].reindex(llave).fillna(0).to_numpy()
        base = X["variante"].map(self.base_).fillna(self.global_).to_numpy()
        med = np.where(np.isnan(med), base, med)
        m = self.suavizado
        X["te_mpio"] = (n * med + m * base) / (n + m) if m > 0 else med
        X["n_obs_mpio"] = n
        return X.drop(columns="cod_mpio")


class InteraccionClima(BaseEstimator, TransformerMixin):
    """roni_medio × variante: permite que el clima afecte distinto a cada variante (Ridge)."""

    def fit(self, X, y=None):
        self.variantes_ = sorted(X["variante"].unique())
        return self

    def transform(self, X):
        X = X.copy()
        for v in self.variantes_:
            X[f"roni_x_{slug(v)}"] = (X["variante"] == v).astype(float) * X["roni_medio"]
        return X


class MedianaHistorica(BaseEstimator, RegressorMixin):
    """Referencia ingenua: predice la mediana histórica del municipio-variante."""

    def fit(self, X, y):
        self.hist_ = HistoricoMunicipio(suavizado=0).fit(X, y)
        return self

    def predict(self, X):
        return self.hist_.transform(X)["te_mpio"].to_numpy()


# ---------------------------------------------------------------- modelos
def construir_modelo(nombre: str, cultivo: str, params=None,
                     target_log: bool = False, usar_area: bool = False):
    params = dict(params or {})
    suavizado = params.pop("suavizado", 5.0)
    _, cat = columnas(cultivo, usar_area)

    if nombre == "naive":
        return MedianaHistorica()

    if nombre == "ridge":
        pre = ColumnTransformer([
            ("cat", OneHotEncoder(handle_unknown="ignore"), cat),
            ("num", Pipeline([("imp", SimpleImputer(strategy="median")),
                              ("esc", StandardScaler())]),
             make_column_selector(dtype_include=np.number)),
        ])
        reg = Pipeline([("hist", HistoricoMunicipio(suavizado)), ("inter", InteraccionClima()),
                        ("pre", pre), ("modelo", Ridge(**params))])
    elif nombre == "hgb":
        pre = ColumnTransformer(
            [("cat", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=np.nan,
                                    encoded_missing_value=np.nan), cat)],
            remainder="passthrough",
        )
        hgb = HistGradientBoostingRegressor(categorical_features=list(range(len(cat))),
                                            random_state=42, **params)
        reg = Pipeline([("hist", HistoricoMunicipio(suavizado)), ("pre", pre), ("modelo", hgb)])
    else:
        raise ValueError(f"Modelo desconocido: {nombre}")

    if target_log:
        return TransformedTargetRegressor(regressor=reg, func=np.log1p, inverse_func=np.expm1)
    return reg


# ---------------------------------------------------------------- evaluación
def metricas(y, p, prefijo: str) -> dict:
    y, p = np.asarray(y, dtype=float), np.asarray(p, dtype=float)
    e = y - p
    return {
        f"{prefijo}_rmse": float(np.sqrt(np.mean(e ** 2))),
        f"{prefijo}_mae": float(np.mean(np.abs(e))),
        f"{prefijo}_r2": float(r2_score(y, p)),
        f"{prefijo}_wape": float(np.abs(e).sum() / np.abs(y).sum()),
    }


def predecir_escenarios(modelo, X: pd.DataFrame) -> dict:
    """Predice cada fila bajo los tres escenarios cambiando solo el clima del periodo."""
    salida = {}
    for nombre, valores in ESCENARIOS.items():
        Xs = X.copy()
        for col, val in valores.items():
            if col in Xs:
                Xs[col] = val
        salida[nombre] = modelo.predict(Xs)
    return salida


def delta_escenarios(modelo, X: pd.DataFrame) -> dict:
    """% de cambio del rendimiento medio estimado frente al neutro, total y por variante.

    Si da ~0 el modelo ignora el clima y el tablero mostraría tres escenarios idénticos.
    """
    pred = predecir_escenarios(modelo, X)
    res = {}
    for esc in ["nino", "nina"]:
        res[f"delta_{esc}_pct"] = float(100 * (pred[esc].mean() / pred["neutro"].mean() - 1))
        for v in X["variante"].unique():
            m = (X["variante"] == v).to_numpy()
            res[f"delta_{esc}_pct_{slug(v)}"] = float(
                100 * (pred[esc][m].mean() / pred["neutro"][m].mean() - 1))
    return res
