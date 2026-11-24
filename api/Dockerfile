# Imagen de la API. Se construye desde la raíz del repositorio:
#   docker build -f api/Dockerfile -t api-rendimiento .
FROM python:3.13-slim
WORKDIR /app
COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt
COPY src/modelado.py src/modelado.py
COPY models/ models/
COPY tablero/datos/dataset_modelo.csv tablero/datos/roni.txt tablero/datos/
COPY api/main.py api/main.py
RUN touch api/__init__.py
EXPOSE 8001
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
