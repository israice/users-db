import os
import secrets
import sqlite3
import sys
from contextlib import asynccontextmanager
from typing import Any, Dict, Tuple

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


def get_nested_setting(settings: Dict[str, Any], path: Tuple[str, ...]) -> Any:
    current_value = settings
    for key in path:
        if not isinstance(current_value, dict) or key not in current_value:
            dotted_path = ".".join(path)
            raise RuntimeError(f"Missing required setting: {dotted_path}")
        current_value = current_value[key]
    if current_value is None:
        dotted_path = ".".join(path)
        raise RuntimeError(f"Setting cannot be null: {dotted_path}")
    return current_value


SETTINGS = load_settings()
SESSION_SIGNING_KEY = os.environ.get("SESSION_SIGNING_KEY")
if not SESSION_SIGNING_KEY:
    raise RuntimeError("SESSION_SIGNING_KEY environment variable is required")

APP_NAME = str(get_nested_setting(SETTINGS, ("app", "name")))
APP_VERSION = str(get_nested_setting(SETTINGS, ("app", "version")))
SERVER_HOST = str(get_nested_setting(SETTINGS, ("server", "host")))
SERVER_PORT = int(get_nested_setting(SETTINGS, ("server", "port")))
SERVER_RELOAD = bool(get_nested_setting(SETTINGS, ("server", "reload")))
DATABASE_PATH = str(get_nested_setting(SETTINGS, ("database", "path")))
SESSION_COOKIE_NAME = str(get_nested_setting(SETTINGS, ("session", "cookie_name")))
SESSION_SAME_SITE = str(get_nested_setting(SETTINGS, ("session", "same_site")))
SESSION_HTTPS_ONLY = bool(get_nested_setting(SETTINGS, ("session", "https_only")))
CSRF_TOKEN_BYTES = int(get_nested_setting(SETTINGS, ("security", "csrf_token_bytes")))
PYTHON_DISABLE_BYTECODE_CACHE = bool(
    get_nested_setting(SETTINGS, ("python", "disable_bytecode_cache"))
)

if not APP_NAME.strip():
    raise RuntimeError("Setting cannot be empty: app.name")
if not APP_VERSION.strip():
    raise RuntimeError("Setting cannot be empty: app.version")
if not SERVER_HOST.strip():
    raise RuntimeError("Setting cannot be empty: server.host")
if not DATABASE_PATH.strip():
    raise RuntimeError("Setting cannot be empty: database.path")
if not SESSION_COOKIE_NAME.strip():
    raise RuntimeError("Setting cannot be empty: session.cookie_name")
if SESSION_SAME_SITE not in {"lax", "strict", "none"}:
    raise RuntimeError("Invalid session.same_site, expected one of: lax, strict, none")
if not (1 <= SERVER_PORT <= 65535):
    raise RuntimeError("Invalid server.port, expected integer in range 1..65535")
if CSRF_TOKEN_BYTES < 16:
    raise RuntimeError("Invalid security.csrf_token_bytes, expected integer >= 16")

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
            password.encode("utf-8"), existing_user["password"].encode("utf-8")
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
        connection = sqlite3.connect(DATABASE_PATH)
        try:
            password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
                "utf-8"
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
