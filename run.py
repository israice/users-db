import os
import secrets
import sqlite3
import subprocess
import sys
from codecs import lookup as lookup_codec
from contextlib import asynccontextmanager
import json
from typing import Any, Dict, Literal

import bcrypt
import uvicorn
import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

load_dotenv()

SETTINGS_PATH = "settings.yaml"


def load_settings() -> Dict[str, Any]:
    if not os.path.exists(SETTINGS_PATH):
        raise RuntimeError("settings.yaml is required")
    with open(SETTINGS_PATH, "r", encoding="utf-8") as settings_file:
        loaded_settings = yaml.safe_load(settings_file) or {}
    if not isinstance(loaded_settings, dict):
        raise RuntimeError("settings.yaml must contain a top-level mapping")
    return loaded_settings


def get_setting(settings: Dict[str, Any], key: str) -> Any:
    if key not in settings:
        raise RuntimeError(f"Missing required setting: {key}")
    setting_value = settings[key]
    if setting_value is None:
        raise RuntimeError(f"Setting cannot be null: {key}")
    return setting_value


def get_bool_setting(settings: Dict[str, Any], key: str) -> bool:
    value = get_setting(settings, key)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
    raise RuntimeError(f"Invalid {key}, expected boolean")


def get_int_setting(settings: Dict[str, Any], key: str) -> int:
    value = get_setting(settings, key)
    try:
        return int(value)
    except (TypeError, ValueError):
        raise RuntimeError(f"Invalid {key}, expected integer") from None


def get_env_bool(key: str, default: bool = False) -> bool:
    raw_value = os.environ.get(key)
    if raw_value is None:
        return default
    normalized_value = raw_value.strip().lower()
    if normalized_value in {"1", "true", "yes", "on"}:
        return True
    if normalized_value in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"Invalid {key}, expected boolean-like value")


def get_required_env(key: str) -> str:
    value = os.environ.get(key)
    if value is None or not value.strip():
        raise RuntimeError(f"{key} environment variable is required")
    return value.strip()


def run_bws_command(*arguments: str, access_token: str) -> str:
    command = ["bws", *arguments]
    command_env = os.environ.copy()
    command_env["BWS_ACCESS_TOKEN"] = access_token
    try:
        completed_process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            env=command_env,
        )
    except FileNotFoundError:
        raise RuntimeError("Bitwarden CLI 'bws' is not installed or not available in PATH") from None
    if completed_process.returncode != 0:
        error_output = (completed_process.stderr or completed_process.stdout or "").strip()
        raise RuntimeError(f"Bitwarden CLI command failed ({' '.join(command)}): {error_output}")
    return completed_process.stdout


def parse_json_payload(payload: str, context: str) -> Any:
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        raise RuntimeError(f"Unexpected JSON response from {context}") from None


def fetch_session_signing_key_from_bitwarden(
    secret_key_name: str,
    project_id: str,
    access_token: str,
    require_write: bool,
    fallback_value: str,
) -> str:
    listed_secrets_payload = run_bws_command(
        "secret", "list", project_id, "--output", "json", access_token=access_token
    )
    listed_secrets = parse_json_payload(listed_secrets_payload, "bws secret list")
    if not isinstance(listed_secrets, list):
        raise RuntimeError("Unexpected response type from 'bws secret list'")

    matched_secret = next(
        (
            item
            for item in listed_secrets
            if isinstance(item, dict) and str(item.get("key", "")) == secret_key_name
        ),
        None,
    )
    if matched_secret is None:
        if not require_write:
            raise RuntimeError(
                f"Bitwarden secret '{secret_key_name}' not found in project '{project_id}'"
            )
        value_to_write = fallback_value.strip() or secrets.token_hex(32)
        run_bws_command(
            "secret",
            "create",
            secret_key_name,
            value_to_write,
            project_id,
            "--output",
            "json",
            access_token=access_token,
        )
        return value_to_write

    secret_id = str(matched_secret.get("id", "")).strip()
    if not secret_id:
        raise RuntimeError(
            f"Bitwarden secret '{secret_key_name}' found but does not contain an id"
        )
    secret_payload = run_bws_command(
        "secret", "get", secret_id, "--output", "json", access_token=access_token
    )
    secret_details = parse_json_payload(secret_payload, "bws secret get")
    if not isinstance(secret_details, dict):
        raise RuntimeError("Unexpected response type from 'bws secret get'")
    secret_value = str(secret_details.get("value", "")).strip()
    if not secret_value:
        raise RuntimeError(f"Bitwarden secret '{secret_key_name}' has an empty value")
    return secret_value


