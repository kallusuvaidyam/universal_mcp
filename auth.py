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
    """Send OTP via email or print to console as fallback."""
    cfg = load_global_config()
    email_cfg = cfg.get("email", {})

    if email_cfg.get("smtp_host") and email_cfg.get("from_email"):
        try:
            msg = MIMEText(f"Your Universal Dev MCP OTP is: {otp}\n\nValid for 5 minutes.")
            msg["Subject"] = "Universal Dev MCP - OTP"
            msg["From"] = email_cfg["from_email"]
            msg["To"] = email_cfg["from_email"]

            with smtplib.SMTP(email_cfg["smtp_host"], email_cfg.get("smtp_port", 587)) as server:
                server.starttls()
                server.login(email_cfg["from_email"], email_cfg["smtp_password"])
                server.sendmail(email_cfg["from_email"], email_cfg["from_email"], msg.as_string())

            return f"OTP sent to {email_cfg['from_email']}. Check your inbox."
        except Exception as e:
            pass

    # Console fallback — print OTP directly
    print(f"\n{'='*40}")
    print(f"  YOUR OTP: {otp}")
    print(f"  (Valid for 5 minutes)")
    print(f"{'='*40}\n")
    return "OTP printed in your server terminal. Check it there."


def request_otp() -> str:
    cfg = load_global_config()
    email = cfg.get("email", {}).get("from_email", "developer")
    otp = generate_otp()
    _pending_otps[email] = {"otp": otp, "created_at": time.time()}
    return send_otp(otp)


def verify_otp(code: str) -> dict:
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
    _sessions[token] = {"email": email, "created_at": time.time()}
    del _pending_otps[email]

    return {"success": True, "session_token": token, "message": "Session shuru! Token saare tools mein pass karo."}


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
    if not is_valid_session(token):
        return "❌ Session invalid. Pehle verify_session tool use karo."
    return None
