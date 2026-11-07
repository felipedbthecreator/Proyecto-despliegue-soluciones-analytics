"""Configuración del tablero. Todo se puede sobrescribir con variables de entorno."""
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent

# Datos descriptivos (mismo archivo que produce src/construir_dataset.py)
RUTA_DATASET = Path(os.getenv("RUTA_DATASET", BASE / "datos" / "dataset_modelo.csv"))
RUTA_RONI = Path(os.getenv("RUTA_RONI", BASE / "datos" / "roni.txt"))

# Conexión con la API del modelo (Entrega 3). Vacío = API no conectada.
API_URL = os.getenv("API_URL", "").rstrip("/")
API_TIMEOUT = float(os.getenv("API_TIMEOUT", "5"))

# Umbral para clasificar la fase del RONI (NOAA/CPC)
UMBRAL_RONI = 0.5

# Escenarios contrafactuales: mismos valores que predecir_escenarios en src/modelado.py
ESCENARIOS = {
    "nino": {"etiqueta": "El Niño", "roni_medio": 1.0, "prop_nino": 1.0, "prop_nina": 0.0},
    "neutro": {"etiqueta": "Neutro", "roni_medio": 0.0, "prop_nino": 0.0, "prop_nina": 0.0},
    "nina": {"etiqueta": "La Niña", "roni_medio": -1.0, "prop_nino": 0.0, "prop_nina": 1.0},
}

# Código usado por la API -> etiqueta en EVA
CULTIVOS = {
    "arroz": {"etiqueta": "Arroz", "periodos": ["2026B", "2027A"]},
    "papa": {"etiqueta": "Papa", "periodos": ["2026B", "2027A"]},
    "cana": {"etiqueta": "Caña", "periodos": ["2026", "2027"]},
}
VARIANTES = {
    "riego": {"cultivo": "arroz", "eva": "Arroz riego", "etiqueta": "Riego"},
    "secano_mec": {"cultivo": "arroz", "eva": "Arroz secano mecanizado", "etiqueta": "Secano mecanizado"},
    "secano_man": {"cultivo": "arroz", "eva": "Arroz secano manual", "etiqueta": "Secano manual"},
    "resto": {"cultivo": "papa", "eva": "Papa todas menos criolla", "etiqueta": "Todas menos criolla"},
    "criolla": {"cultivo": "papa", "eva": "Papa criolla", "etiqueta": "Criolla"},
    "azucar": {"cultivo": "cana", "eva": "Caña de azúcar", "etiqueta": "Caña de azúcar"},
    "panelera": {"cultivo": "cana", "eva": "Caña panelera", "etiqueta": "Caña panelera"},
}
EVA_A_CODIGO = {v["eva"]: k for k, v in VARIANTES.items()}

COLORES = {
    "primario": "#24564A", "nino": "#B4432E", "nino_suave": "#F4DDD6",
    "nina": "#2E6CA4", "nina_suave": "#D9E6F2", "neutro": "#7F8A83",
    "tinta": "#1B2A23", "tenue": "#5B6B62", "linea": "#D2DBD3",
}
