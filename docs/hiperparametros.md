# Hiperparámetros y modelo final

## Instrucciones para ejecutarlo

1. Encienda la instancia de MLflow en AWS (`mlflow-arroz-enso`) y copie su **IPv4 pública** desde la consola de EC2. Cambia cada vez que la instancia se reinicia.
2. Desde la raíz del repositorio, en PowerShell, reemplace `<IP-EC2>` por esa IP:

```powershell
pip install -r requirements-modelo.txt
$env:MLFLOW_TRACKING_URI = "http://<IP-EC2>:5000"   # ej.: http://44.223.34.166:5000
$env:AUTOR = "nombre"
python src/tuning.py --datos tablero/datos/dataset_modelo.csv
```

El archivo `requirements-modelo.txt` fija las versiones utilizadas al entrenar y exportar los
modelos. Para cada modelo final se registra además en su JSON las versiones exactas de Python,
NumPy, pandas, scikit-learn, MLflow y cloudpickle.

3. Verifique en `http://<IP-EC2>:5000` que aparecen los experimentos `eva-rendimiento-arroz`, `eva-rendimiento-papa` y `eva-rendimiento-cana`. Si no se define `MLFLOW_TRACKING_URI`, los runs se guardan en `./mlruns` y no llegan al servidor.

El script genera:

- `reports/tuning_resultados.csv`: todas las configuraciones probadas con sus métricas.
- `reports/hiperparametros.csv`: la configuración elegida por cultivo.
- `models/rendimiento_<cultivo>.pkl` y `.json`: el modelo final y sus datos, que usa la API.

## Qué se probó

Por cultivo se probaron 169 configuraciones, todas registradas en MLflow con la etiqueta `etapa=tuning`:

| Modelo | Hiperparámetro | Valores |
|---|---|---|
| Naive | ninguno | — |
| Ridge | alpha | 0.1, 1, 10, 100 |
| | suavizado | 2, 5, 10 |
| HGB | learning_rate | 0.03, 0.1 |
| | max_depth | 3, 6, sin límite |
| | min_samples_leaf | 20, 50 |
| | l2_regularization | 0, 1 |
| | suavizado | 2, 5, 10 |
| Ridge y HGB | target_log (modelar el logaritmo del rendimiento) | sí, no |

En HGB quedan fijos `max_iter=100` y `random_state=42`. `suavizado` controla cuánto se acerca el histórico de un municipio con pocos registros a la mediana de su variante: con 10, un municipio con 3 registros pesa 3/13 y la mediana 10/13.

La grilla incluye los valores por defecto de la Entrega 2, para comparar contra esa ejecución.

## Cómo se eligió

1. Se entrena con 2019–2023 y se mide el RMSE en 2024 (validación).
2. Se escoge la configuración con menor RMSE de validación.
3. Esa configuración se reentrena con 2019–2024 y se evalúa una sola vez en 2025 (prueba).
4. El modelo final queda en MLflow con `etapa=final` y en el Model Registry como `rendimiento-arroz`, `rendimiento-papa` y `rendimiento-cana`.

El registro debe completar de forma satisfactoria antes de exportar los artefactos locales. Si
MLflow no puede crear la versión del modelo, el script termina con error y no publica un JSON
con una versión de registro nula.

El intervalo del 80 % que devuelve la API sale de los errores en validación de cada variante: percentiles 10 y 90 del cociente entre el valor real y el estimado.

## Resultado

En los tres cultivos la configuración con menor RMSE de validación fue HGB. Las ejecuciones por defecto de la Entrega 2 se reproducen exactamente dentro de la grilla (mismo RMSE de validación), lo que confirma que el tuning parte del mismo punto.

| Cultivo | Modelo | target_log | learning_rate | max_depth | min_samples_leaf | l2 | suavizado |
|---|---|---|---|---|---|---|---|
| Arroz | HGB | sí | 0.1 | sin límite | 20 | 0 | 10 |
| Papa | HGB | sí | 0.1 | sin límite | 20 | 0 | 10 |
| Caña | HGB | no | 0.1 | sin límite | 50 | 1 | 10 |

| Cultivo | RMSE naive (val.) | RMSE HGB por defecto (val.) | RMSE elegido (val.) | RMSE El Niño 2023 | RMSE prueba 2025 | R² prueba |
|---|---|---|---|---|---|---|
| Arroz | 0.8594 | 0.8020 | 0.7800 | 0.7597 | 0.7206 | 0.8667 |
| Papa | 5.2397 | 4.8182 | 4.7811 | 5.2461 | 4.6791 | 0.6532 |
| Caña | 18.0920 | 17.2949 | 17.1344 | 15.2059 | 12.0103 | 0.8247 |

Diferencia media estimada entre escenarios (validación 2024, frente al neutro): arroz −0,2 % en El Niño y +1,0 % en La Niña; papa +0,3 % y +0,2 %; caña 0,0 % y +0,2 %. El modelo final reconoce poco efecto del RONI una vez controla el histórico del municipio, el año y el semestre, en línea con lo reportado en la Entrega 2.

Los archivos `reports/tuning_resultados.csv` y `reports/hiperparametros.csv` contienen el detalle, y `models/rendimiento_<cultivo>.pkl/.json` los modelos que sirve la API (`api/main.py`).
