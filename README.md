# MugiManager

Planificador de viajes en tren, metro y autobús por Gipuzkoa y Bizkaia, con el catálogo de líneas y paradas, los avisos de la red y la gestión de tu tarjeta MUGI.

- **Web:** https://zer0.is-a.dev/MugiManager/
- **API:** https://mugimanager.vercel.app
- **App Android:** descarga el APK desde [Releases](https://github.com/Zer0Dev-exe/MugiManager/releases). En iPhone y Android también se puede instalar desde la web con «Añadir a pantalla de inicio».

> **Proyecto independiente.** MugiManager no está afiliado a MUGI, a la Autoridad Territorial del Transporte de Gipuzkoa (ATTG) ni a los operadores. Horarios y tiempos de viaje son orientativos.

## Qué hace

- **Planificar viaje**: calcula la ruta más rápida entre dos paradas (hasta dos transbordos) combinando Euskotren, Renfe Cercanías, Lurraldebus, Dbus, Metro Bilbao y Bizkaibus. Los tiempos se estiman por distancia y la espera por la frecuencia de cada línea, y muestra el precio con tarjeta MUGI por tramos.
- **Trenes y buses**: líneas, frecuencias y paradas con dirección, mapa y enlaces a Google Maps.
- **Mi tarjeta**: saldo, tramo de descuento e historial. Solo es visible tras iniciar sesión, y cada usuario accede únicamente a su tarjeta.
- **Avisos**: incidencias de la red, comunicados y tarifas obtenidos de la web pública mugi.eus.
- **Predicciones IA**: clasifica avisos (severidad, categoría, demora estimada) con un modelo de scikit-learn.

## Arquitectura

| Parte | Dónde | Código |
|---|---|---|
| Web / PWA | GitHub Pages | `frontend/` (HTML, CSS y JS sin compilación) |
| App Android | APK en las releases | Capacitor sobre `frontend/` (`capacitor.config.json`) |
| API | Vercel (función Python) | `backend/` (FastAPI), entrada en `main.py` |

La URL de la API que usan la web y la app está en `frontend/js/config.js`.

## Desarrollo local

Requisitos: Python 3.10 o superior.

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # en Linux/macOS: .venv/bin/pip
python main.py
```

Abre http://127.0.0.1:8000. En local el propio backend sirve la web.

## Despliegue

- **Web**: cada push a `main` que toca `frontend/` publica en GitHub Pages (`.github/workflows/pages.yml`).
- **API**: `vercel deploy --prod` desde la raíz (Vercel detecta FastAPI y sirve `app` de `main.py`). Hay que definir la variable `MUGI_SECRET`, que firma los tokens de sesión.
- **Release**: al subir una etiqueta `vX.Y.Z`, GitHub Actions compila el APK con Capacitor y lo publica junto a un zip de la web (`.github/workflows/release.yml`).

### Limitaciones conocidas

- En Vercel las cuentas se guardan en `/tmp`, que no es persistente ni se comparte entre instancias. Las cuentas sincronizadas con el portal de MUGI se recrean al iniciar sesión, pero las registradas a mano pueden perderse. Para que sean persistentes hace falta una base de datos (por ejemplo Upstash Redis o Vercel Postgres).
- El APK se firma con la clave de depuración. Para publicarlo en Google Play hay que firmarlo con una clave propia.
