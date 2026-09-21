from flask import Flask, request, jsonify, render_template, redirect
import psycopg2
import psycopg2.extras
import hashlib
import secrets
import os
import pathlib
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from werkzeug.utils import secure_filename

BASE_DIR = pathlib.Path(__file__).parent


def _clean_db_url(url):
    if not url:
        return url
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    try:
        parsed = urlparse(url)
        allowed = {"sslmode", "connect_timeout", "application_name"}
        query = dict(parse_qsl(parsed.query))
        clean_query = {k: v for k, v in query.items() if k in allowed}
        cleaned = parsed._replace(query=urlencode(clean_query))
        return urlunparse(cleaned)
    except Exception:
        return url


DATABASE_URL = _clean_db_url(os.environ.get("DATABASE_URL", ""))

UPLOAD_DIR = BASE_DIR / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp"}


def allowed_file(name):
    return "." in name and name.rsplit(".", 1)[1].lower() in ALLOWED_EXT


app = Flask(__name__)


# ============ АДМИН ============
ADMIN_USERNAME = "Vladimir"
ADMIN_PASSWORD = "Nik09112013"


def ensure_admin(cur):
    """Создаёт админ-аккаунт, если его ещё нет."""
    cur.execute("SELECT id FROM users WHERE username = %s", (ADMIN_USERNAME,))
    row = cur.fetchone()
    if row:
        return
    cur.execute("""
        INSERT INTO users (username, password, nickname, role, balance)
        VALUES (%s, %s, %s, %s, %s)
    """, (ADMIN_USERNAME, hash_pw(ADMIN_PASSWORD), ADMIN_USERNAME, "Администратор", 999999))


