# Users-DB

> Minimal, secure user authentication boilerplate for quick project bootstrapping.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-green.svg)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Overview

A production-ready user management system with login, registration, and session handling. Copy it into your project and start building features instead of writing auth from scratch.

## Features

- User registration and login
- Session-based authentication
- **Secure password hashing** (bcrypt)
- **CSRF protection** (Flask-WTF)
- **Environment-based configuration**
- SQLite database (zero configuration)
- Clean, responsive UI

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python / Flask |
| Database | SQLite |
| Templates | Jinja2 |
| Security | bcrypt, Flask-WTF |

## Quick Start

### 1. Install dependencies

```bash
pip install flask flask-wtf bcrypt python-dotenv
```

### 2. Configure environment

```bash
# Copy example and generate secure secret key
cp .env.example .env

# Generate a secure secret key (Linux/macOS)
python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))" > .env

# Or manually edit .env with your own secure key
```

### 3. Run the server

```bash
python server.py
```

Open http://localhost:5000

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | - | Secure random key for sessions |
| `FLASK_DEBUG` | No | `false` | Enable debug mode |

## Project Structure

```
users-db/
├── server.py           # Flask application
├── templates/
│   ├── login.html      # Login/Register page
│   └── dashboard.html  # User dashboard
├── .env                # Environment variables (not in git)
├── .env.example        # Environment template
└── users.db            # SQLite database (auto-created)
```

## API Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Home page (login or dashboard) |
| `/login` | POST | Authenticate user |
| `/register` | POST | Create new user |
| `/logout` | GET | End session |

## Security

This boilerplate includes:

- **Password Hashing**: All passwords are hashed using bcrypt with automatic salting
- **CSRF Protection**: All forms include CSRF tokens to prevent cross-site request forgery
- **Secure Sessions**: Session cookies are signed with a cryptographically secure key
- **Environment Variables**: Sensitive configuration is kept out of source code

## Development

```bash
# Enable debug mode
echo "FLASK_DEBUG=true" >> .env

# Run with auto-reload
python server.py
```

## License

MIT
