from flask import Flask, request, jsonify, render_template, redirect
import sqlite3
import hashlib
import secrets
import os
import pathlib
from werkzeug.utils import secure_filename

BASE_DIR = pathlib.Path(__file__).parent
DB = BASE_DIR / "sugrob.db"

app = Flask(__name__)


def init_db():
    con = sqlite3.connect(DB)
    con.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nickname TEXT,
            about TEXT,
            avatar TEXT,
            role TEXT DEFAULT 'Новичок',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER NOT NULL,
            type TEXT DEFAULT 'shop',
            shop TEXT,
            item TEXT NOT NULL,
            description TEXT,
            quantity INTEGER DEFAULT 1,
            measure TEXT DEFAULT 'Штук',
            price INTEGER DEFAULT 1,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS plots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            map TEXT,
            title TEXT NOT NULL,
            x INTEGER DEFAULT 0,
            z INTEGER DEFAULT 0,
            price INTEGER DEFAULT 1,
            status TEXT DEFAULT 'free',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    con.commit()
    con.close()


def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


SESSIONS = {}


def make_token(uid):
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


@app.route("/profile")
def profile_page():
    if not current_user():
        return redirect("/")
    return render_template("profile.html")


@app.route("/trade")
def trade_page():
    u = current_user()
    return render_template("trade.html", user=u)


@app.route("/realty")
def realty_page():
    u = current_user()
    return render_template("realty.html", user=u)


# ============ АВТОРИЗАЦИЯ ============
@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "Заполни все поля"}), 400
    if len(password) < 6:
        return jsonify({"error": "Пароль минимум 6 символов"}), 400

    con = db()
    exists = con.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if exists:
        con.close()
        return jsonify({"error": "Такой ник уже занят"}), 400

    cur = con.execute(
        "INSERT INTO users (username, password, nickname) VALUES (?, ?, ?)",
        (username, hash_pw(password), username),
    )
    con.commit()
    uid = cur.lastrowid
    con.close()

    token = make_token(uid)
    res = jsonify({"success": True})
    res.set_cookie("token", token, httponly=True, samesite="Lax", max_age=60 * 60 * 24 * 7)
    return res


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    con = db()
    user = con.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    con.close()

    if not user or user["password"] != hash_pw(password):
        return jsonify({"error": "Неверный ник или пароль"}), 401

    token = make_token(user["id"])
    res = jsonify({"success": True})
    res.set_cookie("token", token, httponly=True, samesite="Lax", max_age=60 * 60 * 24 * 7)
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
    return jsonify({
        "user": {
            "id": u["id"], "username": u["username"],
            "nickname": u["nickname"] or u["username"],
            "about": u["about"] or "", "avatar": u["avatar"] or "",
            "role": u["role"], "created_at": u["created_at"],
        }
    })


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


# ============ ТОВАРЫ ============
@app.route("/api/products", methods=["GET"])
def api_products():
    con = db()
    rows = con.execute("""
        SELECT p.*, u.username, u.nickname, u.avatar
        FROM products p
        JOIN users u ON u.id = p.seller_id
        ORDER BY p.created_at DESC
    """).fetchall()
    con.close()
    return jsonify({"products": [dict(r) for r in rows]})


@app.route("/api/products", methods=["POST"])
def api_create_product():
    u = current_user()
    if not u:
        return jsonify({"error": "Не авторизован"}), 401

    data = request.get_json() or {}
    ptype = data.get("type", "shop")
    shop = data.get("shop", "")
    item = (data.get("item") or "").strip()
    description = data.get("description", "")
    quantity = int(data.get("quantity") or 1)
    measure = data.get("measure", "Штук")
    price = int(data.get("price") or 1)

    if not item:
        return jsonify({"error": "Укажи предмет"}), 400

    con = db()
    con.execute("""
        INSERT INTO products (seller_id, type, shop, item, description, quantity, measure, price)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (u["id"], ptype, shop, item, description, quantity, measure, price))
    con.commit()
    con.close()
    return jsonify({"success": True})


@app.route("/api/products/<int:pid>", methods=["DELETE"])
def api_delete_product(pid):
    u = current_user()
    if not u:
        return jsonify({"error": "Не авторизован"}), 401
    con = db()
    con.execute("DELETE FROM products WHERE id = ? AND seller_id = ?", (pid, u["id"]))
    con.commit()
    con.close()
    return jsonify({"success": True})


# ============ УЧАСТКИ ============
@app.route("/api/plots", methods=["GET"])
def api_plots():
    con = db()
    rows = con.execute("""
        SELECT p.*, u.username, u.nickname
        FROM plots p
        JOIN users u ON u.id = p.owner_id
        ORDER BY p.created_at DESC
    """).fetchall()
    con.close()
    return jsonify({"plots": [dict(r) for r in rows]})


@app.route("/api/plots", methods=["POST"])
def api_create_plot():
    u = current_user()
    if not u:
        return jsonify({"error": "Не авторизован"}), 401

    data = request.get_json() or {}
    map_name = data.get("map", "")
    title = (data.get("title") or "").strip()
    x = int(data.get("x") or 0)
    z = int(data.get("z") or 0)
    price = int(data.get("price") or 1)

    if not title:
        return jsonify({"error": "Укажи название"}), 400

    con = db()
    con.execute("""
        INSERT INTO plots (owner_id, map, title, x, z, price, status)
        VALUES (?, ?, ?, ?, ?, ?, 'free')
    """, (u["id"], map_name, title, x, z, price))
    con.commit()
    con.close()
    return jsonify({"success": True})


@app.route("/api/plots/<int:pid>/rent", methods=["POST"])
def api_rent_plot(pid):
    u = current_user()
    if not u:
        return jsonify({"error": "Не авторизован"}), 401
    con = db()
    plot = con.execute("SELECT * FROM plots WHERE id = ?", (pid,)).fetchone()
    if not plot:
        con.close()
        return jsonify({"error": "Участок не найден"}), 404
    if plot["status"] == "rented":
        con.close()
        return jsonify({"error": "Уже арендован"}), 400
    con.execute("UPDATE plots SET status = 'rented' WHERE id = ?", (pid,))
    con.commit()
    con.close()
    return jsonify({"success": True})


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
