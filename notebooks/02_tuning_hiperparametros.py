# Databricks notebook source
# MAGIC %md
# MAGIC # 02 · Sensibilidad a hiperparámetros: modelos de rendimiento EVA
# MAGIC Reutiliza `src/modelado.py` y `src/entrenar_base.py`. No copiar código aquí: si algo
# MAGIC cambia en el modelo, se cambia en `src/` y se hace commit.

# COMMAND ----------
# MAGIC %pip install mlflow scikit-learn pandas --quiet

# COMMAND ----------
import os, sys
from pathlib import Path

RAIZ = Path.cwd().parent                     # carpeta del repo clonado en Databricks (Git folder)
sys.path.insert(0, str(RAIZ / "src"))
RUTA_DATOS = "/Volumes/<catalogo>/<esquema>/<volumen>/dataset_modelo.csv"  # ajustar

USUARIO = spark.sql("select current_user()").first()[0]
os.environ["AUTOR"] = "felipe"               # o "maria"

from entrenar_base import entrenar
from modelado import slug
from sklearn.model_selection import ParameterGrid

def experimento(cultivo):
    # Databricks exige ruta absoluta del workspace para el experimento
    return f"/Users/{USUARIO}/eva-rendimiento-{slug(cultivo)}"

# COMMAND ----------
# Grilla HGB. Mirar val_rmse, nino2023_rmse y delta_nino_pct, no solo val_rmse.
grilla_hgb = ParameterGrid({
    "learning_rate": [0.03, 0.1],
    "max_depth": [3, 6, None],
    "min_samples_leaf": [20, 50],
    "l2_regularization": [0.0, 1.0],
    "suavizado": [2.0, 10.0],
})
for cultivo in ["Arroz", "Papa", "Caña"]:
    for i, p in enumerate(grilla_hgb):
        entrenar(cultivo, "hgb", p, target_log=True, ruta_datos=RUTA_DATOS, experimento=experimento(cultivo),
                 nombre_run=f"hgb-grid-{i:02d}", registrar_modelo=False)

# COMMAND ----------
# Ridge: alpha controla cuánto se encoge el efecto del clima por variante.
for cultivo in ["Arroz", "Papa", "Caña"]:
    for alpha in [0.1, 1, 10, 100]:
        for suav in [2.0, 10.0]:
            entrenar(cultivo, "ridge", {"alpha": alpha, "suavizado": suav}, target_log=True,
                     ruta_datos=RUTA_DATOS, experimento=experimento(cultivo),
                     nombre_run=f"ridge-a{alpha}-s{suav}",
                     registrar_modelo=False)
