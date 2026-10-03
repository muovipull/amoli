import os
import random
import sqlite3
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, jsonify, g
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'duolingo_super_secret_key_change_in_production'
DATABASE = 'duolingo.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        db.executescript('''
            DROP TABLE IF EXISTS users;
            DROP TABLE IF EXISTS sections;
            DROP TABLE IF EXISTS units;
            DROP TABLE IF EXISTS lessons;
            DROP TABLE IF EXISTS questions;
            DROP TABLE IF EXISTS follows;

            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                xp INTEGER DEFAULT 0,
                streak INTEGER DEFAULT 1,
                gems INTEGER DEFAULT 100
            );

            CREATE TABLE sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                sort_order INTEGER DEFAULT 0
            );

            CREATE TABLE units (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                sort_order INTEGER DEFAULT 0,
                FOREIGN KEY (section_id) REFERENCES sections (id)
            );

            CREATE TABLE lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unit_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                sort_order INTEGER DEFAULT 0,
                FOREIGN KEY (unit_id) REFERENCES units (id)
            );

            CREATE TABLE questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lesson_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                prompt TEXT NOT NULL,
                answer TEXT NOT NULL,
                choices TEXT,
                FOREIGN KEY (lesson_id) REFERENCES lessons (id)
            );

            CREATE TABLE follows (
                follower_id INTEGER NOT NULL,
                followed_id INTEGER NOT NULL,
                PRIMARY KEY (follower_id, followed_id),
                FOREIGN KEY (follower_id) REFERENCES users (id),
                FOREIGN KEY (followed_id) REFERENCES users (id)
            );

            INSERT INTO sections (title) VALUES ('Osa 1: Perusteet');
            INSERT INTO units (section_id, title, description) VALUES (1, 'Yksikkö 1', 'Tervehdykset ja perussanat');
            INSERT INTO lessons (unit_id, title) VALUES (1, 'Oppitunti 1: Tervehdykset');

            INSERT INTO questions (lesson_id, type, prompt, answer, choices) 
            VALUES (1, 'wordbank', 'Hei, kuinka voit?', 'Hello, how are you?', 'yes, fine, cat, dog');

            INSERT INTO questions (lesson_id, type, prompt, answer, choices) 
            VALUES (1, 'choice', 'Mitä tarkoittaa "Good morning"?', 'Hyvää huomenta', 'Hyvää iltaa,Hyvää yötä,Näkemiin');
        ''')
        db.commit()

# --- REITTISUOJAUS ---
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# --- AUTENTIKAATIO ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        
        hashed = generate_password_hash(password)
        try:
            db.execute(
                'INSERT INTO users (username, password_hash) VALUES (?, ?)',
                (username, hashed)
            )
            db.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return render_template('register.html', error="Käyttäjänimi on jo käytössä.")
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('index'))
        return render_template('login.html', error="Virheellinen käyttäjänimi tai salasana.")
        
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- PÄÄSIVUT ---
@app.route('/')
@login_required
def index():
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    sections = db.execute('SELECT * FROM sections ORDER BY sort_order ASC').fetchall()
    sections_data = []
    
    for sec in sections:
        units = db.execute('SELECT * FROM units WHERE section_id = ? ORDER BY sort_order ASC', (sec['id'],)).fetchall()
        units_data = []
        for u in units:
            lessons = db.execute('SELECT * FROM lessons WHERE unit_id = ? ORDER BY sort_order ASC', (u['id'],)).fetchall()
            units_data.append({
                'id': u['id'],
                'title': u['title'],
                'description': u['description'],
                'lessons': [dict(l) for l in lessons]
            })
        sections_data.append({
            'id': sec['id'],
            'title': sec['title'],
            'units': units_data
        })
        
    return render_template('index.html', user=dict(user), sections=sections_data)

ADMIN_PASSWORD = 'admin'

@app.route('/builder/', methods=['GET', 'POST'])
@login_required
def builder():
    # Tarkistetaan onko käyttäjä jo syöttänyt oikean admin-salasanan
    if session.get('is_admin'):
        db = get_db()
        sections = db.execute('SELECT * FROM sections ORDER BY sort_order ASC').fetchall()
        units = db.execute('SELECT * FROM units ORDER BY sort_order ASC').fetchall()
        lessons = db.execute('SELECT * FROM lessons ORDER BY sort_order ASC').fetchall()
        
        return render_template('builder.html', 
                               sections=[dict(s) for s in sections], 
                               units=[dict(u) for u in units], 
                               lessons=[dict(l) for l in lessons])

    # Jos salasana lähetetään lomakkeella
    if request.method == 'POST':
        password = request.form.get('admin_password')
        if password == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(url_for('builder'))
        else:
            return render_template('admin_login.html', error="Virheellinen järjestelmävalvojan salasana!")

    # Näytetään salasanakysely
    return render_template('admin_login.html')


@app.route('/practice')
@login_required
def practice():
    return render_template('practice.html')

@app.route('/friends')
@login_required
def friends():
    db = get_db()
    current_id = session['user_id']
    
    # Seuratut käyttäjät
    following = db.execute('''
        SELECT u.id, u.username, u.xp, u.streak 
        FROM follows f 
        JOIN users u ON f.followed_id = u.id 
        WHERE f.follower_id = ?
    ''', (current_id,)).fetchall()
    
    # Kaikki käyttäjät hakua varten
    all_users = db.execute('SELECT id, username, xp FROM users WHERE id != ?', (current_id,)).fetchall()
    
    return render_template('friends.html', 
                           following=[dict(f) for f in following], 
                           all_users=[dict(u) for u in all_users])

@app.route('/profile/<int:user_id>')
@login_required
def profile(user_id):
    db = get_db()
    target_user = db.execute('SELECT id, username, xp, streak, gems FROM users WHERE id = ?', (user_id,)).fetchone()
    current_user = db.execute('SELECT id, username, xp FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if not target_user:
        return redirect(url_for('index'))
        
    return render_template('profile.html', 
                           target_user=dict(target_user), 
                           current_user=dict(current_user))

# --- API ENDPOINTIT (AJAX-pyynnöille) ---

@app.route('/api/add_section', methods=['POST'])
@login_required
def add_section():
    title = request.json.get('title')
    db = get_db()
    db.execute('INSERT INTO sections (title) VALUES (?)', (title,))
    db.commit()
    return jsonify({'success': True})

@app.route('/api/add_unit', methods=['POST'])
@login_required
def add_unit():
    section_id = request.json.get('section_id')
    title = request.json.get('title')
    desc = request.json.get('description', '')
    db = get_db()
    db.execute('INSERT INTO units (section_id, title, description) VALUES (?, ?, ?)', (section_id, title, desc))
    db.commit()
    return jsonify({'success': True})

@app.route('/api/add_lesson', methods=['POST'])
@login_required
def add_lesson():
    unit_id = request.json.get('unit_id')
    title = request.json.get('title')
    db = get_db()
    db.execute('INSERT INTO lessons (unit_id, title) VALUES (?, ?)', (unit_id, title))
    db.commit()
    return jsonify({'success': True})

@app.route('/api/add_question', methods=['POST'])
@login_required
def add_question():
    data = request.json
    db = get_db()
    db.execute('''
        INSERT INTO questions (lesson_id, type, prompt, answer, choices)
        VALUES (?, ?, ?, ?, ?)
    ''', (data['lesson_id'], data['type'], data['prompt'], data['answer'], data.get('choices', '')))
    db.commit()
    return jsonify({'success': True})

@app.route('/api/get_lesson_questions/<int:lesson_id>')
@login_required
def get_lesson_questions(lesson_id):
    db = get_db()
    questions = db.execute('SELECT * FROM questions WHERE lesson_id = ?', (lesson_id,)).fetchall()
    q_list = [dict(q) for q in questions]
    # Sekoitetaan satunnaiseen järjestykseen
    random.shuffle(q_list)
    return jsonify(q_list)

@app.route('/api/get_random_questions')
@login_required
def get_random_questions():
    db = get_db()
    questions = db.execute('SELECT * FROM questions ORDER BY RANDOM() LIMIT 10').fetchall()
    return jsonify([dict(q) for q in questions])

@app.route('/api/complete_lesson', methods=['POST'])
@login_required
def complete_lesson():
    xp_gained = request.json.get('xp', 10)
    db = get_db()
    db.execute('UPDATE users SET xp = xp + ?, gems = gems + 5 WHERE id = ?', (xp_gained, session['user_id']))
    db.commit()
    return jsonify({'success': True})

@app.route('/api/follow/<int:target_id>', methods=['POST'])
@login_required
def follow(target_id):
    db = get_db()
    try:
        db.execute('INSERT INTO follows (follower_id, followed_id) VALUES (?, ?)', (session['user_id'], target_id))
        db.commit()
    except sqlite3.IntegrityError:
        pass
    return jsonify({'success': True})

if __name__ == '__main__':
    # Tarkistetaan onko tietokannassa jo tauluja
    if not os.path.exists(DATABASE):
        init_db()
    else:
        with app.app_context():
            db = get_db()
            table_check = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';").fetchone()
            if not table_check:
                init_db()

    app.run(debug=True, port=5000)