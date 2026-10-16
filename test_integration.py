import requests
import json
import sys

# Configure UTF-8 for console output on Windows
sys.stdout.reconfigure(encoding='utf-8')

BASE = "http://127.0.0.1:8000"

print("--- 1. Testing GET / (HTML UI) ---")
r = requests.get(f"{BASE}/")
assert r.status_code == 200
assert "MugiGipuzkoa" in r.text or "MugiMaster" in r.text
assert "Gipuzkoako Garraio Agintaritza" in r.text
print("✓ Web UI served correctly (200 OK)")

print("\n--- 2. Testing MUGI Card API ---")
r = requests.get(f"{BASE}/api/mugi/card/1234567890")
assert r.status_code == 200
card = r.json()
print(f"✓ Card 1234567890: Titular={card['holder_name']}, Saldo={card['balance']}€, Tipo={card['card_type']}, Tramo={card['tier_info']['tier_name']}")

print("\n--- 3. Testing MUGI Recharge ---")
r = requests.post(f"{BASE}/api/mugi/recharge", json={"card_number": "1234567890", "amount": 10.0, "payment_method": "Bizum"})
assert r.status_code == 200
rec = r.json()
print(f"✓ Recarga efectuada: +{rec['amount_charged']}€ (Bonif: +{rec['bonus_added']}€) -> Nuevo Saldo: {rec['new_balance']}€")

print("\n--- 4. Testing Integrated Lines (Train + Bus) ---")
r = requests.get(f"{BASE}/api/transport/lines")
assert r.status_code == 200
lines = r.json()
print(f"✓ Total líneas disponibles: {len(lines)}")
for l in lines[:4]:
    print(f"  - [{l['mode']}] {l['operator_name']}: {l['name']}")

print("\n--- 5. Testing Multi-Operator Stop Lookup (Herrera) ---")
r = requests.get(f"{BASE}/api/transport/stops?q=Herrera")
assert r.status_code == 200
stops = r.json()
print(f"✓ Parada 'Herrera' encontrada. Líneas combinadas:")
for s in stops:
    if "Herrera" in s["name"]:
        line_codes = [x["code"] for x in s["lines"]]
        ops = s["operators"]
        print(f"  - {s['name']}: Líneas [{', '.join(line_codes)}] (Operadores: {ops})")

print("\n--- 6. Testing Multimodal Journey Planner (Bus + Train Transfer) ---")
r = requests.post(f"{BASE}/api/transport/route", json={"origin": "Oiartzun Centro", "destination": "Gros"})
assert r.status_code == 200
route_res = r.json()
print(f"✓ Rutas encontradas: {route_res['count']}")
for route in route_res['routes']:
    print(f"  - Ruta: {route['type']} ({route['total_duration_min']} min, Transbordos: {route['num_transfers']})")
    print(f"    Tarifas MUGI: {route['fare_breakdown']['mugi_tramo_1']} vs Billete Ocasional: {route['fare_breakdown']['single_cash_ticket']}")

print("\n--- 7. Testing Machine Learning Incident Detector ---")
test_text = "Caída de ramas en la catenaria entre Herrera y Pasaia con corte temporal de circulación"
r = requests.post(f"{BASE}/api/incidents/analyze", json={"text": test_text})
assert r.status_code == 200
ml = r.json()
print(f"✓ Predicción ML para aviso:")
print(f"  Texto: '{test_text}'")
print(f"  Severidad ML: {ml['predicted_severity']} (Confianza: {ml['confidence_percentage']}%)")
print(f"  Categoría ML: {ml['predicted_category']}")
print(f"  Zona ML: {ml['predicted_zone']}")
print(f"  Operador ML: {ml['predicted_operator']}")
print(f"  Demora estimada: +{ml['estimated_delay_min']} min")
print(f"  Solución de transbordo recomendada: {ml['recommended_alternative']}")

print("\n" + "=" * 60)
print("✓✓✓ TODAS LAS PRUEBAS DE INTEGRACIÓN HAN PASADO EXITOSAMENTE! ✓✓✓")
print("=" * 60)
