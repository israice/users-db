# Users-DB

> Minimal, secure user authentication boilerplate for quick project bootstrapping.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.1x-green.svg)](https://fastapi.tiangolo.com)
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
app:
  name: "Users DB"
  version: "1.0.0"

server:
  host: "127.0.0.1"
  port: 5000
  reload: false

database:
  path: "DATA/users.db"

session:
  cookie_name: "users_db_session"
  same_site: "lax"
  https_only: false

security:
  csrf_token_bytes: 32

python:
  disable_bytecode_cache: true
```

All fields above are required. The app will fail to start if any key is missing.

- `server.host`: bind address for Uvicorn
- `server.port`: HTTP port for Uvicorn
- `server.reload`: enable/disable auto-reload
- `database.path`: path to SQLite file
- `session.cookie_name`: session cookie key
- `session.same_site`: cookie SameSite policy
- `session.https_only`: secure cookie flag (`true` for HTTPS prod)
- `security.csrf_token_bytes`: CSRF token entropy size
- `python.disable_bytecode_cache`: disable `.pyc` generation (`__pycache__`)

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
# server.reload: true

# Run server
python run.py
```

## License

MIT
