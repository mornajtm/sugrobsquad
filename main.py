from flask import Flask, request, jsonify, render_template, redirect, url_for
import sqlite3, hashlib, secrets, os
from functools import wraps

app = Flask(__name__)
DB = "sugrob.db"

# ============ БАЗА ============
def init_db():
    con = sqlite3.connect(DB)
    con.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nickname TEXT,
            about TEXT,
            avatar TEXT,
            role TEXT DEFAULT 'Новичок',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    con.commit()
    con.close()

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

# ============ СЕССИИ ============
SESSIONS = {}

def make_token(uid: int) -> str:
    token = secrets.token_urlsafe(32)
    SESSIONS[token] = uid
    return token

def current_user():
    token = request.cookies.get("token")
    if not token or token not in SESSIONS:
        return None
    con = db()
    user = con.execute("SELECT * FROM users WHERE id = ?", (SESSIONS[token],)).fetchone()
    con.close()
    return user

# ============ СТРАНИЦЫ ============
@app.route("/")
def home():
    return render_template("index.html", user=current_user())

@app.route("/register")
def register_page():
    if current_user():
        return redirect("/profile")
    return render_template("register.html")

@app.route("/login")
def login_page():
    if current_user():
        return redirect("/profile")
    return render_template("login.html")

@app.route("/profile")
def profile_page():
    if not current_user():
        return redirect("/login")
    return render_template("profile.html")

# ============ API ============
@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not username or not email or not password:
        return jsonify({"error": "Заполни все поля"}), 400
    if len(password) < 6:
        return jsonify({"error": "Пароль минимум 6 символов"}), 400

    con = db()
    exists = con.execute(
        "SELECT id FROM users WHERE username = ? OR email = ?", (username, email)
    ).fetchone()
    if exists:
        con.close()
        return jsonify({"error": "Ник или email уже занят"}), 400

    cur = con.execute(
        "INSERT INTO users (username, email, password, nickname) VALUES (?, ?, ?, ?)",
        (username, email, hash_pw(password), username),
    )
    con.commit()
    uid = cur.lastrowid
    con.close()

    token = make_token(uid)
    res = jsonify({"success": True})
    res.set_cookie("token", token, httponly=True, samesite="Lax", max_age=60*60*24*7)
    return res

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    con = db()
    user = con.execute(
        "SELECT * FROM users WHERE username = ? OR email = ?", (username, username)
    ).fetchone()
    con.close()

    if not user or user["password"] != hash_pw(password):
        return jsonify({"error": "Неверный ник или пароль"}), 401

    token = make_token(user["id"])
    res = jsonify({"success": True})
    res.set_cookie("token", token, httponly=True, samesite="Lax", max_age=60*60*24*7)
    return res

@app.route("/api/logout", methods=["POST"])
def api_logout():
    token = request.cookies.get("token")
    SESSIONS.pop(token, None)
    res = jsonify({"success": True})
    res.set_cookie("token", "", max_age=0)
    return res

@app.route("/api/profile", methods=["GET"])
def api_get_profile():
    u = current_user()
    if not u:
        return jsonify({"error": "Не авторизован"}), 401
    return jsonify({"user": {
        "id": u["id"], "username": u["username"], "email": u["email"],
        "nickname": u["nickname"] or u["username"],
        "about": u["about"] or "", "avatar": u["avatar"] or "",
        "role": u["role"], "created_at": u["created_at"],
    }})

@app.route("/api/profile", methods=["PUT"])
def api_update_profile():
    u = current_user()
    if not u:
        return jsonify({"error": "Не авторизован"}), 401
    data = request.get_json() or {}
    con = db()
    con.execute(
        "UPDATE users SET nickname = ?, about = ?, avatar = ? WHERE id = ?",
        (data.get("nickname", ""), data.get("about", ""), data.get("avatar", ""), u["id"]),
    )
    con.commit()
    con.close()
    return jsonify({"success": True})

# ============ ЗАПУСК ============
init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)