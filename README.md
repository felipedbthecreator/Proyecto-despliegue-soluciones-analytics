# Proyecto de la Maestría en Inteligencia de Análisis de Datos para estimar el rendimiento agrícola municipal de arroz, papa y caña.

**Curso:** Despliegue de soluciones analíticas — MIAD 2026  
**Equipo:** María Valentina Páez Romero, Samuel Esteban Vargas, Felipe Delgadillo Barrera y Juan Esteban Misas Ramírez  
**Entrega:** exploración de la base agrícola EVA 2019–2025 y del índice climático RONI


Este proyecto, desarrollado en el curso Despliegue de soluciones analíticas de la Maestría en Inteligencia de Análisis de Datos (Universidad de los Andes), busca estimar el rendimiento agrícola municipal (toneladas por hectárea) de arroz, papa y caña de azúcar los cuales son muy importantes en la producción agricola de Colombia, y explorar cómo cambia bajo distintos escenarios climáticos, en particular frente al fenómeno de El Niño. Su insumo principal son las Evaluaciones Agropecuarias Municipales (EVA) de la UPRA, publicadas como datos abiertos en datos.gov.co, que reportan por municipio y periodo el área sembrada y cosechada, la producción y el rendimiento entre 2019 y 2025. Como EVA no incluye variables climáticas, se incorpora el Índice Oceánico Relativo de El Niño (RONI) de NOAA para identificar si cada periodo corresponde a El Niño, La Niña o condiciones neutrales. Una de las preguntas de apoyo es si el arroz de secano, más dependiente de la lluvia, responde distinto al clima que el arroz de riego. El producto final será un prototipo con modelos supervisados empaquetados, una API que sirva las predicciones y un tablero para consultarlas por municipio, cultivo y escenario, desplegado con contenedores Docker.

Este repositorio corresponde a la Entrega 1 e incluye la descarga reproducible de los datos desde la API de datos.gov.co, su limpieza y transformación, la exploración inicial y la documentación de la maqueta del tablero. El código se versiona con Git y los datos con DVC, de modo que cualquier integrante del equipo pueda reproducir el trabajo clonando el repositorio y recuperando los datos con `dvc pull`. Las decisiones de limpieza, las limitaciones de la fuente y los hallazgos de la exploración se detallan en el cuaderno jupyter que hace parte de este repositorio.

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