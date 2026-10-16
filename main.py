"""
MugiManager - Lanzador Principal del Servidor
Ejecución local:
    python main.py
o:
    .venv\\Scripts\\python.exe main.py

En Vercel no se ejecuta este bloque: la plataforma detecta FastAPI y sirve `app`.
"""
from backend.main import app  # noqa: F401  (punto de entrada para Vercel)

if __name__ == "__main__":
    import uvicorn

    print("=" * 70)
    print("  MugiManager - Planifica tu viaje en Gipuzkoa")
    print("  Euskotren | Renfe Cercanías | Lurraldebus | Dbus | Metro Bilbao | Bizkaibus")
    print("  Servidor iniciado en: http://127.0.0.1:8000")
    print("=" * 70)
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
