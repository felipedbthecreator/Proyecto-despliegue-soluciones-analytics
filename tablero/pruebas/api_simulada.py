"""API simulada para probar la conexión del tablero antes de desplegar la API real.

Implementa el contrato previsto (GET /health y POST /predict) devolviendo la
estimación provisional. Uso:
    python pruebas/api_simulada.py            # http://localhost:8001
    API_URL=http://localhost:8001 python app.py
"""
import sys
from pathlib import Path

from flask import Flask, jsonify, request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import estimador_provisional  # noqa: E402

app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify(status="ok", modelo="api-simulada")


@app.post("/predict")
def predict():
    c = request.get_json()
    faltan = [k for k in ("cod_mpio", "variante", "periodo", "escenario") if k not in c]
    if faltan:
        return jsonify(error=f"Faltan campos: {faltan}"), 422
    r = estimador_provisional.predecir(int(c["cod_mpio"]), c["variante"], c["periodo"], c["escenario"])
    r["modelo"] = "api-simulada"
    return jsonify(r)


if __name__ == "__main__":
    app.run(port=8001)
