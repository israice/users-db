from flask import Flask, request, redirect, session, render_template
import sqlite3

app = Flask(__name__)
app.secret_key = 'secret'

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
    user = conn.execute('SELECT * FROM users WHERE username=? AND password=?',
        (request.form['username'], request.form['password'])).fetchone()
    conn.close()
    if user:
        session['user'] = request.form['username']
        return redirect('/')
    return render_template('login.html', error='Invalid credentials')

@app.route('/register', methods=['POST'])
def register():
    conn = sqlite3.connect('users.db')
    try:
        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)',
            (request.form['username'], request.form['password']))
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
    app.run(debug=True)
