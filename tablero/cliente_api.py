"""Cliente de la API de inferencia del modelo de rendimiento.

Contrato (implementado en api/main.py):

    GET  {API_URL}/health        -> 200 {"status": "ok", "modelo": "rendimiento-v1", "modelos": {...}}
    GET  {API_URL}/modelos       -> 200 metadatos y métricas de cada modelo final
    POST {API_URL}/predict       <- {"municipio", "cod_mpio", "cultivo", "variante", "periodo", "escenario"}
                                 -> 200 {"rendimiento_t_ha": float, "intervalo_80": [lo, hi], "modelo": str}
    POST {API_URL}/predict/lote  <- lista de peticiones /predict -> lista de respuestas

Si la API no responde, el tablero vuelve a estimador_provisional, que devuelve la misma
estructura, y lo advierte con una franja amarilla. En el despliegue con docker-compose
API_URL apunta al servicio api (http://api:8001).
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
        try:
            metadatos = requests.get(f"{url}/modelos", timeout=API_TIMEOUT).json()
        except Exception:  # noqa: BLE001 - /modelos es informativo
            metadatos = {}
        return {"url": url, "conectada": True, "modelos": info.get("modelos", {}), "metadatos": metadatos,
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


def predecir_lote(estado_api: dict | None, municipios: list[tuple[int, str]], cultivo: str,
                  variante: str, periodo: str) -> tuple[dict, str]:
    """Escenarios para varios municipios en una sola petición (ranking departamental).

    Devuelve ({cod_mpio: {escenario: respuesta}}, fuente).
    """
    if estado_api and estado_api.get("conectada"):
        cuerpo = [armar_peticion(c, n, cultivo, variante, periodo, e) for c, n in municipios for e in ESCENARIOS]
        try:
            r = requests.post(f"{estado_api['url']}/predict/lote", json=cuerpo, timeout=API_TIMEOUT * 4)
            r.raise_for_status()
            salida: dict = {}
            for pet, res in zip(cuerpo, r.json()):
                salida.setdefault(pet["cod_mpio"], {})[pet["escenario"]] = res
            return salida, "api"
        except Exception:  # noqa: BLE001 - API antigua sin /predict/lote: una petición por municipio
            pass
    return {c: predecir_escenarios(estado_api, c, n, cultivo, variante, periodo)[0] for c, n in municipios}, (
        "api" if estado_api and estado_api.get("conectada") else "provisional")
