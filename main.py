"""
MugiManager - Lanzador Principal del Servidor
Ejecución:
    python main.py
o:
    .venv\\Scripts\\python.exe main.py
"""
import sys
import uvicorn

if __name__ == "__main__":
    print("=" * 70)
    print("  MugiManager - Planifica tu viaje en Gipuzkoa")
    print("  Euskotren | Renfe Cercanías | Lurraldebus | Dbus | Tarjeta MUGI")
    print("  Servidor iniciado en: http://127.0.0.1:8000")
    print("=" * 70)
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
