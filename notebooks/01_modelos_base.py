# Databricks notebook source
# MAGIC %md
# MAGIC # 01 · Modelos base de rendimiento (EVA + RONI)
# MAGIC Autor: Juan Esteban Misas. Corre los tres modelos base por cultivo y los registra en el
# MAGIC MLflow del workspace. La lógica vive en `src/`; este cuaderno solo la ejecuta y muestra resultados.

# COMMAND ----------
# MAGIC %pip install mlflow scikit-learn pandas --quiet

# COMMAND ----------
import os, sys
from pathlib import Path
import mlflow, pandas as pd

RAIZ = Path.cwd().parent                       # Git folder del repo en Databricks
sys.path.insert(0, str(RAIZ / "src"))
RUTA_DATOS = "/Volumes/<catalogo>/<esquema>/<volumen>/dataset_modelo.csv"  # ajustar
USUARIO = spark.sql("select current_user()").first()[0]
os.environ["AUTOR"] = "juancho"

from entrenar_base import entrenar
from modelado import slug

def experimento(cultivo):
    return f"/Users/{USUARIO}/eva-rendimiento-{slug(cultivo)}"

# COMMAND ----------
resultados = []
for cultivo in ["Arroz", "Papa", "Caña"]:
    for modelo in ["naive", "ridge", "hgb"]:
        run_id, m = entrenar(cultivo, modelo, ruta_datos=RUTA_DATOS,
                             experimento=experimento(cultivo), nombre_run=f"base-{modelo}")
        resultados.append({"cultivo": cultivo, "modelo": modelo, **m})

# COMMAND ----------
# MAGIC %md
# MAGIC ## Comparación de modelos base
# MAGIC Si ridge o hgb no le ganan a `naive`, el histórico del municipio explica casi todo y el clima aporta poco.

# COMMAND ----------
cols = ["cultivo", "modelo", "val_rmse", "val_mae", "val_r2", "nino2023_rmse", "delta_nino_pct"]
display(pd.DataFrame(resultados)[cols].round(3))
