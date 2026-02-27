# Users-DB

> Minimal, secure user authentication boilerplate for quick project bootstrapping.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.1x-green.svg)](https://fastapi.tiangolo.com)
[![Uvicorn](https://img.shields.io/badge/Uvicorn-ASGI%20Server-4051b5.svg)](https://www.uvicorn.org)
[![bcrypt](https://img.shields.io/badge/bcrypt-Password%20Hashing-6a1b9a.svg)](https://pypi.org/project/bcrypt/)
[![python-dotenv](https://img.shields.io/badge/python--dotenv-Environment%20Vars-2e7d32.svg)](https://pypi.org/project/python-dotenv/)
[![python-multipart](https://img.shields.io/badge/python--multipart-Form%20Data-00897b.svg)](https://pypi.org/project/python-multipart/)
[![Jinja2](https://img.shields.io/badge/Jinja2-Templates-b71c1c.svg)](https://pypi.org/project/Jinja2/)
[![PyYAML](https://img.shields.io/badge/PyYAML-Config%20YAML-455a64.svg)](https://pypi.org/project/PyYAML/)
[![SQLite](https://img.shields.io/badge/SQLite-Database-0f80cc.svg)](https://www.sqlite.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Overview

A production-ready user management system with login, registration, and session handling. Copy it into your project and start building features instead of writing auth from scratch.

## Features

- User registration and login
- Session-based authentication
- **Secure password hashing** (bcrypt)
- **CSRF protection** (session token validation)
- **Environment-based configuration**
- SQLite database (zero configuration)
- Clean, responsive UI

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python / FastAPI |
| Database | SQLite |
| Templates | Jinja2 |
| Security | bcrypt, Session middleware, CSRF token |

## Quick Start

### 1. Install dependencies

```bash
pip install fastapi "uvicorn[standard]" bcrypt python-dotenv python-multipart jinja2 PyYAML
```

### 2. Configure environment

```bash
# Copy example and generate secure secret key
cp .env.example .env

# Generate a secure secret key (Linux/macOS)
python -c "import secrets; print('SESSION_SIGNING_KEY=' + secrets.token_hex(32))" > .env

# Or manually edit .env with your own secure key
```

### 3. Run the server

```bash
python run.py
```

Open http://127.0.0.1:5000

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SESSION_SIGNING_KEY` | Yes | - | Secure random key for sessions |

### `settings.yaml`

```yaml
APP_NAME: "Users DB"
APP_VERSION: "1.0.0"
SERVER_HOST: "127.0.0.1"
SERVER_PORT: 5000
SERVER_RELOAD: false
DATABASE_PATH: "DATA/users.db"
SESSION_COOKIE_NAME: "users_db_session"
SESSION_SAME_SITE: "lax"
SESSION_HTTPS_ONLY: false
CSRF_TOKEN_BYTES: 32
AUTH_USERNAME_MAX_LENGTH: 128
AUTH_PASSWORD_MIN_LENGTH: 8
AUTH_PASSWORD_MAX_LENGTH: 128
TEXT_ENCODING: "utf-8"
PYTHON_DISABLE_BYTECODE_CACHE: true
```

All fields above are required. The app will fail to start if any key is missing.

- `SERVER_HOST`: bind address for Uvicorn
- `SERVER_PORT`: HTTP port for Uvicorn
- `SERVER_RELOAD`: enable/disable auto-reload
- `DATABASE_PATH`: path to SQLite file
- `SESSION_COOKIE_NAME`: session cookie key
- `SESSION_SAME_SITE`: cookie SameSite policy
- `SESSION_HTTPS_ONLY`: secure cookie flag (`true` for HTTPS prod)
- `CSRF_TOKEN_BYTES`: CSRF token entropy size
- `AUTH_USERNAME_MAX_LENGTH`: max username length for auth forms
- `AUTH_PASSWORD_MIN_LENGTH`: min password length for auth forms
- `AUTH_PASSWORD_MAX_LENGTH`: max password length for auth forms
- `TEXT_ENCODING`: HTML charset and string encoding for auth processing
- `PYTHON_DISABLE_BYTECODE_CACHE`: disable `.pyc` generation (`__pycache__`)

## Project Structure

```
users-db/
├── run.py              # FastAPI application
├── settings.yaml       # App settings (server port)
├── FRONTEND/
│   ├── login.html      # Login/Register page
│   └── dashboard.html  # User dashboard
├── DATA/
│   └── users.db        # SQLite database
├── .env                # Environment variables (not in git)
├── .env.example        # Environment template
└── README.md
```

## API Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Home page (login or dashboard) |
| `/` | POST | Auth actions (`login`, `register`, `logout`) |
| `/api/auth` | POST | AJAX auth actions (`login`, `register`, `logout`) |

## Security

This boilerplate includes:

- **Password Hashing**: All passwords are hashed using bcrypt with automatic salting
- **CSRF Protection**: All forms include CSRF tokens to prevent cross-site request forgery
- **Secure Sessions**: Session cookies are signed with a cryptographically secure key
- **Environment Variables**: Sensitive configuration is kept out of source code

## Development

```bash
# Enable auto-reload in settings.yaml:
# SERVER_RELOAD: true

# Run server
python run.py
```

## License

MIT
