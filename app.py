#!/usr/bin/env python3
"""
Nexus Tunnel VLESS & V2Ray Multi-Account Manager — Pro v3.0
Nexus Tunnel Control Panel & Client Ecosystem
Compatible avec docker.io/nextl/nexus-tunnel
"""

import os
import sys
import json
import time
import uuid
import base64
import io
import re
import ssl
import copy
import hmac
import secrets
import socket
import threading
import urllib.parse
import urllib.request
import hashlib
import shutil
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Request, Depends, status, APIRouter
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import qrcode

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "database.json")
DB_BAK_PATH = os.path.join(DATA_DIR, "database.json.bak")
SECRET_KEY_PATH = os.path.join(DATA_DIR, ".secret_key")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# Global Thread-Safe Locks & In-Memory Fallback
DB_LOCK = threading.RLock()
_LAST_GOOD_DB: Optional[Dict[str, Any]] = None
_LOGIN_LOCK = threading.RLock()
_LOGIN_FAILURES: Dict[str, List[float]] = {}

# 54 African Countries with flags, dial prefixes, and exact mobile digit lengths
AFRICAN_COUNTRIES = [
    {"code": "CM", "name": "Cameroun", "flag": "🇨🇲", "dial": "+237", "digits": 9, "example": "690123456"},
    {"code": "CI", "name": "Côte d'Ivoire", "flag": "🇨🇮", "dial": "+225", "digits": 10, "example": "0701234567"},
    {"code": "SN", "name": "Sénégal", "flag": "🇸🇳", "dial": "+221", "digits": 9, "example": "770123456"},
    {"code": "CD", "name": "RD Congo", "flag": "🇨🇩", "dial": "+243", "digits": 9, "example": "810123456"},
    {"code": "GA", "name": "Gabon", "flag": "🇬🇦", "dial": "+241", "digits": 8, "example": "74012345"},
    {"code": "ML", "name": "Mali", "flag": "🇲🇱", "dial": "+223", "digits": 8, "example": "70012345"},
    {"code": "BF", "name": "Burkina Faso", "flag": "🇧🇫", "dial": "+226", "digits": 8, "example": "70012345"},
    {"code": "GN", "name": "Guinée", "flag": "🇬🇳", "dial": "+224", "digits": 9, "example": "620123456"},
    {"code": "BJ", "name": "Bénin", "flag": "🇧🇯", "dial": "+229", "digits": 8, "example": "97012345"},
    {"code": "TG", "name": "Togo", "flag": "🇹🇬", "dial": "+228", "digits": 8, "example": "90012345"},
    {"code": "CG", "name": "Congo-Brazzaville", "flag": "🇨🇬", "dial": "+242", "digits": 9, "example": "060123456"},
    {"code": "TD", "name": "Tchad", "flag": "🇹🇩", "dial": "+235", "digits": 8, "example": "66012345"},
    {"code": "NE", "name": "Niger", "flag": "🇳🇪", "dial": "+227", "digits": 8, "example": "90012345"},
    {"code": "CF", "name": "Centrafrique", "flag": "🇨🇫", "dial": "+236", "digits": 8, "example": "70012345"},
    {"code": "MG", "name": "Madagascar", "flag": "🇲🇬", "dial": "+261", "digits": 9, "example": "340123456"},
    {"code": "DZ", "name": "Algérie", "flag": "🇩🇿", "dial": "+213", "digits": 9, "example": "550123456"},
    {"code": "MA", "name": "Maroc", "flag": "🇲🇦", "dial": "+212", "digits": 9, "example": "660123456"},
    {"code": "TN", "name": "Tunisie", "flag": "🇹🇳", "dial": "+216", "digits": 8, "example": "98012345"},
    {"code": "EG", "name": "Égypte", "flag": "🇪🇬", "dial": "+20", "digits": 10, "example": "1001234567"},
    {"code": "NG", "name": "Nigeria", "flag": "🇳🇬", "dial": "+234", "digits": 10, "example": "8021234567"},
    {"code": "GH", "name": "Ghana", "flag": "🇬🇭", "dial": "+233", "digits": 9, "example": "240123456"},
    {"code": "KE", "name": "Kenya", "flag": "🇰🇪", "dial": "+254", "digits": 9, "example": "712123456"},
    {"code": "RW", "name": "Rwanda", "flag": "🇷🇼", "dial": "+250", "digits": 9, "example": "780123456"},
    {"code": "BI", "name": "Burundi", "flag": "🇧🇮", "dial": "+257", "digits": 8, "example": "79012345"},
    {"code": "AO", "name": "Angola", "flag": "🇦🇴", "dial": "+244", "digits": 9, "example": "923123456"},
    {"code": "MZ", "name": "Mozambique", "flag": "🇲🇿", "dial": "+258", "digits": 9, "example": "840123456"},
    {"code": "ET", "name": "Éthiopie", "flag": "🇪🇹", "dial": "+251", "digits": 9, "example": "911123456"},
    {"code": "TZ", "name": "Tanzanie", "flag": "🇹🇿", "dial": "+255", "digits": 9, "example": "754123456"},
    {"code": "UG", "name": "Ouganda", "flag": "🇺🇬", "dial": "+256", "digits": 9, "example": "772123456"},
    {"code": "ZA", "name": "Afrique du Sud", "flag": "🇿🇦", "dial": "+27", "digits": 9, "example": "821234567"},
    {"code": "MR", "name": "Mauritanie", "flag": "🇲🇷", "dial": "+222", "digits": 8, "example": "46012345"},
    {"code": "GQ", "name": "Guinée Équatoriale", "flag": "🇬🇶", "dial": "+240", "digits": 9, "example": "222123456"},
    {"code": "DJ", "name": "Djibouti", "flag": "🇩🇯", "dial": "+253", "digits": 8, "example": "77012345"},
    {"code": "KM", "name": "Comores", "flag": "🇰🇲", "dial": "+269", "digits": 7, "example": "3201234"},
    {"code": "MU", "name": "Maurice", "flag": "🇲🇺", "dial": "+230", "digits": 8, "example": "57012345"},
    {"code": "SC", "name": "Seychelles", "flag": "🇸🇨", "dial": "+248", "digits": 7, "example": "2501234"},
    {"code": "CV", "name": "Cap-Vert", "flag": "🇨🇻", "dial": "+238", "digits": 7, "example": "9912345"},
    {"code": "GW", "name": "Guinée-Bissau", "flag": "🇬🇼", "dial": "+245", "digits": 7, "example": "9551234"},
    {"code": "LR", "name": "Libéria", "flag": "🇱🇷", "dial": "+231", "digits": 8, "example": "77012345"},
    {"code": "SL", "name": "Sierra Leone", "flag": "🇸🇱", "dial": "+232", "digits": 8, "example": "76012345"},
    {"code": "GM", "name": "Gambie", "flag": "🇬🇲", "dial": "+220", "digits": 7, "example": "7012345"},
    {"code": "ST", "name": "Sao Tomé-et-Principe", "flag": "🇸🇹", "dial": "+239", "digits": 7, "example": "9901234"},
    {"code": "ZW", "name": "Zimbabwe", "flag": "🇿🇼", "dial": "+263", "digits": 9, "example": "771234567"},
    {"code": "ZM", "name": "Zambie", "flag": "🇿🇲", "dial": "+260", "digits": 9, "example": "977123456"},
    {"code": "MW", "name": "Malawi", "flag": "🇲🇼", "dial": "+265", "digits": 9, "example": "991234567"},
    {"code": "BW", "name": "Botswana", "flag": "🇧🇼", "dial": "+267", "digits": 8, "example": "71234567"},
    {"code": "NA", "name": "Namibie", "flag": "🇳🇦", "dial": "+264", "digits": 8, "example": "81123456"},
    {"code": "SZ", "name": "Eswatini", "flag": "🇸🇿", "dial": "+268", "digits": 8, "example": "76123456"},
    {"code": "LS", "name": "Lesotho", "flag": "🇱🇸", "dial": "+266", "digits": 8, "example": "58123456"},
    {"code": "SO", "name": "Somalie", "flag": "🇸🇴", "dial": "+252", "digits": 8, "example": "61512345"},
    {"code": "SD", "name": "Soudan", "flag": "🇸🇩", "dial": "+249", "digits": 9, "example": "912345678"},
    {"code": "SS", "name": "Soudan du Sud", "flag": "🇸🇸", "dial": "+211", "digits": 9, "example": "920123456"},
    {"code": "LY", "name": "Libye", "flag": "🇱🇾", "dial": "+218", "digits": 9, "example": "912345678"},
    {"code": "ER", "name": "Érythrée", "flag": "🇪🇷", "dial": "+291", "digits": 7, "example": "7123456"}
]

DEFAULT_SETTINGS = {
    "host": "nexus-tunnel-753027553589.us-east1.run.app",
    "target_server": "192.179.18.100:443",
    "sni": "crashlyticsreports-pa.googleapis.com",
    "path": "/nexustunnel",
    "docker_image": "docker.io/nextl/nexus-tunnel",
    "panel_title": "Nexus Tunnel - V2Ray / VLESS Multi-Account Panel",
    "root_uuid": "e3a478b2-5e1b-4cf7-8b09-1a2b3c4d5e6f",
    "sni_list": [
        "crashlyticsreports-pa.googleapis.com",
        "firebaselogging-pa.googleapis.com",
        "clientservices.googleapis.com",
        "play.googleapis.com"
    ],
    "target_ips": [
        "192.179.18.100:443",
        "142.250.180.14:443",
        "172.217.18.206:443",
        "142.250.74.206:443",
        "216.239.38.120:443",
        "142.250.185.238:443",
        "172.217.170.206:443"
    ]
}

DEFAULT_PLANS = [
    {"id": "plan_trial", "name": "Essai Gratuit 24h", "quota_gb": 2.0, "duration_days": 1, "price_cfa": 0, "badge": "GRATUIT"},
    {"id": "plan_10gb", "name": "Découverte 10 Go", "quota_gb": 10.0, "duration_days": 30, "price_cfa": 2000, "badge": "POPULAIRE"},
    {"id": "plan_25gb", "name": "Standard 25 Go", "quota_gb": 25.0, "duration_days": 30, "price_cfa": 3500, "badge": "RECOMMANDÉ"},
    {"id": "plan_50gb", "name": "Performance 50 Go", "quota_gb": 50.0, "duration_days": 60, "price_cfa": 6000, "badge": "PRO"},
    {"id": "plan_unlimited", "name": "VIP Illimité", "quota_gb": 0.0, "duration_days": 30, "price_cfa": 10000, "badge": "ILLIMITÉ"}
]

PASSWORD_SALT = "nexus_tunnel_salt_2026"
PBKDF2_ITERATIONS = 260000


def get_secret_key() -> str:
    try:
        if os.path.exists(SECRET_KEY_PATH):
            with open(SECRET_KEY_PATH, "r", encoding="utf-8") as f:
                key = f.read().strip()
                if len(key) >= 32:
                    return key
        key = secrets.token_hex(32)
        with open(SECRET_KEY_PATH, "w", encoding="utf-8") as f:
            f.write(key)
        try:
            os.chmod(SECRET_KEY_PATH, 0o600)
        except Exception:
            pass
        return key
    except Exception:
        return "nexus_fallback_hmac_secret_key_2026_pro_v3"


SECRET_KEY = get_secret_key()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${dk}"


def verify_password(password: str, hashed: str) -> bool:
    if not hashed or not isinstance(hashed, str):
        return False
    if hashed.startswith("pbkdf2_sha256$"):
        try:
            parts = hashed.split("$", 3)
            if len(parts) != 4:
                return False
            _, iter_str, salt, stored_dk = parts
            iterations = int(iter_str)
            dk = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                iterations
            ).hex()
            return hmac.compare_digest(dk, stored_dk)
        except Exception:
            return False
    # Legacy SHA-256 format support
    legacy_hash = hashlib.sha256((PASSWORD_SALT + password).encode("utf-8")).hexdigest()
    return hmac.compare_digest(legacy_hash, hashed)


