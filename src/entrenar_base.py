"""Entrena un modelo de rendimiento y lo registra en MLflow.

Uso (desde la raíz del repo):
    python src/entrenar_base.py --cultivo Arroz --modelo hgb --params '{"learning_rate": 0.05}'
    python src/entrenar_base.py --cultivo Caña --modelo ridge --params '{"alpha": 10}' --target-log

El servidor de MLflow se toma de la variable MLFLOW_TRACKING_URI (p. ej. http://<IP-EC2>:5000).
Sin ella, los runs quedan en ./mlruns. La prueba (2025) solo se evalúa con --evaluar-test:
se usa una vez, con el modelo elegido, no para escoger hiperparámetros.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import mlflow
import mlflow.sklearn
import pandas as pd
from mlflow.models import infer_signature

sys.path.insert(0, str(Path(__file__).resolve().parent))
from modelado import (  # noqa: E402
    backtest_nino, columnas, construir_modelo, delta_escenarios, metricas, particiones, slug,
)

DATOS = Path("data/processed/dataset_modelo.csv")
MODULO = Path(__file__).resolve().parent / "modelado.py"


def cargar(ruta) -> pd.DataFrame:
    return pd.read_csv(ruta, dtype={"cod_mpio": str, "cod_depto": str, "periodo": str})


def md5(ruta) -> str:
    return hashlib.md5(Path(ruta).read_bytes()).hexdigest()


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "desconocido"


def entrenar(cultivo, modelo, params=None, target_log=False, usar_area=False,
             evaluar_test=False, ruta_datos=DATOS, experimento=None, nombre_run=None,
             registrar_modelo=True):
    params = dict(params or {})
    df = cargar(ruta_datos)
    feats, _ = columnas(cultivo, usar_area)
    y = "rendimiento"
    tr, va, te = particiones(df, cultivo)

    def nuevo():
        return construir_modelo(modelo, cultivo, params, target_log, usar_area)

    mlflow.set_experiment(experimento or f"eva-rendimiento-{slug(cultivo)}")
    with mlflow.start_run(run_name=nombre_run or f"{modelo}-{slug(cultivo)}") as run:
        mlflow.set_tags({"cultivo": cultivo, "modelo": modelo, "git_commit": git_commit(),
                         "datos_md5": md5(ruta_datos), "autor": os.getenv("AUTOR", "sin_autor")})
        mlflow.log_params({"cultivo": cultivo, "modelo": modelo, "target_log": target_log,
                           "usar_area": usar_area, "n_train": len(tr), "n_val": len(va),
                           "variables": ",".join(feats), **params})

        m = nuevo().fit(tr[feats], tr[y])
        res = metricas(tr[y], m.predict(tr[feats]), "train")
        res |= metricas(va[y], m.predict(va[feats]), "val")
        res |= delta_escenarios(m, va[feats])

        # ¿Qué tan bien habría anticipado el único El Niño fuerte del periodo?
        b_tr, b_te = backtest_nino(df, cultivo)
        if len(b_te):
            mb = nuevo().fit(b_tr[feats], b_tr[y])
            res |= metricas(b_te[y], mb.predict(b_te[feats]), "nino2023")

        final, muestra = m, va
        if evaluar_test:
            trva = pd.concat([tr, va])
            final = nuevo().fit(trva[feats], trva[y])
            res |= metricas(te[y], final.predict(te[feats]), "test")
            muestra = te
        mlflow.log_metrics(res)

        if registrar_modelo:
            X_ej = muestra[feats].head(5)
            mlflow.sklearn.log_model(
                final, artifact_path="modelo", input_example=X_ej,
                signature=infer_signature(X_ej, final.predict(X_ej)),
                code_paths=[str(MODULO)], serialization_format="cloudpickle",
            )
        print(f"[{cultivo} | {modelo}] run {run.info.run_id}")
        for k in sorted(k for k in res if not k.startswith("delta_") or k.count("_") == 2):
            print(f"  {k:>22}: {res[k]:.4f}")
        return run.info.run_id, res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--cultivo", required=True, choices=["Arroz", "Papa", "Caña"])
    ap.add_argument("--modelo", required=True, choices=["naive", "ridge", "hgb"])
    ap.add_argument("--params", default="{}", help="JSON con hiperparámetros")
    ap.add_argument("--target-log", action="store_true")
    ap.add_argument("--usar-area", action="store_true")
    ap.add_argument("--evaluar-test", action="store_true")
    ap.add_argument("--datos", default=str(DATOS))
    a = ap.parse_args()
    entrenar(a.cultivo, a.modelo, json.loads(a.params), a.target_log, a.usar_area,
             a.evaluar_test, a.datos)


if __name__ == "__main__":
    main()
