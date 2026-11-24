"""Ajuste de hiperparámetros y modelo final por cultivo.

Corre la grilla de Ridge y HGB con entrenamiento (<=2023) y validación (2024), elige
por val_rmse, reentrena la elegida con 2019-2024 y la evalúa en 2025. Registra todo
en MLflow y exporta el modelo final a models/ para la API.

Uso (desde la raíz del repo):
    python src/tuning.py --datos tablero/datos/dataset_modelo.csv

El servidor de MLflow se toma de MLFLOW_TRACKING_URI; sin ella, los runs quedan en ./mlruns.
"""

import argparse
import json
import sys
from importlib.metadata import version
from itertools import product
from pathlib import Path

import cloudpickle
import mlflow
import sklearn
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from entrenar_base import DATOS, cargar, entrenar  # noqa: E402
from modelado import columnas, construir_modelo, particiones, slug  # noqa: E402

MODELOS = Path("models")
REPORTES = Path("reports")

# Grilla. Los valores por defecto (suavizado=5, lr=0.1, sin límite de profundidad,
# min_samples_leaf=20, l2=0, alpha=1) quedan incluidos para que el tuning nunca
# elija algo peor que la ejecución base sin darse cuenta.
GRILLA = {
    "ridge": {"alpha": [0.1, 1.0, 10.0, 100.0], "suavizado": [2.0, 5.0, 10.0]},
    "hgb": {"learning_rate": [0.03, 0.1], "max_depth": [3, 6, None],"min_samples_leaf": [20, 50], "l2_regularization": [0.0, 1.0],"suavizado": [2.0, 5.0, 10.0]},
}
TARGET_LOG = [False, True]
# Fijos en HGB (valores por defecto de scikit-learn, se registran para reproducibilidad)
# (random_state=42 ya lo fija construir_modelo en src/modelado.py)
HGB_FIJOS = {"max_iter": 100, "early_stopping": "auto"}


def configuraciones():
    yield "naive", {}, False
    for modelo, grilla in GRILLA.items():
        llaves = list(grilla)
        for valores in product(*grilla.values()):
            for tlog in TARGET_LOG:
                yield modelo, dict(zip(llaves, valores)), tlog


def intervalo_80(cultivo, modelo, params, target_log, df):
    """Cuantiles 10 y 90 del error relativo (y/ŷ) en validación, por variante.

    Se usa el modelo entrenado solo con <=2023, así los residuos son fuera de muestra.
    La API multiplica la predicción por estos factores.
    """
    feats, _ = columnas(cultivo)
    tr, va, _ = particiones(df, cultivo)
    m = construir_modelo(modelo, cultivo, params, target_log).fit(tr[feats], tr["rendimiento"])
    ratio = va["rendimiento"].to_numpy() / np.clip(m.predict(va[feats]), 1e-6, None)
    r = pd.DataFrame({"variante": va["variante"].to_numpy(), "ratio": ratio})
    q = r.groupby("variante")["ratio"].quantile([0.1, 0.9]).unstack()
    salida = {v: [round(float(f[0.1]), 4), round(float(f[0.9]), 4)] for v, f in q.iterrows()}
    salida["_global"] = [round(float(np.quantile(ratio, 0.1)), 4),
                         round(float(np.quantile(ratio, 0.9)), 4)]
    return salida


def ajustar(cultivo, ruta_datos):
    filas = []
    for i, (modelo, params, tlog) in enumerate(configuraciones()):
        p = {**params, **(HGB_FIJOS if modelo == "hgb" else {})}
        run_id, res = entrenar(cultivo, modelo, p, target_log=tlog, ruta_datos=ruta_datos,
                               nombre_run=f"tuning-{modelo}-{i:03d}", registrar_modelo=False,
                               etapa="tuning")
        filas.append({"cultivo": cultivo, "modelo": modelo, "target_log": tlog,
                      "params": json.dumps(params), "run_id": run_id, **res})
    return pd.DataFrame(filas)


def final(cultivo, elegido, ruta_datos):
    params = json.loads(elegido["params"])
    modelo, tlog = elegido["modelo"], bool(elegido["target_log"])
    p = {**params, **(HGB_FIJOS if modelo == "hgb" else {})}
    run_id, res, ajustado = entrenar(
        cultivo, modelo, p, target_log=tlog, evaluar_test=True, ruta_datos=ruta_datos,
        nombre_run=f"final-{modelo}", registrar_modelo=True, etapa="final", devolver_modelo=True)

    nombre = f"rendimiento-{slug(cultivo)}"
    version_registro = mlflow.register_model(
        f"runs:/{run_id}/modelo",
        nombre,
    ).version

    df = cargar(ruta_datos)
    feats, _ = columnas(cultivo)
    versiones = {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "numpy": version("numpy"),
        "pandas": version("pandas"),
        "scikit-learn": version("scikit-learn"),
        "mlflow": version("mlflow"),
        "cloudpickle": version("cloudpickle"),
    }
    meta = {
        "cultivo": cultivo, "modelo": modelo, "target_log": tlog,
        "hiperparametros": {**p, **({"random_state": 42} if modelo == "hgb" else {})},
        "variables": feats, "run_id": run_id,
        "registro": {"nombre": nombre, "version": version_registro},
        "versiones": versiones,
        "sklearn_version": sklearn.__version__,
        "entrenado_con": "2019-2024 (entrenamiento + validación)", "evaluado_en": "2025",
        "metricas": {k: round(v, 4) for k, v in res.items()
                     if k.split("_")[0] in {"train", "val", "test", "nino2023"}
                     or k in {"delta_nino_pct", "delta_nina_pct"}},
        "intervalo_80_factores": intervalo_80(cultivo, modelo, params, tlog, df),
    }
    MODELOS.mkdir(exist_ok=True)
    base = MODELOS / f"rendimiento_{slug(cultivo)}"
    base.with_suffix(".pkl").write_bytes(cloudpickle.dumps(ajustado))
    base.with_suffix(".json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    return meta


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--cultivos", nargs="+", default=["Arroz", "Papa", "Caña"])
    ap.add_argument("--datos", default=str(DATOS))
    a = ap.parse_args()

    REPORTES.mkdir(exist_ok=True)
    todos, resumen = [], []
    for cultivo in a.cultivos:
        t = ajustar(cultivo, a.datos)
        todos.append(t)
        elegido = t.loc[t["val_rmse"].idxmin()]   # idxmin: no mezcla columnas de filas distintas
        meta = final(cultivo, elegido, a.datos)
        base = t[t["modelo"] == "naive"].iloc[0]
        resumen.append({
            "cultivo": cultivo, "modelo": meta["modelo"], "target_log": meta["target_log"],
            "hiperparametros": json.dumps(meta["hiperparametros"]),
            "n_configuraciones": len(t), "val_rmse_naive": round(base["val_rmse"], 4),
            **{k: v for k, v in meta["metricas"].items()
               if k.startswith(("val_", "test_", "nino2023_")) or k.startswith("delta_")},
            "run_id_final": meta["run_id"], "version_registro": meta["registro"]["version"],
        })
    pd.concat(todos).to_csv(REPORTES / "tuning_resultados.csv", index=False)
    pd.DataFrame(resumen).to_csv(REPORTES / "hiperparametros.csv", index=False)
    print(pd.DataFrame(resumen).T.to_string())


if __name__ == "__main__":
    main()