def generate_session_token(user_id: str, role: str, impersonated_by: Optional[str] = None) -> str:
    now_ts = int(time.time())
    payload = {
        "sub": user_id,
        "user_id": user_id,
        "role": role,
        "iat": now_ts,
        "exp": now_ts + 86400,
        "imp": impersonated_by
    }
    raw_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    b64_payload = base64.urlsafe_b64encode(raw_json).decode("utf-8").rstrip("=")
    sig = hmac.new(SECRET_KEY.encode("utf-8"), b64_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{b64_payload}.{sig}"


def decode_session_token(token: str) -> Optional[Dict[str, Any]]:
    if not token or not isinstance(token, str):
        return None
    token = token.strip()
    if "." in token:
        try:
            b64_payload, sig = token.rsplit(".", 1)
            expected_sig = hmac.new(
                SECRET_KEY.encode("utf-8"),
                b64_payload.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(sig, expected_sig):
                return None
            padded = b64_payload + "=" * (-len(b64_payload) % 4)
            payload = json.loads(base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8"))
            now_ts = int(time.time())
            if payload.get("exp", 0) < now_ts:
                return None
            sub = payload.get("sub") or payload.get("user_id")
            if not sub:
                return None
            return {
                "sub": sub,
                "user_id": sub,
                "role": payload.get("role", "ADMIN"),
                "iat": payload.get("iat", now_ts),
                "exp": payload.get("exp", now_ts + 86400),
                "imp": payload.get("imp")
            }
        except Exception:
            return None
    # Temporary fallback for legacy session tokens if non-expired (24h)
    try:
        raw = base64.b64decode(token.encode("utf-8")).decode("utf-8")
        parts = raw.split(":")
        if len(parts) >= 4:
            ts = int(parts[2])
            if int(time.time()) - ts <= 86400:
                return {"sub": parts[0], "user_id": parts[0], "role": parts[1], "iat": ts, "exp": ts + 86400, "imp": None}
    except Exception:
        pass
    return None


def sanitize_account(acc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not acc or not isinstance(acc, dict):
        return acc
    hidden_keys = {"password_hash", "totp_secret", "password"}
    return {k: v for k, v in acc.items() if k not in hidden_keys}


def add_audit_log(db: dict, actor_username: str, actor_role: str, action: str, details: str, target_id: Optional[str] = None):
    log_entry = {
        "id": f"log_{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor_username": actor_username or "Système",
        "actor_role": actor_role or "SYSTEM",
        "action": action,
        "details": details,
        "target_id": target_id
    }
    logs = db.setdefault("audit_logs", [])
    logs.insert(0, log_entry)
    db["audit_logs"] = logs[:300]


def record_reseller_transaction(
    db: dict,
    reseller: dict,
    action: str,
    gb_delta: float,
    target_id: Optional[str] = None,
    notes: str = ""
) -> dict:
    tx = {
        "id": f"tx_{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reseller_id": reseller.get("id"),
        "reseller_name": reseller.get("display_name") or reseller.get("username"),
        "action": action,
        "gb_delta": round(float(gb_delta), 2),
        "remaining_gb": round(float(reseller.get("credit_gb", 0.0)), 2),
        "target_id": target_id,
        "notes": notes
    }
    tx_list = db.setdefault("reseller_transactions", [])
    tx_list.insert(0, tx)
    db["reseller_transactions"] = tx_list[:500]
    return tx


def normalize_channel(val: Optional[str]) -> str:
    if not val:
        return "WHATSAPP"
    v = str(val).strip().upper()
    if "TELEGRAM" in v or v == "TG":
        return "TELEGRAM"
    return "WHATSAPP"


def format_bytes(num_bytes: Optional[int]) -> str:
    if num_bytes is None or num_bytes <= 0:
        return "0 B"
    val = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if val < 1024.0:
            return f"{val:.1f} {unit}"
        val /= 1024.0
    return f"{val:.1f} PB"


def compute_user_status(user: dict, db: Optional[dict] = None) -> dict:
    now_utc = datetime.now(timezone.utc)

    # 1. Auto Data Reset Strategy
    strategy = (user.get("data_reset_strategy") or "no_reset").lower().strip()
    if strategy not in ("no_reset", "daily", "weekly", "monthly"):
        strategy = "no_reset"

    if strategy != "no_reset":
        last_reset_str = user.get("last_reset_at") or user.get("created_at")
        period_days = {"daily": 1, "weekly": 7, "monthly": 30}.get(strategy, 0)
        if last_reset_str and period_days > 0:
            try:
                lr_dt = datetime.fromisoformat(str(last_reset_str).replace("Z", "+00:00"))
                if lr_dt.tzinfo is None:
                    lr_dt = lr_dt.replace(tzinfo=timezone.utc)
                if (now_utc - lr_dt) >= timedelta(days=period_days):
                    user["used_bytes_up"] = 0
                    user["used_bytes_down"] = 0
                    user["last_reset_at"] = now_utc.isoformat()
            except Exception:
                pass

    total_used = int(user.get("used_bytes_up", 0) or 0) + int(user.get("used_bytes_down", 0) or 0)
    quota = int(user.get("quota_bytes", 0) or 0)
    expires_at = user.get("expires_at")
    on_hold = bool(user.get("on_hold", False))
    on_hold_duration_days = int(user.get("on_hold_duration_days") or 30)

    # 2. Expiration & On-Hold check
    is_expired = False
    remaining_seconds = None
    readable_remaining_time = "Illimitée"

    if on_hold:
        is_expired = False
        remaining_seconds = on_hold_duration_days * 86400
        readable_remaining_time = f"En attente 1ère connexion ({on_hold_duration_days}j)"
    elif expires_at:
        try:
            exp_date = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
            if exp_date.tzinfo is None:
                exp_date = exp_date.replace(tzinfo=timezone.utc)
            diff = (exp_date - now_utc).total_seconds()
            if diff <= 0:
                is_expired = True
                remaining_seconds = 0
                readable_remaining_time = "Expiré"
            else:
                remaining_seconds = int(diff)
                days = remaining_seconds // 86400
                hours = (remaining_seconds % 86400) // 3600
                mins = (remaining_seconds % 3600) // 60
                if days > 0:
                    readable_remaining_time = f"{days}j {hours}h"
                else:
                    readable_remaining_time = f"{hours}h {mins}m"
        except Exception:
            pass

    # 3. Quota check
    is_quota_exceeded = False
    remaining_bytes = None
    if quota > 0:
        if total_used >= quota:
            is_quota_exceeded = True
            remaining_bytes = 0
        else:
            remaining_bytes = quota - total_used

    if quota > 0:
        pct = min(round((total_used / quota) * 100, 1), 100.0)
    else:
        pct = 0.0

    if quota <= 0:
        readable_quota = "Illimité"
    elif quota >= 1024 * 1024 * 1024:
        readable_quota = f"{quota / (1024 * 1024 * 1024):.1f} Go"
    else:
        readable_quota = f"{quota / (1024 * 1024):.0f} Mo"

    # 4. Strict Online check (< 120s AND active_ips > 0)
    is_recently_seen = False
    last_seen_str = user.get("last_seen_at")
    if last_seen_str:
        try:
            ls_dt = datetime.fromisoformat(str(last_seen_str).replace("Z", "+00:00"))
            if ls_dt.tzinfo is None:
                ls_dt = ls_dt.replace(tzinfo=timezone.utc)
            if 0 <= (now_utc - ls_dt).total_seconds() <= 120:
                is_recently_seen = True
        except Exception:
            pass

    is_enabled = bool(user.get("is_enabled", True))
    active_ips = user.get("active_ips") or []
    is_online = (
        is_enabled
        and not is_expired
        and not is_quota_exceeded
        and not on_hold
        and len(active_ips) > 0
        and is_recently_seen
    )

    # 5. Status Code
    if not is_enabled:
        status_code = "disabled"
    elif is_expired:
        status_code = "expired"
    elif is_quota_exceeded:
        status_code = "limited"
    elif on_hold:
        status_code = "on_hold"
    elif is_online:
        status_code = "online"
    else:
        status_code = "active"

    # 6. Reseller Name Lookup
    reseller_name = user.get("reseller_name")
    r_id = user.get("reseller_id")
    lookup_db = db if db is not None else _LAST_GOOD_DB
    if r_id and lookup_db:
        res_obj = next((r for r in lookup_db.get("resellers", []) if r.get("id") == r_id), None)
        if res_obj:
            reseller_name = res_obj.get("display_name") or res_obj.get("username")

    return {
        **user,
        "channel": normalize_channel(user.get("channel")),
        "used_bytes": total_used,
        "total_used_bytes": total_used,
        "remaining_bytes": remaining_bytes,
        "readable_remaining_bytes": format_bytes(remaining_bytes) if remaining_bytes is not None else "Illimité",
        "readable_used": format_bytes(total_used),
        "readable_up": format_bytes(user.get("used_bytes_up", 0)),
        "readable_down": format_bytes(user.get("used_bytes_down", 0)),
        "readable_quota": readable_quota,
        "percent_quota_used": pct,
        "remaining_seconds": remaining_seconds,
        "readable_remaining_time": readable_remaining_time,
        "is_expired": is_expired,
        "is_quota_exceeded": is_quota_exceeded,
        "is_online": is_online,
        "is_valid": is_enabled and not is_expired and not is_quota_exceeded,
        "status_code": status_code,
        "on_hold": on_hold,
        "on_hold_duration_days": on_hold_duration_days,
        "data_reset_strategy": strategy,
        "reseller_name": reseller_name
    }


def enrich_voucher(v: dict) -> dict:
    q_bytes = int(v.get("quota_bytes", 0) or 0)
    q_gb = v.get("quota_gb")
    if q_gb is None:
        q_gb = round(q_bytes / (1024**3), 2) if q_bytes > 0 else 0.0
    is_red = bool(v.get("is_redeemed", False))
    return {
        **v,
        "quota_bytes": q_bytes,
        "quota_gb": round(float(q_gb), 2),
        "readable_quota": format_bytes(q_bytes) if q_bytes > 0 else "Illimité",
        "is_redeemed": is_red,
        "is_used": is_red
    }


def sync_devices_registry(db: dict) -> List[dict]:
    """Maintient db['devices'] synchronisé avec les appareils des users et requests."""
    now_iso = datetime.now(timezone.utc).isoformat()
    existing_devices = db.get("devices", [])
    by_hwid: Dict[str, dict] = {}
    for d in existing_devices:
        hwid = (d.get("device_id") or "").strip()
        if hwid:
            by_hwid[hwid] = d

    deleted_hwids = set(db.get("deleted_devices", []))
    seen_hwids = set()
    updated_list: List[dict] = []

    # 1. Devices attached to Users
    for u in db.get("users", []):
        hwid = (u.get("device_id") or "").strip()
        if not hwid:
            continue
        # Fix historical collision in memory if any
        if hwid == "891f16209bd1152f" and u.get("id") in ("usr_default_root", "usr_eada8417"):
            u["device_id"] = None
            continue
        seen_hwids.add(hwid)
        deleted_hwids.discard(hwid)
        prev = by_hwid.get(hwid, {})
        u_st = compute_user_status(u, db)
        dev_status = prev.get("status") or "AUTHORIZED"
        if dev_status not in ("AUTHORIZED", "REVOKED", "BANNED"):
            dev_status = "AUTHORIZED"

        model_str = u.get("device_model") or prev.get("device_model") or "Android Device"
        owner_str = u.get("name") or prev.get("owner_name") or "Client Nexus"
        default_name = f"{model_str} de {owner_str}"

        dev_entry = {
            "id": prev.get("id") or f"dev_{hashlib.md5(hwid.encode('utf-8')).hexdigest()[:8]}",
            "device_id": hwid,
            "name": prev.get("name") or default_name,
            "device_model": model_str,
            "device_os": u.get("device_os") or prev.get("device_os") or "Android",
            "user_id": u.get("id"),
            "owner_name": owner_str,
            "reseller_id": u.get("reseller_id") if u.get("reseller_id") is not None else prev.get("reseller_id"),
            "country": u.get("country") or prev.get("country") or "Cameroun",
            "channel": normalize_channel(u.get("channel") or prev.get("channel")),
            "contact": u.get("contact_detail") or prev.get("contact") or "",
            "ips": u.get("active_ips", []) if dev_status == "AUTHORIZED" else [],
            "is_online": bool(u_st["is_online"] and dev_status == "AUTHORIZED"),
            "status": dev_status,
            "first_seen_at": prev.get("first_seen_at") or u.get("created_at") or now_iso,
            "last_seen_at": u.get("last_seen_at") or prev.get("last_seen_at") or u.get("created_at") or now_iso,
            "notes": prev.get("notes") or ""
        }
        updated_list.append(dev_entry)
        by_hwid[hwid] = dev_entry

    # 2. Devices from Requests not yet in updated_list
    for r in db.get("requests", []):
        hwid = (r.get("device_id") or "").strip()
        if not hwid or hwid in seen_hwids or hwid in deleted_hwids:
            continue
        seen_hwids.add(hwid)
        prev = by_hwid.get(hwid, {})
        req_status = (r.get("status") or "PENDING").upper()
        default_dev_status = "REVOKED" if req_status == "REJECTED" else "AUTHORIZED"
        dev_status = prev.get("status") or default_dev_status
        if dev_status not in ("AUTHORIZED", "REVOKED", "BANNED"):
            dev_status = "AUTHORIZED"

        model_str = r.get("device_model") or prev.get("device_model") or "Android Device"
        owner_str = r.get("full_name") or prev.get("owner_name") or "Demandeur"
        default_name = f"{model_str} de {owner_str}"
        ip_addr = r.get("ip_address")

        dev_entry = {
            "id": prev.get("id") or f"dev_{hashlib.md5(hwid.encode('utf-8')).hexdigest()[:8]}",
            "device_id": hwid,
            "name": prev.get("name") or default_name,
            "device_model": model_str,
            "device_os": r.get("device_os") or prev.get("device_os") or "Android",
            "user_id": prev.get("user_id") or r.get("assigned_user_id"),
            "owner_name": owner_str,
            "reseller_id": r.get("reseller_id") if r.get("reseller_id") is not None else prev.get("reseller_id"),
            "country": r.get("country_name") or prev.get("country") or "Cameroun",
            "channel": normalize_channel(r.get("channel") or prev.get("channel")),
            "contact": r.get("contact_detail") or prev.get("contact") or "",
            "ips": [ip_addr] if (ip_addr and dev_status == "AUTHORIZED") else prev.get("ips", []),
            "is_online": False,
            "status": dev_status,
            "first_seen_at": prev.get("first_seen_at") or r.get("submitted_at") or now_iso,
            "last_seen_at": prev.get("last_seen_at") or r.get("submitted_at") or now_iso,
            "notes": prev.get("notes") or ""
        }
        updated_list.append(dev_entry)
        by_hwid[hwid] = dev_entry

    # 3. Keep any standalone device records in db['devices'] (e.g. REVOKED/BANNED detached from user)
    for hwid, prev in by_hwid.items():
        if hwid not in seen_hwids and hwid not in deleted_hwids:
            prev["is_online"] = False
            prev["channel"] = normalize_channel(prev.get("channel"))
            updated_list.append(prev)

    db["devices"] = updated_list
    db["deleted_devices"] = list(deleted_hwids)
    return updated_list


def find_device_entry(db: dict, identifier: str) -> Optional[dict]:
    if not identifier:
        return None
    sync_devices_registry(db)
    for d in db.get("devices", []):
        if d.get("device_id") == identifier or d.get("id") == identifier:
            return d
    return None


def check_device_access(db: dict, hwid: Optional[str], is_heartbeat: bool = False) -> Optional[str]:
    """Vérifie si le device_id est BANNED ou REVOKED.
    Lève HTTPException(403) si BANNED (ou REVOKED hors heartbeat).
    Retourne 'revoked' si REVOKED pendant un heartbeat.
    """
    if not hwid:
        return None
    dev = find_device_entry(db, hwid)
    if not dev:
        return None
    st = (dev.get("status") or "AUTHORIZED").upper()
    if st == "BANNED":
        raise HTTPException(status_code=403, detail="Cet appareil a été banni par l'administrateur.")
    if st == "REVOKED":
        if is_heartbeat:
            return "revoked"
        raise HTTPException(status_code=403, detail="Cet appareil a été révoqué par l'administrateur.")
    return None


def migrate_and_normalize_db(data: Dict[str, Any]) -> Dict[str, Any]:
    data.setdefault("requests", [])
    data.setdefault("vouchers", [])
    data.setdefault("users", [])
    data.setdefault("admins", [])
    data.setdefault("resellers", [])
    data.setdefault("audit_logs", [])
    data.setdefault("pricing_plans", copy.deepcopy(DEFAULT_PLANS))
    data.setdefault("reseller_transactions", [])
    data.setdefault("devices", [])
    data.setdefault("stats", {"created_at": "2026-10-22T00:00:00Z", "total_historical_connections": 142})

    # Settings enrichment
    st = data.setdefault("settings", {})
    for k, v in DEFAULT_SETTINGS.items():
        if k not in st or st[k] is None or (isinstance(v, list) and not st.get(k)):
            st[k] = copy.deepcopy(v)
    if isinstance(st.get("target_ips"), list):
        for ip in DEFAULT_SETTINGS["target_ips"]:
            if ip not in st["target_ips"]:
                st["target_ips"].append(ip)

    # Users cleanup & normalization
    for u in data.get("users", []):
        if u.get("id") in ("usr_default_root", "usr_eada8417") and u.get("device_id") == "891f16209bd1152f":
            u["device_id"] = None
        u["channel"] = normalize_channel(u.get("channel"))
        u.setdefault("on_hold", False)
        u.setdefault("on_hold_duration_days", 30)
        u.setdefault("data_reset_strategy", "no_reset")

    # Requests normalization
    for r in data.get("requests", []):
        r["channel"] = normalize_channel(r.get("channel"))

    # Vouchers enrichment
    for v in data.get("vouchers", []):
        q_b = int(v.get("quota_bytes", 0) or 0)
        if "quota_gb" not in v or v["quota_gb"] is None:
            v["quota_gb"] = round(q_b / (1024**3), 2) if q_b > 0 else 0.0
        v["readable_quota"] = format_bytes(q_b) if q_b > 0 else "Illimité"
        v["is_used"] = bool(v.get("is_redeemed", False))

    # Default Super Admin
    if not data.get("admins"):
        data["admins"].append({
            "id": "adm_super_01",
            "username": "superadmin",
            "password_hash": hash_password("nexus2026!"),
            "display_name": "Admin Suprême (Maître)",
            "role": "SUPER_ADMIN",
            "email": "superadmin@nexustunnel.com",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_login_at": None,
            "is_active": True
        })

    # Default Reseller
    if not data.get("resellers"):
        data["resellers"].append({
            "id": "res_douala_01",
            "username": "revendeur_douala",
            "password_hash": hash_password("reseller123"),
            "display_name": "Azice Telecom Douala",
            "role": "RESELLER",
            "contact_phone": "+237 690123456",
            "contact_channel": "WHATSAPP",
            "telegram_username": "@azice_vpn",
            "credit_gb": 500.0,
            "total_credit_gb": 500.0,
            "max_accounts": 100,
            "commission_rate": "15%",
            "referral_code": "DOUALA",
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_login_at": None,
            "notes": "Revendeur officiel Douala - Cameroun"
        })

    sync_devices_registry(data)
    return data


def save_db(data: Dict[str, Any]):
    global _LAST_GOOD_DB
    with DB_LOCK:
        sync_devices_registry(data)
        tmp_path = f"{DB_PATH}.{uuid.uuid4().hex}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, DB_PATH)
            _LAST_GOOD_DB = copy.deepcopy(data)
            try:
                shutil.copyfile(DB_PATH, DB_BAK_PATH)
            except Exception:
                pass
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass


def load_db() -> Dict[str, Any]:
    global _LAST_GOOD_DB
    with DB_LOCK:
        if not os.path.exists(DB_PATH) and not os.path.exists(DB_BAK_PATH):
            if _LAST_GOOD_DB is not None:
                return copy.deepcopy(_LAST_GOOD_DB)
            initial_data = migrate_and_normalize_db({
                "settings": copy.deepcopy(DEFAULT_SETTINGS),
                "users": [
                    {
                        "id": "usr_default_root",
                        "name": "Compte Principal (Root Docker)",
                        "uuid": "e3a478b2-5e1b-4cf7-8b09-1a2b3c4d5e6f",
                        "email": "nexus-root@nexustunnel",
                        "token": "NEXUS-VLESS-ROOT01",
                        "is_enabled": True,
                        "created_at": "2026-10-14T09:00:00Z",
                        "expires_at": None,
                        "quota_bytes": 0,
                        "used_bytes_up": 34225800,
                        "used_bytes_down": 67667419,
                        "max_ips": 0,
                        "notes": "Compte maître extrait directement de l'image docker.io/nextl/nexus-tunnel (Quota illimité)",
                        "last_seen_at": "2026-10-23T16:48:43.933657+00:00",
                        "active_ips": ["102.244.222.15", "41.202.219.66"],
                        "device_id": None,
                        "country": "Cameroun",
                        "channel": "WHATSAPP",
                        "contact_detail": "+237690000000"
                    }
                ],
                "requests": [],
                "vouchers": [],
                "devices": [],
                "stats": {"created_at": "2026-10-22T00:00:00Z", "total_historical_connections": 142}
            })
            save_db(initial_data)
            return initial_data

        # Try reading main DB_PATH
        try:
            with open(DB_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            data = migrate_and_normalize_db(data)
            _LAST_GOOD_DB = copy.deepcopy(data)
            return data
        except Exception as e:
            print(f"[CRITICAL] Error reading {DB_PATH}: {e}", file=sys.stderr)

        # Fallback 1: Read database.json.bak
        if os.path.exists(DB_BAK_PATH):
            try:
                with open(DB_BAK_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data = migrate_and_normalize_db(data)
                _LAST_GOOD_DB = copy.deepcopy(data)
                return data
            except Exception as bak_err:
                print(f"[CRITICAL] Error reading backup {DB_BAK_PATH}: {bak_err}", file=sys.stderr)

        # Fallback 2: In-memory _LAST_GOOD_DB (NEVER return an empty dict that overwrites data!)
        if _LAST_GOOD_DB is not None:
            return copy.deepcopy(_LAST_GOOD_DB)

        raise RuntimeError("Impossible de charger database.json ni database.json.bak")


# --- VLESS URI, Multi-Variants & Xray Client Generator ---

def generate_vless_uri(
    user_uuid: str,
    user_name: str,
    settings: dict,
    variant: str = "fast",
    custom_sni: Optional[str] = None,
    custom_target: Optional[str] = None
) -> str:
    target_server = (custom_target or settings.get("target_server", "192.179.18.100:443")).strip()
    host = settings.get("host", "nexus-tunnel-753027553589.us-east1.run.app").strip()
    sni = (custom_sni or settings.get("sni", "crashlyticsreports-pa.googleapis.com")).strip()
    raw_path = settings.get("path", "/nexustunnel").strip()
    clean_path = raw_path.split("?")[0] if "?" in raw_path else raw_path
    if not clean_path.startswith("/"):
        clean_path = "/" + clean_path

    if ":" in target_server:
        server_ip, server_port = target_server.split(":", 1)
    else:
        server_ip, server_port = target_server, "443"

    # Authentification VLESS au niveau de l'image Docker Cloud Run docker.io/nextl/nexus-tunnel
    # Le conteneur requiert root_uuid pour router le trafic réseau.
    transport_uuid = settings.get("root_uuid", DEFAULT_SETTINGS.get("root_uuid", "e3a478b2-5e1b-4cf7-8b09-1a2b3c4d5e6f"))

    base_name = (user_name or "NexusTunnel").strip()
    if variant == "stable":
        final_path = clean_path
        tag_name = base_name if "🛡️" in base_name else f"{base_name} 🛡️ Stable"
    else:
        final_path = f"{clean_path}?ed=2048"
        tag_name = base_name if ("⚡" in base_name or "🛡️" in base_name) else f"{base_name} ⚡ Fast"

    encoded_path = urllib.parse.quote(final_path, safe="")
    encoded_name = urllib.parse.quote(tag_name)

    uri = (
        f"vless://{transport_uuid}@{server_ip}:{server_port}"
        f"?encryption=none"
        f"&security=tls"
        f"&sni={sni}"
        f"&fp=chrome"
        f"&alpn=http%2F1.1"
        f"&type=ws"
        f"&host={host}"
        f"&path={encoded_path}"
        f"#{encoded_name}"
    )
    return uri


def generate_user_vless_variants(user_uuid: str, user_name: str, settings: dict) -> List[Dict[str, Any]]:
    primary_sni = settings.get("sni", "crashlyticsreports-pa.googleapis.com").strip()
    primary_target = settings.get("target_server", "192.179.18.100:443").strip()
    sni_list = settings.get("sni_list") or DEFAULT_SETTINGS["sni_list"]
    target_ips = settings.get("target_ips") or DEFAULT_SETTINGS["target_ips"]

    variants: List[Dict[str, Any]] = []

    # 1. Fast 0-RTT Early Data
    fast_uri = generate_vless_uri(user_uuid, user_name, settings, variant="fast")
    variants.append({
        "id": "fast",
        "label": "⚡ Nexus Fast (0-RTT Early Data)",
        "badge": "0-RTT • RECOMMANDÉ",
        "uri": fast_uri,
        "sni": primary_sni,
        "target": primary_target
    })

    # 2. Stable Standard Compatible
    stable_uri = generate_vless_uri(user_uuid, user_name, settings, variant="stable")
    variants.append({
        "id": "stable",
        "label": "🛡️ Nexus Stable (Standard Compatible)",
        "badge": "COMPATIBILITÉ MAX",
        "uri": stable_uri,
        "sni": primary_sni,
        "target": primary_target
    })

    # 3. Multi-SNI / Bug Hosts (up to 4)
    added_sni = 0
    for idx, alt_sni in enumerate(sni_list[:4]):
        alt_sni_clean = str(alt_sni).strip()
        if not alt_sni_clean or alt_sni_clean == primary_sni:
            continue
        added_sni += 1
        short_sni = alt_sni_clean.split(".")[0]
        v_uri = generate_vless_uri(
            user_uuid,
            f"{user_name} ({short_sni})",
            settings,
            variant="fast",
            custom_sni=alt_sni_clean
        )
        variants.append({
            "id": f"sni_{added_sni}",
            "label": f"🌐 Bug Host SNI • {alt_sni_clean}",
            "badge": "MULTI-SNI",
            "uri": v_uri,
            "sni": alt_sni_clean,
            "target": primary_target
        })

    # 4. Anycast Edge Target IPs
    for idx, alt_target in enumerate(target_ips[:4]):
        alt_target_clean = str(alt_target).strip()
        if not alt_target_clean or alt_target_clean == primary_target:
            continue
        ip_only = alt_target_clean.split(":")[0]
        v_uri = generate_vless_uri(
            user_uuid,
            f"{user_name} [Edge {ip_only}]",
            settings,
            variant="fast",
            custom_target=alt_target_clean
        )
        variants.append({
            "id": f"edge_{idx + 1}",
            "label": f"🚀 Google Edge Anycast • {alt_target_clean}",
            "badge": "ANYCAST EDGE",
            "uri": v_uri,
            "sni": primary_sni,
            "target": alt_target_clean
        })

    return variants


def generate_xray_client_json(user_uuid: str, user_name: str, settings: dict) -> Dict[str, Any]:
    target_server = settings.get("target_server", "192.179.18.100:443").strip()
    host = settings.get("host", "nexus-tunnel-753027553589.us-east1.run.app").strip()
    sni = settings.get("sni", "crashlyticsreports-pa.googleapis.com").strip()
    raw_path = settings.get("path", "/nexustunnel").strip()
    clean_path = raw_path.split("?")[0] if "?" in raw_path else raw_path
    server_ip, server_port = target_server.split(":", 1) if ":" in target_server else (target_server, "443")

    return {
        "remarks": f"{user_name} ⚡ Nexus Pro",
        "log": {"loglevel": "warning"},
        "policy": {
            "levels": {
                "0": {
                    "handshake": 6,
                    "connIdle": 600,
                    "uplinkOnly": 2,
                    "downlinkOnly": 5,
                    "bufferSize": 2048
                }
            },
            "system": {
                "statsInboundUplink": True,
                "statsInboundDownlink": True,
                "statsOutboundUplink": True,
                "statsOutboundDownlink": True
            }
        },
        "dns": {
            "servers": [
                "https+local://1.1.1.1/dns-query",
                "https+local://8.8.8.8/dns-query",
                "1.1.1.1",
                "8.8.8.8"
            ],
            "queryStrategy": "UseIPv4",
            "disableCache": False,
            "disableFallback": False
        },
        "inbounds": [
            {
                "tag": "socks-in",
                "port": 10808,
                "listen": "127.0.0.1",
                "protocol": "socks",
                "settings": {"auth": "noauth", "udp": True},
                "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"], "routeOnly": True}
            },
            {
                "tag": "http-in",
                "port": 10809,
                "listen": "127.0.0.1",
                "protocol": "http",
                "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"], "routeOnly": True}
            }
        ],
        "outbounds": [
            {
                "tag": "proxy",
                "protocol": "vless",
                "settings": {
                    "vnext": [
                        {
                            "address": server_ip,
                            "port": int(server_port),
                            "users": [
                                {
                                    "id": settings.get("root_uuid", DEFAULT_SETTINGS.get("root_uuid", "e3a478b2-5e1b-4cf7-8b09-1a2b3c4d5e6f")),
                                    "encryption": "none",
                                    "level": 0
                                }
                            ]
                        }
                    ]
                },
                "streamSettings": {
                    "network": "ws",
                    "security": "tls",
                    "tlsSettings": {
                        "serverName": sni,
                        "allowInsecure": False,
                        "fingerprint": "chrome",
                        "alpn": ["http/1.1"]
                    },
                    "wsSettings": {
                        "path": clean_path,
                        "headers": {"Host": host}
                    },
                    "sockopt": {
                        "tcpFastOpen": True,
                        "tcpNoDelay": True,
                        "tcpKeepAliveIdle": 30,
                        "tcpKeepAliveInterval": 15
                    }
                },
                "mux": {
                    "enabled": False
                }
            },
            {"tag": "dns-out", "protocol": "dns", "settings": {"network": "tcp", "nonIPQuery": "skip"}},
            {"tag": "direct", "protocol": "freedom", "settings": {"domainStrategy": "UseIPv4"}},
            {"tag": "block", "protocol": "blackhole", "settings": {"response": {"type": "none"}}}
        ],
        "routing": {
            "domainStrategy": "AsIs",
            "rules": [
                {"type": "field", "inboundTag": ["socks-in"], "outboundTag": "proxy"}
            ]
        }
    }


def generate_qr_base64(data: str) -> str:
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{b64}"
    except Exception as e:
        print(f"QR Gen Error: {e}", file=sys.stderr)
        return ""


# --- Pydantic Models ---
class MembershipRequestCreate(BaseModel):
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    country_code: Optional[str] = None
    country: Optional[str] = None
    channel: Optional[str] = None
    contact_type: Optional[str] = None
    contact_detail: Optional[str] = None
    contact_value: Optional[str] = None
    device_id: str = Field(..., min_length=3)
    device_model: Optional[str] = "Android Device"
    device_manufacturer: Optional[str] = "Android"
    device_os: Optional[str] = "Android"
    reseller_id: Optional[str] = None
    referral_code: Optional[str] = None


class RequestApproval(BaseModel):
    quota_bytes: Optional[int] = None
    quota_gb: Optional[float] = None
    validity_days: int = 30
    max_ips: int = 2
    on_hold: bool = False
    on_hold_duration_days: int = 30
    data_reset_strategy: str = "no_reset"
    notes: Optional[str] = "Compte approuvé via le panel Nexus Tunnel"
    reseller_id: Optional[str] = None


class RequestRejection(BaseModel):
    reason: str = Field(..., min_length=1)


class TokenRedeem(BaseModel):
    token: str = Field(..., min_length=3)
    device_id: Optional[str] = None
    user_id: Optional[str] = None
    uuid: Optional[str] = None


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    uuid_str: Optional[str] = None
    uuid: Optional[str] = None
    token: Optional[str] = None
    quota_bytes: Optional[int] = None
    quota_gb: Optional[float] = None
    expires_at: Optional[str] = None
    validity_days: Optional[int] = None
    on_hold: bool = False
    on_hold_duration_days: int = 30
    data_reset_strategy: str = "no_reset"
    max_ips: int = 2
    notes: Optional[str] = ""
    is_enabled: bool = True
    reseller_id: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_detail: Optional[str] = None
    channel: Optional[str] = "WHATSAPP"
    country: Optional[str] = None
    device_id: Optional[str] = None
    device_model: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    uuid_str: Optional[str] = None
    uuid: Optional[str] = None
    token: Optional[str] = None
    quota_bytes: Optional[int] = None
    quota_gb: Optional[float] = None
    expires_at: Optional[str] = None
    on_hold: Optional[bool] = None
    on_hold_duration_days: Optional[int] = None
    data_reset_strategy: Optional[str] = None
    max_ips: Optional[int] = None
    notes: Optional[str] = None
    is_enabled: Optional[bool] = None
    country: Optional[str] = None
    channel: Optional[str] = None
    contact_detail: Optional[str] = None
    contact_phone: Optional[str] = None
    device_id: Optional[str] = None
    device_model: Optional[str] = None
    reseller_id: Optional[str] = None


class RevokeCredentialsPayload(BaseModel):
    regen_uuid: bool = True
    regen_token: bool = True
    detach_device: bool = False


class BulkUsersPayload(BaseModel):
    user_ids: List[str]
    action: str
    value: Optional[float] = None


class DeviceUpdatePayload(BaseModel):
    name: Optional[str] = None
    device_model: Optional[str] = None
    device_os: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    user_id: Optional[str] = None


class PlanCreatePayload(BaseModel):
    id: Optional[str] = None
    name: str
    quota_gb: float = 10.0
    duration_days: int = 30
    price_cfa: int = 2000
    badge: Optional[str] = "STANDARD"
    description: Optional[str] = ""


class PlanUpdatePayload(BaseModel):
    name: Optional[str] = None
    quota_gb: Optional[float] = None
    duration_days: Optional[int] = None
    price_cfa: Optional[int] = None
    badge: Optional[str] = None
    description: Optional[str] = None


class TrafficHeartbeat(BaseModel):
    token: Optional[str] = None
    uuid: Optional[str] = None
    device_id: Optional[str] = None
    bytes_up: int = 0
    bytes_down: int = 0
    bytes_delta: Optional[int] = 0
    client_ip: Optional[str] = None
    device_model: Optional[str] = None
    os_version: Optional[str] = None
    app_version: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class ResellerCreate(BaseModel):
    username: str
    password: str
    display_name: str
    credit_gb: float = 100.0
    max_accounts: int = 100
    contact_phone: Optional[str] = None
    contact_channel: Optional[str] = "WHATSAPP"
    telegram_username: Optional[str] = None
    commission_rate: Optional[str] = "15%"
    referral_code: Optional[str] = None
    notes: Optional[str] = None


class ResellerUpdate(BaseModel):
    display_name: Optional[str] = None
    password: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_channel: Optional[str] = None
    telegram_username: Optional[str] = None
    commission_rate: Optional[str] = None
    max_accounts: Optional[int] = None
    credit_gb: Optional[float] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class ResellerRecharge(BaseModel):
    add_credit_gb: float
    notes: Optional[str] = "Recharge solde data"


class AdminCreate(BaseModel):
    username: str
    password: str
    display_name: str
    email: Optional[str] = None
    role: str = "ADMIN"


class VoucherBatchCreate(BaseModel):
    count: int = 5
    plan_name: str = "Forfait Nexus 25 Go"
    quota_gb: float = 25.0
    validity_days: int = 30
    max_ips: int = 2
    reseller_id: Optional[str] = None


class QuickTrialCreate(BaseModel):
    client_name: Optional[str] = "Client Essai"
    contact_phone: Optional[str] = None
    channel: Optional[str] = "WHATSAPP"
    reseller_id: Optional[str] = None


class UserExtendPlan(BaseModel):
    add_gb: float = 0.0
    add_days: int = 0
    reset_traffic: bool = False
    notes: Optional[str] = None


class VoucherCreate(BaseModel):
    code: Optional[str] = None
    plan_name: Optional[str] = "Forfait Recharge Nexus"
    quota_bytes: Optional[int] = None
    quota_gb: Optional[float] = None
    validity_days: int = 30
    max_ips: int = 2
    reseller_id: Optional[str] = None
    notes: Optional[str] = None


class SettingsUpdate(BaseModel):
    host: Optional[str] = None
    target_server: Optional[str] = None
    sni: Optional[str] = None
    path: Optional[str] = None
    docker_image: Optional[str] = None
    panel_title: Optional[str] = None
    root_uuid: Optional[str] = None
    sni_list: Optional[List[str]] = None
    target_ips: Optional[List[str]] = None


# --- FastAPI App Setup ---
app = FastAPI(
    title="Nexus Tunnel Control Panel",
    description="Panel complet V2Ray / VLESS Multi-Tenant avec sécurité HMAC, gestion d'appareils et portail d'abonnement",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter()


def get_current_actor(request: Request, strict: bool = True) -> Dict[str, Any]:
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    if not token:
        token = request.cookies.get("nexus_token") or request.query_params.get("token")

    if not token:
        if strict:
            raise HTTPException(
                status_code=401,
                detail="Session expirée ou non authentifiée. Veuillez vous connecter."
            )
        return {}

    sess = decode_session_token(token)
    if not sess:
        if strict:
            raise HTTPException(
                status_code=401,
                detail="Session expirée ou non authentifiée. Veuillez vous connecter."
            )
        return {}

    db = load_db()
    user_id = sess.get("sub") or sess.get("user_id")
    imp_by = sess.get("imp")

    # 1. Check in admins
    adm = next((a for a in db.get("admins", []) if a.get("id") == user_id), None)
    if adm:
        if not adm.get("is_active", True):
            raise HTTPException(status_code=403, detail="Ce compte a été suspendu.")
        return {**adm, "role": adm.get("role", "ADMIN"), "impersonated_by": imp_by}

    # 2. Check in resellers
    res = next((r for r in db.get("resellers", []) if r.get("id") == user_id), None)
    if res:
        if not res.get("is_active", True):
            raise HTTPException(status_code=403, detail="Ce compte a été suspendu.")
        return {**res, "role": "RESELLER", "impersonated_by": imp_by}

    if strict:
        raise HTTPException(
            status_code=401,
            detail="Session expirée ou non authentifiée. Veuillez vous connecter."
        )
    return {}


# --- HTML Page Routes ---
@app.get("/", response_class=HTMLResponse)
@app.get("/admin", response_class=HTMLResponse)
@app.get("/nexus", response_class=HTMLResponse)
@app.get("/nexus/", response_class=HTMLResponse)
@app.get("/nexus/admin", response_class=HTMLResponse)
async def serve_control_panel():
    index_file = os.path.join(TEMPLATES_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Nexus Tunnel Control Panel en cours de chargement...</h1>")


@app.get("/app", response_class=HTMLResponse)
@app.get("/nexus/app", response_class=HTMLResponse)
@app.get("/nexus/app/", response_class=HTMLResponse)
async def serve_vpn_mobile_app():
    app_file = os.path.join(TEMPLATES_DIR, "app.html")
    if os.path.exists(app_file):
        with open(app_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Nexus Tunnel Mobile App en cours de chargement...</h1>")


# --- Static and Native App Download Endpoints ---
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/nexus/static", StaticFiles(directory=STATIC_DIR), name="nexus_static")


@app.api_route("/download/NexusTunnel.apk", methods=["GET", "HEAD"])
@app.api_route("/nexus/download/NexusTunnel.apk", methods=["GET", "HEAD"])
async def download_apk():
    apk_path = os.path.join(STATIC_DIR, "NexusTunnel.apk")
    if os.path.exists(apk_path):
        return FileResponse(
            apk_path,
            media_type="application/vnd.android.package-archive",
            filename="NexusTunnel.apk"
        )
    raise HTTPException(status_code=404, detail="Fichier APK non trouvé")


@app.api_route("/download/NexusTunnel.app", methods=["GET", "HEAD"])
@app.api_route("/nexus/download/NexusTunnel.app", methods=["GET", "HEAD"])
async def download_app_file():
    app_path = os.path.join(STATIC_DIR, "NexusTunnel.app")
    if os.path.exists(app_path):
        return FileResponse(
            app_path,
            media_type="application/octet-stream",
            filename="NexusTunnel.app"
        )
    raise HTTPException(status_code=404, detail="Fichier .app non trouvé")


@router.get("/api/download/info")
async def get_download_info():
    apk_path = os.path.join(STATIC_DIR, "NexusTunnel.apk")
    size_bytes = os.path.getsize(apk_path) if os.path.exists(apk_path) else 0
    return {
        "app_name": "Nexus Tunnel",
        "version": "1.0.0",
        "package": "com.nexustunnel.vpn",
        "apk_url": "/nexus/download/NexusTunnel.apk",
        "app_url": "/nexus/download/NexusTunnel.app",
        "size_bytes": size_bytes,
        "size_formatted": f"{size_bytes / (1024 * 1024):.1f} MB"
    }


@router.get("/api/time")
async def get_server_time():
    now = datetime.now(timezone.utc)
    return {
        "timestamp_ms": int(now.timestamp() * 1000),
        "epoch": int(now.timestamp()),
        "iso": now.isoformat(),
        "timezone": "UTC"
    }


@router.get("/api/countries")
async def get_african_countries():
    return AFRICAN_COUNTRIES


def get_system_telemetry():
    try:
        with open("/proc/meminfo") as f:
            lines = f.readlines()
        mem = {}
        for line in lines:
            parts = line.split(":")
            if len(parts) == 2:
                mem[parts[0].strip()] = int(parts[1].strip().split()[0])
        total_mb = mem.get("MemTotal", 0) // 1024
        avail_mb = mem.get("MemAvailable", 0) // 1024
        used_mb = total_mb - avail_mb
        mem_pct = round((used_mb / total_mb) * 100, 1) if total_mb else 0
    except Exception:
        total_mb, used_mb, mem_pct = 1024, 512, 50.0

    try:
        with open("/proc/uptime") as f:
            up_sec = float(f.readline().split()[0])
        days = int(up_sec // 86400)
        hours = int((up_sec % 86400) // 3600)
        mins = int((up_sec % 3600) // 60)
        uptime_str = f"{days}j {hours}h {mins}m"
    except Exception:
        uptime_str = "En ligne"

    try:
        st = os.statvfs("/")
        total_gb = round((st.f_blocks * st.f_frsize) / (1024**3), 1)
        free_gb = round((st.f_bavail * st.f_frsize) / (1024**3), 1)
        used_gb = round(total_gb - free_gb, 1)
        disk_pct = round((used_gb / total_gb) * 100, 1) if total_gb else 0
    except Exception:
        total_gb, used_gb, disk_pct = 40.0, 10.0, 25.0

    try:
        load1, load5, load15 = os.getloadavg()
    except Exception:
        load1, load5, load15 = 0.5, 0.5, 0.5

    return {
        "memory": {"used_mb": used_mb, "total_mb": total_mb, "percent": mem_pct},
        "disk": {"used_gb": used_gb, "total_gb": total_gb, "percent": disk_pct},
        "uptime": uptime_str,
        "load": {"load1": round(load1, 2), "load5": round(load5, 2), "load15": round(load15, 2)}
    }


@router.get("/api/health")
@router.head("/api/health")
async def api_health():
    return {"status": "ok", "service": "Nexus Tunnel Panel", "version": "3.0.0", "time": int(time.time())}


@router.get("/api/status")
async def get_system_status(request: Request):
    actor = get_current_actor(request)
    db = load_db()
    settings = db.get("settings", DEFAULT_SETTINGS)

    raw_users = db.get("users", [])
    raw_requests = db.get("requests", [])
    raw_vouchers = db.get("vouchers", [])

    if actor.get("role") == "RESELLER":
        r_id = actor.get("id")
        raw_users = [u for u in raw_users if u.get("reseller_id") == r_id]
        raw_requests = [r for r in raw_requests if r.get("reseller_id") == r_id]
        raw_vouchers = [v for v in raw_vouchers if v.get("reseller_id") == r_id]

    users = [compute_user_status(u, db) for u in raw_users]

    total_accounts = len(users)
    online_accounts = sum(1 for u in users if u["is_online"])
    active_accounts = sum(1 for u in users if u["is_valid"])
    expired_accounts = sum(1 for u in users if u["is_expired"])
    quota_exceeded_accounts = sum(1 for u in users if u["is_quota_exceeded"])
    on_hold_accounts = sum(1 for u in users if u.get("on_hold"))
    pending_requests = sum(1 for r in raw_requests if r.get("status") == "PENDING")

    total_bytes_up = sum(u.get("used_bytes_up", 0) for u in users)
    total_bytes_down = sum(u.get("used_bytes_down", 0) for u in users)
    total_bytes = total_bytes_up + total_bytes_down

    resp: Dict[str, Any] = {
        "status": "healthy",
        "service": "Nexus Tunnel Control Panel",
        "docker_image": settings.get("docker_image", DEFAULT_SETTINGS["docker_image"]),
        "host": settings.get("host", DEFAULT_SETTINGS["host"]),
        "target_server": settings.get("target_server", DEFAULT_SETTINGS["target_server"]),
        "sni": settings.get("sni", DEFAULT_SETTINGS["sni"]),
        "path": settings.get("path", DEFAULT_SETTINGS["path"]),
        "telemetry": get_system_telemetry(),
        "actor": sanitize_account(actor),
        "stats": {
            "total_accounts": total_accounts,
            "online_accounts": online_accounts,
            "active_accounts": active_accounts,
            "expired_accounts": expired_accounts,
            "quota_exceeded_accounts": quota_exceeded_accounts,
            "on_hold_accounts": on_hold_accounts,
            "pending_requests": pending_requests,
            "total_vouchers": len(raw_vouchers),
            "available_vouchers": sum(1 for v in raw_vouchers if not v.get("is_redeemed", False)),
            "total_bytes_up": total_bytes_up,
            "total_bytes_down": total_bytes_down,
            "total_bandwidth_used": format_bytes(total_bytes),
            "readable_up": format_bytes(total_bytes_up),
            "readable_down": format_bytes(total_bytes_down),
            "total_historical_connections": db.get("stats", {}).get("total_historical_connections", 100) + online_accounts
        }
    }
    if actor.get("role") == "RESELLER":
        resp["reseller"] = sanitize_account(actor)
    return resp


# --- Onboarding / Inscription Flow ---

@router.post("/api/membership/request")
async def create_membership_request(payload: MembershipRequestCreate, request: Request):
    db = load_db()

    if payload.device_id in db.get("deleted_devices", []):
        try:
            db["deleted_devices"].remove(payload.device_id)
        except Exception:
            pass

    # Check if device is banned or revoked
    check_device_access(db, payload.device_id, is_heartbeat=False)

    # Normalize country_code
    c_code = (payload.country_code or "").upper().strip()
    if not c_code and payload.country:
        matching_c = next(
            (c for c in AFRICAN_COUNTRIES if c["name"].lower() == payload.country.lower() or c["code"].lower() == payload.country.lower()),
            None
        )
        if matching_c:
            c_code = matching_c["code"]
    if not c_code:
        c_code = "CM"

    country_info = next((c for c in AFRICAN_COUNTRIES if c["code"] == c_code), None) or AFRICAN_COUNTRIES[0]

    channel_norm = normalize_channel(payload.channel or payload.contact_type)
    contact_raw = (payload.contact_detail or payload.contact_value or "").strip()

    if channel_norm == "WHATSAPP":
        digits_only = re.sub(r"\D", "", contact_raw)
        dial_digits = re.sub(r"\D", "", country_info["dial"])
        if digits_only.startswith(dial_digits):
            digits_only = digits_only[len(dial_digits):]

        if len(digits_only) != country_info["digits"]:
            raise HTTPException(
                status_code=400,
                detail=f"Le numéro WhatsApp pour {country_info['name']} doit comporter exactement {country_info['digits']} chiffres (ex: {country_info['example']}). Vous avez entré {len(digits_only)} chiffres."
            )
        contact_formatted = f"{country_info['dial']} {digits_only}"
    else:
        if not contact_raw.startswith("@"):
            contact_raw = f"@{contact_raw}"
        if len(contact_raw) < 4 or not re.match(r"^@[a-zA-Z0-9_]{3,}$", contact_raw):
            raise HTTPException(
                status_code=400,
                detail="L'identifiant Telegram doit commencer par '@' suivi d'au moins 3 caractères alphanumériques (ex: @mon_pseudo)."
            )
        contact_formatted = contact_raw

    # Optional reseller matching via referral_code or reseller_id
    assigned_reseller_id = payload.reseller_id
    if not assigned_reseller_id and payload.referral_code:
        ref = payload.referral_code.strip().upper()
        matched_res = next((r for r in db.get("resellers", []) if (r.get("referral_code") or "").upper() == ref), None)
        if matched_res:
            assigned_reseller_id = matched_res.get("id")

    client_ip = request.client.host if request.client else "127.0.0.1"
    request_id = f"req_{uuid.uuid4().hex[:8]}"

    existing = next(
        (r for r in db.get("requests", []) if r.get("device_id") == payload.device_id and r.get("status") == "PENDING"),
        None
    )
    if existing:
        existing["first_name"] = payload.first_name.strip()
        existing["last_name"] = payload.last_name.strip()
        existing["full_name"] = f"{payload.first_name.strip()} {payload.last_name.strip()}"
        existing["country_code"] = country_info["code"]
        existing["country_name"] = country_info["name"]
        existing["flag"] = country_info["flag"]
        existing["dial_prefix"] = country_info["dial"]
        existing["channel"] = channel_norm
        existing["contact_detail"] = contact_formatted
        existing["device_model"] = payload.device_model
        existing["device_os"] = payload.device_os
        existing["ip_address"] = client_ip
        if assigned_reseller_id:
            existing["reseller_id"] = assigned_reseller_id
        existing["submitted_at"] = datetime.now(timezone.utc).isoformat()
        save_db(db)
        return {
            "status": "pending",
            "request": existing,
            "message": "Votre demande existante a été mise à jour et est en attente d'approbation."
        }

    req_obj = {
        "id": request_id,
        "first_name": payload.first_name.strip(),
        "last_name": payload.last_name.strip(),
        "full_name": f"{payload.first_name.strip()} {payload.last_name.strip()}",
        "country_code": country_info["code"],
        "country_name": country_info["name"],
        "flag": country_info["flag"],
        "dial_prefix": country_info["dial"],
        "channel": channel_norm,
        "contact_detail": contact_formatted,
        "device_id": payload.device_id,
        "device_model": payload.device_model,
        "device_os": payload.device_os,
        "ip_address": client_ip,
        "reseller_id": assigned_reseller_id,
        "status": "PENDING",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "rejection_reason": ""
    }

    db.setdefault("requests", []).append(req_obj)
    save_db(db)

    return {
        "status": "pending",
        "request": req_obj,
        "message": "Demande transmise avec succès au panel Nexus Tunnel. Veuillez patienter pendant la validation de l'administrateur."
    }


@router.get("/api/membership/status")
async def get_membership_status(
    device_id: str,
    uuid: Optional[str] = None,
    token: Optional[str] = None
):
    db = load_db()
    settings = db.get("settings", DEFAULT_SETTINGS)
    plans = db.get("pricing_plans", DEFAULT_PLANS)

    # Check if device is banned or revoked in devices registry
    dev_entry = find_device_entry(db, device_id)
    if dev_entry and dev_entry.get("status") in ("BANNED", "REVOKED"):
        st_code = dev_entry["status"].lower()
        return {
            "status": st_code,
            "should_disconnect": True,
            "reason": "Cet appareil a été révoqué ou banni par l'administrateur.",
            "message": "Accès révoqué par l'administrateur.",
            "plans": plans
        }

    if device_id in db.get("deleted_devices", []):
        return {
            "status": "deleted",
            "reset_onboarding": True,
            "should_disconnect": True,
            "reason": "Cet appareil a été détaché ou supprimé par l'administrateur.",
            "message": "Appareil supprimé par l'administrateur.",
            "plans": plans
        }

    # 1. Check user account for this device (or by token/uuid if device matches)
    matching_user = next(
        (u for u in db.get("users", []) if u.get("device_id") == device_id and u.get("id") != "usr_default_root"),
        None
    )
    if not matching_user:
        matching_user = next(
            (u for u in db.get("users", []) if u.get("device_id") == device_id),
            None
        )
    if not matching_user and token:
        tok_up = token.strip().upper()
        matching_user = next(
            (u for u in db.get("users", []) if (u.get("token") or "").upper() == tok_up and (not u.get("device_id") or u.get("device_id") == device_id)),
            None
        )
    if not matching_user and uuid:
        uuid_low = uuid.strip().lower()
        matching_user = next(
            (u for u in db.get("users", []) if (u.get("uuid") or "").lower() == uuid_low and (not u.get("device_id") or u.get("device_id") == device_id)),
            None
        )

    if matching_user:
        u_status = compute_user_status(matching_user, db)
        vless_uri = generate_vless_uri(matching_user["uuid"], matching_user.get("name", "Client Nexus"), settings)
        vless_variants = generate_user_vless_variants(matching_user["uuid"], matching_user.get("name", "Client Nexus"), settings)
        tunnel_master_uuid = settings.get("root_uuid", DEFAULT_SETTINGS.get("root_uuid", "e3a478b2-5e1b-4cf7-8b09-1a2b3c4d5e6f"))
        cfg_block = {
            "vless_uri": vless_uri,
            "vless_variants": vless_variants,
            "xray_client_json": generate_xray_client_json(matching_user["uuid"], matching_user.get("name", "Client Nexus"), settings),
            "tunnel_uuid": tunnel_master_uuid,
            "uuid": matching_user.get("uuid"),
            "token": matching_user.get("token"),
            "host": settings.get("host", DEFAULT_SETTINGS["host"]),
            "target_server": settings.get("target_server", DEFAULT_SETTINGS["target_server"]),
            "port": 443,
            "path": settings.get("path", DEFAULT_SETTINGS["path"]),
            "sni": settings.get("sni", DEFAULT_SETTINGS["sni"]),
            "sni_list": settings.get("sni_list", DEFAULT_SETTINGS["sni_list"]),
            "target_ips": settings.get("target_ips", DEFAULT_SETTINGS["target_ips"])
        }
        if not matching_user.get("is_enabled", True):
            return {
                "status": "disabled",
                "should_disconnect": True,
                "reason": "Votre compte a été temporairement suspendu par l'administrateur.",
                "account": u_status,
                "user": u_status,
                "config": cfg_block,
                "sni_list": cfg_block["sni_list"],
                "target_ips": cfg_block["target_ips"],
                "plans": plans,
                "message": "Compte suspendu par l'administrateur."
            }
        is_finished = bool(u_status.get("is_expired") or u_status.get("is_quota_exceeded"))
        return {
            "status": "approved",
            "should_disconnect": is_finished,
            "is_expired": bool(u_status.get("is_expired")),
            "is_quota_exceeded": bool(u_status.get("is_quota_exceeded")),
            "account": u_status,
            "user": u_status,
            "token": matching_user.get("token"),
            "uuid": matching_user.get("uuid"),
            "config": cfg_block,
            "sni_list": cfg_block["sni_list"],
            "target_ips": cfg_block["target_ips"],
            "plans": plans,
            "message": "Forfait expiré ou épuisé." if is_finished else "Appareil approuvé et actif."
        }

    req_list = [r for r in db.get("requests", []) if r.get("device_id") == device_id]
    if not req_list:
        return {"status": "not_found", "message": "Aucune demande trouvée pour cet appareil.", "plans": plans}

    latest_req = req_list[-1]
    req_status = (latest_req.get("status") or "PENDING").lower()
    if req_status == "rejected":
        return {
            "status": "rejected",
            "reason": latest_req.get("rejection_reason", "Demande refusée par l'administrateur."),
            "request": latest_req,
            "submitted_at": latest_req.get("submitted_at"),
            "plans": plans
        }

    return {
        "status": "pending",
        "request": latest_req,
        "message": "Votre demande est en cours d'examen par l'administrateur.",
        "plans": plans
    }


@router.get("/api/admin/requests")
async def list_membership_requests(request: Request):
    actor = get_current_actor(request)
    db = load_db()
    reqs = db.get("requests", [])
    if actor.get("role") == "RESELLER":
        reqs = [r for r in reqs if r.get("reseller_id") == actor.get("id")]
    return {"requests": reqs}


@router.post("/api/admin/requests/{request_id}/approve")
async def approve_membership_request(request_id: str, payload: RequestApproval, request: Request):
    actor = get_current_actor(request)
    db = load_db()
    req = next((r for r in db.get("requests", []) if r.get("id") == request_id), None)
    if not req:
        raise HTTPException(status_code=404, detail="Demande introuvable.")

    if actor.get("role") == "RESELLER" and req.get("reseller_id") not in (None, actor.get("id")):
        raise HTTPException(status_code=403, detail="Cette demande appartient à un autre revendeur.")

    # Calculate quota
    quota_bytes = payload.quota_bytes
    if quota_bytes is None:
        if payload.quota_gb is not None:
            if payload.quota_gb < 0:
                raise HTTPException(status_code=400, detail="Le quota ne peut pas être négatif.")
            quota_bytes = int(payload.quota_gb * (1024**3))
        else:
            quota_bytes = 10 * 1024 * 1024 * 1024

    if quota_bytes < 0:
        raise HTTPException(status_code=400, detail="Le quota ne peut pas être négatif.")

    # Reseller enforcement
    r_id = actor.get("id") if actor.get("role") == "RESELLER" else (payload.reseller_id or req.get("reseller_id"))
    reseller_obj = None
    req_gb = 0.0
    if r_id:
        reseller_obj = next((r for r in db.get("resellers", []) if r.get("id") == r_id), None)
        if not reseller_obj:
            raise HTTPException(status_code=404, detail="Revendeur introuvable.")
        if actor.get("role") == "RESELLER" and quota_bytes <= 0:
            raise HTTPException(status_code=400, detail="Un revendeur doit attribuer un quota strictement positif.")
        my_users_count = sum(1 for u in db.get("users", []) if u.get("reseller_id") == r_id)
        max_acc = int(reseller_obj.get("max_accounts", 100) or 100)
        if my_users_count >= max_acc:
            raise HTTPException(status_code=400, detail=f"Plafond de comptes atteint ({max_acc} comptes max).")
        req_gb = round(quota_bytes / (1024**3), 2) if quota_bytes > 0 else 100.0
        if reseller_obj.get("credit_gb", 0.0) < req_gb:
            raise HTTPException(
                status_code=400,
                detail=f"Solde revendeur insuffisant : {reseller_obj.get('credit_gb')} Go disponibles, {req_gb} Go requis."
            )
        reseller_obj["credit_gb"] = round(reseller_obj["credit_gb"] - req_gb, 2)

    expires_at = None
    if not payload.on_hold and payload.validity_days > 0:
        exp_date = datetime.now(timezone.utc) + timedelta(days=payload.validity_days)
        expires_at = exp_date.isoformat()

    new_uuid = str(uuid.uuid4())
    token = "NEXUS-VLESS-" + uuid.uuid4().hex[:8].upper()
    user_id = f"usr_{uuid.uuid4().hex[:8]}"
    ch_norm = normalize_channel(req.get("channel"))

    new_user = {
        "id": user_id,
        "name": req.get("full_name", "Client Nexus"),
        "uuid": new_uuid,
        "email": f"{req.get('first_name', 'user').lower()}_{req.get('last_name', 'client').lower()}@nexustunnel",
        "token": token,
        "is_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expires_at,
        "on_hold": bool(payload.on_hold),
        "on_hold_duration_days": int(payload.on_hold_duration_days or payload.validity_days or 30),
        "data_reset_strategy": payload.data_reset_strategy or "no_reset",
        "quota_bytes": quota_bytes,
        "used_bytes_up": 0,
        "used_bytes_down": 0,
        "max_ips": payload.max_ips,
        "notes": f"Approuvé via demande mobile ({req.get('country_name')}, {ch_norm}: {req.get('contact_detail')})",
        "device_id": req.get("device_id"),
        "device_model": req.get("device_model"),
        "device_os": req.get("device_os", "Android"),
        "country": req.get("country_name"),
        "channel": ch_norm,
        "contact_detail": req.get("contact_detail"),
        "reseller_id": r_id,
        "last_seen_at": None,
        "active_ips": []
    }

    db.setdefault("users", []).append(new_user)
    req["status"] = "APPROVED"
    req["approved_at"] = datetime.now(timezone.utc).isoformat()
    req["assigned_user_id"] = user_id
    req["reseller_id"] = r_id

    if reseller_obj and req_gb > 0:
        record_reseller_transaction(
            db,
            reseller_obj,
            "APPROVE_REQUEST",
            -req_gb,
            target_id=user_id,
            notes=f"Approbation demande {new_user['name']} (-{req_gb} Go)"
        )

    add_audit_log(
        db,
        actor.get("username"),
        actor.get("role"),
        "APPROVE_REQUEST",
        f"Demande approuvée pour {new_user['name']} ({round(quota_bytes/(1024**3), 1)} Go)",
        user_id
    )
    save_db(db)

    return {
        "status": "approved",
        "user": compute_user_status(new_user, db),
        "token": token,
        "message": f"Demande approuvée avec succès ! Compte créé avec {payload.validity_days} jours de validité."
    }


@router.post("/api/admin/requests/{request_id}/reject")
async def reject_membership_request(request_id: str, payload: RequestRejection, request: Request):
    actor = get_current_actor(request)
    db = load_db()
    req = next((r for r in db.get("requests", []) if r.get("id") == request_id), None)
    if not req:
        raise HTTPException(status_code=404, detail="Demande introuvable.")

    if actor.get("role") == "RESELLER" and req.get("reseller_id") != actor.get("id"):
        raise HTTPException(status_code=403, detail="Vous ne pouvez rejeter que vos propres demandes.")

    req["status"] = "REJECTED"
    req["rejection_reason"] = payload.reason.strip()
    req["rejected_at"] = datetime.now(timezone.utc).isoformat()
    add_audit_log(db, actor.get("username"), actor.get("role"), "REJECT_REQUEST", f"Rejet demande {req.get('full_name')}: {payload.reason.strip()}", request_id)
    save_db(db)

    return {
        "status": "rejected",
        "message": f"Demande rejetée avec le motif : '{payload.reason.strip()}'."
    }


@router.delete("/api/admin/requests/{request_id}")
async def delete_membership_request(request_id: str, request: Request):
    actor = get_current_actor(request)
    db = load_db()
    target_req = next((r for r in db.get("requests", []) if r.get("id") == request_id), None)
    if not target_req:
        raise HTTPException(status_code=404, detail="Demande introuvable.")

    if actor.get("role") == "RESELLER" and target_req.get("reseller_id") != actor.get("id"):
        raise HTTPException(status_code=403, detail="Vous ne pouvez supprimer que vos propres demandes.")

    db["requests"] = [r for r in db.get("requests", []) if r.get("id") != request_id]
    add_audit_log(db, actor.get("username"), actor.get("role"), "DELETE_REQUEST", f"Suppression demande {target_req.get('full_name')}", request_id)
    save_db(db)
    return {"status": "deleted", "id": request_id}


# --- Token / Voucher Activation ---

@router.post("/api/token/verify")
async def redeem_token_voucher(payload: TokenRedeem):
    db = load_db()
    raw_token = payload.token.strip().upper()

    if payload.device_id:
        check_device_access(db, payload.device_id, is_heartbeat=False)

    # 1. Check if it is an existing account token
    existing_user = next((u for u in db.get("users", []) if (u.get("token") or "").upper() == raw_token), None)
    if existing_user:
        if existing_user.get("device_id"):
            check_device_access(db, existing_user.get("device_id"), is_heartbeat=False)

        # Protect usr_default_root and already locked devices with max_ips > 0 from device_id overwrite!
        if payload.device_id and existing_user.get("id") != "usr_default_root":
            curr_dev = existing_user.get("device_id")
            max_ips = int(existing_user.get("max_ips", 0) or 0)
            if not curr_dev or curr_dev == payload.device_id or max_ips == 0:
                existing_user["device_id"] = payload.device_id

        save_db(db)
        u_st = compute_user_status(existing_user, db)
        return {
            "status": "success",
            "type": "ACCOUNT_SYNC",
            "user": u_st,
            "message": f"Compte synchronisé avec succès pour {existing_user['name']} !"
        }

    # 2. Check if it is a Recharge Voucher
    voucher = next((v for v in db.get("vouchers", []) if (v.get("code") or "").upper() == raw_token), None)
    if not voucher:
        raise HTTPException(status_code=404, detail="Token ou code de recharge invalide.")

    if voucher.get("is_redeemed", False):
        raise HTTPException(status_code=400, detail="Ce coupon a déjà été utilisé.")

    # Find target user: by user_id / uuid first, then by non-root device_id
    user = None
    if payload.user_id:
        user = next((u for u in db.get("users", []) if u.get("id") == payload.user_id and u.get("id") != "usr_default_root"), None)
    if not user and payload.uuid:
        user = next((u for u in db.get("users", []) if (u.get("uuid") or "").lower() == payload.uuid.strip().lower() and u.get("id") != "usr_default_root"), None)
    if not user and payload.device_id:
        user = next((u for u in db.get("users", []) if u.get("device_id") == payload.device_id and u.get("id") != "usr_default_root"), None)

    if not user:
        user_id = f"usr_{uuid.uuid4().hex[:8]}"
        new_uuid = str(uuid.uuid4())
        user_token = "NEXUS-VLESS-" + uuid.uuid4().hex[:8].upper()
        exp_date = datetime.now(timezone.utc) + timedelta(days=voucher.get("validity_days", 30))

        user = {
            "id": user_id,
            "name": f"Client Voucher ({voucher['code']})",
            "uuid": new_uuid,
            "email": f"voucher_{voucher['code'].lower()}@nexustunnel",
            "token": user_token,
            "is_enabled": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": exp_date.isoformat(),
            "on_hold": False,
            "on_hold_duration_days": voucher.get("validity_days", 30),
            "data_reset_strategy": "no_reset",
            "quota_bytes": voucher["quota_bytes"],
            "used_bytes_up": 0,
            "used_bytes_down": 0,
            "max_ips": voucher.get("max_ips", 2),
            "notes": f"Activé via Coupon {voucher['code']} ({voucher['plan_name']})",
            "device_id": payload.device_id,
            "device_model": "Voucher Client Device",
            "channel": "WHATSAPP",
            "reseller_id": voucher.get("reseller_id"),
            "last_seen_at": datetime.now(timezone.utc).isoformat(),
            "active_ips": []
        }
        db.setdefault("users", []).append(user)
    else:
        user["quota_bytes"] = int(user.get("quota_bytes", 0) or 0) + int(voucher["quota_bytes"])
        now_utc = datetime.now(timezone.utc)
        current_exp = None
        if user.get("expires_at"):
            try:
                current_exp = datetime.fromisoformat(str(user["expires_at"]).replace("Z", "+00:00"))
                if current_exp.tzinfo is None:
                    current_exp = current_exp.replace(tzinfo=timezone.utc)
            except Exception:
                pass

        base_date = current_exp if (current_exp and current_exp > now_utc) else now_utc
        new_exp = base_date + timedelta(days=voucher.get("validity_days", 30))
        user["expires_at"] = new_exp.isoformat()
        user["is_enabled"] = True
        user["on_hold"] = False

    voucher["is_redeemed"] = True
    voucher["is_used"] = True
    voucher["redeemed_by"] = user["id"]
    voucher["redeemed_at"] = datetime.now(timezone.utc).isoformat()
    save_db(db)

    u_status = compute_user_status(user, db)
    return {
        "status": "valid",
        "type": "VOUCHER_REDEEMED",
        "user": u_status,
        "voucher": enrich_voucher(voucher),
        "message": f"Félicitations ! Le forfait '{voucher['plan_name']}' a été appliqué à votre compte."
    }


# --- Vouchers Admin Management ---

@router.get("/api/vouchers")
async def list_vouchers(request: Request):
    actor = get_current_actor(request)
    db = load_db()
    vouchers = db.get("vouchers", [])
    if actor.get("role") == "RESELLER":
        vouchers = [v for v in vouchers if v.get("reseller_id") == actor.get("id")]
    return {"vouchers": [enrich_voucher(v) for v in vouchers]}


@router.post("/api/vouchers")
async def create_voucher(payload: VoucherCreate, request: Request):
    actor = get_current_actor(request)
    db = load_db()
    code = payload.code.strip().upper() if payload.code else f"NX-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}"

    for v in db.get("vouchers", []):
        if (v.get("code") or "").upper() == code:
            raise HTTPException(status_code=400, detail="Ce code de voucher existe déjà.")

    q_bytes = payload.quota_bytes
    if q_bytes is None:
        if payload.quota_gb is not None:
            if payload.quota_gb <= 0:
                raise HTTPException(status_code=400, detail="Le quota du voucher doit être strictement positif.")
            q_bytes = int(payload.quota_gb * (1024**3))
        else:
            q_bytes = 10 * 1024 * 1024 * 1024

    if q_bytes <= 0:
        raise HTTPException(status_code=400, detail="Le quota du voucher doit être strictement positif.")

    q_gb = round(q_bytes / (1024**3), 2)
    r_id = actor.get("id") if actor.get("role") == "RESELLER" else payload.reseller_id
    if r_id:
        reseller = next((r for r in db.get("resellers", []) if r.get("id") == r_id), None)
        if not reseller:
            raise HTTPException(status_code=404, detail="Revendeur introuvable.")
        if reseller.get("credit_gb", 0.0) < q_gb:
            raise HTTPException(
                status_code=400,
                detail=f"Solde revendeur insuffisant : {reseller.get('credit_gb')} Go disponibles, {q_gb} Go requis."
            )
        reseller["credit_gb"] = round(reseller["credit_gb"] - q_gb, 2)
        record_reseller_transaction(
            db,
            reseller,
            "CREATE_VOUCHER",
            -q_gb,
            target_id=code,
            notes=f"Création voucher {code} (-{q_gb} Go)"
        )

    new_v = {
        "code": code,
        "plan_name": payload.plan_name.strip() if payload.plan_name else "Forfait Recharge Nexus",
        "quota_bytes": q_bytes,
        "quota_gb": q_gb,
        "readable_quota": format_bytes(q_bytes),
        "validity_days": payload.validity_days,
        "max_ips": payload.max_ips,
        "is_redeemed": False,
        "is_used": False,
        "redeemed_by": None,
        "redeemed_at": None,
        "reseller_id": r_id,
        "created_by": actor.get("username"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    db.setdefault("vouchers", []).append(new_v)
    add_audit_log(db, actor.get("username"), actor.get("role"), "CREATE_VOUCHER", f"Création du voucher {code} ({q_gb} Go)", code)
    save_db(db)
    return {"status": "created", "voucher": enrich_voucher(new_v), "code": code}


@router.delete("/api/vouchers/{code}")
async def delete_voucher(code: str, request: Request):
    actor = get_current_actor(request)
    db = load_db()
    clean_code = code.strip().upper()
    vouchers = db.get("vouchers", [])
    target = next((v for v in vouchers if (v.get("code") or "").upper() == clean_code), None)
    if not target:
        raise HTTPException(status_code=404, detail="Voucher introuvable.")

    if actor.get("role") == "RESELLER" and target.get("reseller_id") != actor.get("id"):
        raise HTTPException(status_code=403, detail="Vous ne pouvez supprimer que vos propres vouchers.")

    # Refund reseller if voucher was not redeemed
    r_id = target.get("reseller_id")
    if r_id and not target.get("is_redeemed", False):
        reseller = next((r for r in db.get("resellers", []) if r.get("id") == r_id), None)
        if reseller:
            refund_gb = round(target.get("quota_bytes", 0) / (1024**3), 2)
            if refund_gb > 0:
                reseller["credit_gb"] = round(reseller.get("credit_gb", 0.0) + refund_gb, 2)
                record_reseller_transaction(
                    db,
                    reseller,
                    "REFUND_VOUCHER",
                    refund_gb,
                    target_id=target["code"],
                    notes=f"Remboursement voucher non utilisé {target['code']} (+{refund_gb} Go)"
                )

    db["vouchers"] = [v for v in vouchers if (v.get("code") or "").upper() != clean_code]
    add_audit_log(db, actor.get("username"), actor.get("role"), "DELETE_VOUCHER", f"Suppression du voucher {clean_code}", clean_code)
    save_db(db)
    return {"status": "deleted", "code": clean_code}


# --- VPN Real-Time Session & Heartbeat ---

@router.post("/api/vpn/connect")
async def vpn_connect_handshake(request: Request, payload: Dict[str, Any]):
    db = load_db()
    token = (payload.get("token") or "").strip().upper()
    uuid_str = (payload.get("uuid") or "").strip().lower()
    device_id = (payload.get("device_id") or "").strip()

    if device_id:
        check_device_access(db, device_id, is_heartbeat=False)

    user = None
    if token:
        user = next((u for u in db.get("users", []) if (u.get("token") or "").upper() == token), None)
    if not user and uuid_str:
        user = next((u for u in db.get("users", []) if (u.get("uuid") or "").lower() == uuid_str), None)
    if not user and device_id:
        user = next(
            (u for u in db.get("users", []) if u.get("device_id") == device_id and u.get("id") != "usr_default_root" and u.get("is_enabled", True)),
            None
        )

    if not user:
        raise HTTPException(status_code=403, detail="Compte ou token VPN introuvable.")

    if user.get("device_id"):
        check_device_access(db, user.get("device_id"), is_heartbeat=False)

    # Activate "Start on First Use" (on_hold)
    if user.get("on_hold"):
        dur_days = int(user.get("on_hold_duration_days") or 30)
        user["on_hold"] = False
        user["expires_at"] = (datetime.now(timezone.utc) + timedelta(days=dur_days)).isoformat()
        user["first_connected_at"] = datetime.now(timezone.utc).isoformat()

    u_st = compute_user_status(user, db)
    if not u_st["is_valid"]:
        if u_st["is_expired"]:
            raise HTTPException(status_code=403, detail="Votre forfait a expiré. Veuillez le recharger.")
        if u_st["is_quota_exceeded"]:
            raise HTTPException(status_code=403, detail="Votre quota de données est épuisé. Veuillez activer un forfait.")
        raise HTTPException(status_code=403, detail="Compte suspendu par l'administrateur.")

    client_ip = request.client.host if request.client else "127.0.0.1"
    ips = user.get("active_ips", [])
    if client_ip not in ips:
        ips.append(client_ip)
        max_allowed = int(user.get("max_ips", 0) or 3)
        user["active_ips"] = ips[-(max_allowed if max_allowed > 0 else 3):]
    if device_id and not user.get("device_id") and user.get("id") != "usr_default_root":
        user["device_id"] = device_id
    user["last_seen_at"] = datetime.now(timezone.utc).isoformat()
    save_db(db)

    settings = db.get("settings", DEFAULT_SETTINGS)
    vless_uri = generate_vless_uri(user["uuid"], user["name"], settings)

    return {
        "status": "connected",
        "user": compute_user_status(user, db),
        "session": {
            "uuid": user["uuid"],
            "token": user.get("token")
        },
        "vless_uri": vless_uri,
        "vless_variants": generate_user_vless_variants(user["uuid"], user["name"], settings),
        "server": {
            "target": settings.get("target_server"),
            "host": settings.get("host"),
            "path": settings.get("path"),
            "sni": settings.get("sni")
        },
        "session_id": f"sess_{uuid.uuid4().hex[:8]}"
    }


@router.post("/api/vpn/heartbeat")
async def vpn_heartbeat(payload: TrafficHeartbeat):
    db = load_db()
    settings = db.get("settings", DEFAULT_SETTINGS)
    token = (payload.token or "").strip().upper()
    req_uuid = (payload.uuid or "").strip().lower()

    if payload.device_id:
        dev_entry = find_device_entry(db, payload.device_id)
        if dev_entry and dev_entry.get("status") in ("BANNED", "REVOKED"):
            return {
                "status": "revoked",
                "should_disconnect": True,
                "disconnect_reason": "Appareil révoqué ou banni par l'administrateur"
            }
        if payload.device_id in db.get("deleted_devices", []):
            return {
                "status": "deleted",
                "reset_onboarding": True,
                "should_disconnect": True,
                "disconnect_reason": "Appareil détaché ou supprimé par l'administrateur"
            }

    user = None
    if payload.device_id:
        dev_str = payload.device_id.strip().lower()
        user = next((u for u in db.get("users", []) if (u.get("device_id") or "").lower() == dev_str and u.get("id") != "usr_default_root"), None)
        if not user:
            user = next((u for u in db.get("users", []) if (u.get("device_id") or "").lower() == dev_str), None)
    if not user and token:
        user = next(
            (u for u in db.get("users", []) if (u.get("token") or "").upper() == token or (u.get("uuid") or "").upper() == token),
            None
        )
    if not user and req_uuid:
        user = next((u for u in db.get("users", []) if (u.get("uuid") or "").lower() == req_uuid), None)

    if not user:
        return {
            "status": "revoked",
            "should_disconnect": True,
            "disconnect_reason": "Compte ou identifiants révoqués par l'administrateur"
        }

    dev_hwid = payload.device_id or user.get("device_id")
    dev_access = check_device_access(db, dev_hwid, is_heartbeat=True)

    # Activate "Start on First Use" (on_hold) if first heartbeat
    if user.get("on_hold"):
        dur_days = int(user.get("on_hold_duration_days") or 30)
        user["on_hold"] = False
        user["expires_at"] = (datetime.now(timezone.utc) + timedelta(days=dur_days)).isoformat()
        user["first_connected_at"] = datetime.now(timezone.utc).isoformat()

    if payload.device_model:
        user["device_model"] = payload.device_model
    if payload.os_version:
        user["device_os"] = payload.os_version

    b_up = max(0, payload.bytes_up)
    b_down = max(0, payload.bytes_down)
    if b_up == 0 and b_down == 0 and payload.bytes_delta and payload.bytes_delta > 0:
        b_down += int(payload.bytes_delta * 0.8)
        b_up += int(payload.bytes_delta * 0.2)

    user["used_bytes_up"] = int(user.get("used_bytes_up", 0) or 0) + b_up
    user["used_bytes_down"] = int(user.get("used_bytes_down", 0) or 0) + b_down
    user["last_seen_at"] = datetime.now(timezone.utc).isoformat()

    if dev_hwid:
        dev_rec = find_device_entry(db, dev_hwid)
        if dev_rec:
            dev_rec["last_seen_at"] = user["last_seen_at"]
            dev_rec["is_online"] = True
            if payload.device_model:
                dev_rec["device_model"] = payload.device_model
            if payload.os_version:
                dev_rec["device_os"] = payload.os_version
            if payload.app_version:
                dev_rec["app_version"] = payload.app_version

    if payload.client_ip:
        ips = user.get("active_ips", [])
        if payload.client_ip not in ips:
            ips.append(payload.client_ip)
            user["active_ips"] = ips[-3:]

    save_db(db)
    u_st = compute_user_status(user, db)
    creds_changed = bool(req_uuid and req_uuid != (user.get("uuid") or "").lower())
    cfg_block = {
        "uuid": user.get("uuid"),
        "token": user.get("token"),
        "host": settings.get("host", DEFAULT_SETTINGS["host"]),
        "target_server": settings.get("target_server", DEFAULT_SETTINGS["target_server"]),
        "port": 443,
        "path": settings.get("path", DEFAULT_SETTINGS["path"]),
        "sni": settings.get("sni", DEFAULT_SETTINGS["sni"]),
        "sni_list": settings.get("sni_list", DEFAULT_SETTINGS["sni_list"]),
        "target_ips": settings.get("target_ips", DEFAULT_SETTINGS["target_ips"])
    }

    if dev_access == "revoked":
        return {
            "status": "revoked",
            "user": u_st,
            "config": cfg_block,
            "credentials_changed": creds_changed,
            "should_disconnect": True,
            "disconnect_reason": "Appareil révoqué par l'administrateur"
        }

    if not user.get("is_enabled", True):
        return {
            "status": "disabled",
            "user": u_st,
            "config": cfg_block,
            "credentials_changed": creds_changed,
            "should_disconnect": True,
            "disconnect_reason": "Compte suspendu par l'administrateur"
        }

    if u_st["is_expired"]:
        return {
            "status": "expired",
            "user": u_st,
            "config": cfg_block,
            "credentials_changed": creds_changed,
            "should_disconnect": True,
            "disconnect_reason": "Forfait arrivé à expiration"
        }

    if u_st["is_quota_exceeded"]:
        return {
            "status": "quota_exceeded",
            "user": u_st,
            "config": cfg_block,
            "credentials_changed": creds_changed,
            "should_disconnect": True,
            "disconnect_reason": "Quota de données atteint"
        }

    return {
        "status": "ok",
        "user": u_st,
        "config": cfg_block,
        "credentials_changed": creds_changed,
        "should_disconnect": False,
        "disconnect_reason": ""
    }


@router.post("/api/vpn/disconnect")
async def vpn_disconnect(payload: Dict[str, Any]):
    db = load_db()
    token = (payload.get("token") or "").strip().upper()
    uuid_str = (payload.get("uuid") or "").strip().lower()
    user = None
    if token:
        user = next((u for u in db.get("users", []) if (u.get("token") or "").upper() == token), None)
    if not user and uuid_str:
        user = next((u for u in db.get("users", []) if (u.get("uuid") or "").lower() == uuid_str), None)
    if user:
        user["active_ips"] = []
        user["last_seen_at"] = datetime.now(timezone.utc).isoformat()
        save_db(db)
    return {"status": "disconnected"}


# --- Advanced Device Management ---

@router.get("/api/devices")
async def list_devices(request: Request):
    actor = get_current_actor(request)
    db = load_db()
    devices = sync_devices_registry(db)
    if actor.get("role") == "RESELLER":
        devices = [d for d in devices if d.get("reseller_id") == actor.get("id")]
    return {"devices": devices}


@router.put("/api/devices/{device_id}")
async def update_device(device_id: str, payload: DeviceUpdatePayload, request: Request):
    actor = get_current_actor(request)
    db = load_db()
    dev = find_device_entry(db, device_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Appareil introuvable.")

    if actor.get("role") == "RESELLER" and dev.get("reseller_id") != actor.get("id"):
        raise HTTPException(status_code=403, detail="Vous ne pouvez modifier que les appareils de vos clients.")

    if payload.name is not None:
        dev["name"] = payload.name.strip()
    if payload.device_model is not None:
        dev["device_model"] = payload.device_model.strip()
    if payload.device_os is not None:
        dev["device_os"] = payload.device_os.strip()
    if payload.notes is not None:
        dev["notes"] = payload.notes.strip()
    if payload.status is not None and payload.status.upper() in ("AUTHORIZED", "REVOKED", "BANNED"):
        dev["status"] = payload.status.upper()

    if payload.user_id is not None:
        hwid = dev.get("device_id")
        # Detach from previous user
        for u in db.get("users", []):
            if u.get("device_id") == hwid and u.get("id") != payload.user_id:
                u["device_id"] = None
        if payload.user_id == "":
            dev["user_id"] = None
        else:
            new_owner = next((u for u in db.get("users", []) if u.get("id") == payload.user_id), None)
            if not new_owner:
                raise HTTPException(status_code=404, detail="Utilisateur cible introuvable.")
            new_owner["device_id"] = hwid
            if payload.device_model:
                new_owner["device_model"] = payload.device_model.strip()
            dev["user_id"] = new_owner["id"]
            dev["owner_name"] = new_owner["name"]
            dev["reseller_id"] = new_owner.get("reseller_id")

    add_audit_log(db, actor.get("username"), actor.get("role"), "UPDATE_DEVICE", f"Modification de l'appareil {dev.get('name')} ({dev.get('device_id')})", dev.get("device_id"))
    save_db(db)
    return {"status": "updated", "device": dev}


@router.post("/api/devices/{device_id}/revoke")
async def revoke_device(device_id: str, request: Request):
    actor = get_current_actor(request)
    db = load_db()
    dev = find_device_entry(db, device_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Appareil introuvable.")

    if actor.get("role") == "RESELLER" and dev.get("reseller_id") != actor.get("id"):
        raise HTTPException(status_code=403, detail="Accès refusé à cet appareil.")

    hwid = dev.get("device_id")
    dev["status"] = "REVOKED"
    dev["is_online"] = False
    dev["ips"] = []

    for u in db.get("users", []):
        if u.get("device_id") == hwid or u.get("id") == dev.get("user_id"):
            if u.get("device_id") == hwid:
                u["device_id"] = None
            u["active_ips"] = []

    add_audit_log(db, actor.get("username"), actor.get("role"), "REVOKE_DEVICE", f"Révocation de l'appareil {dev.get('name')} ({hwid})", hwid)
    save_db(db)
    return {"status": "revoked", "device": dev}


@router.post("/api/devices/{device_id}/authorize")
async def authorize_device(device_id: str, request: Request):
    actor = get_current_actor(request)
    db = load_db()
    dev = find_device_entry(db, device_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Appareil introuvable.")

    if actor.get("role") == "RESELLER" and dev.get("reseller_id") != actor.get("id"):
        raise HTTPException(status_code=403, detail="Accès refusé à cet appareil.")

    hwid = dev.get("device_id")
    dev["status"] = "AUTHORIZED"
    if dev.get("user_id"):
        owner = next((u for u in db.get("users", []) if u.get("id") == dev["user_id"]), None)
        if owner and not owner.get("device_id") and owner.get("id") != "usr_default_root":
            owner["device_id"] = hwid

    add_audit_log(db, actor.get("username"), actor.get("role"), "AUTHORIZE_DEVICE", f"Autorisation de l'appareil {dev.get('name')} ({hwid})", hwid)
    save_db(db)
    return {"status": "authorized", "device": dev}


@router.post("/api/devices/{device_id}/ban")
async def ban_device(device_id: str, request: Request):
    actor = get_current_actor(request)
    db = load_db()
    dev = find_device_entry(db, device_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Appareil introuvable.")

    if actor.get("role") == "RESELLER" and dev.get("reseller_id") != actor.get("id"):
        raise HTTPException(status_code=403, detail="Accès refusé à cet appareil.")

    hwid = dev.get("device_id")
    dev["status"] = "BANNED"
    dev["is_online"] = False
    dev["ips"] = []

    for u in db.get("users", []):
        if u.get("device_id") == hwid:
            u["active_ips"] = []

    add_audit_log(db, actor.get("username"), actor.get("role"), "BAN_DEVICE", f"Bannissement définitif de l'appareil {dev.get('name')} ({hwid})", hwid)
    save_db(db)
    return {"status": "banned", "device": dev}


@router.delete("/api/devices/{device_id}")
async def delete_device(device_id: str, request: Request):
    actor = get_current_actor(request)
    db = load_db()
    dev = find_device_entry(db, device_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Appareil introuvable.")

    if actor.get("role") == "RESELLER" and dev.get("reseller_id") != actor.get("id"):
        raise HTTPException(status_code=403, detail="Accès refusé à cet appareil.")

    hwid = dev.get("device_id")
    dev_internal_id = dev.get("id")

    for u in db.get("users", []):
        if u.get("device_id") == hwid:
            u["device_id"] = None
            u["active_ips"] = []

    db["devices"] = [d for d in db.get("devices", []) if d.get("device_id") != hwid and d.get("id") != dev_internal_id]
    deleted_list = db.setdefault("deleted_devices", [])
    if hwid and hwid not in deleted_list:
        deleted_list.append(hwid)

    add_audit_log(db, actor.get("username"), actor.get("role"), "DELETE_DEVICE", f"Suppression de l'appareil {hwid}", hwid)
    save_db(db)
    return {"status": "deleted", "device_id": hwid}


# --- Standard & Advanced User Management (CRUD + Bulk + Security) ---

@router.get("/api/users")
async def list_users(request: Request):
    actor = get_current_actor(request)
    db = load_db()
    raw_users = db.get("users", [])
    if actor.get("role") == "RESELLER":
        raw_users = [u for u in raw_users if u.get("reseller_id") == actor.get("id")]
    users = [compute_user_status(u, db) for u in raw_users]
    return {"users": users}


@router.post("/api/users")
async def create_user(payload: UserCreate, request: Request):
    actor = get_current_actor(request)
    db = load_db()

    chosen_uuid = (payload.uuid_str or payload.uuid or "").strip() or str(uuid.uuid4())
    for u in db.get("users", []):
        if (u.get("uuid") or "").lower() == chosen_uuid.lower():
            raise HTTPException(status_code=400, detail="Cet UUID existe déjà.")

    # Compute quota_bytes
    if payload.quota_bytes is not None:
        q_bytes = payload.quota_bytes
    elif payload.quota_gb is not None:
        if payload.quota_gb < 0:
            raise HTTPException(status_code=400, detail="Le quota ne peut pas être négatif.")
        q_bytes = int(payload.quota_gb * (1024**3))
    else:
        q_bytes = 0

    if q_bytes < 0:
        raise HTTPException(status_code=400, detail="Le quota ne peut pas être négatif.")

    # Reseller rules & debit
    r_id = actor.get("id") if actor.get("role") == "RESELLER" else payload.reseller_id
    reseller_obj = None
    req_gb = 0.0
    if r_id:
        reseller_obj = next((r for r in db.get("resellers", []) if r.get("id") == r_id), None)
        if not reseller_obj:
            raise HTTPException(status_code=404, detail="Revendeur introuvable.")
        if actor.get("role") == "RESELLER" and q_bytes <= 0:
            raise HTTPException(status_code=400, detail="Un revendeur doit définir un quota strictement positif.")
        my_users_count = sum(1 for u in db.get("users", []) if u.get("reseller_id") == r_id)
        max_acc = int(reseller_obj.get("max_accounts", 100) or 100)
        if my_users_count >= max_acc:
            raise HTTPException(status_code=400, detail=f"Plafond de comptes atteint ({max_acc} comptes max).")
        req_gb = round(q_bytes / (1024**3), 2) if q_bytes > 0 else 100.0
        if reseller_obj.get("credit_gb", 0.0) < req_gb:
            raise HTTPException(
                status_code=400,
                detail=f"Solde revendeur insuffisant : {reseller_obj.get('credit_gb')} Go disponibles, {req_gb} Go requis."
            )
        reseller_obj["credit_gb"] = round(reseller_obj["credit_gb"] - req_gb, 2)

    user_id = f"usr_{uuid.uuid4().hex[:8]}"
    clean_name = payload.name.strip()
    slug_token = (payload.token or "").strip().upper() or ("NEXUS-VLESS-" + uuid.uuid4().hex[:8].upper())

    expires_at = payload.expires_at
    if not expires_at and not payload.on_hold and payload.validity_days and payload.validity_days > 0:
        expires_at = (datetime.now(timezone.utc) + timedelta(days=payload.validity_days)).isoformat()

    new_user = {
        "id": user_id,
        "name": clean_name,
        "uuid": chosen_uuid,
        "email": f"{clean_name.lower().replace(' ', '_')}@nexustunnel",
        "token": slug_token,
        "is_enabled": payload.is_enabled,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": None if payload.on_hold else expires_at,
        "on_hold": bool(payload.on_hold),
        "on_hold_duration_days": int(payload.on_hold_duration_days or payload.validity_days or 30),
        "data_reset_strategy": payload.data_reset_strategy or "no_reset",
        "quota_bytes": q_bytes,
        "used_bytes_up": 0,
        "used_bytes_down": 0,
        "max_ips": payload.max_ips,
        "notes": payload.notes or "",
        "reseller_id": r_id,
        "country": payload.country or "Cameroun",
        "channel": normalize_channel(payload.channel),
        "contact_detail": payload.contact_detail or payload.contact_phone,
        "device_id": payload.device_id,
        "device_model": payload.device_model,
        "last_seen_at": None,
        "active_ips": []
    }

    db.setdefault("users", []).append(new_user)
    if reseller_obj and req_gb > 0:
        record_reseller_transaction(
            db,
            reseller_obj,
            "CREATE_USER",
            -req_gb,
            target_id=user_id,
            notes=f"Création compte {clean_name} (-{req_gb} Go)"
        )

    add_audit_log(
        db,
        actor.get("username"),
        actor.get("role"),
        "CREATE_USER",
        f"Création compte {clean_name} ({round(q_bytes/(1024**3), 1)} Go)",
        user_id
    )
    save_db(db)

    return {"status": "created", "user": compute_user_status(new_user, db)}


@router.post("/api/users/bulk")
async def bulk_users_action(payload: BulkUsersPayload, request: Request):
    actor = get_current_actor(request)
    db = load_db()
    action = payload.action.strip().lower()
    valid_actions = {"enable", "disable", "reset_traffic", "extend_days", "add_gb", "delete"}
    if action not in valid_actions:
        raise HTTPException(status_code=400, detail=f"Action groupée invalide : {action}")

    target_ids = set(payload.user_ids or [])
    if not target_ids:
        raise HTTPException(status_code=400, detail="Aucun utilisateur sélectionné.")

    users = db.get("users", [])
    matched_users = [
        u for u in users
        if (u.get("id") in target_ids or u.get("uuid") in target_ids)
        and (actor.get("role") != "RESELLER" or u.get("reseller_id") == actor.get("id"))
    ]
    if not matched_users:
        raise HTTPException(status_code=404, detail="Aucun utilisateur correspondant trouvé.")

    now_utc = datetime.now(timezone.utc)
    affected_users = []

    if action == "add_gb":
        add_gb = float(payload.value or 0.0)
        if add_gb <= 0:
            raise HTTPException(status_code=400, detail="La quantité de Go à ajouter doit être positive.")
        if actor.get("role") == "RESELLER":
            reseller = next((r for r in db.get("resellers", []) if r.get("id") == actor.get("id")), None)
            total_needed = round(add_gb * len(matched_users), 2)
            if not reseller or reseller.get("credit_gb", 0.0) < total_needed:
                raise HTTPException(status_code=400, detail=f"Solde revendeur insuffisant ({total_needed} Go requis).")
            reseller["credit_gb"] = round(reseller["credit_gb"] - total_needed, 2)
            record_reseller_transaction(
                db,
                reseller,
                "BULK_ADD_GB",
                -total_needed,
                notes=f"Ajout groupé de +{add_gb} Go sur {len(matched_users)} comptes"
            )
        add_bytes = int(add_gb * (1024**3))
        for u in matched_users:
            u["quota_bytes"] = int(u.get("quota_bytes", 0) or 0) + add_bytes
            affected_users.append(u)

    elif action == "extend_days":
        add_days = int(payload.value or 30)
        if add_days <= 0:
            raise HTTPException(status_code=400, detail="Le nombre de jours doit être positif.")
        for u in matched_users:
            base_dt = now_utc
            if u.get("expires_at"):
                try:
                    parsed = datetime.fromisoformat(str(u["expires_at"]).replace("Z", "+00:00"))
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    if parsed > now_utc:
                        base_dt = parsed
                except Exception:
                    pass
            u["expires_at"] = (base_dt + timedelta(days=add_days)).isoformat()
            affected_users.append(u)

    elif action == "enable":
        for u in matched_users:
            u["is_enabled"] = True
            affected_users.append(u)

    elif action == "disable":
        for u in matched_users:
            u["is_enabled"] = False
            u["active_ips"] = []
            affected_users.append(u)

    elif action == "reset_traffic":
        for u in matched_users:
            u["used_bytes_up"] = 0
            u["used_bytes_down"] = 0
            u["last_reset_at"] = now_utc.isoformat()
            affected_users.append(u)

    elif action == "delete":
        to_delete_ids = set()
        for u in matched_users:
            if u.get("id") == "usr_default_root":
                continue
            to_delete_ids.add(u.get("id"))
            r_id = u.get("reseller_id")
            if r_id:
                reseller = next((r for r in db.get("resellers", []) if r.get("id") == r_id), None)
                u_st = compute_user_status(u, db)
                q_b = int(u.get("quota_bytes", 0) or 0)
                used_b = u_st["total_used_bytes"]
                if reseller and not u_st["is_expired"] and q_b > used_b:
                    refund_gb = round((q_b - used_b) / (1024**3), 2)
                    if refund_gb > 0:
                        reseller["credit_gb"] = round(reseller.get("credit_gb", 0.0) + refund_gb, 2)
                        record_reseller_transaction(
                            db,
                            reseller,
                            "REFUND_PRORATA",
                            refund_gb,
                            target_id=u.get("id"),
                            notes=f"Remboursement prorata suppression groupée {u.get('name')} (+{refund_gb} Go)"
                        )
            affected_users.append(u)
        db["users"] = [u for u in users if u.get("id") not in to_delete_ids]

    add_audit_log(
        db,
        actor.get("username"),
        actor.get("role"),
        "BULK_USERS_ACTION",
        f"Action groupée '{action}' sur {len(affected_users)} compte(s)"
    )
    save_db(db)
    return {
        "status": "ok",
        "action": action,
        "affected": len(affected_users),
        "users": [compute_user_status(u, db) for u in affected_users]
    }


@router.get("/api/users/{user_id}")
async def get_user_detail(user_id: str, request: Request):
    actor = get_current_actor(request)
    db = load_db()
    for u in db.get("users", []):
        if u.get("id") == user_id or u.get("uuid") == user_id:
            if actor.get("role") == "RESELLER" and u.get("reseller_id") != actor.get("id"):
                raise HTTPException(status_code=403, detail="Accès refusé à ce compte.")
            return {"user": compute_user_status(u, db)}
    raise HTTPException(status_code=404, detail="Utilisateur introuvable.")


@router.put("/api/users/{user_id}")
async def update_user(user_id: str, payload: UserUpdate, request: Request):
    actor = get_current_actor(request)
    db = load_db()
    target_user = next((u for u in db.get("users", []) if u.get("id") == user_id or u.get("uuid") == user_id), None)
    if not target_user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    if actor.get("role") == "RESELLER" and target_user.get("reseller_id") != actor.get("id"):
        raise HTTPException(status_code=403, detail="Vous ne pouvez modifier que vos propres clients.")

    # Quota resolution & Reseller debit if increased
    new_quota_bytes = payload.quota_bytes
    if new_quota_bytes is None and payload.quota_gb is not None:
        if payload.quota_gb < 0:
            raise HTTPException(status_code=400, detail="Le quota ne peut pas être négatif.")
        new_quota_bytes = int(payload.quota_gb * (1024**3))

    if new_quota_bytes is not None:
        if new_quota_bytes < 0:
            raise HTTPException(status_code=400, detail="Le quota ne peut pas être négatif.")
        old_quota_bytes = int(target_user.get("quota_bytes", 0) or 0)
        r_id = actor.get("id") if actor.get("role") == "RESELLER" else target_user.get("reseller_id")
        if r_id:
            if actor.get("role") == "RESELLER" and new_quota_bytes <= 0:
                raise HTTPException(status_code=400, detail="Un revendeur ne peut pas définir un quota illimité ou nul.")
            if new_quota_bytes > old_quota_bytes:
                delta_gb = round((new_quota_bytes - old_quota_bytes) / (1024**3), 2)
                if delta_gb > 0:
                    reseller = next((r for r in db.get("resellers", []) if r.get("id") == r_id), None)
                    if reseller:
                        if reseller.get("credit_gb", 0.0) < delta_gb:
                            raise HTTPException(
                                status_code=400,
                                detail=f"Solde revendeur insuffisant : {reseller.get('credit_gb')} Go disponibles, {delta_gb} Go requis."
                            )
                        reseller["credit_gb"] = round(reseller["credit_gb"] - delta_gb, 2)
                        record_reseller_transaction(
                            db,
                            reseller,
                            "EDIT_USER_QUOTA",
                            -delta_gb,
                            target_id=target_user["id"],
                            notes=f"Augmentation quota de {target_user.get('name')} (-{delta_gb} Go)"
                        )
        target_user["quota_bytes"] = new_quota_bytes

    new_uuid = (payload.uuid_str or payload.uuid or "").strip()
    if new_uuid and new_uuid.lower() != (target_user.get("uuid") or "").lower():
        if any((u.get("uuid") or "").lower() == new_uuid.lower() for u in db.get("users", []) if u.get("id") != target_user["id"]):
            raise HTTPException(status_code=400, detail="Cet UUID est déjà utilisé par un autre compte.")
        target_user["uuid"] = new_uuid

    if payload.token is not None and payload.token.strip():
        new_tok = payload.token.strip().upper()
        if any((u.get("token") or "").upper() == new_tok for u in db.get("users", []) if u.get("id") != target_user["id"]):
            raise HTTPException(status_code=400, detail="Ce token est déjà utilisé par un autre compte.")
        target_user["token"] = new_tok

    if payload.name is not None:
        target_user["name"] = payload.name.strip()
    if payload.expires_at is not None:
        target_user["expires_at"] = payload.expires_at if payload.expires_at != "" else None
    if payload.on_hold is not None:
        target_user["on_hold"] = bool(payload.on_hold)
    if payload.on_hold_duration_days is not None:
        target_user["on_hold_duration_days"] = int(payload.on_hold_duration_days)
    if payload.data_reset_strategy is not None:
        target_user["data_reset_strategy"] = payload.data_reset_strategy
    if payload.max_ips is not None:
        target_user["max_ips"] = payload.max_ips
    if payload.notes is not None:
        target_user["notes"] = payload.notes
    if payload.is_enabled is not None:
        target_user["is_enabled"] = payload.is_enabled
    if payload.country is not None:
        target_user["country"] = payload.country
    if payload.channel is not None:
        target_user["channel"] = normalize_channel(payload.channel)
    if payload.contact_detail is not None or payload.contact_phone is not None:
        target_user["contact_detail"] = payload.contact_detail if payload.contact_detail is not None else payload.contact_phone
    if payload.device_id is not None:
        target_user["device_id"] = payload.device_id if payload.device_id != "" else None
    if payload.device_model is not None:
        target_user["device_model"] = payload.device_model
    if payload.reseller_id is not None and actor.get("role") != "RESELLER":
        target_user["reseller_id"] = payload.reseller_id if payload.reseller_id != "" else None

    add_audit_log(db, actor.get("username"), actor.get("role"), "UPDATE_USER", f"Mise à jour du compte {target_user.get('name')}", target_user["id"])
    save_db(db)
    return {"status": "updated", "user": compute_user_status(target_user, db)}


@router.post("/api/users/{user_id}/revoke-credentials")
async def revoke_user_credentials(user_id: str, request: Request, payload: Optional[RevokeCredentialsPayload] = None):
    actor = get_current_actor(request)
    db = load_db()
    target_user = next((u for u in db.get("users", []) if u.get("id") == user_id or u.get("uuid") == user_id), None)
    if not target_user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    if actor.get("role") == "RESELLER" and target_user.get("reseller_id") != actor.get("id"):
        raise HTTPException(status_code=403, detail="Accès refusé à ce compte.")

    opts = payload or RevokeCredentialsPayload()
    if opts.regen_uuid:
        target_user["uuid"] = str(uuid.uuid4())
    if opts.regen_token:
        target_user["token"] = "NEXUS-VLESS-" + uuid.uuid4().hex[:8].upper()
    target_user["active_ips"] = []

    if opts.detach_device and target_user.get("device_id"):
        old_dev = target_user.get("device_id")
        target_user["device_id"] = None
        dev_entry = find_device_entry(db, old_dev)
        if dev_entry:
            dev_entry["status"] = "REVOKED"
            dev_entry["is_online"] = False
            dev_entry["ips"] = []

    add_audit_log(
        db,
        actor.get("username"),
        actor.get("role"),
        "REVOKE_CREDENTIALS",
        f"Régénération des identifiants VLESS/Token pour {target_user.get('name')}",
        target_user["id"]
    )
    save_db(db)
    return {
        "status": "revoked",
        "uuid": target_user["uuid"],
        "token": target_user["token"],
        "user": compute_user_status(target_user, db)
    }


@router.post("/api/users/{user_id}/clear-devices")
async def clear_user_devices(user_id: str, request: Request):
    actor = get_current_actor(request)
    db = load_db()
    target_user = next((u for u in db.get("users", []) if u.get("id") == user_id or u.get("uuid") == user_id), None)
    if not target_user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    if actor.get("role") == "RESELLER" and target_user.get("reseller_id") != actor.get("id"):
        raise HTTPException(status_code=403, detail="Accès refusé à ce compte.")

    old_hwid = target_user.get("device_id")
    target_user["device_id"] = None
    target_user["active_ips"] = []

    sync_devices_registry(db)
    for d in db.get("devices", []):
        if d.get("user_id") == target_user["id"] or (old_hwid and d.get("device_id") == old_hwid):
            d["status"] = "REVOKED"
            d["is_online"] = False
            d["ips"] = []

    add_audit_log(
        db,
        actor.get("username"),
        actor.get("role"),
        "CLEAR_USER_DEVICES",
        f"Détachement et révocation des appareils de {target_user.get('name')}",
        target_user["id"]
    )
    save_db(db)
    return {"status": "cleared", "user": compute_user_status(target_user, db)}


@router.post("/api/users/{user_id}/toggle")
async def toggle_user(user_id: str, request: Request):
    actor = get_current_actor(request)
    db = load_db()
    target_user = next((u for u in db.get("users", []) if u.get("id") == user_id or u.get("uuid") == user_id), None)
    if not target_user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    if actor.get("role") == "RESELLER" and target_user.get("reseller_id") != actor.get("id"):
        raise HTTPException(status_code=403, detail="Accès refusé à ce compte.")

    target_user["is_enabled"] = not target_user.get("is_enabled", True)
    if not target_user["is_enabled"]:
        target_user["active_ips"] = []
    save_db(db)
    return {"status": "toggled", "is_enabled": target_user["is_enabled"], "user": compute_user_status(target_user, db)}


@router.post("/api/users/{user_id}/reset-traffic")
async def reset_user_traffic(user_id: str, request: Request):
    actor = get_current_actor(request)
    db = load_db()
    target_user = next((u for u in db.get("users", []) if u.get("id") == user_id or u.get("uuid") == user_id), None)
    if not target_user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    if actor.get("role") == "RESELLER" and target_user.get("reseller_id") != actor.get("id"):
        raise HTTPException(status_code=403, detail="Accès refusé à ce compte.")

    target_user["used_bytes_up"] = 0
    target_user["used_bytes_down"] = 0
    target_user["last_reset_at"] = datetime.now(timezone.utc).isoformat()
    save_db(db)
    return {"status": "traffic_reset", "user": compute_user_status(target_user, db)}


@router.delete("/api/users/{user_id}")
async def delete_user(user_id: str, request: Request):
    actor = get_current_actor(request)
    db = load_db()
    users = db.get("users", [])
    target = next((u for u in users if u.get("id") == user_id or u.get("uuid") == user_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    if target.get("id") == "usr_default_root":
        raise HTTPException(status_code=400, detail="Impossible de supprimer le compte maître Root Docker.")

    if actor.get("role") == "RESELLER" and target.get("reseller_id") != actor.get("id"):
        raise HTTPException(status_code=403, detail="Vous ne pouvez supprimer que vos propres clients.")

    # Prorata / Grace-period refund for Reseller
    r_id = target.get("reseller_id")
    refund_gb = 0.0
    if r_id:
        reseller = next((r for r in db.get("resellers", []) if r.get("id") == r_id), None)
        u_st = compute_user_status(target, db)
        q_bytes = int(target.get("quota_bytes", 0) or 0)
        used_bytes = u_st["total_used_bytes"]

        if reseller and not u_st["is_expired"] and q_bytes > 0:
            now_utc = datetime.now(timezone.utc)
            created_recent = False
            if target.get("created_at"):
                try:
                    c_dt = datetime.fromisoformat(str(target["created_at"]).replace("Z", "+00:00"))
                    if c_dt.tzinfo is None:
                        c_dt = c_dt.replace(tzinfo=timezone.utc)
                    if (now_utc - c_dt).total_seconds() <= 3600 and used_bytes < 100 * 1024 * 1024:
                        created_recent = True
                except Exception:
                    pass

            if created_recent:
                refund_gb = round(q_bytes / (1024**3), 2)
            elif q_bytes > used_bytes:
                refund_gb = round((q_bytes - used_bytes) / (1024**3), 2)

            if refund_gb > 0:
                reseller["credit_gb"] = round(reseller.get("credit_gb", 0.0) + refund_gb, 2)
                record_reseller_transaction(
                    db,
                    reseller,
                    "REFUND_PRORATA",
                    refund_gb,
                    target_id=target["id"],
                    notes=f"Remboursement prorata suppression {target.get('name')} (+{refund_gb} Go)"
                )

    db["users"] = [u for u in users if u.get("id") != user_id and u.get("uuid") != user_id]
    add_audit_log(
        db,
        actor.get("username"),
        actor.get("role"),
        "DELETE_USER",
        f"Suppression du compte {target.get('name')}" + (f" (Remboursement +{refund_gb} Go)" if refund_gb > 0 else ""),
        user_id
    )
    save_db(db)
    return {"status": "deleted", "id": user_id, "refunded_gb": refund_gb}


@router.get("/api/users/{user_id}/export")
async def export_user_configs(user_id: str, request: Request):
    db = load_db()
    settings = db.get("settings", DEFAULT_SETTINGS)
    target_user = None
    for u in db.get("users", []):
        if u.get("id") == user_id or u.get("uuid") == user_id:
            target_user = compute_user_status(u, db)
            break

    if not target_user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    u_uuid = target_user["uuid"]
    u_name = target_user["name"]
    u_token = target_user.get("token") or u_uuid

    target_server = settings.get("target_server", "192.179.18.100:443")
    host = settings.get("host", "nexus-tunnel-753027553589.us-east1.run.app")
    sni = settings.get("sni", "crashlyticsreports-pa.googleapis.com")
    raw_path = settings.get("path", "/nexustunnel")
    clean_path = raw_path.split("?")[0] if "?" in raw_path else raw_path

    server_ip, server_port = target_server.split(":", 1) if ":" in target_server else (target_server, "443")

    vless_uri = generate_vless_uri(u_uuid, u_name, settings, variant="fast")
    vless_uri_stable = generate_vless_uri(u_uuid, u_name, settings, variant="stable")
    vless_variants = generate_user_vless_variants(u_uuid, u_name, settings)
    qr_code_b64 = generate_qr_base64(vless_uri)

    base_url = str(request.base_url).rstrip("/")
    sub_path = f"/nexus/sub/{u_token}"
    full_sub_url = f"{base_url}{sub_path}"
    qr_code_sub = generate_qr_base64(full_sub_url)

    darktunnel_config = {
        "protocol": "VLess • Websocket SSL/TLS • Mux",
        "target_server": target_server,
        "uuid": u_uuid,
        "path": f"{clean_path}?ed=2048",
        "sni": sni,
        "header_host": host,
        "formatted_text": (
            f"VLess • Websocket SSL/TLS • Mux\n"
            f"Target Server : {target_server}\n"
            f"UUID          : {u_uuid}\n"
            f"Path          : {clean_path}?ed=2048\n"
            f"SNI           : {sni}\n"
            f"Header Host   : {host}"
        )
    }

    clash_meta_config = {
        "name": f"{u_name} ⚡ Fast",
        "type": "vless",
        "server": server_ip,
        "port": int(server_port),
        "uuid": u_uuid,
        "network": "ws",
        "tls": True,
        "udp": True,
        "client-fingerprint": "chrome",
        "alpn": ["http/1.1"],
        "servername": sni,
        "ws-opts": {
            "path": f"{clean_path}?ed=2048",
            "max-early-data": 2048,
            "early-data-header-name": "Sec-WebSocket-Protocol",
            "headers": {
                "Host": host
            }
        }
    }

    singbox_config = {
        "type": "vless",
        "tag": f"{u_name} ⚡ Fast",
        "server": server_ip,
        "server_port": int(server_port),
        "uuid": u_uuid,
        "tls": {
            "enabled": True,
            "server_name": sni,
            "insecure": False,
            "alpn": ["http/1.1"],
            "utls": {"enabled": True, "fingerprint": "chrome"}
        },
        "transport": {
            "type": "ws",
            "path": clean_path,
            "max_early_data": 2048,
            "early_data_header_name": "Sec-WebSocket-Protocol",
            "headers": {
                "Host": host
            }
        }
    }

    xray_client_json = generate_xray_client_json(u_uuid, u_name, settings)

    return {
        "user": target_user,
        "vless_uri": vless_uri,
        "vless_uri_stable": vless_uri_stable,
        "vless_variants": vless_variants,
        "qr_code": qr_code_b64,
        "sub_url": full_sub_url,
        "subscription_url": f"/sub/{u_token}",
        "qr_code_sub": qr_code_sub,
        "darktunnel": darktunnel_config,
        "clash": clash_meta_config,
        "clash_meta": clash_meta_config,
        "singbox": singbox_config,
        "xray_client_json": xray_client_json
    }


# --- Xray Config & Server Settings ---

@router.get("/api/config/xray")
async def get_xray_config():
    db = load_db()
    settings = db.get("settings", DEFAULT_SETTINGS)
    raw_path = settings.get("path", "/nexustunnel")
    clean_path = raw_path.split("?")[0] if "?" in raw_path else raw_path

    clients = []
    for u in db.get("users", []):
        st = compute_user_status(u, db)
        if st["is_valid"]:
            clients.append({
                "id": u.get("uuid"),
                "level": 0,
                "email": u.get("email", f"{u.get('id')}@nexus")
            })

    if not clients:
        clients.append({
            "id": settings.get("root_uuid", "e3a478b2-5e1b-4cf7-8b09-1a2b3c4d5e6f"),
            "level": 0,
            "email": "root@nexustunnel"
        })

    xray_json = {
        "log": {"loglevel": "warning"},
        "policy": {
            "levels": {
                "0": {
                    "handshake": 4,
                    "connIdle": 300,
                    "uplinkOnly": 2,
                    "downlinkOnly": 5,
                    "bufferSize": 512,
                    "statsUserUplink": True,
                    "statsUserDownlink": True
                }
            },
            "system": {
                "statsInboundUplink": True,
                "statsInboundDownlink": True
            }
        },
        "inbounds": [
            {
                "port": 8080,
                "protocol": "vless",
                "settings": {
                    "clients": clients,
                    "decryption": "none"
                },
                "streamSettings": {
                    "network": "ws",
                    "wsSettings": {
                        "path": clean_path,
                        "maxEarlyData": 2048,
                        "earlyDataHeaderName": "Sec-WebSocket-Protocol"
                    }
                },
                "sniffing": {
                    "enabled": True,
                    "destOverride": ["http", "tls", "quic"]
                }
            }
        ],
        "outbounds": [
            {"tag": "direct", "protocol": "freedom", "settings": {"domainStrategy": "UseIP"}},
            {"tag": "block", "protocol": "blackhole"}
        ]
    }
    return JSONResponse(content=xray_json)


@router.get("/api/settings")
async def get_settings():
    db = load_db()
    return {"settings": db.get("settings", DEFAULT_SETTINGS)}


@router.post("/api/settings")
async def update_settings(payload: SettingsUpdate, request: Request):
    actor = get_current_actor(request)
    if actor.get("role") not in ("SUPER_ADMIN", "ADMIN"):
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs.")

    db = load_db()
    st = db.setdefault("settings", copy.deepcopy(DEFAULT_SETTINGS))

    if payload.host is not None:
        st["host"] = payload.host.strip()
    if payload.target_server is not None:
        st["target_server"] = payload.target_server.strip()
    if payload.sni is not None:
        st["sni"] = payload.sni.strip()
    if payload.path is not None:
        st["path"] = payload.path.strip()
    if payload.docker_image is not None:
        st["docker_image"] = payload.docker_image.strip()
    if payload.panel_title is not None:
        st["panel_title"] = payload.panel_title.strip()
    if payload.root_uuid is not None:
        st["root_uuid"] = payload.root_uuid.strip()
    if payload.sni_list is not None:
        cleaned_snis = [s.strip() for s in payload.sni_list if s and s.strip()]
        if cleaned_snis:
            st["sni_list"] = cleaned_snis
    if payload.target_ips is not None:
        cleaned_ips = [ip.strip() for ip in payload.target_ips if ip and ip.strip()]
        if cleaned_ips:
            st["target_ips"] = cleaned_ips

    add_audit_log(db, actor.get("username"), actor.get("role"), "UPDATE_SETTINGS", "Mise à jour des paramètres serveur Cloud Run / VLESS")
    save_db(db)
    return {"status": "saved", "settings": st}


@router.post("/api/probe")
async def probe_endpoint(request: Request):
    """Réalise un vrai test TCP + TLS (SNI + ALPN http/1.1) + WebSocket Upgrade vers target_server."""
    db = load_db()
    settings = db.get("settings", DEFAULT_SETTINGS)

    body = {}
    try:
        body = await request.json()
    except Exception:
        body = {}

    host = (body.get("host") or settings.get("host", DEFAULT_SETTINGS["host"])).strip()
    target_server = (body.get("target_server") or settings.get("target_server", DEFAULT_SETTINGS["target_server"])).strip()
    sni = (body.get("sni") or settings.get("sni", DEFAULT_SETTINGS["sni"])).strip()
    raw_path = (body.get("path") or settings.get("path", DEFAULT_SETTINGS["path"])).strip()
    clean_path = raw_path if raw_path.startswith("/") else f"/{raw_path}"

    if ":" in target_server:
        server_ip, port_str = target_server.split(":", 1)
        server_port = int(port_str)
    else:
        server_ip, server_port = target_server, 443

    url = f"wss://{host}{clean_path} (via {server_ip}:{server_port} | SNI: {sni})"
    t0 = time.perf_counter()
    tcp_latency_ms = None
    tls_latency_ms = None

    try:
        # 1. TCP Handshake to target_server
        sock = socket.create_connection((server_ip, server_port), timeout=5.0)
        t_tcp = time.perf_counter()
        tcp_latency_ms = round((t_tcp - t0) * 1000, 1)

        # 2. TLS Handshake with SNI & ALPN http/1.1
        ctx = ssl.create_default_context()
        try:
            ctx.set_alpn_protocols(["http/1.1"])
        except Exception:
            pass

        with ctx.wrap_socket(sock, server_hostname=sni) as ssock:
            t_tls = time.perf_counter()
            tls_latency_ms = round((t_tls - t_tcp) * 1000, 1)
            tls_version = ssock.version()
            alpn_proto = ssock.selected_alpn_protocol() or "http/1.1"

            # 3. HTTP/1.1 WebSocket Upgrade Request
            ws_key = base64.b64encode(uuid.uuid4().bytes).decode("utf-8")
            http_req = (
                f"GET {clean_path} HTTP/1.1\r\n"
                f"Host: {host}\r\n"
                f"User-Agent: Mozilla/5.0 (Linux; Android 14) Chrome/124.0.0.0 Mobile\r\n"
                f"Upgrade: websocket\r\n"
                f"Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {ws_key}\r\n"
                f"Sec-WebSocket-Version: 13\r\n\r\n"
            )
            ssock.sendall(http_req.encode("utf-8"))
            raw_resp = ssock.recv(2048).decode("utf-8", errors="ignore")

        total_latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        lines = raw_resp.split("\r\n")
        status_line = lines[0] if lines else "HTTP/1.1 200 OK"
        status_code = 200
        parts = status_line.split(" ")
        if len(parts) >= 2 and parts[1].isdigit():
            status_code = int(parts[1])

        resp_headers = {}
        for line in lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                resp_headers[k.strip().lower()] = v.strip()

        is_ok = status_code in (101, 200, 400, 426)
        return {
            "success": is_ok,
            "url": url,
            "host": host,
            "target_server": target_server,
            "sni": sni,
            "status_code": status_code,
            "status_line": status_line,
            "tcp_latency_ms": tcp_latency_ms,
            "tls_latency_ms": tls_latency_ms,
            "latency_ms": total_latency_ms,
            "tls_version": tls_version,
            "alpn": alpn_proto,
            "server": resp_headers.get("server", "Google Frontend (GFE)"),
            "preview": status_line,
            "message": (
                f"Sonde réussie en {total_latency_ms} ms (TCP: {tcp_latency_ms} ms, TLS: {tls_latency_ms} ms) — {status_line}"
                if is_ok else f"Réponse HTTP inattendue ({status_code}) en {total_latency_ms} ms : {status_line}"
            )
        }
    except Exception as e:
        total_latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        return {
            "success": False,
            "url": url,
            "host": host,
            "target_server": target_server,
            "sni": sni,
            "status_code": 502,
            "tcp_latency_ms": tcp_latency_ms,
            "tls_latency_ms": tls_latency_ms,
            "latency_ms": total_latency_ms,
            "error": str(e),
            "message": f"Échec de sonde ({total_latency_ms} ms) : {str(e)}"
        }


@router.get("/sub/{token}")
async def get_subscription(token: str, request: Request):
    """Portail d'abonnement universel :
    - Navigateur web : rend templates/sub.html (Portail Client interactif)
    - Application VPN (ou ?raw=1) : renvoie toutes les variantes VLESS en Base64 avec headers Marzban/Remnawave
    """
    db = load_db()
    settings = db.get("settings", DEFAULT_SETTINGS)
    clean_tok = token.strip()

    matched_user = None
    for u in db.get("users", []):
        if (
            (u.get("token") or "").upper() == clean_tok.upper()
            or (u.get("uuid") or "").lower() == clean_tok.lower()
            or u.get("id") == clean_tok
        ):
            matched_user = compute_user_status(u, db)
            break

    if not matched_user:
        raise HTTPException(status_code=404, detail="Abonnement introuvable.")

    accept_hdr = request.headers.get("accept", "").lower()
    ua_hdr = request.headers.get("user-agent", "").lower()
    vpn_keywords = (
        "v2ray", "xray", "clash", "hiddify", "sing-box", "singbox",
        "streisand", "shadowrocket", "v2box", "nekobox", "nekoray",
        "darktunnel", "httpcustom", "matsuri", "karing", "flclash",
        "curl", "wget", "python", "okhttp", "go-http-client"
    )
    is_browser = (
        "text/html" in accept_hdr
        and "mozilla" in ua_hdr
        and not any(k in ua_hdr for k in vpn_keywords)
        and request.query_params.get("raw") != "1"
    )

    variants = generate_user_vless_variants(matched_user["uuid"], matched_user["name"], settings)

    if is_browser:
        sub_template_path = os.path.join(TEMPLATES_DIR, "sub.html")
        if os.path.exists(sub_template_path):
            with open(sub_template_path, "r", encoding="utf-8") as f:
                html = f.read()

            # Enrich variants with QR codes for browser portal
            browser_variants = []
            for v in variants:
                browser_variants.append({
                    **v,
                    "qr_code": generate_qr_base64(v["uri"])
                })

            # Find support contact (Reseller or Default Admin)
            support_phone = "+237690123456"
            if matched_user.get("reseller_id"):
                res_obj = next((r for r in db.get("resellers", []) if r.get("id") == matched_user.get("reseller_id")), None)
                if res_obj and res_obj.get("contact_phone"):
                    support_phone = res_obj.get("contact_phone")

            u_tok = matched_user.get("token") or matched_user["uuid"]
            sub_data = {
                "user": matched_user,
                "variants": browser_variants,
                "sub_path": f"/nexus/sub/{u_tok}",
                "support_phone": support_phone
            }

            primary_uri = browser_variants[0]["uri"] if browser_variants else ""
            primary_qr = browser_variants[0]["qr_code"] if browser_variants else ""

            html = html.replace("{{USER_NAME}}", matched_user.get("name", "Client Nexus"))
            html = html.replace("{{USER_TOKEN}}", u_tok)
            html = html.replace("{{PANEL_TITLE}}", settings.get("panel_title", "Nexus Tunnel"))
            html = html.replace("{{VLESS_URI}}", primary_uri)
            html = html.replace("{{QR_CODE}}", primary_qr)
            html = html.replace("{{SUB_DATA_JSON}}", json.dumps(sub_data, ensure_ascii=False))
            return HTMLResponse(content=html)

    # Raw VPN App Subscription Response
    if not matched_user["is_valid"]:
        raise HTTPException(status_code=403, detail="Compte inactif, expiré ou quota dépassé.")

    raw_uris = "\n".join(v["uri"] for v in variants)
    b64_sub = base64.b64encode(raw_uris.encode("utf-8")).decode("utf-8")

    used_up = matched_user.get("used_bytes_up", 0)
    used_down = matched_user.get("used_bytes_down", 0)
    total_quota = matched_user.get("quota_bytes", 0)
    exp_ts = 0
    if matched_user.get("expires_at"):
        try:
            dt = datetime.fromisoformat(str(matched_user["expires_at"]).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            exp_ts = int(dt.timestamp())
        except Exception:
            pass

    title_b64 = base64.b64encode(f"Nexus Tunnel - {matched_user['name']}".encode("utf-8")).decode("utf-8")
    headers = {
        "Subscription-Userinfo": f"upload={used_up}; download={used_down}; total={total_quota}; expire={exp_ts}",
        "Profile-Update-Interval": "12",
        "Profile-Title": f"base64:{title_b64}",
        "Content-Disposition": f'inline; filename="{matched_user["name"]}.txt"'
    }
    return Response(content=b64_sub, media_type="text/plain; charset=utf-8", headers=headers)


@router.get("/api/uuid/generate")
async def generate_random_uuid():
    return {"uuid": str(uuid.uuid4())}


# ==================== AUTHENTICATION & SESSIONS ====================

def _check_login_rate_limit(client_ip: str):
    now = time.time()
    with _LOGIN_LOCK:
        attempts = [t for t in _LOGIN_FAILURES.get(client_ip, []) if now - t < 300]
        _LOGIN_FAILURES[client_ip] = attempts
        if len(attempts) >= 10:
            raise HTTPException(
                status_code=429,
                detail="Trop de tentatives de connexion échouées. Veuillez patienter 5 minutes."
            )


def _record_login_failure(client_ip: str):
    now = time.time()
    with _LOGIN_LOCK:
        attempts = [t for t in _LOGIN_FAILURES.get(client_ip, []) if now - t < 300]
        attempts.append(now)
        _LOGIN_FAILURES[client_ip] = attempts


def _clear_login_failures(client_ip: str):
    with _LOGIN_LOCK:
        _LOGIN_FAILURES.pop(client_ip, None)


@router.post("/api/auth/login")
async def auth_login(payload: LoginRequest, request: Request, response: Response):
    client_ip = request.client.host if request.client else "127.0.0.1"
    _check_login_rate_limit(client_ip)

    db = load_db()
    username = payload.username.strip().lower()
    password = payload.password.strip()

    # 1. Search in Admins
    admin = next((a for a in db.get("admins", []) if (a.get("username") or "").lower() == username), None)
    if admin:
        stored_hash = admin.get("password_hash", "")
        if not verify_password(password, stored_hash):
            _record_login_failure(client_ip)
            raise HTTPException(status_code=401, detail="Mot de passe administrateur incorrect.")
        if not admin.get("is_active", True):
            raise HTTPException(status_code=403, detail="Ce compte a été suspendu.")

        _clear_login_failures(client_ip)
        # Auto-migrate legacy SHA-256 hash to PBKDF2-HMAC-SHA256
        if not stored_hash.startswith("pbkdf2_sha256$"):
            admin["password_hash"] = hash_password(password)

        role = admin.get("role", "ADMIN")
        token = generate_session_token(admin["id"], role)
        admin["last_login_at"] = datetime.now(timezone.utc).isoformat()
        add_audit_log(db, admin["username"], role, "LOGIN", f"Connexion réussie de l'administrateur {admin.get('display_name')}")
        save_db(db)
        response.set_cookie(key="nexus_token", value=token, max_age=86400, httponly=False)
        return {
            "status": "success",
            "token": token,
            "user": sanitize_account({**admin, "role": role})
        }

    # 2. Search in Resellers
    reseller = next((r for r in db.get("resellers", []) if (r.get("username") or "").lower() == username), None)
    if reseller:
        stored_hash = reseller.get("password_hash", "")
        if not verify_password(password, stored_hash):
            _record_login_failure(client_ip)
            raise HTTPException(status_code=401, detail="Mot de passe revendeur incorrect.")
        if not reseller.get("is_active", True):
            raise HTTPException(status_code=403, detail="Ce compte a été suspendu.")

        _clear_login_failures(client_ip)
        if not stored_hash.startswith("pbkdf2_sha256$"):
            reseller["password_hash"] = hash_password(password)

        token = generate_session_token(reseller["id"], "RESELLER")
        reseller["last_login_at"] = datetime.now(timezone.utc).isoformat()
        add_audit_log(db, reseller["username"], "RESELLER", "LOGIN", f"Connexion réussie du revendeur {reseller.get('display_name')}")
        save_db(db)
        response.set_cookie(key="nexus_token", value=token, max_age=86400, httponly=False)
        return {
            "status": "success",
            "token": token,
            "user": sanitize_account({**reseller, "role": "RESELLER"})
        }

    _record_login_failure(client_ip)
    raise HTTPException(status_code=404, detail="Nom d'utilisateur introuvable.")


@router.get("/api/auth/me")
async def auth_get_me(request: Request):
    actor = get_current_actor(request)
    db = load_db()

    if actor.get("role") == "RESELLER":
        my_users = [u for u in db.get("users", []) if u.get("reseller_id") == actor.get("id")]
        active_cnt = sum(1 for u in my_users if compute_user_status(u, db)["is_valid"])
        actor["clients_count"] = len(my_users)
        actor["active_clients_count"] = active_cnt
        actor["used_credit_gb"] = round(sum(u.get("quota_bytes", 0) / (1024**3) for u in my_users), 2)

    return {
        "status": "authenticated",
        "user": sanitize_account(actor),
        "impersonated_by": actor.get("impersonated_by")
    }


@router.post("/api/auth/logout")
async def auth_logout(response: Response):
    response.delete_cookie(key="nexus_token")
    return {"status": "logged_out"}


@router.post("/api/auth/change-password")
async def auth_change_password(payload: ChangePasswordRequest, request: Request):
    actor = get_current_actor(request)
    db = load_db()
    u_id = actor.get("id")

    target = next((a for a in db.get("admins", []) if a.get("id") == u_id), None)
    if not target:
        target = next((r for r in db.get("resellers", []) if r.get("id") == u_id), None)

    if not target:
        raise HTTPException(status_code=404, detail="Compte introuvable.")

    if not verify_password(payload.old_password, target.get("password_hash", "")):
        raise HTTPException(status_code=400, detail="Ancien mot de passe invalide.")

    target["password_hash"] = hash_password(payload.new_password)
    add_audit_log(db, target.get("username"), target.get("role", "ADMIN"), "CHANGE_PASSWORD", "Mot de passe mis à jour avec succès.")
    save_db(db)
    return {"status": "password_changed", "message": "Mot de passe modifié avec succès."}


# ==================== GESTION DES REVENDEURS & TRANSACTIONS ====================

@router.get("/api/resellers/transactions")
async def list_reseller_transactions(request: Request, reseller_id: Optional[str] = None):
    actor = get_current_actor(request)
    db = load_db()
    txs = db.get("reseller_transactions", [])

    if actor.get("role") == "RESELLER":
        txs = [t for t in txs if t.get("reseller_id") == actor.get("id")]
    elif reseller_id:
        txs = [t for t in txs if t.get("reseller_id") == reseller_id]

    return {"transactions": txs}


@router.get("/api/resellers")
async def list_resellers(request: Request):
    actor = get_current_actor(request)
    if actor.get("role") == "RESELLER":
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs.")

    db = load_db()
    users = db.get("users", [])
    resellers = []

    for r in db.get("resellers", []):
        r_id = r.get("id")
        my_users = [u for u in users if u.get("reseller_id") == r_id]
        active_cnt = sum(1 for u in my_users if compute_user_status(u, db)["is_valid"])
        total_used_bytes = sum(int(u.get("used_bytes_up", 0) or 0) + int(u.get("used_bytes_down", 0) or 0) for u in my_users)

        resellers.append(sanitize_account({
            **r,
            "credit_gb": round(float(r.get("credit_gb", 0.0)), 2),
            "total_credit_gb": round(float(r.get("total_credit_gb", 0.0)), 2),
            "max_accounts": int(r.get("max_accounts", 100) or 100),
            "clients_count": len(my_users),
            "active_clients_count": active_cnt,
            "total_bandwidth_used": format_bytes(total_used_bytes)
        }))

    return {"resellers": resellers}


@router.post("/api/resellers")
async def create_reseller(payload: ResellerCreate, request: Request):
    actor = get_current_actor(request)
    if actor.get("role") != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Seul l'Admin Suprême peut créer des revendeurs.")

    db = load_db()
    username = payload.username.strip().lower()

    if any((r.get("username") or "").lower() == username for r in db.get("resellers", [])):
        raise HTTPException(status_code=400, detail="Ce nom d'utilisateur revendeur existe déjà.")

    reseller_id = f"res_{uuid.uuid4().hex[:8]}"
    ref_code = (payload.referral_code or payload.username).strip().upper()
    init_credit = max(0.0, float(payload.credit_gb))

    new_reseller = {
        "id": reseller_id,
        "username": username,
        "password_hash": hash_password(payload.password),
        "display_name": payload.display_name.strip(),
        "role": "RESELLER",
        "contact_phone": payload.contact_phone,
        "contact_channel": normalize_channel(payload.contact_channel),
        "telegram_username": payload.telegram_username,
        "credit_gb": init_credit,
        "total_credit_gb": init_credit,
        "max_accounts": max(1, int(payload.max_accounts or 100)),
        "commission_rate": payload.commission_rate or "15%",
        "referral_code": ref_code,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_login_at": None,
        "notes": payload.notes or ""
    }

    db.setdefault("resellers", []).append(new_reseller)
    if init_credit > 0:
        record_reseller_transaction(
            db,
            new_reseller,
            "INITIAL_CREDIT",
            init_credit,
            target_id=reseller_id,
            notes=f"Dotation initiale à la création (+{init_credit} Go)"
        )
    add_audit_log(db, actor.get("username"), "SUPER_ADMIN", "CREATE_RESELLER", f"Création du revendeur {payload.display_name} avec {init_credit} Go de crédit.", reseller_id)
    save_db(db)

    return {"status": "created", "reseller": sanitize_account(new_reseller)}


@router.get("/api/resellers/{reseller_id}")
async def get_reseller_detail(reseller_id: str, request: Request):
    actor = get_current_actor(request)
    if actor.get("role") == "RESELLER" and actor.get("id") != reseller_id:
        raise HTTPException(status_code=403, detail="Accès refusé.")

    db = load_db()
    reseller = next((r for r in db.get("resellers", []) if r.get("id") == reseller_id), None)
    if not reseller:
        raise HTTPException(status_code=404, detail="Revendeur introuvable.")

    clients = [compute_user_status(u, db) for u in db.get("users", []) if u.get("reseller_id") == reseller_id]
    transactions = [t for t in db.get("reseller_transactions", []) if t.get("reseller_id") == reseller_id][:100]

    return {
        "reseller": sanitize_account(reseller),
        "clients": clients,
        "transactions": transactions
    }


@router.put("/api/resellers/{reseller_id}")
async def update_reseller(reseller_id: str, payload: ResellerUpdate, request: Request):
    actor = get_current_actor(request)
    if actor.get("role") != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Seul l'Admin Suprême peut modifier les revendeurs.")

    db = load_db()
    reseller = next((r for r in db.get("resellers", []) if r.get("id") == reseller_id), None)
    if not reseller:
        raise HTTPException(status_code=404, detail="Revendeur introuvable.")

    if payload.display_name:
        reseller["display_name"] = payload.display_name.strip()
    if payload.password:
        reseller["password_hash"] = hash_password(payload.password)
    if payload.contact_phone is not None:
        reseller["contact_phone"] = payload.contact_phone
    if payload.contact_channel is not None:
        reseller["contact_channel"] = normalize_channel(payload.contact_channel)
    if payload.telegram_username is not None:
        reseller["telegram_username"] = payload.telegram_username
    if payload.commission_rate is not None:
        reseller["commission_rate"] = payload.commission_rate
    if payload.max_accounts is not None:
        reseller["max_accounts"] = max(1, int(payload.max_accounts))
    if payload.credit_gb is not None:
        reseller["credit_gb"] = max(0.0, round(float(payload.credit_gb), 2))
    if payload.notes is not None:
        reseller["notes"] = payload.notes
    if payload.is_active is not None:
        reseller["is_active"] = payload.is_active

    save_db(db)
    return {"status": "updated", "reseller": sanitize_account(reseller)}


@router.post("/api/resellers/{reseller_id}/recharge")
async def recharge_reseller(reseller_id: str, payload: ResellerRecharge, request: Request):
    actor = get_current_actor(request)
    if actor.get("role") != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Seul l'Admin Suprême peut recharger les revendeurs.")

    db = load_db()
    reseller = next((r for r in db.get("resellers", []) if r.get("id") == reseller_id), None)
    if not reseller:
        raise HTTPException(status_code=404, detail="Revendeur introuvable.")

    add_gb = float(payload.add_credit_gb)
    reseller["credit_gb"] = max(0.0, round(reseller.get("credit_gb", 0.0) + add_gb, 2))
    if add_gb > 0:
        reseller["total_credit_gb"] = round(reseller.get("total_credit_gb", 0.0) + add_gb, 2)

    tx = record_reseller_transaction(
        db,
        reseller,
        "RECHARGE",
        add_gb,
        target_id=reseller_id,
        notes=payload.notes or f"Recharge de +{add_gb} Go par {actor.get('display_name')}"
    )
    add_audit_log(
        db,
        actor.get("username"),
        "SUPER_ADMIN",
        "RECHARGE_RESELLER",
        f"Recharge de {add_gb:+} Go pour le revendeur {reseller['display_name']}. Nouveau solde: {reseller['credit_gb']} Go.",
        reseller_id
    )
    save_db(db)

    return {"status": "recharged", "new_credit_gb": reseller["credit_gb"], "transaction": tx}


@router.post("/api/resellers/{reseller_id}/impersonate")
async def impersonate_reseller(reseller_id: str, request: Request, response: Response):
    actor = get_current_actor(request)
    if actor.get("role") != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Seul l'Admin Suprême peut incarner un revendeur.")

    db = load_db()
    reseller = next((r for r in db.get("resellers", []) if r.get("id") == reseller_id), None)
    if not reseller:
        raise HTTPException(status_code=404, detail="Revendeur introuvable.")

    token = generate_session_token(reseller["id"], "RESELLER", impersonated_by=actor.get("username"))
    add_audit_log(
        db,
        actor.get("username"),
        "SUPER_ADMIN",
        "IMPERSONATE_RESELLER",
        f"Prise de contrôle (Impersonation) du compte revendeur {reseller.get('display_name')} ({reseller.get('username')})",
        reseller_id
    )
    save_db(db)
    response.set_cookie(key="nexus_token", value=token, max_age=86400, httponly=False)

    return {
        "status": "ok",
        "token": token,
        "user": sanitize_account({**reseller, "role": "RESELLER"}),
        "impersonated_by": actor.get("username")
    }


@router.post("/api/resellers/{reseller_id}/toggle")
async def toggle_reseller(reseller_id: str, request: Request):
    actor = get_current_actor(request)
    if actor.get("role") != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Seul l'Admin Suprême peut suspendre/activer un revendeur.")

    db = load_db()
    reseller = next((r for r in db.get("resellers", []) if r.get("id") == reseller_id), None)
    if not reseller:
        raise HTTPException(status_code=404, detail="Revendeur introuvable.")

    reseller["is_active"] = not reseller.get("is_active", True)
    save_db(db)
    return {"status": "toggled", "is_active": reseller["is_active"]}


@router.delete("/api/resellers/{reseller_id}")
async def delete_reseller(reseller_id: str, request: Request):
    actor = get_current_actor(request)
    if actor.get("role") != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Seul l'Admin Suprême peut supprimer des revendeurs.")

    db = load_db()
    resellers = db.get("resellers", [])
    new_resellers = [r for r in resellers if r.get("id") != reseller_id]
    if len(new_resellers) == len(resellers):
        raise HTTPException(status_code=404, detail="Revendeur introuvable.")

    db["resellers"] = new_resellers
    for u in db.get("users", []):
        if u.get("reseller_id") == reseller_id:
            u["reseller_id"] = None
            u["notes"] = (u.get("notes", "") + " [Revendeur dissous]").strip()

    add_audit_log(db, actor.get("username"), "SUPER_ADMIN", "DELETE_RESELLER", f"Suppression du revendeur {reseller_id}.", reseller_id)
    save_db(db)
    return {"status": "deleted", "id": reseller_id}


# ==================== GESTION DES ADMINS (SUPER ADMIN) ====================

@router.get("/api/admins")
async def list_admins(request: Request):
    actor = get_current_actor(request)
    if actor.get("role") != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Accès réservé à l'Admin Suprême.")

    db = load_db()
    admins = [sanitize_account(a) for a in db.get("admins", [])]
    return {"admins": admins}


@router.post("/api/admins")
async def create_admin(payload: AdminCreate, request: Request):
    actor = get_current_actor(request)
    if actor.get("role") != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Accès réservé à l'Admin Suprême.")

    db = load_db()
    username = payload.username.strip().lower()
    if any((a.get("username") or "").lower() == username for a in db.get("admins", [])):
        raise HTTPException(status_code=400, detail="Ce nom d'utilisateur admin existe déjà.")

    new_admin = {
        "id": f"adm_{uuid.uuid4().hex[:8]}",
        "username": username,
        "password_hash": hash_password(payload.password),
        "display_name": payload.display_name.strip(),
        "role": payload.role if payload.role in ["ADMIN", "SUPER_ADMIN"] else "ADMIN",
        "email": payload.email,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_login_at": None,
        "is_active": True
    }
    db.setdefault("admins", []).append(new_admin)
    add_audit_log(db, actor.get("username"), "SUPER_ADMIN", "CREATE_ADMIN", f"Création de l'administrateur {payload.display_name} ({new_admin['role']})", new_admin["id"])
    save_db(db)
    return {"status": "created", "admin": sanitize_account(new_admin)}


@router.delete("/api/admins/{admin_id}")
async def delete_admin(admin_id: str, request: Request):
    actor = get_current_actor(request)
    if actor.get("role") != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Accès réservé à l'Admin Suprême.")

    db = load_db()
    target = next((a for a in db.get("admins", []) if a.get("id") == admin_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Admin introuvable.")
    if target.get("username") == "superadmin" or admin_id == "adm_super_01":
        raise HTTPException(status_code=400, detail="Impossible de supprimer le compte Super Admin principal.")

    db["admins"] = [a for a in db.get("admins", []) if a.get("id") != admin_id]
    add_audit_log(db, actor.get("username"), "SUPER_ADMIN", "DELETE_ADMIN", f"Suppression de l'admin {target.get('display_name')}", admin_id)
    save_db(db)
    return {"status": "deleted", "id": admin_id}


# ==================== OUTILS PRO : ESSAI 24H, EXTENSION & BATCH VOUCHERS ====================

@router.post("/api/users/quick-trial")
async def create_quick_trial_account(payload: QuickTrialCreate, request: Request):
    actor = get_current_actor(request)
    db = load_db()
    settings = db.get("settings", DEFAULT_SETTINGS)

    exp_date = datetime.now(timezone.utc) + timedelta(hours=24)
    u_uuid = str(uuid.uuid4())
    slug_token = "NEXUS-TRIAL-" + uuid.uuid4().hex[:6].upper()
    user_id = f"usr_{uuid.uuid4().hex[:8]}"

    r_id = actor.get("id") if actor.get("role") == "RESELLER" else payload.reseller_id
    reseller_obj = None
    if r_id:
        reseller_obj = next((r for r in db.get("resellers", []) if r.get("id") == r_id), None)
        if reseller_obj:
            my_users_count = sum(1 for u in db.get("users", []) if u.get("reseller_id") == r_id)
            max_acc = int(reseller_obj.get("max_accounts", 100) or 100)
            if my_users_count >= max_acc:
                raise HTTPException(status_code=400, detail=f"Plafond de comptes atteint ({max_acc} comptes max).")
            if reseller_obj.get("credit_gb", 0.0) < 2.0:
                raise HTTPException(status_code=400, detail="Solde revendeur insuffisant pour offrir un compte d'essai (2 Go requis).")
            reseller_obj["credit_gb"] = round(reseller_obj["credit_gb"] - 2.0, 2)

    client_name = payload.client_name.strip() if payload.client_name else f"Essai 24h {slug_token[-4:]}"
    ch_norm = normalize_channel(payload.channel)
    new_user = {
        "id": user_id,
        "name": client_name,
        "uuid": u_uuid,
        "email": f"trial_{u_uuid[:8]}@nexustunnel",
        "token": slug_token,
        "is_enabled": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": exp_date.isoformat(),
        "on_hold": False,
        "on_hold_duration_days": 1,
        "data_reset_strategy": "no_reset",
        "quota_bytes": 2 * 1024 * 1024 * 1024,
        "used_bytes_up": 0,
        "used_bytes_down": 0,
        "max_ips": 1,
        "notes": f"Compte essai 24h gratuit ({ch_norm}: {payload.contact_phone or 'Non spécifié'})",
        "contact_detail": payload.contact_phone,
        "channel": ch_norm,
        "reseller_id": r_id,
        "last_seen_at": None,
        "active_ips": []
    }

    db.setdefault("users", []).append(new_user)
    if reseller_obj:
        record_reseller_transaction(
            db,
            reseller_obj,
            "CREATE_TRIAL",
            -2.0,
            target_id=user_id,
            notes=f"Création essai 24h {client_name} (-2.0 Go)"
        )
    add_audit_log(db, actor.get("username"), actor.get("role"), "CREATE_TRIAL", f"Création compte d'essai 24h pour {client_name}", user_id)
    save_db(db)

    vless_uri = generate_vless_uri(u_uuid, client_name, settings, variant="fast")
    qr_b64 = generate_qr_base64(vless_uri)

    target_server = settings.get("target_server", "192.179.18.100:443")
    host = settings.get("host", "nexus-tunnel-753027553589.us-east1.run.app")
    sni = settings.get("sni", "crashlyticsreports-pa.googleapis.com")
    path = settings.get("path", "/nexustunnel")
    base_url = str(request.base_url).rstrip("/")
    sub_url = f"{base_url}/nexus/sub/{slug_token}"

    whatsapp_share_text = "\n".join([
        "🛡️ *Nexus Tunnel VPN • Compte Essai 24h Activé !*",
        "",
        f"👤 *Nom* : {client_name}",
        f"🔑 *Code Token* : {slug_token}",
        "⚡ *Quota* : 2.0 Go",
        "⏳ *Validité* : 24 Heures",
        "",
        "🌐 *Portail & Configuration 1-Clic* :",
        sub_url,
        "",
        "📲 *Lien VLESS Direct* :",
        vless_uri,
        "",
        "⚙️ *Paramètres DarkTunnel* :",
        f"• Target Server : {target_server}",
        f"• UUID : {u_uuid}",
        f"• Path : {path}?ed=2048",
        f"• SNI : {sni}",
        f"• Header Host : {host}",
        "",
        "Bon surf sur Nexus Tunnel !"
    ])

    return {
        "status": "created",
        "user": compute_user_status(new_user, db),
        "vless_uri": vless_uri,
        "sub_url": sub_url,
        "qr_code": qr_b64,
        "whatsapp_share_text": whatsapp_share_text,
        "whatsapp_text": whatsapp_share_text
    }


@router.post("/api/users/{user_id}/extend")
async def extend_user_plan(user_id: str, payload: UserExtendPlan, request: Request):
    actor = get_current_actor(request)
    db = load_db()
    user = next((u for u in db.get("users", []) if u.get("id") == user_id or u.get("uuid") == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    if actor.get("role") == "RESELLER" and user.get("reseller_id") != actor.get("id"):
        raise HTTPException(status_code=403, detail="Vous ne pouvez prolonger que vos propres clients.")

    if payload.add_gb < 0 or payload.add_days < 0:
        raise HTTPException(status_code=400, detail="Les valeurs d'extension ne peuvent pas être négatives.")

    add_gb = float(payload.add_gb)
    add_bytes = int(add_gb * (1024**3))
    add_days = int(payload.add_days)

    r_id = actor.get("id") if actor.get("role") == "RESELLER" else user.get("reseller_id")
    if r_id and add_gb > 0:
        reseller = next((r for r in db.get("resellers", []) if r.get("id") == r_id), None)
        if reseller:
            if reseller.get("credit_gb", 0.0) < add_gb:
                raise HTTPException(
                    status_code=400,
                    detail=f"Solde revendeur insuffisant : {reseller.get('credit_gb')} Go disponibles, {add_gb} Go requis."
                )
            reseller["credit_gb"] = round(reseller["credit_gb"] - add_gb, 2)
            record_reseller_transaction(
                db,
                reseller,
                "EXTEND_PLAN",
                -add_gb,
                target_id=user["id"],
                notes=f"Prolongation compte {user.get('name')} (-{add_gb} Go, +{add_days}j)"
            )

    if add_bytes > 0:
        curr_quota = int(user.get("quota_bytes", 0) or 0)
        user["quota_bytes"] = curr_quota + add_bytes if curr_quota > 0 else add_bytes

    if payload.reset_traffic:
        user["used_bytes_up"] = 0
        user["used_bytes_down"] = 0

    if add_days > 0:
        now_utc = datetime.now(timezone.utc)
        curr_exp = user.get("expires_at")
        base_date = now_utc
        if curr_exp:
            try:
                parsed = datetime.fromisoformat(str(curr_exp).replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                if parsed > now_utc:
                    base_date = parsed
            except Exception:
                pass
        new_exp = base_date + timedelta(days=add_days)
        user["expires_at"] = new_exp.isoformat()
        user["on_hold"] = False

    user["is_enabled"] = True
    if payload.notes:
        user["notes"] = f"{user.get('notes', '')} | {payload.notes}".strip(" |")

    add_audit_log(db, actor.get("username"), actor.get("role"), "EXTEND_PLAN", f"Recharge +{add_gb} Go et +{add_days} jours pour {user.get('name')}", user_id)
    save_db(db)
    return {"status": "extended", "user": compute_user_status(user, db)}


@router.post("/api/vouchers/generate-batch")
async def generate_vouchers_batch(payload: VoucherBatchCreate, request: Request):
    actor = get_current_actor(request)
    db = load_db()
    count = min(max(1, payload.count), 50)
    if payload.quota_gb <= 0:
        raise HTTPException(status_code=400, detail="Le quota par voucher doit être strictement positif.")

    quota_bytes = int(payload.quota_gb * (1024**3))
    total_req_gb = round(count * payload.quota_gb, 2)

    r_id = actor.get("id") if actor.get("role") == "RESELLER" else payload.reseller_id
    if r_id:
        reseller = next((r for r in db.get("resellers", []) if r.get("id") == r_id), None)
        if not reseller:
            raise HTTPException(status_code=404, detail="Revendeur introuvable.")
        if reseller.get("credit_gb", 0.0) < total_req_gb:
            raise HTTPException(
                status_code=400,
                detail=f"Solde revendeur insuffisant : {reseller.get('credit_gb')} Go disponibles, {total_req_gb} Go requis pour générer {count} bons de {payload.quota_gb} Go."
            )
        reseller["credit_gb"] = round(reseller["credit_gb"] - total_req_gb, 2)
        record_reseller_transaction(
            db,
            reseller,
            "GENERATE_VOUCHERS_BATCH",
            -total_req_gb,
            notes=f"Lot de {count} vouchers de {payload.quota_gb} Go ({payload.plan_name})"
        )

    generated = []
    for _ in range(count):
        unique_code = f"NX-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[4:8].upper()}"
        voucher = {
            "code": unique_code,
            "plan_name": payload.plan_name,
            "quota_bytes": quota_bytes,
            "quota_gb": round(float(payload.quota_gb), 2),
            "readable_quota": format_bytes(quota_bytes),
            "validity_days": payload.validity_days,
            "max_ips": payload.max_ips,
            "is_redeemed": False,
            "is_used": False,
            "redeemed_by": None,
            "redeemed_at": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "reseller_id": r_id,
            "created_by": actor.get("username")
        }
        db.setdefault("vouchers", []).append(voucher)
        generated.append(enrich_voucher(voucher))

    add_audit_log(
        db,
        actor.get("username"),
        actor.get("role"),
        "GENERATE_VOUCHERS_BATCH",
        f"Génération en lot de {count} vouchers de {payload.quota_gb} Go ({payload.plan_name})"
    )
    save_db(db)
    return {"status": "generated", "count": count, "vouchers": generated}


# ==================== PLANS TARIFAIRES (CRUD) ====================

@router.get("/api/plans")
async def get_pricing_plans():
    db = load_db()
    return {"plans": db.get("pricing_plans", DEFAULT_PLANS)}


@router.post("/api/plans")
async def create_pricing_plan(payload: PlanCreatePayload, request: Request):
    actor = get_current_actor(request)
    if actor.get("role") != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Seul l'Admin Suprême peut créer un plan tarifaire.")

    db = load_db()
    plans = db.setdefault("pricing_plans", copy.deepcopy(DEFAULT_PLANS))
    plan_id = (payload.id or f"plan_{uuid.uuid4().hex[:6]}").strip()
    if any(p.get("id") == plan_id for p in plans):
        raise HTTPException(status_code=400, detail="Cet identifiant de plan existe déjà.")

    new_plan = {
        "id": plan_id,
        "name": payload.name.strip(),
        "quota_gb": float(payload.quota_gb),
        "duration_days": int(payload.duration_days),
        "price_cfa": int(payload.price_cfa),
        "badge": (payload.badge or "STANDARD").strip(),
        "description": payload.description or ""
    }
    plans.append(new_plan)
    add_audit_log(db, actor.get("username"), "SUPER_ADMIN", "CREATE_PLAN", f"Création du plan tarifaire {new_plan['name']} ({new_plan['price_cfa']} FCFA)", plan_id)
    save_db(db)
    return {"status": "created", "plan": new_plan}


@router.put("/api/plans/{plan_id}")
async def update_pricing_plan(plan_id: str, payload: PlanUpdatePayload, request: Request):
    actor = get_current_actor(request)
    if actor.get("role") != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Seul l'Admin Suprême peut modifier un plan tarifaire.")

    db = load_db()
    plans = db.setdefault("pricing_plans", copy.deepcopy(DEFAULT_PLANS))
    plan = next((p for p in plans if p.get("id") == plan_id), None)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan tarifaire introuvable.")

    if payload.name is not None:
        plan["name"] = payload.name.strip()
    if payload.quota_gb is not None:
        plan["quota_gb"] = float(payload.quota_gb)
    if payload.duration_days is not None:
        plan["duration_days"] = int(payload.duration_days)
    if payload.price_cfa is not None:
        plan["price_cfa"] = int(payload.price_cfa)
    if payload.badge is not None:
        plan["badge"] = payload.badge.strip()
    if payload.description is not None:
        plan["description"] = payload.description

    add_audit_log(db, actor.get("username"), "SUPER_ADMIN", "UPDATE_PLAN", f"Modification du plan tarifaire {plan['name']}", plan_id)
    save_db(db)
    return {"status": "updated", "plan": plan}


@router.delete("/api/plans/{plan_id}")
async def delete_pricing_plan(plan_id: str, request: Request):
    actor = get_current_actor(request)
    if actor.get("role") != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Seul l'Admin Suprême peut supprimer un plan tarifaire.")

    db = load_db()
    plans = db.get("pricing_plans", [])
    new_plans = [p for p in plans if p.get("id") != plan_id]
    if len(new_plans) == len(plans):
        raise HTTPException(status_code=404, detail="Plan tarifaire introuvable.")

    db["pricing_plans"] = new_plans
    add_audit_log(db, actor.get("username"), "SUPER_ADMIN", "DELETE_PLAN", f"Suppression du plan tarifaire {plan_id}", plan_id)
    save_db(db)
    return {"status": "deleted", "id": plan_id}


# ==================== AUDIT LOGS, BACKUP & DIAGNOSTICS ====================

@router.get("/api/system/audit-logs")
async def get_audit_logs(request: Request):
    actor = get_current_actor(request)
    db = load_db()
    logs = db.get("audit_logs", [])
    if actor.get("role") == "RESELLER":
        logs = [l for l in logs if l.get("actor_username") == actor.get("username")]
    return {"logs": logs[:150]}


@router.get("/api/system/backup")
async def backup_database(request: Request):
    actor = get_current_actor(request)
    if actor.get("role") != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Seul l'Admin Suprême peut télécharger une sauvegarde.")
    db = load_db()
    filename = f"nexus_backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    content = json.dumps(db, indent=2, ensure_ascii=False)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/api/system/restore")
async def restore_database(request: Request):
    actor = get_current_actor(request)
    if actor.get("role") != "SUPER_ADMIN":
        raise HTTPException(status_code=403, detail="Seul l'Admin Suprême peut restaurer une sauvegarde.")
    try:
        body = await request.json()
        if not isinstance(body, dict) or "settings" not in body or "users" not in body:
            raise HTTPException(status_code=400, detail="Format de sauvegarde JSON invalide.")
        body = migrate_and_normalize_db(body)
        add_audit_log(body, actor.get("username"), "SUPER_ADMIN", "RESTORE_DATABASE", "Restauration complète de la base de données effectuée.")
        save_db(body)
        return {"status": "restored", "message": "Base de données restaurée avec succès."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur de restauration : {str(e)}")


@router.get("/api/system/diagnostics")
async def get_system_diagnostics(request: Request):
    actor = get_current_actor(request)
    db = load_db()
    settings = db.get("settings", DEFAULT_SETTINGS)
    host = settings.get("host")
    target = settings.get("target_server")
    sni = settings.get("sni")

    probe_res = {}
    try:
        t0 = time.perf_counter()
        server_ip, port_str = target.split(":", 1) if ":" in target else (target, "443")
        with socket.create_connection((server_ip, int(port_str)), timeout=3.5) as sock:
            ctx = ssl.create_default_context()
            with ctx.wrap_socket(sock, server_hostname=sni) as ssock:
                probe_res = {
                    "online": True,
                    "tls_version": ssock.version(),
                    "latency_ms": round((time.perf_counter() - t0) * 1000, 1)
                }
    except Exception as e:
        probe_res = {"online": False, "error": str(e), "latency_ms": None}

    return {
        "server_time": datetime.now(timezone.utc).isoformat(),
        "actor": sanitize_account(actor),
        "cloud_run_probe": probe_res,
        "target_server": target,
        "host": host,
        "sni": sni,
        "total_users": len(db.get("users", [])),
        "total_devices": len(db.get("devices", [])),
        "total_resellers": len(db.get("resellers", [])),
        "total_vouchers": len(db.get("vouchers", [])),
        "total_requests": len(db.get("requests", []))
    }


# Include Router twice for direct and /nexus prefix (MUST BE AT THE END OF FILE)
app.include_router(router)
app.include_router(router, prefix="/nexus")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PANEL_PORT", 8888))
    print(f"[*] Démarrage du Nexus Tunnel Control Panel Pro v3.0 sur le port {port}...")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
