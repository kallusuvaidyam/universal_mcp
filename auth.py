import random
import time
import json
import smtplib
from pathlib import Path
from email.mime.text import MIMEText
from config import load_global_config, GLOBAL_CONFIG_DIR

# In-memory session store
_sessions: dict = {}  # token -> {email, created_at}
_pending_otps: dict = {}  # email -> {otp, created_at}

SESSION_EXPIRY_SECONDS = 7200  # 2 hours
OTP_EXPIRY_SECONDS = 300       # 5 minutes


def generate_otp() -> str:
    return str(random.randint(100000, 999999))


def send_otp(otp: str) -> str:
    cfg = load_global_config()
    email_cfg = cfg.get("email", {})

    smtp_host = email_cfg.get("smtp_host")
    from_email = email_cfg.get("from_email")
    to_email = email_cfg.get("to_email") or from_email  # allow separate recipient
    smtp_password = email_cfg.get("smtp_password")

    if smtp_host and from_email and smtp_password:
        try:
            msg = MIMEText(f"Your Universal Dev MCP OTP is: {otp}\n\nValid for 5 minutes.")
            msg["Subject"] = "Universal Dev MCP - OTP"
            msg["From"] = from_email
            msg["To"] = to_email

            with smtplib.SMTP(smtp_host, email_cfg.get("smtp_port", 587)) as server:
                server.starttls()
                server.login(from_email, smtp_password)
                server.sendmail(from_email, to_email, msg.as_string())

            return f"OTP sent to {to_email}. Check your inbox."
        except Exception as e:
            # Email failed — warn clearly and fall through to console
            print(f"\n  ⚠ Email send failed: {e}")
            print(f"  Falling back to console OTP.\n")

    # Console fallback — print OTP directly
    print(f"\n{'='*40}")
    print(f"  YOUR OTP: {otp}")
    print(f"  (Valid for 5 minutes)")
    print(f"{'='*40}\n")
    return "OTP terminal mein print hua hai. Server terminal mein dekho."


def request_otp() -> str:
    cfg = load_global_config()
    email = cfg.get("email", {}).get("from_email", "developer")
    otp = generate_otp()
    _pending_otps[email] = {"otp": otp, "created_at": time.time()}
    return send_otp(otp)


def verify_otp(code: str, developer_name: str = "") -> dict:
    cfg = load_global_config()
    email = cfg.get("email", {}).get("from_email", "developer")
    pending = _pending_otps.get(email)

    if not pending:
        # Auto-send new OTP
        msg = request_otp()
        return {"success": False, "message": f"OTP bheji gayi. {msg}"}

    if time.time() - pending["created_at"] > OTP_EXPIRY_SECONDS:
        del _pending_otps[email]
        msg = request_otp()
        return {"success": False, "message": f"OTP expire ho gayi. Nayi OTP: {msg}"}

    if pending["otp"] != str(code).strip():
        return {"success": False, "message": "Galat OTP. Dobara try karo."}

    # Valid — create session
    import secrets
    token = secrets.token_hex(16)
    dev = developer_name.strip() or email.split("@")[0]
    _sessions[token] = {"email": email, "developer_name": dev, "created_at": time.time()}
    del _pending_otps[email]

    return {"success": True, "session_token": token, "message": f"Session shuru! Naam: {dev}. Token saare tools mein pass karo."}


def is_valid_session(token: str) -> bool:
    if not token:
        return False
    session = _sessions.get(token)
    if not session:
        return False
    if time.time() - session["created_at"] > SESSION_EXPIRY_SECONDS:
        del _sessions[token]
        return False
    # Refresh on use
    session["created_at"] = time.time()
    return True


def auth_required(token: str) -> str | None:
    """Returns error string if not authenticated, None if ok."""
    cfg = load_global_config()
    if not cfg.get("require_auth", True):
        return None  # auth disabled
    if not is_valid_session(token):
        return "❌ Session invalid. Pehle verify_session tool use karo."
    return None
