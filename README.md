# Proyecto de la Maestría en Inteligencia de Análisis de Datos para estimar el rendimiento agrícola municipal de arroz, papa y caña.

**Curso:** Despliegue de soluciones analíticas — MIAD 2026  
**Equipo:** María Valentina Páez Romero, Samuel Esteban Vargas, Felipe Delgadillo Barrera y Juan Esteban Misas Ramírez  
**Entrega:** exploración de la base agrícola EVA 2019–2025 y del índice climático RONI


Este proyecto, desarrollado en el curso Despliegue de soluciones analíticas de la Maestría en Inteligencia de Análisis de Datos (Universidad de los Andes), busca estimar el rendimiento agrícola municipal (toneladas por hectárea) de arroz, papa y caña de azúcar los cuales son muy importantes en la producción agricola de Colombia, y explorar cómo cambia bajo distintos escenarios climáticos, en particular frente al fenómeno de El Niño. Su insumo principal son las Evaluaciones Agropecuarias Municipales (EVA) de la UPRA, publicadas como datos abiertos en datos.gov.co, que reportan por municipio y periodo el área sembrada y cosechada, la producción y el rendimiento entre 2019 y 2025. Como EVA no incluye variables climáticas, se incorpora el Índice Oceánico Relativo de El Niño (RONI) de NOAA para identificar si cada periodo corresponde a El Niño, La Niña o condiciones neutrales. Una de las preguntas de apoyo es si el arroz de secano, más dependiente de la lluvia, responde distinto al clima que el arroz de riego. El producto final será un prototipo con modelos supervisados empaquetados, una API que sirva las predicciones y un tablero para consultarlas por municipio, cultivo y escenario, desplegado con contenedores Docker.

Este repositorio incluye la Entrega 1, con la descarga reproducible de los datos desde la API de datos.gov.co, su limpieza y transformación, la exploración inicial y la documentación de la maqueta del tablero, y la Entrega 2, con el modelaje, la evaluación experimental y el desarrollo funcional del tablero. El código se versiona con Git y los datos con DVC, de modo que cualquier integrante del equipo pueda reproducir el trabajo clonando el repositorio y recuperando los datos con `dvc pull`. Las decisiones de limpieza, las limitaciones de la fuente y los hallazgos de la exploración se detallan en los cuadernos Jupyter que hacen parte de este repositorio.

La descarga usa el token opcional `SOCRATA_TOKEN` 

## Decisiones de limpieza

- Se conservan arroz, papa y caña: se conservan solo las de arroz, papa y caña de azúcar (unas 15.100 filas, cerca del 9% del total), porque son los cultivos definidos como foco del proyecto. Además cubren casos distintos frente al clima: dos transitorios con datos semestrales (arroz y papa) y un permanente con datos anuales (caña). El resto de cultivos de la base queda fuera para mantener el alcance acotado y la pregunta de negocio coherente.
- Se conservan las variantes de arroz y las variantes azúcar/panelera de caña:  arroz de riego, secano manual y secano mecanizado, y caña de azúcar y caña panelera. En el arroz, la variante permite contrastar si el arroz de secano, más dependiente de la lluvia, responde distinto al clima que el de riego. En la caña, azúcar y panelera se tratan como variantes de un mismo cultivo, lo que aporta más municipios y más diversidad climática que usar solo la caña de azúcar (57 municipios frente a 581 de la panelera).
- Se excluye caña miel pues su producción no es relevante para el sector cañicultor: Se excluye porque su peso es marginal: en la base representa apenas el 0,4% de la producción y el 1,0% del área cosechada de caña, frente al 70% y 55% de la caña de azúcar y el 30% y 44% de la panelera.
- Se excluyen periodos anuales de arroz/papa pues estos y periodos semestrales de caña: La EVA reporta los cultivos transitorios por semestre (por ejemplo 2021A y 2021B) y los permanentes por año (2021). Para evitar mezclar escalas temporales, el modelo de arroz y papa usa solo periodos semestrales, y el de caña solo anuales. 
- Se deriva `Papa todas menos criolla` a partir de las filas de papa total: La base publica la papa criolla y el total de papa (“todas las variedades”), y este último incluye a la criolla.
- Se valida que la criolla no supere el total antes de hacer la resta: Antes de restar se verifica que la criolla no supere al total en ninguna de las tres medidas, porque un subconjunto no puede ser mayor que el conjunto.
- El rendimiento se recalcula como producción dividida por área cosechada.

