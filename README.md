# Proyecto EVA: despliegue de soluciones analíticas

Proyecto de la Maestría en Inteligencia de Análisis de Datos para estimar el
rendimiento agrícola municipal de arroz, papa y caña.

# Proyecto EVA: despliegue de soluciones analíticas

Este proyecto, desarrollado en el curso Despliegue de soluciones analíticas de la Maestría en Inteligencia de Análisis de Datos (Universidad de los Andes), busca estimar el rendimiento agrícola municipal (toneladas por hectárea) de arroz, papa y caña de azúcar los cuales son muy importantes en la producció agricola de Colombia, y explorar cómo cambia bajo distintos escenarios climáticos, en particular frente al fenómeno de El Niño. Su insumo principal son las Evaluaciones Agropecuarias Municipales (EVA) de la UPRA, publicadas como datos abiertos en datos.gov.co, que reportan por municipio y periodo el área sembrada y cosechada, la producción y el rendimiento entre 2019 y 2025. La hipótesis central es que, en periodos con El Niño, el rendimiento del arroz de secano cae más que el del arroz de riego, por su mayor dependencia de la lluvia. El producto final será un prototipo con modelos supervisados empaquetados, una API que sirva las predicciones y un tablero para consultarlas por municipio, cultivo y escenario, desplegado con contenedores Docker.

Este repositorio corresponde a la Entrega 1 e incluye la descarga reproducible de los datos desde la API de datos.gov.co, su limpieza y transformación, la exploración inicial y la documentación de la maqueta del tablero. El código se versiona con Git y los datos con DVC, de modo que cualquier integrante del equipo pueda reproducir el trabajo clonando el repositorio y recuperando los datos con `dvc pull`. Las decisiones de limpieza, las limitaciones de la fuente y los hallazgos de la exploración se detallan en el cuaderno jupyter que hace parte de este repositorio.

La descarga usa el token opcional `SOCRATA_TOKEN` 

## Decisiones de limpieza

- Se conservan arroz, papa y caña: se conservan solo las de arroz, papa y caña de azúcar (unas 15.100 filas, cerca del 9% del total), porque son los cultivos definidos como foco del proyecto. Además cubren casos distintos frente al clima: dos transitorios con datos semestrales (arroz y papa) y un permanente con datos anuales (caña). El resto de cultivos de la base queda fuera para mantener el alcance acotado y la pregunta de negocio coherente.
- Se conservan las variantes de arroz y las variantes azúcar/panelera de caña:  arroz de riego, secano manual y secano mecanizado, y caña de azúcar y caña panelera. En el arroz, la variante  permite contrastar la hipótesis central, que el arroz de secano que es más dependiente de la lluvia, pierde más rendimiento que el de riego en periodos con El Niño. En la caña, azúcar y panelera se tratan como variantes de un mismo cultivo, lo que aporta más municipios y más diversidad climática que usar solo la caña de azúcar (57 municipios frente a 581 de la panelera).
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
