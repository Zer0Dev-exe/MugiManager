"""
MugiManager - Ubicación de los datos persistentes.
En Vercel el sistema de archivos es de solo lectura salvo /tmp, que además no se
comparte entre instancias: los datos allí son temporales.
"""
import os

if os.environ.get("MUGI_DATA_DIR"):
    DATA_DIR = os.environ["MUGI_DATA_DIR"]
elif os.environ.get("VERCEL"):
    DATA_DIR = "/tmp/mugimanager-data"
else:
    DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

os.makedirs(DATA_DIR, exist_ok=True)
