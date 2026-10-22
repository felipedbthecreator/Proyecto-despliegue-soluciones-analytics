# Proyecto EVA: despliegue de soluciones analíticas

Proyecto de la Maestría en Inteligencia de Análisis de Datos para estimar el
rendimiento agrícola municipal de arroz, papa y caña.

## Preparación local

```bash
conda activate MIAD2026
pip install pandas numpy requests
python src/descargar_eva.py
python src/limpiar_eva.py
python src/eda_eva.py
```

La descarga usa el token opcional `SOCRATA_TOKEN` si está definido como
variable de entorno. Nunca se debe escribir el token en el repositorio.

## Decisiones de limpieza

- Se conservan arroz, papa y caña.
- Se conservan las variantes de arroz y las variantes azúcar/panelera de caña.
- Se excluye caña miel.
- Se excluyen periodos anuales de arroz/papa y periodos semestrales de caña.
- Se deriva `Papa todas menos criolla` a partir de las filas de papa total.
- Se valida que la criolla no supere el total antes de hacer la resta. Cuando
  la validación falla, se usa el total y se excluye la criolla para esa llave.
  Las llaves sin total correspondiente se conservan como criolla, pero no
  generan una fila derivada.
- El rendimiento se recalcula como producción dividida por área cosechada.

Los datos descargados se versionan con DVC, no con Git:

```bash
dvc add data/raw/eva_2019_2025.json
git add data/raw/eva_2019_2025.json.dvc .gitignore src docs README.md
git commit -m "Prepara descarga y limpieza de EVA"
dvc push
```
