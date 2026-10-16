"""
MugiManager - Central Application Server
Gipuzkoako Garraio Agintaritza / ATTG Integrated Transport Portal
Authentication with Email (Correo) & Password (Contraseña)
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List

from backend.auth_service import auth_service
from backend.mugi_service import mugi_service
from backend.transport_service import transport_service
from backend.ml_incident_model import incident_ml_service
from backend.scraper_service import mugi_scraper

app = FastAPI(
    title="MugiManager - Sistema Integrado de Transporte de Gipuzkoa",
    description="Portal integral de consulta de saldo MUGI con autenticación por correo y contraseña, directorio de trenes y autobuses, planificador de transbordos y detector predictivo de incidencias.",
    version="2.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount frontend directory for static assets
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# Request Models
class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    card_number: str
    initial_balance: float = Field(..., ge=0.0)
    monthly_trips: Optional[int] = 0
    card_type: Optional[str] = "MUGI Ordinaria (Arrunta)"

class UpdateBalanceRequest(BaseModel):
    email: str
    exact_balance: float = Field(..., ge=0.0)
    monthly_trips: Optional[int] = None

class CardCalibrateRequest(BaseModel):
    card_number: str
    balance: float = Field(..., ge=0.0)
    holder_name: Optional[str] = "Titular MUGI"
    monthly_trips: Optional[int] = 0
    card_type: Optional[str] = "MUGI Ordinaria (Arrunta)"

class RechargeRequest(BaseModel):
    card_number: str
    amount: float = Field(..., ge=5.0, le=150.0)
    payment_method: Optional[str] = "Bizum / Kutxabank"

class TripSimulationRequest(BaseModel):
    card_number: str
    operator: str
    line: str
    stop_pair: str
    is_transfer: bool = False

class RoutePlannerRequest(BaseModel):
    origin: str
    destination: str

class MLAnalyzeRequest(BaseModel):
    text: str

class ReportIncidentRequest(BaseModel):
    title: str
    text: str
    operator: str = "Auto"
    zone: str = "Auto"

# --- Root HTML Route & Favicon ---
@app.get("/", response_class=FileResponse)
@app.get("/index.html", response_class=FileResponse)
async def serve_index():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="Index file not found")
    return FileResponse(index_path)

@app.get("/favicon.ico", include_in_schema=False)
async def serve_favicon():
    favicon_path = os.path.join(FRONTEND_DIR, "img", "icon-192.png")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path)
    raise HTTPException(status_code=404, detail="Favicon not found")

# --- AUTHENTICATION ENDPOINTS (EMAIL & PASSWORD) ---
@app.post("/api/auth/login")
async def login(req: LoginRequest):
    try:
        user = auth_service.authenticate(req.email, req.password)
        if not user:
            raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos en el portal MUGI.")
        card = user.get("card")
        if card:
            card["tier_info"] = mugi_service._determine_tier(card["monthly_trips"])
        return user
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.post("/api/auth/register")
async def register(req: RegisterRequest):
    try:
        user = auth_service.register_user(
            email=req.email,
            password=req.password,
            full_name=req.full_name,
            card_number=req.card_number,
            initial_balance=req.initial_balance,
            monthly_trips=req.monthly_trips or 0,
            card_type=req.card_type or "MUGI Ordinaria (Arrunta)"
        )
        card = user.get("card")
        if card:
            card["tier_info"] = mugi_service._determine_tier(card["monthly_trips"])
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/auth/me")
async def get_current_user(token: str = Query(...)):
    user = auth_service.get_user_by_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Sesión expirada o no válida.")
    card = user.get("card")
    if card:
        card["tier_info"] = mugi_service._determine_tier(card["monthly_trips"])
    return user

@app.post("/api/auth/update-balance")
async def update_balance(req: UpdateBalanceRequest, token: Optional[str] = Query(None)):
    user = auth_service.get_user_by_token(token) if token else None
    if not user or user["email"] != req.email.strip().lower():
        raise HTTPException(status_code=401, detail="Inicia sesión para actualizar tu saldo.")
    try:
        card = auth_service.update_balance(req.email, req.exact_balance, req.monthly_trips)
        card["tier_info"] = mugi_service._determine_tier(card["monthly_trips"])
        return {
            "success": True,
            "message": "Saldo real actualizado con éxito en tu cuenta MUGI.",
            "card": card
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/auth/logout")
async def logout(token: str = Query(...)):
    auth_service.logout(token)
    return {"success": True}

# --- CARD LOOKUP & CALIBRATION (solo el titular con sesión iniciada) ---
def require_card_owner(token: Optional[str], card_number: str) -> dict:
    """Devuelve el usuario si el token es válido y la tarjeta es suya; si no, 401/403."""
    user = auth_service.get_user_by_token(token) if token else None
    if not user:
        raise HTTPException(status_code=401, detail="Inicia sesión para consultar o gestionar tu tarjeta MUGI.")
    clean_num = card_number.replace(" ", "").replace("-", "").strip()
    if user.get("card", {}).get("card_number") != clean_num:
        raise HTTPException(status_code=403, detail="Esta tarjeta no está vinculada a tu cuenta.")
    return user

@app.get("/api/mugi/card/{card_number}")
async def get_mugi_card(card_number: str, token: Optional[str] = Query(None)):
    require_card_owner(token, card_number)
    card = mugi_service.get_card(card_number)
    if not card:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada.")
    card["registered"] = True
    return card

@app.post("/api/mugi/card/calibrate")
async def calibrate_card(req: CardCalibrateRequest, token: Optional[str] = Query(None)):
    require_card_owner(token, req.card_number)
    try:
        card = mugi_service.save_or_calibrate_card(
            card_number=req.card_number,
            balance=req.balance,
            holder_name=req.holder_name,
            monthly_trips=req.monthly_trips,
            card_type=req.card_type
        )
        return {
            "success": True,
            "message": "Saldo real de la tarjeta calibrado y guardado correctamente.",
            "card": card
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- RECHARGE & TRIP SIMULATION ---
@app.post("/api/mugi/recharge")
async def recharge_card(req: RechargeRequest, token: Optional[str] = Query(None)):
    require_card_owner(token, req.card_number)
    try:
        result = mugi_service.recharge_card(req.card_number, req.amount, req.payment_method or "Bizum")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/mugi/simulate-trip")
async def simulate_trip(req: TripSimulationRequest, token: Optional[str] = Query(None)):
    require_card_owner(token, req.card_number)
    try:
        result = mugi_service.simulate_trip(req.card_number, req.operator, req.line, req.stop_pair, req.is_transfer)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- WEB SCRAPING ENDPOINTS (mugi.eus) ---
@app.get("/api/mugi/scraped-news")
async def get_scraped_news():
    data = mugi_scraper.get_scraped_data()
    return {
        "status": data.get("status", "connected"),
        "last_updated": data.get("last_updated"),
        "source": "https://www.mugi.eus",
        "count": len(data.get("news", [])),
        "news": data.get("news", [])
    }

@app.get("/api/mugi/scraped-tariffs")
async def get_scraped_tariffs():
    data = mugi_scraper.get_scraped_data()
    return {
        "status": data.get("status", "connected"),
        "last_updated": data.get("last_updated"),
        "source": "https://www.mugi.eus/index.php/es/tarjetas/tarifas",
        "tariffs": data.get("tariffs", [])
    }

@app.post("/api/mugi/sync-web")
async def sync_web_data():
    data = mugi_scraper.scrape_all()
    return {
        "success": True,
        "message": f"Web scraping completado con éxito de {data.get('source_domain')}",
        "last_updated": data.get("last_updated"),
        "news_scraped": len(data.get("news", [])),
        "tariffs_scraped": len(data.get("tariffs", []))
    }

# --- Transport Endpoints ---
@app.get("/api/transport/operators")
async def get_operators():
    return transport_service.operators

@app.get("/api/transport/lines")
async def get_lines(operator: Optional[str] = None, mode: Optional[str] = None):
    return transport_service.get_all_lines(operator_filter=operator, mode_filter=mode)

@app.get("/api/transport/lines/{line_id}")
async def get_line(line_id: str):
    line = transport_service.get_line_by_id(line_id)
    if not line:
        raise HTTPException(status_code=404, detail="Línea no encontrada")
    return line

@app.get("/api/transport/stops")
async def search_stops(q: str = ""):
    return transport_service.search_stops(q)

@app.get("/api/transport/hubs")
async def get_transfer_hubs():
    return transport_service.transfer_hubs

@app.post("/api/transport/route")
async def plan_journey(req: RoutePlannerRequest):
    result = transport_service.plan_multimodal_journey(req.origin, req.destination)
    return result

# --- Machine Learning Incidents Endpoints ---
@app.get("/api/incidents")
async def get_active_incidents(zone: Optional[str] = None):
    return {
        "count": len(incident_ml_service.get_active_incidents(zone)),
        "ml_status": incident_ml_service.accuracy_metrics,
        "incidents": incident_ml_service.get_active_incidents(zone)
    }

@app.post("/api/incidents/analyze")
async def analyze_incident_text(req: MLAnalyzeRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="El texto del aviso no puede estar vacío.")
    analysis = incident_ml_service.predict_incident(req.text)
    return analysis

@app.post("/api/incidents/train")
async def retrain_model():
    metrics = incident_ml_service.train()
    return {
        "success": True,
        "message": "Modelo de Machine Learning re-entrenado con éxito.",
        "metrics": metrics
    }

@app.post("/api/incidents/report")
async def report_incident(req: ReportIncidentRequest):
    if not req.text.strip() or not req.title.strip():
        raise HTTPException(status_code=400, detail="Título y descripción son obligatorios.")
    incident = incident_ml_service.report_incident(req.title, req.text, req.operator, req.zone)
    return incident

# La web (index.html, css, js, img) se sirve desde la raíz con rutas relativas.
# Va al final para que las rutas /api tengan prioridad.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="web")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
