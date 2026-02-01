import os
from flask import Flask, request, redirect, session, render_template
from dotenv import load_dotenv
import bcrypt
from flask_wtf.csrf import CSRFProtect
import sqlite3

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')
if not app.secret_key:
    raise RuntimeError("SECRET_KEY environment variable is required")

csrf = CSRFProtect(app)

def init_db():
    conn = sqlite3.connect('users.db')
    conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)')
    conn.close()

@app.route('/')
def index():
    if 'user' in session:
        return render_template('dashboard.html', user=session['user'])
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    user = conn.execute('SELECT * FROM users WHERE username=?',
        (request.form['username'],)).fetchone()
    conn.close()
    if user and bcrypt.checkpw(
        request.form['password'].encode('utf-8'),
        user['password'].encode('utf-8')
    ):
        session['user'] = user['username']
        return redirect('/')
    return render_template('login.html', error='Invalid credentials')

@app.route('/register', methods=['POST'])
def register():
    conn = sqlite3.connect('users.db')
    try:
        password_hash = bcrypt.hashpw(
            request.form['password'].encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)',
            (request.form['username'], password_hash))
        conn.commit()
        session['user'] = request.form['username']
        conn.close()
        return redirect('/')
    except:
        conn.close()
        return render_template('login.html', error='User already exists')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

if __name__ == '__main__':
    init_db()
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode)
