# museum.py
import os
import sqlite3
from flask import Flask, render_template_string, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'school_museum_secret_key_2026'  # 📌 Замени на свой случайный ключ
app.config['UPLOAD_FOLDER'] = 'uploads'
ADMIN_USER, ADMIN_PASS = 'admin', 'school2026'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Создаём папку для фото при запуске
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ─────────── БАЗА ДАННЫХ ───────────
def get_db():
    db = sqlite3.connect('museum.db')
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS exhibits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                image_filename TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

# ─────────── ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ───────────
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def render_page(title, content_html, **kwargs):
    """Обёртка для рендера страницы с единым дизайном"""
    template = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{{ title }}</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { font-family: system-ui, -apple-system, sans-serif; background: #f5f7fa; color: #333; line-height: 1.6; }
            header { background: #2c3e50; color: white; padding: 1rem; text-align: center; }
            nav a { color: #ecf0f1; margin: 0 10px; text-decoration: none; font-weight: 500; }
            nav a:hover { text-decoration: underline; }
            main { max-width: 1100px; margin: 2rem auto; padding: 0 1rem; }
            .exhibits-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1.5rem; margin-top: 1rem; }
            .card { background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); transition: transform 0.2s; }
            .card:hover { transform: translateY(-3px); }
            .card img { width: 100%; height: 200px; object-fit: cover; }
            .card h3 { padding: 0.8rem 1rem 0; }
            .card p, .card small { padding: 0 1rem 0.8rem; }
            table { width: 100%; border-collapse: collapse; margin-top: 1rem; background: white; border-radius: 8px; overflow: hidden; }
            th, td { padding: 0.8rem; border-bottom: 1px solid #ddd; text-align: left; }
            th { background: #f8f9fa; }
            .thumb { width: 80px; height: 60px; object-fit: cover; border-radius: 4px; }
            .flashes li { padding: 0.8rem; margin-bottom: 0.5rem; border-radius: 4px; list-style: none; }
            .success { background: #d4edda; color: #155724; }
            .danger { background: #f8d7da; color: #721c24; }
            .warning { background: #fff3cd; color: #856404; }
            .btn, button, .btn-danger { display: inline-block; padding: 0.6rem 1.2rem; background: #3498db; color: white; text-decoration: none; border: none; border-radius: 4px; cursor: pointer; margin-top: 0.5rem; margin-right: 5px; }
            .btn-danger { background: #e74c3c; }
            form input, form textarea { width: 100%; padding: 0.7rem; margin: 0.5rem 0; border: 1px solid #ccc; border-radius: 4px; font-family: inherit; }
            footer { text-align: center; padding: 2rem; color: #777; font-size: 0.9rem; }
            @media (max-width: 600px) { .exhibits-grid { grid-template-columns: 1fr; } }
        </style>
    </head>
    <body>
        <header>
            <h1>🏛 Электронный музей школы</h1>
            <nav>
                <a href="/">Главная</a>
                {% if session.get('logged_in') %}
                    <a href="/admin">Панель админа</a>
                    <a href="/admin/logout">Выйти</a>
                {% else %}
                    <a href="/admin/login">Вход</a>
                {% endif %}
            </nav>
        </header>
        <main>
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    <ul class="flashes">
                        {% for category, message in messages %}
                            <li class="{{ category }}">{{ message }}</li>
                        {% endfor %}
                    </ul>
                {% endif %}
            {% endwith %}
            {{ content_html | safe }}
        </main>
        <footer>© 2026 Школьный электронный музей</footer>
    </body>
    </html>
    """
    return render_template_string(template, title=title, content_html=content_html, **kwargs)

def require_login(f):
    """Простой декоратор для защиты админки"""
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Для доступа войдите в систему', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated

# ─────────── МАРШРУТЫ ───────────
@app.route('/')
def index():
    db = get_db()
    exhibits = db.execute('SELECT * FROM exhibits ORDER BY created_at DESC').fetchall()
    db.close()
    
    if not exhibits:
        content = "<p>Экспонатов пока нет. Администратор может добавить их через панель управления.</p>"
    else:
        cards = "".join([
            f"""<div class="card">
                <img src="/uploads/{ex['image_filename']}" alt="{ex['title']}">
                <h3>{ex['title']}</h3>
                <p>{ex['description']}</p>
                <small>Добавлено: {ex['created_at']}</small>
            </div>""" for ex in exhibits
        ])
        content = f'<h2>Экспонаты</h2><div class="exhibits-grid">{cards}</div>'
        
    return render_page("Главная - Музей", content, exhibits=exhibits)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USER and password == ADMIN_PASS:
            session['logged_in'] = True
            flash('Вход выполнен успешно!', 'success')
            return redirect(url_for('admin_panel'))
        flash('Неверный логин или пароль', 'danger')
        
    content = """
    <h2>🔐 Вход в панель администратора</h2>
    <form method="POST" style="max-width: 400px; margin: 1rem auto;">
        <input type="text" name="username" placeholder="Логин" required>
        <input type="password" name="password" placeholder="Пароль" required>
        <button type="submit" style="width: 100%;">Войти</button>
    </form>
    """
    return render_page("Вход - Админка", content)

@app.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    flash('Вы вышли из панели администратора', 'info')
    return redirect(url_for('index'))

@app.route('/admin')
@require_login
def admin_panel():
    db = get_db()
    exhibits = db.execute('SELECT * FROM exhibits ORDER BY created_at DESC').fetchall()
    db.close()
    
    rows = "".join([
        f"""<tr>
            <td>{ex['id']}</td>
            <td>{ex['title']}</td>
            <td><img src="/uploads/{ex['image_filename']}" class="thumb"></td>
            <td><a href="/admin/delete/{ex['id']}" class="btn-danger" onclick="return confirm('Удалить экспонат?')">Удалить</a></td>
        </tr>""" for ex in exhibits
    ])
    
    content = f"""
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <h2>📋 Панель управления</h2>
        <a href="/admin/add" class="btn">+ Добавить экспонат</a>
    </div>
    <table>
        <tr><th>ID</th><th>Название</th><th>Фото</th><th>Действия</th></tr>
        {rows if rows else '<tr><td colspan="4" style="text-align:center">Пока нет экспонатов</td></tr>'}
    </table>
    """
    return render_page("Панель админа", content, exhibits=exhibits)

@app.route('/admin/add', methods=['GET', 'POST'])
@require_login
def add_exhibit():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        file = request.files.get('image')
        
        filename = 'default.jpg'
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
        db = get_db()
        db.execute('INSERT INTO exhibits (title, description, image_filename) VALUES (?, ?, ?)',
                   (title, description, filename))
        db.commit()
        db.close()
        flash('Экспонат успешно добавлен!', 'success')
        return redirect(url_for('admin_panel'))
        
    content = """
    <h2>➕ Добавить новый экспонат</h2>
    <form method="POST" enctype="multipart/form-data" style="max-width: 500px;">
        <input type="text" name="title" placeholder="Название экспоната" required>
        <textarea name="description" placeholder="История создания, год, автор..." rows="4" required></textarea>
        <label style="display:block; margin-top: 10px;">Фотография:</label>
        <input type="file" name="image" accept="image/*" required>
        <button type="submit" style="width: 100%;">Сохранить</button>
    </form>
    <a href="/admin" style="display:inline-block; margin-top: 1rem;">← Назад</a>
    """
    return render_page("Добавить экспонат", content)

@app.route('/admin/delete/<int:exhibit_id>')
@require_login
def delete_exhibit(exhibit_id):
    db = get_db()
    exhibit = db.execute('SELECT image_filename FROM exhibits WHERE id = ?', (exhibit_id,)).fetchone()
    if exhibit and exhibit['image_filename'] != 'default.jpg':
        img_path = os.path.join(app.config['UPLOAD_FOLDER'], exhibit['image_filename'])
        if os.path.exists(img_path):
            os.remove(img_path)
    db.execute('DELETE FROM exhibits WHERE id = ?', (exhibit_id,))
    db.commit()
    db.close()
    flash('Экспонат удалён', 'warning')
    return redirect(url_for('admin_panel'))

# Маршрут для отдачи загруженных изображений
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    print("🚀 Запуск школьного электронного музея...")
    print("🌐 Откройте в браузере: http://127.0.0.1:5000")
    print("🔑 Вход в админку: /admin/login")
    print(f"👤 Логин: {ADMIN_USER} | 🔑 Пароль: {ADMIN_PASS}")
    init_db()
    app.run(debug=True)