def resolve_session_signing_key() -> str:
    fallback_session_key = os.environ.get("SESSION_SIGNING_KEY", "")
    if not get_env_bool("BITWARDEN_ENABLED", default=False):
        if not fallback_session_key.strip():
            raise RuntimeError("SESSION_SIGNING_KEY environment variable is required")
        return fallback_session_key.strip()

    provider = os.environ.get("BITWARDEN_PROVIDER", "").strip().lower()
    if provider != "bws":
        raise RuntimeError("BITWARDEN_PROVIDER must be set to 'bws' when BITWARDEN_ENABLED=true")

    access_token = get_required_env("BWS_ACCESS_TOKEN")
    project_id = get_required_env("BWS_PROJECT_ID")
    require_write = get_env_bool("BWS_REQUIRE_WRITE", default=False)
    secret_key_name = (
        os.environ.get("BWS_SESSION_SIGNING_KEY")
        or os.environ.get("BMS_SESSION_SIGNING_KEY")
        or "SESSION_SIGNING_KEY"
    ).strip()
    if not secret_key_name:
        raise RuntimeError("BWS_SESSION_SIGNING_KEY must not be empty")
    return fetch_session_signing_key_from_bitwarden(
        secret_key_name=secret_key_name,
        project_id=project_id,
        access_token=access_token,
        require_write=require_write,
        fallback_value=fallback_session_key,
    )


def get_same_site_setting(
    settings: Dict[str, Any], key: str
) -> Literal["lax", "strict", "none"]:
    value = str(get_setting(settings, key)).strip().lower()
    if value == "lax":
        return "lax"
    if value == "strict":
        return "strict"
    if value == "none":
        return "none"
    raise RuntimeError(f"Invalid {key}, expected one of: lax, strict, none")


SETTINGS = load_settings()
SESSION_SIGNING_KEY = resolve_session_signing_key()

APP_NAME = str(get_setting(SETTINGS, "APP_NAME"))
APP_VERSION = str(get_setting(SETTINGS, "APP_VERSION"))
SERVER_HOST = str(get_setting(SETTINGS, "SERVER_HOST"))
SERVER_PORT = get_int_setting(SETTINGS, "SERVER_PORT")
SERVER_RELOAD = get_bool_setting(SETTINGS, "SERVER_RELOAD")
DATABASE_PATH = str(get_setting(SETTINGS, "DATABASE_PATH"))
SESSION_COOKIE_NAME = str(get_setting(SETTINGS, "SESSION_COOKIE_NAME"))
SESSION_SAME_SITE = get_same_site_setting(SETTINGS, "SESSION_SAME_SITE")
SESSION_HTTPS_ONLY = get_bool_setting(SETTINGS, "SESSION_HTTPS_ONLY")
CSRF_TOKEN_BYTES = get_int_setting(SETTINGS, "CSRF_TOKEN_BYTES")
PYTHON_DISABLE_BYTECODE_CACHE = get_bool_setting(SETTINGS, "PYTHON_DISABLE_BYTECODE_CACHE")
AUTH_USERNAME_MAX_LENGTH = get_int_setting(SETTINGS, "AUTH_USERNAME_MAX_LENGTH")
AUTH_PASSWORD_MIN_LENGTH = get_int_setting(SETTINGS, "AUTH_PASSWORD_MIN_LENGTH")
AUTH_PASSWORD_MAX_LENGTH = get_int_setting(SETTINGS, "AUTH_PASSWORD_MAX_LENGTH")
TEXT_ENCODING = str(get_setting(SETTINGS, "TEXT_ENCODING")).strip()

if not APP_NAME.strip():
    raise RuntimeError("Setting cannot be empty: APP_NAME")
if not APP_VERSION.strip():
    raise RuntimeError("Setting cannot be empty: APP_VERSION")
