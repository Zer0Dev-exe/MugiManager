import requests
import sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = "http://127.0.0.1:8000"

print("--- 1. Querying unconfigured card 4800554433 ---")
res = requests.get(f"{BASE}/api/mugi/card/4800554433")
assert res.status_code == 200
data = res.json()
assert data["registered"] is False
print(f"[OK] Tarjeta no configurada devuelta limpiamente: {data['message']}")

print("\n--- 2. Direct Saving Card 4800554433 with exact balance 3.75€ (NO DNI, NO Password) ---")
res = requests.post(f"{BASE}/api/mugi/card/direct-save", json={
    "card_number": "4800554433",
    "balance": 3.75,
    "holder_name": "Mi Mugi Personal",
    "monthly_trips": 5
})
assert res.status_code == 200
save_data = res.json()
print(f"[OK] Guardada directamente: {save_data['card']['holder_name']} - Saldo: {save_data['card']['balance']}€ - Tramo: {save_data['card']['tier_info']['tier_name']}")

print("\n--- 3. Querying card again (Must return exact 3.75€) ---")
res = requests.get(f"{BASE}/api/mugi/card/4800554433")
assert res.status_code == 200
card = res.json()
assert card["registered"] is True
assert card["balance"] == 3.75
print(f"[OK] Saldo confirmado al 100%: {card['balance']}€")

print("\n--- 4. Testing Recharge on direct card (+10€) ---")
res = requests.post(f"{BASE}/api/mugi/recharge", json={
    "card_number": "4800554433",
    "amount": 10.0
})
assert res.status_code == 200
rec = res.json()
assert rec["new_balance"] == 13.75
print(f"[OK] Recarga efectuada: Nuevo saldo exacto = {rec['new_balance']}€")

print("\n--- 5. Testing Trip Simulation on direct card ---")
res = requests.post(f"{BASE}/api/mugi/simulate-trip", json={
    "card_number": "4800554433",
    "operator": "Dbus",
    "line": "28",
    "stop_pair": "Boulevard -> Policlínica",
    "is_transfer": False
})
assert res.status_code == 200
trip = res.json()
print(f"[OK] Viaje descontado: Coste = {trip['cost']}€ - Saldo posterior = {trip['new_balance']}€")

print("\n=======================================================")
print("[OK] ¡MODO DIRECTO SIN DNI NI CONTRASEÑAS FUNCIONANDO AL 100%!")
print("=======================================================")
