"""
MugiManager - Authentication Service
User Accounts with Email (Correo Electrónico) and Password (Contraseña)
Persists accounts and exact card balances in JSON database.
"""
import os
import json
import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from backend.storage import DATA_DIR
DB_USERS_PATH = os.path.join(DATA_DIR, "mugi_users.json")

# Clave para firmar los tokens de sesión. En producción se define MUGI_SECRET;
# si falta, se genera una por proceso (las sesiones se pierden al reiniciar).
SESSION_SECRET = os.environ.get("MUGI_SECRET") or secrets.token_hex(32)
SESSION_TTL_SECONDS = 7 * 24 * 3600

from backend.mugi_portal_scraper import authenticate_mugi_portal

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

class AuthService:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self._load_users_db()

    # --- Tokens de sesión firmados: email|caducidad|firma ---
    def _issue_token(self, email: str) -> str:
        payload = f"{email}|{int(time.time()) + SESSION_TTL_SECONDS}"
        sig = hmac.new(SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return f"{payload}|{sig}"

    def _verify_token(self, token: str) -> Optional[str]:
        try:
            email, expires, sig = token.rsplit("|", 2)
        except (AttributeError, ValueError):
            return None
        expected = hmac.new(SESSION_SECRET.encode(), f"{email}|{expires}".encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected) or int(expires) < time.time():
            return None
        return email

    def _load_users_db(self):
        self.users = {}
        if os.path.exists(DB_USERS_PATH):
            try:
                with open(DB_USERS_PATH, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    for k, u in loaded.items():
                        email = u.get("email", k).strip().lower()
                        # Do not keep demo accounts if requested
                        if "mugimaster.eus" in email:
                            continue
                        self.users[email] = u
            except Exception as e:
                print(f"Error loading {DB_USERS_PATH}: {e}")

    def _save_users_db(self):
        try:
            with open(DB_USERS_PATH, "w", encoding="utf-8") as f:
                json.dump(self.users, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving {DB_USERS_PATH}: {e}")

    # --- EMAIL & PASSWORD AUTHENTICATION WITH OFFICIAL MUGI PORTAL INTEGRATION ---
    def authenticate(self, email: str, password: str) -> Dict[str, Any]:
        clean_email = email.strip().lower()

        # 1. Attempt official MUGI web portal authentication (gunepribatua.atgipuzkoa.eus)
        portal_res = authenticate_mugi_portal(clean_email, password)
        if portal_res.get("success"):
            data = portal_res["data"]
            # Save or update user in persistent database
            user_record = {
                "email": clean_email,
                "full_name": data["full_name"],
                "password_hash": hash_password(password),
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "official_sync": True,
                "card": {
                    "card_number": data["card_number"],
                    "holder_name": data["full_name"],
                    "card_type": data["card_type"],
                    "type_code": data["type_code"],
                    "balance": data["balance"],
                    "monthly_trips": data["monthly_trips"],
                    "status": data["status"],
                    "expiry_date": data.get("expiry_date", "--"),
                    "last_use": data.get("last_use", "--"),
                    "virtual": data.get("virtual", "No"),
                    "bonus_percentage": data["bonus_percentage"],
                    "history": data["history"]
                }
            }
            self.users[clean_email] = user_record
            self._save_users_db()

            token = self._issue_token(clean_email)
            user_copy = json.loads(json.dumps(user_record))
            del user_copy["password_hash"]
            user_copy["token"] = token
            user_copy["message"] = "¡Autenticación con éxito en el portal oficial de MUGI (Gune Pribatua)!"
            return user_copy

        # 2. Check local registered user accounts
        user = self.users.get(clean_email)
        if not user:
            for u in self.users.values():
                if u.get("email", "").strip().lower() == clean_email:
                    user = u
                    break

        if user:
            if user.get("password_hash") == hash_password(password):
                token = self._issue_token(clean_email)
                user_copy = json.loads(json.dumps(user))
                del user_copy["password_hash"]
                user_copy["token"] = token
                return user_copy
            else:
                raise ValueError("Contraseña incorrecta para la cuenta especificada.")

        raise ValueError("No existe ninguna cuenta con ese correo. Regístrate o usa tus credenciales del portal oficial de MUGI.")

    def register_user(self, email: str, password: str, full_name: str, 
                      card_number: str, initial_balance: float, monthly_trips: int = 0,
                      card_type: str = "MUGI Ordinaria (Arrunta)") -> Dict[str, Any]:
        clean_email = email.strip().lower()
        clean_card = card_number.replace(" ", "").replace("-", "").strip()

        if not clean_email or "@" not in clean_email:
            raise ValueError("Por favor introduce un correo electrónico válido.")

        if not password or len(password) < 4:
            raise ValueError("La contraseña debe tener al menos 4 caracteres.")

        if not clean_card or len(clean_card) < 4:
            raise ValueError("Introduce el número de tu tarjeta MUGI.")

        if initial_balance < 0:
            raise ValueError("El saldo inicial no puede ser negativo.")

        for other in self.users.values():
            if other.get("card", {}).get("card_number") == clean_card and other.get("email") != clean_email:
                raise ValueError("Esta tarjeta MUGI ya está vinculada a otra cuenta.")

        bonus_pct = 0.0
        type_code = "ordinaria"
        if "gaztea" in card_type.lower() or "joven" in card_type.lower():
            bonus_pct = 14.0
            type_code = "gaztea"
        elif "berezia" in card_type.lower():
            bonus_pct = 50.0
            type_code = "familia_berezia"
        elif "orokorra" in card_type.lower():
            bonus_pct = 20.0
            type_code = "familia_orokorra"
        elif "jubilatua" in card_type.lower() or "nagusia" in card_type.lower():
            bonus_pct = 20.0
            type_code = "jubilatua"

        card_data = {
            "card_number": clean_card,
            "holder_name": full_name.strip() or f"Tarjeta {clean_card[-4:]}",
            "card_type": card_type,
            "type_code": type_code,
            "balance": round(float(initial_balance), 2),
            "monthly_trips": int(monthly_trips),
            "status": "Activa",
            "expiry_date": "--",
            "last_use": "--",
            "virtual": "No",
            "bonus_percentage": bonus_pct,
            "history": [
                {
                    "id": "MOV-REG",
                    "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "operator": "MugiManager",
                    "line": "Registro por Correo",
                    "stop": "Alta de Cuenta Personal",
                    "type": "Saldo Real Inicial",
                    "cost": 0.00,
                    "balance_after": round(float(initial_balance), 2),
                    "discount_applied": "Saldo real configurado por el usuario"
                }
            ]
        }

        new_user = {
            "email": clean_email,
            "full_name": full_name.strip() or clean_email.split("@")[0],
            "password_hash": hash_password(password),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "card": card_data
        }

        self.users[clean_email] = new_user
        self._save_users_db()

        token = self._issue_token(clean_email)
        user_copy = json.loads(json.dumps(new_user))
        del user_copy["password_hash"]
        user_copy["token"] = token
        return user_copy

    def get_user_by_token(self, token: str) -> Optional[Dict[str, Any]]:
        self._load_users_db()
        email = self._verify_token(token)
        if not email:
            return None
        user = self.users.get(email)
        if not user:
            return None
        user_copy = json.loads(json.dumps(user))
        del user_copy["password_hash"]
        user_copy["token"] = token
        return user_copy

    def update_balance(self, email: str, exact_balance: float, monthly_trips: Optional[int] = None) -> Dict[str, Any]:
        self._load_users_db()
        clean_email = email.strip().lower()
        user = self.users.get(clean_email)
        if not user:
            for u in self.users.values():
                if u.get("email", "").strip().lower() == clean_email:
                    user = u
                    break
        if not user:
            raise ValueError("Usuario no encontrado.")

        if exact_balance < 0:
            raise ValueError("El saldo no puede ser negativo.")

        card = user["card"]
        old_balance = card["balance"]
        card["balance"] = round(float(exact_balance), 2)
        if monthly_trips is not None and monthly_trips >= 0:
            card["monthly_trips"] = int(monthly_trips)

        diff = round(card["balance"] - old_balance, 2)
        diff_str = f"+{diff:.2f}€" if diff > 0 else f"{diff:.2f}€"

        card["history"].insert(0, {
            "id": f"MOV-AJUSTE-{datetime.now().strftime('%M%S')}",
            "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "operator": "MugiManager",
            "line": "Ajuste de Saldo Real",
            "stop": "Actualización por el Usuario",
            "type": "Sincronización de Saldo",
            "cost": diff,
            "balance_after": card["balance"],
            "discount_applied": f"Calibrado de saldo ({diff_str})"
        })

        self._save_users_db()
        return card

    def find_card_by_number(self, card_number: str) -> Optional[Dict[str, Any]]:
        self._load_users_db()
        clean_num = card_number.replace(" ", "").replace("-", "").strip()
        for email, user in self.users.items():
            card = user.get("card", {})
            if card.get("card_number") == clean_num:
                card_copy = card.copy()
                card_copy["user_email"] = email
                card_copy["holder_name"] = user.get("full_name", card.get("holder_name"))
                return card_copy
        return None

    def logout(self, token: str):
        # Los tokens firmados no se guardan en el servidor: cerrar sesión es borrarlo en el cliente.
        pass

auth_service = AuthService()
