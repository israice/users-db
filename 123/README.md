# users-db

Minimal user authentication boilerplate for quick project bootstrapping.

## What is this?

A ready-to-use user management system with login, registration, and session handling. Copy it into your new project and start building features instead of writing auth from scratch.

## Features

- User registration and login
- Session-based authentication
- SQLite database (zero configuration)
- Clean, responsive UI

## Tech Stack

- Python / Flask
- SQLite
- Jinja2 templates

## Quick Start

```bash
# Install Flask
pip install flask

# Run the server
python server.py
```

Open http://localhost:5000

## Project Structure

```
users-db/
├── server.py           # Flask application
├── templates/
│   ├── login.html      # Login/Register page
│   └── dashboard.html  # User dashboard
└── users.db            # SQLite database (auto-created)
```

## API Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Home page (login or dashboard) |
| `/login` | POST | Authenticate user |
| `/register` | POST | Create new user |
| `/logout` | GET | End session |

## Usage

This is a starting point for development. For production use, you should:

- Change `app.secret_key` to a secure random value
- Add password hashing (e.g., bcrypt)
- Add CSRF protection
- Use environment variables for configuration

## License

MIT
