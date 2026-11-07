"""Cliente de la API de inferencia del modelo de rendimiento.

Contrato previsto (definido en la maqueta de la Entrega 1):

    GET  {API_URL}/health   -> 200 {"status": "ok", "modelo": "rendimiento-vX"}
    POST {API_URL}/predict  <- {"municipio", "cod_mpio", "cultivo", "variante", "periodo", "escenario"}
                            -> 200 {"rendimiento_t_ha": float, "intervalo_80": [lo, hi], "modelo": str}

Mientras la API no esté desplegada (Entrega 3), el tablero usa estimador_provisional,
que devuelve exactamente la misma estructura. Así el paso a producción solo exige
definir la variable de entorno API_URL o escribir la URL en el panel de conexión.
"""
from functools import lru_cache

import requests

import estimador_provisional
from config import API_TIMEOUT, ESCENARIOS


def armar_peticion(cod_mpio: int, municipio: str, cultivo: str, variante: str,
                   periodo: str, escenario: str) -> dict:
    return {"municipio": municipio, "cod_mpio": int(cod_mpio), "cultivo": cultivo,
            "variante": variante, "periodo": periodo, "escenario": escenario}


def probar_conexion(url: str) -> dict:
    """Consulta /health. Devuelve el estado que se guarda en el tablero."""
    url = (url or "").strip().rstrip("/")
    if not url:
        return {"url": "", "conectada": False, "mensaje": "API no configurada"}
    try:
        r = requests.get(f"{url}/health", timeout=API_TIMEOUT)
        r.raise_for_status()
        info = r.json()
        return {"url": url, "conectada": True,
                "mensaje": f"Conectada · modelo {info.get('modelo', 'sin nombre')}"}
    except Exception as e:  # noqa: BLE001 - se informa cualquier fallo al usuario
        return {"url": url, "conectada": False, "mensaje": f"Sin respuesta ({type(e).__name__})"}


@lru_cache(maxsize=4096)
def _predecir_api(url: str, cod_mpio: int, municipio: str, cultivo: str,
                  variante: str, periodo: str, escenario: str) -> dict:
    cuerpo = armar_peticion(cod_mpio, municipio, cultivo, variante, periodo, escenario)
    r = requests.post(f"{url}/predict", json=cuerpo, timeout=API_TIMEOUT)
    r.raise_for_status()
    datos = r.json()
    return {"rendimiento_t_ha": float(datos["rendimiento_t_ha"]),
            "intervalo_80": [float(x) for x in datos["intervalo_80"]],
            "modelo": datos.get("modelo", "api"), "advertencia": datos.get("advertencia")}


def predecir_escenarios(estado_api: dict | None, cod_mpio: int, municipio: str,
                        cultivo: str, variante: str, periodo: str) -> tuple[dict, str]:
    """Una petición por escenario. Devuelve (predicciones, fuente)."""
    if estado_api and estado_api.get("conectada"):
        try:
            pred = {esc: _predecir_api(estado_api["url"], cod_mpio, municipio, cultivo,
                                       variante, periodo, esc) for esc in ESCENARIOS}
            return pred, "api"
        except Exception:  # noqa: BLE001 - si la API falla se vuelve al provisional
            pass
    pred = {esc: estimador_provisional.predecir(cod_mpio, variante, periodo, esc) for esc in ESCENARIOS}
    return pred, "provisional"