if not SERVER_HOST.strip():
    raise RuntimeError("Setting cannot be empty: SERVER_HOST")
if not DATABASE_PATH.strip():
    raise RuntimeError("Setting cannot be empty: DATABASE_PATH")
if not SESSION_COOKIE_NAME.strip():
    raise RuntimeError("Setting cannot be empty: SESSION_COOKIE_NAME")
if not (1 <= SERVER_PORT <= 65535):
    raise RuntimeError("Invalid SERVER_PORT, expected integer in range 1..65535")
if CSRF_TOKEN_BYTES < 16:
    raise RuntimeError("Invalid CSRF_TOKEN_BYTES, expected integer >= 16")
if AUTH_USERNAME_MAX_LENGTH < 1:
    raise RuntimeError("Invalid AUTH_USERNAME_MAX_LENGTH, expected integer >= 1")
if AUTH_PASSWORD_MIN_LENGTH < 1:
    raise RuntimeError("Invalid AUTH_PASSWORD_MIN_LENGTH, expected integer >= 1")
if AUTH_PASSWORD_MAX_LENGTH < AUTH_PASSWORD_MIN_LENGTH:
    raise RuntimeError(
        "Invalid AUTH_PASSWORD_MAX_LENGTH, expected integer >= AUTH_PASSWORD_MIN_LENGTH"
    )
if not TEXT_ENCODING:
    raise RuntimeError("Setting cannot be empty: TEXT_ENCODING")
try:
    lookup_codec(TEXT_ENCODING)
except LookupError:
    raise RuntimeError("Invalid TEXT_ENCODING, expected a valid Python codec name") from None

if PYTHON_DISABLE_BYTECODE_CACHE:
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.dont_write_bytecode = True

def initialize_database() -> None:
    database_directory = os.path.dirname(DATABASE_PATH)
    if database_directory:
        os.makedirs(database_directory, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute(
        "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)"
    )
    connection.close()


class Always200StaticFiles(StaticFiles):
    def is_not_modified(self, response_headers, request_headers) -> bool:
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SIGNING_KEY,
    session_cookie=SESSION_COOKIE_NAME,
    same_site=SESSION_SAME_SITE,
    https_only=SESSION_HTTPS_ONLY,
)
templates = Jinja2Templates(directory="FRONTEND")
app.mount("/assets", Always200StaticFiles(directory="FRONTEND"), name="assets")
SESSION_USER_KEY = "user"
SESSION_CSRF_TOKEN_KEY = "csrf_token"


def get_or_create_csrf_token(request: Request) -> str:
    csrf_token_value = request.session.get(SESSION_CSRF_TOKEN_KEY)
    if not csrf_token_value:
        csrf_token_value = secrets.token_urlsafe(CSRF_TOKEN_BYTES)
        request.session[SESSION_CSRF_TOKEN_KEY] = csrf_token_value
    return csrf_token_value


def is_csrf_token_valid(request: Request, submitted_csrf_token: str) -> bool:
    session_csrf_token = request.session.get(SESSION_CSRF_TOKEN_KEY)
    return bool(
        session_csrf_token
        and submitted_csrf_token
        and session_csrf_token == submitted_csrf_token
    )


def render_login_template(
    request: Request, error_message: str | None = None, status_code: int = 200
):
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error_message": error_message,
            "csrf_token_value": get_or_create_csrf_token(request),
            "auth_username_max_length": AUTH_USERNAME_MAX_LENGTH,
            "auth_password_min_length": AUTH_PASSWORD_MIN_LENGTH,
            "auth_password_max_length": AUTH_PASSWORD_MAX_LENGTH,
            "html_charset": TEXT_ENCODING,
        },
        status_code=status_code,
    )


def render_dashboard_template(request: Request, username: str):
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": username,
            "csrf_token_value": get_or_create_csrf_token(request),
            "html_charset": TEXT_ENCODING,
        },
    )