Los datos descargados se versionan con DVC:

```bash
dvc add data/raw/eva_2019_2025.json
git add data/raw/eva_2019_2025.json.dvc .gitignore src docs README.md
git commit -m "Prepara descarga y limpieza de EVA"
dvc push
```

## Índice climático (RONI)

Fuente: Índice Oceánico Relativo de El Niño (RONI) de NOAA/CPC, indicador oficial de ENSO desde febrero de 2026.
https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt

Ejecución, desde la raíz del repositorio:

    python src/descargar_roni.py   # descarga a data/raw/roni.txt (versionado con DVC)
    python src/limpiar_roni.py     # agrega por semestre y año -> data/processed/roni_periodos.csv
    python src/eda_roni.py         # gráfica de la serie -> data/processed/eda/roni_serie.png

Decisiones:

- El índice se agrega al periodo de cada cultivo: por semestre para arroz y papa, y por año para la caña.
- Cada periodo se clasifica como El Niño, neutro o La Niña con los umbrales de ±0,5 °C.
- Para la caña, además de la fase, se calcula la proporción de trimestres del año en El Niño y en La Niña, porque un promedio anual puede diluir los episodios.
- Se guardan los valores del periodo anterior para capturar el rezago entre la siembra y la cosecha.

Nota aclaratoria: las fases ENSO definidas manualmente en `src/analisis_arroz_enso.py` son provisionales. En la Entrega 2 se reemplazarán por `data/processed/roni_periodos.csv`.

## Entrega 2: modelaje y evaluación

El cuaderno [`cuaderno y mockup/cuaderno_entrega_2_proyecto_DSA.ipynb`](cuaderno%20y%20mockup/cuaderno_entrega_2_proyecto_DSA.ipynb) documenta el proceso completo de modelaje y testeo. La preparación del dataset se realiza con `src/construir_dataset.py` y genera `data/processed/dataset_modelo.csv`, junto con archivos de trazabilidad y filas excluidas.

### Diseño experimental

- Se construye un modelo independiente para arroz, papa y caña, debido a sus diferentes escalas de rendimiento, variantes y frecuencias temporales.
- La variable objetivo es el rendimiento en toneladas por hectárea. No se utilizan producción ni área cosechada como predictores porque solo están disponibles después de la cosecha y producirían fuga de información.
- Las variables predictoras incluyen municipio, departamento, variante, año, semestre cuando aplica, RONI del periodo y RONI del periodo anterior. Para caña se agregan las proporciones de trimestres en El Niño y La Niña. El área sembrada se puede incluir opcionalmente como `log_area_sembrada`.
- La separación es temporal: entrenamiento con años anteriores a 2024, validación con 2024 y prueba final con 2025. El conjunto de prueba no se utiliza para escoger modelos ni hiperparámetros.
- El transformador `HistoricoMunicipio` calcula el histórico municipio-variante exclusivamente durante `fit` y aplica suavizamiento para municipios con pocas observaciones.

### Modelos y métricas

Se comparan tres alternativas:

- `naive`: mediana histórica del municipio-variante.
- `ridge`: regresión regularizada con variables categóricas e interacciones entre RONI y variante.
- `hgb`: `HistGradientBoostingRegressor`, para capturar relaciones no lineales.

