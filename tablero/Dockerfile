# Imagen del tablero (se usará en la Entrega 3 junto con la imagen de la API)
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV API_URL="" PUERTO=8050
EXPOSE 8050
CMD ["sh", "-c", "gunicorn -b 0.0.0.0:${PUERTO} --workers 2 --timeout 120 app:server"]