def init_db():
    con = psycopg2.connect(DATABASE_URL)
    cur = con.cursor()

    # ---- USERS ----
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nickname TEXT,
            about TEXT,
            avatar TEXT,
            role TEXT DEFAULT 'Новичок',
            balance INTEGER DEFAULT 1000,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'users'")
    ucols = [row[0] for row in cur.fetchall()]
    if "balance" not in ucols:
        cur.execute("ALTER TABLE users ADD COLUMN balance INTEGER DEFAULT 1000")

    # ---- PRODUCTS ----
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            seller_id INTEGER NOT NULL,
            type TEXT DEFAULT 'shop',
            shop TEXT,
            item TEXT NOT NULL,
            description TEXT,
            quantity INTEGER DEFAULT 1,
            per_slot INTEGER DEFAULT 1,
            measure TEXT DEFAULT 'Штук',
            price INTEGER DEFAULT 1,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'products'")
    pcols = [row[0] for row in cur.fetchall()]
    if "per_slot" not in pcols:
        cur.execute("ALTER TABLE products ADD COLUMN per_slot INTEGER DEFAULT 1")
    if "updated_at" not in pcols:
        cur.execute("ALTER TABLE products ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

    # ---- PURCHASES ----
    cur.execute("""
        CREATE TABLE IF NOT EXISTS purchases (
            id SERIAL PRIMARY KEY,
            product_id INTEGER,
            seller_id INTEGER NOT NULL,
            buyer_id INTEGER NOT NULL,
            item TEXT NOT NULL,
            quantity INTEGER DEFAULT 1,
            per_slot INTEGER DEFAULT 1,
            measure TEXT DEFAULT 'Штук',
            total INTEGER NOT NULL,
            shop TEXT,
            map TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ---- PLOTS ----
    cur.execute("""
        CREATE TABLE IF NOT EXISTS plots (
            id SERIAL PRIMARY KEY,
            owner_id INTEGER NOT NULL,
            map TEXT,
            title TEXT NOT NULL,
            x INTEGER DEFAULT 0,
            z INTEGER DEFAULT 0,
            price INTEGER DEFAULT 1,
            status TEXT DEFAULT 'free',
            kind TEXT DEFAULT 'rent',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'plots'")
    cols = [row[0] for row in cur.fetchall()]
    if "kind" not in cols:
        cur.execute("ALTER TABLE plots ADD COLUMN kind TEXT DEFAULT 'rent'")

    # ---- PLACES ----
    cur.execute("""
        CREATE TABLE IF NOT EXISTS places (
            id SERIAL PRIMARY KEY,
            owner_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            x INTEGER DEFAULT 0,
            z INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Чистка товаров с несуществующим магазином
    cur.execute("""
        DELETE FROM products
        WHERE shop IS NULL OR shop = '' OR shop NOT IN (
            SELECT title FROM plots WHERE kind = 'shop'
        )
    """)

    # Создаём админа
    ensure_admin(cur)

    con.commit()
    cur.close()
    con.close()


def db():
    con = psycopg2.connect(DATABASE_URL)
    con.cursor_factory = psycopg2.extras.RealDictCursor
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
    cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (SESSIONS[token],))
    user = cur.fetchone()
    cur.close()
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
    return render_template("trade.html", user=current_user())


@app.route("/realty")
def realty_page():
    return render_template("realty.html", user=current_user())


@app.route("/places")
def places_page():
    return render_template("places.html", user=current_user())


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
    cur = con.cursor()
    cur.execute("SELECT id FROM users WHERE username = %s", (username,))
    exists = cur.fetchone()
    if exists:
        cur.close()
        con.close()
        return jsonify({"error": "Такой ник уже занят"}), 400

    cur.execute(
        "INSERT INTO users (username, password, nickname, balance) VALUES (%s, %s, %s, %s) RETURNING id",
        (username, hash_pw(password), username, 1000),
    )
    uid = cur.fetchone()["id"]
    con.commit()
    cur.close()
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
    cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cur.fetchone()
    cur.close()
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


# ============ ПРОФИЛЬ ============
@app.route("/api/profile", methods=["GET"])
def api_get_profile():
    u = current_user()
    if not u:
        return jsonify({"error": "Не авторизован"}), 401
    return jsonify({
        "user": {
            "id": u["id"],
            "username": u["username"],
            "nickname": u["nickname"] or u["username"],
            "about": u["about"] or "",
            "avatar": u["avatar"] or "",
            "role": u["role"],
            "balance": u.get("balance", 0),
            "created_at": u["created_at"].isoformat() if u["created_at"] else "",
        }
    })


@app.route("/api/profile", methods=["PUT"])
def api_update_profile():
    u = current_user()
    if not u:
        return jsonify({"error": "Не авторизован"}), 401
    data = request.get_json() or {}
    con = db()
    cur = con.cursor()
    cur.execute(
        "UPDATE users SET nickname = %s, about = %s, avatar = %s WHERE id = %s",
        (data.get("nickname", ""), data.get("about", ""), data.get("avatar", ""), u["id"]),
    )
    con.commit()
    cur.close()
    con.close()
    return jsonify({"success": True})


@app.route("/api/upload-avatar", methods=["POST"])
def api_upload_avatar():
    u = current_user()
    if not u:
        return jsonify({"error": "Не авторизован"}), 401
    if "file" not in request.files:
        return jsonify({"error": "Файл не передан"}), 400
    f = request.files["file"]
    if not f or not f.filename:
        return jsonify({"error": "Пустое имя файла"}), 400
    if not allowed_file(f.filename):
        return jsonify({"error": "Разрешены png, jpg, jpeg, gif, webp"}), 400

    ext = f.filename.rsplit(".", 1)[1].lower()
    filename = "avatar_" + str(u["id"]) + "_" + secrets.token_hex(6) + "." + ext
    save_path = UPLOAD_DIR / filename
    f.save(str(save_path))

    url = "/static/uploads/" + filename

    con = db()
    cur = con.cursor()
    cur.execute("UPDATE users SET avatar = %s WHERE id = %s", (url, u["id"]))
    con.commit()
    cur.close()
    con.close()
    return jsonify({"success": True, "url": url})


# ============ ТОВАРЫ ============
@app.route("/api/products", methods=["GET"])
def api_products():
    con = db()
    cur = con.cursor()
    cur.execute("""
        SELECT p.*, u.username, u.nickname, u.avatar
        FROM products p
        JOIN users u ON u.id = p.seller_id
        ORDER BY p.updated_at DESC, p.created_at DESC
    """)
    rows = cur.fetchall()
    cur.close()
    con.close()
    result = []
    for r in rows:
        d = dict(r)
        if d.get("created_at"): d["created_at"] = d["created_at"].isoformat()
        if d.get("updated_at"): d["updated_at"] = d["updated_at"].isoformat()
        result.append(d)
    return jsonify({"products": result})


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
    per_slot = int(data.get("per_slot") or 1)
    measure = data.get("measure", "Штук")
    price = int(data.get("price") or 1)

    if not item:
        return jsonify({"error": "Укажи предмет"}), 400
    if not shop:
        return jsonify({"error": "Выбери магазин"}), 400

    con = db()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO products (seller_id, type, shop, item, description, quantity, per_slot, measure, price)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (u["id"], ptype, shop, item, description, quantity, per_slot, measure, price))
    con.commit()
    cur.close()
    con.close()
    return jsonify({"success": True})


@app.route("/api/products/<int:pid>", methods=["DELETE"])
def api_delete_product(pid):
    u = current_user()
    if not u:
        return jsonify({"error": "Не авторизован"}), 401
    con = db()
    cur = con.cursor()
    cur.execute("DELETE FROM products WHERE id = %s AND seller_id = %s", (pid, u["id"]))
    con.commit()
    cur.close()
    con.close()
    return jsonify({"success": True})


# ============ ПОКУПКИ ============
@app.route("/api/purchases", methods=["GET"])
def api_purchases():
    con = db()
    cur = con.cursor()
    cur.execute("""
        SELECT pu.*,
               s.nickname AS seller_nickname, s.username AS seller_username, s.avatar AS seller_avatar,
               b.nickname AS buyer_nickname, b.username AS buyer_username, b.avatar AS buyer_avatar
        FROM purchases pu
        JOIN users s ON s.id = pu.seller_id
        JOIN users b ON b.id = pu.buyer_id
        ORDER BY pu.created_at DESC
    """)
    rows = cur.fetchall()
    cur.close()
    con.close()
    result = []
    for r in rows:
        d = dict(r)
        if d.get("created_at"):
            d["created_at"] = d["created_at"].isoformat()
        result.append(d)
    return jsonify({"purchases": result})


@app.route("/api/products/<int:pid>/buy", methods=["POST"])
def api_buy_product(pid):
    buyer = current_user()
    if not buyer:
        return jsonify({"error": "Не авторизован"}), 401

    data = request.get_json() or {}
    qty = int(data.get("quantity") or 1)
    map_name = data.get("map", "")

    if qty < 1:
        return jsonify({"error": "Количество минимум 1"}), 400

    con = db()
    cur = con.cursor()

    cur.execute("SELECT * FROM products WHERE id = %s", (pid,))
    product = cur.fetchone()
    if not product:
        cur.close()
        con.close()
        return jsonify({"error": "Товар не найден"}), 404

    if product["seller_id"] == buyer["id"]:
        cur.close()
        con.close()
        return jsonify({"error": "Нельзя купить свой товар"}), 400

    if product["quantity"] < qty:
        cur.close()
        con.close()
        return jsonify({"error": "Недостаточно товара"}), 400

    total = product["price"] * qty * (product["per_slot"] or 1)

    balance = buyer.get("balance", 0)
    if balance < total:
        cur.close()
        con.close()
        return jsonify({"error": "Недостаточно АР"}), 400

    cur.execute("UPDATE users SET balance = balance - %s WHERE id = %s", (total, buyer["id"]))
    cur.execute("UPDATE users SET balance = balance + %s WHERE id = %s", (total, product["seller_id"]))

    cur.execute("UPDATE products SET quantity = quantity - %s, updated_at = NOW() WHERE id = %s", (qty, pid))
    cur.execute("UPDATE products SET status = 'sold' WHERE id = %s AND quantity <= 0", (pid,))

    cur.execute("""
        INSERT INTO purchases (product_id, seller_id, buyer_id, item, quantity, per_slot, measure, total, shop, map)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (pid, product["seller_id"], buyer["id"], product["item"], qty,
          product["per_slot"], product["measure"], total, product["shop"], map_name))

    con.commit()
    cur.close()
    con.close()
    return jsonify({"success": True, "total": total})


# ============ УЧАСТКИ / МАГАЗИНЫ ============
@app.route("/api/plots", methods=["GET"])
def api_plots():
    con = db()
    cur = con.cursor()
    cur.execute("""
        SELECT p.*, u.username, u.nickname
        FROM plots p
        JOIN users u ON u.id = p.owner_id
        ORDER BY p.created_at DESC
    """)
    rows = cur.fetchall()
    cur.close()
    con.close()
    result = []
    for r in rows:
        d = dict(r)
        if d.get("created_at"): d["created_at"] = d["created_at"].isoformat()
        result.append(d)
    return jsonify({"plots": result})


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
    kind = data.get("kind", "rent")

    if not title:
        return jsonify({"error": "Укажи название"}), 400

    con = db()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO plots (owner_id, map, title, x, z, price, status, kind)
        VALUES (%s, %s, %s, %s, %s, %s, 'free', %s)
    """, (u["id"], map_name, title, x, z, price, kind))
    con.commit()
    cur.close()
    con.close()
    return jsonify({"success": True})


@app.route("/api/plots/<int:pid>/rent", methods=["POST"])
def api_rent_plot(pid):
    u = current_user()
    if not u:
        return jsonify({"error": "Не авторизован"}), 401
    con = db()
    cur = con.cursor()
    cur.execute("SELECT * FROM plots WHERE id = %s", (pid,))
    plot = cur.fetchone()
    if not plot:
        cur.close()
        con.close()
        return jsonify({"error": "Объект не найден"}), 404
    if plot["status"] == "rented":
        cur.close()
        con.close()
        return jsonify({"error": "Уже арендован"}), 400
    cur.execute("UPDATE plots SET status = 'rented' WHERE id = %s", (pid,))
    con.commit()
    cur.close()
    con.close()
    return jsonify({"success": True})


@app.route("/api/my-shops", methods=["GET"])
def api_my_shops():
    u = current_user()
    if not u:
        return jsonify({"error": "Не авторизован"}), 401
    con = db()
    cur = con.cursor()
    cur.execute("""
        SELECT id, title, map, x, z FROM plots
        WHERE owner_id = %s AND kind = 'shop'
        ORDER BY created_at DESC
    """, (u["id"],))
    rows = cur.fetchall()
    cur.close()
    con.close()
    return jsonify({"shops": [dict(r) for r in rows]})


# ============ ОБЩЕСТВЕННЫЕ МЕСТА ============
@app.route("/api/places", methods=["GET"])
def api_places():
    con = db()
    cur = con.cursor()
    cur.execute("""
        SELECT p.*, u.username, u.nickname, u.avatar
        FROM places p
        JOIN users u ON u.id = p.owner_id
        ORDER BY p.created_at DESC
    """)
    rows = cur.fetchall()
    cur.close()
    con.close()
    result = []
    for r in rows:
        d = dict(r)
        if d.get("created_at"):
            d["created_at"] = d["created_at"].isoformat()
        result.append(d)
    return jsonify({"places": result})


@app.route("/api/places", methods=["POST"])
def api_create_place():
    u = current_user()
    if not u:
        return jsonify({"error": "Не авторизован"}), 401

    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    x = int(data.get("x") or 0)
    z = int(data.get("z") or 0)

    if not title:
        return jsonify({"error": "Укажи название"}), 400

    con = db()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO places (owner_id, title, x, z)
        VALUES (%s, %s, %s, %s)
    """, (u["id"], title, x, z))
    con.commit()
    cur.close()
    con.close()
    return jsonify({"success": True})


@app.route("/api/places/<int:pid>", methods=["DELETE"])
def api_delete_place(pid):
    u = current_user()
    if not u:
        return jsonify({"error": "Не авторизован"}), 401
    con = db()
    cur = con.cursor()
    cur.execute("DELETE FROM places WHERE id = %s AND owner_id = %s", (pid, u["id"]))
    con.commit()
    cur.close()
    con.close()
    return jsonify({"success": True})


# ============ ДИАГНОСТИКА ============
@app.route("/api/health")
def api_health():
    info = {
        "db_url_present": bool(DATABASE_URL),
        "db_url_scheme": DATABASE_URL.split("://")[0] if DATABASE_URL else None,
        "db_url_length": len(DATABASE_URL) if DATABASE_URL else 0,
    }
    try:
        con = db()
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM users")
        row = cur.fetchone()
        info["users_count"] = row["c"] if isinstance(row, dict) else row[0]
        cur.close()
        con.close()
        info["db_status"] = "OK"
    except Exception as e:
        info["db_status"] = "ERROR"
        info["db_error"] = str(e)
    return jsonify(info)


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
