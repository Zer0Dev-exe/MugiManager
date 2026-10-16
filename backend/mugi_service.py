"""
MugiManager - MUGI Card Management Service
Official ATTG Tariff System & Real Balance Card Lookup
Integrated with User Accounts Authenticated by Email & Password
"""
from datetime import datetime, timedelta
import random
from typing import Dict, List, Optional, Any
from backend.auth_service import auth_service

class MugiService:
    def __init__(self):
        pass

    def _determine_tier(self, trips: int) -> Dict[str, Any]:
        """Calculates current ATTG discount bracket based on monthly trips."""
        if trips <= 20:
            return {
                "tier_number": 1,
                "tier_name": "Tramo 1 (1 - 20 viajes)",
                "discount_percentage": 47,
                "trips_to_next_tier": 21 - trips,
                "next_tier_name": "Tramo 2 (57% dto.)",
                "progress_percentage": round((trips / 20) * 100, 1)
            }
        elif trips <= 50:
            return {
                "tier_number": 2,
                "tier_name": "Tramo 2 (21 - 50 viajes)",
                "discount_percentage": 57,
                "trips_to_next_tier": 51 - trips,
                "next_tier_name": "Tramo 3 (90% dto.)",
                "progress_percentage": round(((trips - 20) / 30) * 100, 1)
            }
        else:
            return {
                "tier_number": 3,
                "tier_name": "Tramo 3 (51+ viajes)",
                "discount_percentage": 90,
                "trips_to_next_tier": 0,
                "next_tier_name": "Máxima bonificación alcanzada",
                "progress_percentage": 100.0
            }

    def get_card(self, card_number: str) -> Optional[Dict[str, Any]]:
        """Look up card by number in authenticated accounts or cards database."""
        clean_num = card_number.replace(" ", "").replace("-", "").strip()
        card = auth_service.find_card_by_number(clean_num)
        if card:
            card["tier_info"] = self._determine_tier(card["monthly_trips"])
            return card

        return None

    def save_or_calibrate_card(self, card_number: str, balance: float, 
                               holder_name: Optional[str] = None,
                               monthly_trips: Optional[int] = None,
                               card_type: Optional[str] = None) -> Dict[str, Any]:
        """Saves or calibrates a card balance directly and persists it."""
        clean_num = card_number.replace(" ", "").replace("-", "").strip()
        if not clean_num:
            raise ValueError("Introduce un número de tarjeta válido.")
        if balance < 0:
            raise ValueError("El saldo no puede ser negativo.")

        linked_user = next((u for u in auth_service.users.values()
                            if u.get("card", {}).get("card_number") == clean_num), None)
        if not linked_user:
            raise ValueError("Tarjeta no vinculada a ninguna cuenta. Inicia sesión para gestionarla.")

        existing = linked_user["card"]
        new_holder = (holder_name or existing.get("holder_name") or f"Titular {clean_num[-4:]}").strip()
        new_trips = monthly_trips if monthly_trips is not None else existing.get("monthly_trips", 0)
        new_type = card_type or existing.get("card_type", "MUGI Ordinaria (Arrunta)")

        bonus_pct = 0.0
        type_code = "ordinaria"
        if "gaztea" in new_type.lower():
            bonus_pct = 14.0
            type_code = "gaztea"
        elif "berezia" in new_type.lower():
            bonus_pct = 50.0
            type_code = "familia_berezia"
        elif "jubilatua" in new_type.lower():
            bonus_pct = 20.0
            type_code = "jubilatua"

        history = existing.get("history", [])
        history.insert(0, {
            "id": f"MOV-CALIB-{datetime.now().strftime('%M%S')}",
            "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "operator": "MugiManager",
            "line": "Calibrado de Saldo Real",
            "stop": "Actualización Manual",
            "type": "Saldo Exacto Calibrado",
            "cost": 0.0,
            "balance_after": round(float(balance), 2),
            "discount_applied": "Calibrado manual por el usuario"
        })

        card_obj = {
            "card_number": clean_num,
            "holder_name": new_holder,
            "card_type": new_type,
            "type_code": type_code,
            "balance": round(float(balance), 2),
            "monthly_trips": int(new_trips),
            "status": existing.get("status", "Activa"),
            "expiry_date": existing.get("expiry_date", "--"),
            "last_use": existing.get("last_use", datetime.now().strftime("%d/%m/%Y")),
            "virtual": existing.get("virtual", "No"),
            "bonus_percentage": bonus_pct,
            "history": history
        }

        linked_user["card"] = card_obj
        auth_service._save_users_db()

        card_obj["tier_info"] = self._determine_tier(card_obj["monthly_trips"])
        return card_obj

    def recharge_card(self, card_number: str, amount: float, payment_method: str = "Bizum / Kutxabank") -> Dict[str, Any]:
        """Perform a balance recharge on a MUGI card."""
        clean_num = card_number.replace(" ", "").replace("-", "").strip()
        card_user = None

        for email, u in auth_service.users.items():
            if u.get("card", {}).get("card_number") == clean_num:
                card_user = u
                break

        if not card_user:
            raise ValueError(f"Tarjeta {clean_num} no encontrada. Inicia sesión con tu correo para gestionarla.")

        card = card_user["card"]
        if amount <= 0 or amount > 150:
            raise ValueError("El importe de recarga debe ser entre 5.00€ y 150.00€")

        bonus = round(amount * (card["bonus_percentage"] / 100.0), 2)
        total_credit = amount + bonus

        card["balance"] = round(card["balance"] + total_credit, 2)

        tx_id = f"REC-{random.randint(1000, 9999)}"
        mov = {
            "id": tx_id,
            "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "operator": "MUGI Pasarela Oficial",
            "line": f"Recarga {payment_method}",
            "stop": "Sede Electrónica MUGI / ATTG",
            "type": "Recarga de Saldo",
            "cost": amount,
            "balance_after": card["balance"],
            "discount_applied": f"+{bonus:.2f}€ Bonificación tipo de tarjeta" if bonus > 0 else "Sin bonif. extra"
        }
        card["history"].insert(0, mov)
        auth_service._save_users_db()

        return {
            "success": True,
            "transaction_id": tx_id,
            "card_number": card["card_number"],
            "amount_charged": amount,
            "bonus_added": bonus,
            "new_balance": card["balance"],
            "timestamp": mov["date"]
        }

    def simulate_trip(self, card_number: str, operator: str, line: str, stop_pair: str, is_transfer: bool = False) -> Dict[str, Any]:
        """Record a validation / trip on card and apply transfer discount rules."""
        clean_num = card_number.replace(" ", "").replace("-", "").strip()
        card_user = None

        for email, u in auth_service.users.items():
            if u.get("card", {}).get("card_number") == clean_num:
                card_user = u
                break

        if not card_user:
            raise ValueError(f"Tarjeta {clean_num} no encontrada. Inicia sesión con tu correo para gestionarla.")

        card = card_user["card"]
        base_cost = 1.95
        tier_info = self._determine_tier(card["monthly_trips"])
        discount_pct = tier_info["discount_percentage"]

        if is_transfer:
            cost = 0.00
            discount_note = "100% Bonificación Transbordo ATTG (< 50 min)"
        else:
            cost = round(base_cost * (1 - discount_pct / 100.0), 2)
            if card["type_code"] == "familia_berezia":
                cost = round(cost * 0.5, 2)
            discount_note = f"{discount_pct}% {tier_info['tier_name']}"

        if card["balance"] < cost:
            raise ValueError(f"Saldo insuficiente ({card['balance']:.2f}€). El viaje cuesta {cost:.2f}€")

        card["balance"] = round(card["balance"] - cost, 2)
        if not is_transfer:
            card["monthly_trips"] += 1

        mov = {
            "id": f"VIA-{random.randint(1000, 9999)}",
            "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "operator": operator,
            "line": line,
            "stop": stop_pair,
            "type": "Transbordo Bonificado" if is_transfer else "Viaje MUGI",
            "cost": -cost,
            "balance_after": card["balance"],
            "discount_applied": discount_note
        }
        card["history"].insert(0, mov)
        auth_service._save_users_db()

        return {
            "success": True,
            "cost": cost,
            "new_balance": card["balance"],
            "monthly_trips": card["monthly_trips"],
            "movement": mov
        }

mugi_service = MugiService()
