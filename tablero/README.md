# Tablero – Rendimiento agrícola esperado bajo El Niño

Tablero en Dash que responde la pregunta de negocio del proyecto: **¿cuál es el rendimiento esperado (t/ha) de arroz, papa y caña en un municipio y periodo dados, y cuánto difiere bajo El Niño frente a un escenario neutro o de La Niña?** Sigue la maqueta de la Entrega 1 (`docs/maqueta_tablero.md`).

## Ejecutar en local

```bash
cd tablero
pip install -r requirements.txt
python app.py                 # http://localhost:8050
```

Con la API (recomendado), desde la raíz del repositorio:

```bash
docker compose up -d --build      # API en :8001 y tablero en :8050
```

Solo el tablero con Docker, apuntando a una API ya desplegada:

```bash
docker build -t tablero-rendimiento .
docker run -p 8050:8050 -e API_URL=http://<ip-api>:8001 tablero-rendimiento
```

## Estructura

| Archivo | Contenido |
|---|---|
| `app.py` | Diseño del tablero (Dash), filtros encadenados, gráficas y callbacks. |
| `datos.py` | Carga de `dataset_modelo.csv` y del RONI; consultas descriptivas (histórico, medianas, área sembrada, fase actual). |
| `cliente_api.py` | Cliente de la API del modelo: `GET /health`, `GET /modelos`, `POST /predict` (una petición por escenario) y `POST /predict/lote` (ranking). |
| `estimador_provisional.py` | Estimación local con la misma respuesta de la API, usada solo si la API no responde. |
| `config.py` | Rutas, URL de la API, escenarios, códigos de cultivo y variante, colores. |
| `assets/estilos.css` | Estilos (paleta y estructura de la maqueta). |
| `pruebas/api_simulada.py` | API de prueba con el contrato previsto, para verificar la conexión. |
| `datos/` | Copia de `data/processed/dataset_modelo.csv` y de `roni.txt` (NOAA/CPC). |

Variables de entorno: `API_URL` (vacío = no conectada), `API_TIMEOUT`, `RUTA_DATASET`, `RUTA_RONI`, `PUERTO`.

## Conexión con la API

La API está en `api/main.py` (raíz del repositorio) y sirve los modelos finales de `models/`. El panel *Conexión con la API del modelo* muestra el estado (`GET /health`), permite cambiar la URL y la petición JSON enviada. Con la API conectada, la franja superior es verde e indica el modelo y su RMSE en prueba; si la API no responde, las cifras pasan al estimador provisional y la franja se vuelve amarilla.

Contrato:

```json
GET /health  ->  {"status": "ok", "modelo": "rendimiento-v1",
                  "modelos": {"arroz": "rendimiento-arroz-hgb-v1", ...}}

POST /predict
{"municipio": "Pueblo Nuevo", "cod_mpio": 23570, "cultivo": "arroz",
 "variante": "secano_man", "periodo": "2026B", "escenario": "nino"}

200 OK
{"rendimiento_t_ha": 1.51, "intervalo_80": [1.179, 1.931], "modelo": "rendimiento-arroz-hgb-v1",
 "escenario": "nino", "variables_clima": {"roni_medio": 1.0, "roni_medio_previo": -0.115},
 "advertencia": null}
```

Códigos: `cultivo` ∈ {arroz, papa, cana}; `variante` ∈ {riego, secano_mec, secano_man, resto, criolla, azucar, panelera}; `escenario` ∈ {nino, neutro, nina}. La API traduce el escenario a `roni_medio = 1 / 0 / −1` (y `prop_nino`, `prop_nina` en caña), igual que `predecir_escenarios` en `src/modelado.py`.

La API simulada (`pruebas/api_simulada.py`) se conserva para probar el tablero sin los modelos.
