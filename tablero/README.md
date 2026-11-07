# Tablero – Rendimiento agrícola esperado bajo El Niño

Tablero en Dash que responde la pregunta de negocio del proyecto: **¿cuál es el rendimiento esperado (t/ha) de arroz, papa y caña en un municipio y periodo dados, y cuánto difiere bajo El Niño frente a un escenario neutro o de La Niña?** Sigue la maqueta de la Entrega 1 (`docs/maqueta_tablero.md`).

## Ejecutar en local

```bash
cd tablero
pip install -r requirements.txt
python app.py                 # http://localhost:8050
```

Con Docker:

```bash
docker build -t tablero-rendimiento .
docker run -p 8050:8050 -e API_URL=http://<ip-api>:8001 tablero-rendimiento
```

## Estructura

| Archivo | Contenido |
|---|---|
| `app.py` | Diseño del tablero (Dash), filtros encadenados, gráficas y callbacks. |
| `datos.py` | Carga de `dataset_modelo.csv` y del RONI; consultas descriptivas (histórico, medianas, área sembrada, fase actual). |
| `cliente_api.py` | Cliente de la API del modelo: `GET /health`, `POST /predict`, una petición por escenario. |
| `estimador_provisional.py` | Estimación local con la misma respuesta de la API, usada solo mientras la API no está conectada. |
| `config.py` | Rutas, URL de la API, escenarios, códigos de cultivo y variante, colores. |
| `assets/estilos.css` | Estilos (paleta y estructura de la maqueta). |
| `pruebas/api_simulada.py` | API de prueba con el contrato previsto, para verificar la conexión. |
| `datos/` | Copia de `data/processed/dataset_modelo.csv` y de `roni.txt` (NOAA/CPC). |

Variables de entorno: `API_URL` (vacío = no conectada), `API_TIMEOUT`, `RUTA_DATASET`, `RUTA_RONI`, `PUERTO`.

## Conexión con la API (pendiente para la Entrega 3)

El panel *Conexión con la API del modelo* permite escribir la URL y probarla. Mientras la API no responda, las tarjetas de escenarios, el panel de variantes y el ranking usan `estimador_provisional.py` y una franja amarilla lo advierte. Cuando la API esté desplegada basta con definir `API_URL`; no hay que cambiar el tablero.

Contrato que debe cumplir la API:

```json
GET /health  ->  {"status": "ok", "modelo": "rendimiento-v1"}

POST /predict
{"municipio": "Pueblo Nuevo", "cod_mpio": 23570, "cultivo": "arroz",
 "variante": "secano_man", "periodo": "2026B", "escenario": "nino"}

200 OK
{"rendimiento_t_ha": 1.53, "intervalo_80": [0.97, 1.82], "modelo": "rendimiento-v1"}
```

Códigos: `cultivo` ∈ {arroz, papa, cana}; `variante` ∈ {riego, secano_mec, secano_man, resto, criolla, azucar, panelera}; `escenario` ∈ {nino, neutro, nina}. La API traduce el escenario a `roni_medio = 1 / 0 / −1` (y `prop_nino`, `prop_nina` en caña), igual que `predecir_escenarios` en `src/modelado.py`.

Para probar la conexión sin la API real:

```bash
python pruebas/api_simulada.py                       # terminal 1
API_URL=http://localhost:8001 python app.py          # terminal 2
```