Se reportan RMSE, MAE, R² y WAPE. También se realiza un backtest específico de El Niño 2023: `2023B` para arroz y papa y `2023` para caña. La selección considera el desempeño frente a `naive`, el backtest, la estabilidad entre entrenamiento y validación y la sensibilidad entre escenarios, no únicamente el RMSE.

En las ejecuciones base documentadas:

- **Arroz:** HGB obtuvo el menor RMSE (0.8020) y el mayor R² (0.8434); `naive` obtuvo el menor MAE (0.5285) y WAPE (0.1174).
- **Papa:** HGB obtuvo el menor RMSE (4.8182) y el mayor R² (0.6302). Su WAPE (0.1554) fue muy cercano al de `naive` (0.1556).
- **Caña:** HGB obtuvo el menor RMSE (17.2949) y el mayor R² (0.6581); `naive` presentó el menor MAE (8.1874) y WAPE (0.1434).

En conjunto, HGB fue la alternativa más eficaz para reducir errores grandes y explicar variabilidad, mientras que `naive` siguió siendo competitiva para el error promedio y relativo en arroz y caña. Ridge no superó consistentemente a las otras alternativas. Papa presentó el menor R², lo que indica que su variabilidad municipal y productiva es más difícil de explicar con las variables disponibles.

Los escenarios Niño, neutro y Niña son simulaciones condicionadas: reemplazan las variables climáticas del periodo, pero no pronostican la ocurrencia del fenómeno. Los deltas frente al escenario neutro se calculan globalmente y por variante.

## Tablero y preparación para despliegue

El tablero Dash implementado en `tablero/app.py` responde la pregunta de negocio para un municipio, cultivo, variante y periodo. Incluye:

- filtros encadenados por municipio, cultivo, variante y periodo;
- tarjetas para los escenarios Niño, neutro y Niña;
- intervalo de predicción del 80%, diferencia frente al escenario neutro en porcentaje y toneladas por hectárea;
- contexto histórico, serie temporal con fases RONI y comparación entre variantes;
- ranking departamental de sensibilidad a El Niño;
- panel de estado y contrato de conexión con `GET /health` y `POST /predict`.

Los datos descriptivos del tablero provienen del dataset EVA–RONI. Mientras la API real no esté desplegada, `tablero/estimador_provisional.py` ofrece una respuesta local basada en la línea base municipal ajustada por sensibilidad histórica al RONI y la interfaz muestra una advertencia para distinguirla del modelo seleccionado. La API simulada en `tablero/pruebas/api_simulada.py` permite probar el contrato antes del despliegue.

## Limitaciones y siguientes pasos

- La ventana 2019–2025 contiene pocos periodos y pocos episodios climáticos extremos; el backtest de 2023 es evidencia exploratoria y no permite establecer causalidad.
- El RONI es una señal climática agregada y no representa por sí solo lluvia, temperatura, riego, suelo o prácticas productivas locales.
- EVA puede presentar heterogeneidad municipal, cambios de medición y diferencias de cobertura entre variantes.
- Los escenarios son contrafactuales determinísticos y no probabilidades de ocurrencia climática. Una sensibilidad estimada por el modelo no equivale a un efecto causal.
- Los intervalos de predicción deben calcularse y validarse a partir del modelo final antes de utilizarse en decisiones operativas; el estimador provisional no debe presentarse como el modelo productivo.
- La Entrega 3 debe conectar la API real, conservar el contrato de respuesta (`rendimiento_t_ha`, `intervalo_80`, `modelo`), registrar los artefactos en MLflow y verificar que las predicciones servidas correspondan al modelo seleccionado.
## Maqueta del tablero

La maqueta interactiva de la Entrega 1 está en `cuaderno y mockup/tablero_mockup.html` (se abre directamente en el navegador) y su documentación, con la relación de cada elemento con la pregunta de negocio, en `cuaderno y mockup/maqueta_tablero.md`. La implementación funcional de la Entrega 2 se encuentra en `tablero/`; mientras la API real no esté desplegada, utiliza el estimador provisional local descrito arriba.
