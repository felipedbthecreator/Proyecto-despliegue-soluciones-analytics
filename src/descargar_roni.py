"""Descarga el Índice Oceánico Relativo de El Niño (RONI) publicado por NOAA/CPC."""

from pathlib import Path
import requests


URL = "https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt"
SALIDA = Path("data/raw/roni.txt")


def main() -> None:
    respuesta = requests.get(URL, timeout=60)
    respuesta.raise_for_status()
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(respuesta.text, encoding="utf-8")
    trimestres = len(respuesta.text.strip().splitlines()) - 1
    print(f"Archivo guardado en {SALIDA}: {trimestres} trimestres")


if __name__ == "__main__":
    main()