def execute_auth_action(
    request: Request, auth_action: str, username: str, password: str, csrf_token: str
) -> dict:
    if not is_csrf_token_valid(request, csrf_token):
        return {"ok": False, "status_code": 400, "error_message": "Invalid CSRF token"}

    if auth_action == "logout":
        request.session.pop(SESSION_USER_KEY, None)
        request.session[SESSION_CSRF_TOKEN_KEY] = secrets.token_urlsafe(CSRF_TOKEN_BYTES)
        return {"ok": True, "status_code": 200, "view_name": "login"}

    if auth_action == "login":
        if not username or not password:
            return {
                "ok": False,
                "status_code": 400,
                "error_message": "Username and password are required",
            }
        connection = sqlite3.connect(DATABASE_PATH)
        connection.row_factory = sqlite3.Row
        existing_user = connection.execute(
            "SELECT * FROM users WHERE username=?",
            (username,),
        ).fetchone()
        connection.close()

        if existing_user and bcrypt.checkpw(
            password.encode(TEXT_ENCODING), existing_user["password"].encode(TEXT_ENCODING)
        ):
            request.session[SESSION_USER_KEY] = existing_user["username"]
            request.session[SESSION_CSRF_TOKEN_KEY] = secrets.token_urlsafe(
                CSRF_TOKEN_BYTES
            )
            return {
                "ok": True,
                "status_code": 200,
                "view_name": "dashboard",
                "username": existing_user["username"],
            }
        return {"ok": False, "status_code": 200, "error_message": "Invalid credentials"}

    if auth_action == "register":
        if not username or not password:
            return {
                "ok": False,
                "status_code": 400,
                "error_message": "Username and password are required",
            }
        if len(username) > AUTH_USERNAME_MAX_LENGTH:
            return {
                "ok": False,
                "status_code": 400,
                "error_message": f"Username must be at most {AUTH_USERNAME_MAX_LENGTH} characters",
            }
        if not (AUTH_PASSWORD_MIN_LENGTH <= len(password) <= AUTH_PASSWORD_MAX_LENGTH):
            return {
                "ok": False,
                "status_code": 400,
                "error_message": (
                    f"Password must be {AUTH_PASSWORD_MIN_LENGTH}-{AUTH_PASSWORD_MAX_LENGTH} characters"
                ),
            }
        connection = sqlite3.connect(DATABASE_PATH)
        try:
            password_hash = bcrypt.hashpw(password.encode(TEXT_ENCODING), bcrypt.gensalt()).decode(
                TEXT_ENCODING
            )
            connection.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password_hash),
            )
            connection.commit()
            request.session[SESSION_USER_KEY] = username
            request.session[SESSION_CSRF_TOKEN_KEY] = secrets.token_urlsafe(
                CSRF_TOKEN_BYTES
            )
            return {
                "ok": True,
                "status_code": 200,
                "view_name": "dashboard",
                "username": username,
            }
        except sqlite3.IntegrityError:
            return {"ok": False, "status_code": 200, "error_message": "User already exists"}
        finally:
            connection.close()

    return {"ok": False, "status_code": 400, "error_message": "Unsupported action"}


@app.get("/")
def render_home_page(request: Request):
    authenticated_username = request.session.get(SESSION_USER_KEY)
    if authenticated_username:
        return render_dashboard_template(request, authenticated_username)
    return render_login_template(request)


@app.post("/")
def handle_auth_action(
    request: Request,
    auth_action: str = Form(...),
    username: str = Form(""),
    password: str = Form(""),
    csrf_token: str = Form(...),
):
    action_result = execute_auth_action(request, auth_action, username, password, csrf_token)
    if not action_result["ok"]:
        return render_login_template(
            request,
            action_result["error_message"],
            status_code=action_result["status_code"],
        )
    if action_result["view_name"] == "dashboard":
        return render_dashboard_template(request, action_result["username"])
    return render_login_template(request)


@app.post("/api/auth")
def handle_auth_action_ajax(
    request: Request,
    auth_action: str = Form(...),
    username: str = Form(""),
    password: str = Form(""),
    csrf_token: str = Form(...),
):
    action_result = execute_auth_action(request, auth_action, username, password, csrf_token)
    response_payload = {
        "ok": action_result["ok"],
        "error_message": action_result.get("error_message"),
        "redirect_url": "/",
        "csrf_token_value": get_or_create_csrf_token(request),
    }
    return JSONResponse(content=response_payload, status_code=action_result["status_code"])


if __name__ == "__main__":
    uvicorn.run(
        "run:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=SERVER_RELOAD,
    )
