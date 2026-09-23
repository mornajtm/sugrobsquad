from flask import Flask, request, jsonify, render_template, redirect
import psycopg2
import psycopg2.extras
import hashlib
import secrets
import os
import pathlib
import urllib.request
import urllib.parse
import time
import json as json_lib
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

# ============ АДМИНЫ ============
ADMIN_USERNAME = "Vladimir"
ADMIN_PASSWORD = "Nik09112013"
ADMIN2_USERNAME = "Wito"
ADMIN2_PASSWORD = "kvadrober"


def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


# ============ DISCORD OAUTH ============
DISCORD_CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID", "")
DISCORD_CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET", "")
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
DISCORD_GUILD_ID = os.environ.get("DISCORD_GUILD_ID", "")
DISCORD_ROLE_ID = os.environ.get("DISCORD_ROLE_ID", "")
DISCORD_REDIRECT = os.environ.get(
    "DISCORD_REDIRECT",
    "https://sugrobsquad.relaxdev.ru/auth/discord/callback"
)

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")


def send_discord(text):
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        data = json_lib.dumps({"content": text}).encode("utf-8")
        req = urllib.request.Request(
            DISCORD_WEBHOOK_URL,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print("Discord webhook error:", e)


# ============ БАЗА ============
def ensure_admin(cur):
    admins = [
        (ADMIN_USERNAME, ADMIN_PASSWORD),
        (ADMIN2_USERNAME, ADMIN2_PASSWORD),
    ]
    for username, password in admins:
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        row = cur.fetchone()
        if row:
            uid = row["id"] if isinstance(row, dict) else row[0]
            cur.execute("UPDATE users SET role = 'Администратор' WHERE id = %s", (uid,))
            continue
        cur.execute("""
            INSERT INTO users (username, password, nickname, role, balance)
            VALUES (%s, %s, %s, %s, %s)
        """, (username, hash_pw(password), username, "Администратор", 999999))


def init_db():
    con = psycopg2.connect(DATABASE_URL)
    cur = con.cursor()

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
            is_banned BOOLEAN DEFAULT FALSE,
            discord_id TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'users'")
    ucols = [row[0] for row in cur.fetchall()]
    if "balance" not in ucols:
        cur.execute("ALTER TABLE users ADD COLUMN balance INTEGER DEFAULT 1000")
    if "is_banned" not in ucols:
        cur.execute("ALTER TABLE users ADD COLUMN is_banned BOOLEAN DEFAULT FALSE")
    if "discord_id" not in ucols:
        cur.execute("ALTER TABLE users ADD COLUMN discord_id TEXT DEFAULT NULL")

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

    cur.execute("""
        DELETE FROM products
        WHERE shop IS NULL OR shop = '' OR shop NOT IN (
            SELECT title FROM plots WHERE kind = 'shop'
        )
    """)

    ensure_admin(cur)

    con.commit()
    cur.close()
    con.close()


def db():
    con = psycopg2.connect(DATABASE_URL)
    con.cursor_factory = psycopg2.extras.RealDictCursor
    return con


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


def is_admin(u):
    if not u:
        return False
    return u.get("role") == "Администратор" or u.get("username") in ("Vladimir", "Wito")


def require_admin(u):
    if not is_admin(u):
        return jsonify({"error": "Доступ только для админа"}), 403
    return None


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

@app.route("/organizations")
def organizations_page():
    return render_template("organizations.html", user=current_user())


@app.route("/docs")
def docs_page():
    return render_template("docs.html", user=current_user())

@app.route("/admin")
def admin_page():
    u = current_user()
    if not is_admin(u):
        return redirect("/")
    return render_template("admin.html", user=u)


# ============ DISCORD OAUTH (РУЧНОЙ) ============
@app.route("/auth/discord")
def auth_discord():
    if not DISCORD_CLIENT_ID:
        return "DISCORD_CLIENT_ID не задан в переменных окружения.", 500

    params = urllib.parse.urlencode({
        "client_id": DISCORD_CLIENT_ID,
        "redirect_uri": DISCORD_REDIRECT,
        "response_type": "code",
        "scope": "identify guilds.join",
    })
    return redirect(f"https://discord.com/oauth2/authorize?{params}")


@app.route("/auth/discord/callback")
def auth_discord_callback():
    import traceback

    args = dict(request.args)
    print("DISCORD CALLBACK ARGS:", args)

    if "error" in args:
        return f"<pre>Discord вернул ошибку:\n{args}</pre>", 400

    code = args.get("code")
    if not code:
        return f"<pre>Discord не вернул code.\nПришло: {args}</pre>", 400

    try:
        # === Обмен кода на токен ===
        payload = urllib.parse.urlencode({
            "client_id": DISCORD_CLIENT_ID,
            "client_secret": DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": DISCORD_REDIRECT,
        }).encode()

        req = urllib.request.Request(
            "https://discord.com/api/v10/oauth2/token",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        print("Начинаем обмен кода...")
        with urllib.request.urlopen(req, timeout=20) as resp:
            token_data = json_lib.loads(resp.read().decode())
        print("Токен получен:", list(token_data.keys()))

        access_token = token_data["access_token"]

        # === Получаем профиль Discord ===
        req2 = urllib.request.Request(
            "https://discord.com/api/v10/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        with urllib.request.urlopen(req2, timeout=20) as resp:
            identify = json_lib.loads(resp.read().decode())

        discord_id = str(identify["id"])
        discord_username = identify.get("username", "player")
        discord_avatar = identify.get("avatar")

        if discord_avatar:
            avatar_url = f"https://cdn.discordapp.com/avatars/{discord_id}/{discord_avatar}.png"
        else:
            avatar_url = "https://cdn.discordapp.com/embed/avatars/0.png"

        # === Сохраняем/обновляем пользователя ===
        con = db()
        cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE discord_id = %s", (discord_id,))
        user = cur.fetchone()

        if not user:
            username = f"dc_{discord_username}"
            cur.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cur.fetchone():
                username = f"dc_{discord_username}_{discord_id[:4]}"
            cur.execute("""
                INSERT INTO users (username, password, nickname, avatar, role, balance, discord_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (username, "discord_oauth", discord_username, avatar_url, "Новичок", 1000, discord_id))
            uid = cur.fetchone()["id"]
            con.commit()
            send_discord(f"🆕 Новый игрок вошёл через Discord: **{discord_username}**")
        else:
            uid = user["id"]

        cur.close()
        con.close()

        # === Добавляем на сервер ===
        try:
            put_req = urllib.request.Request(
                f"https://discord.com/api/v10/guilds/{DISCORD_GUILD_ID}/members/{discord_id}",
                data=json_lib.dumps({"access_token": access_token}).encode(),
                headers={
                    "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
                    "Content-Type": "application/json",
                },
                method="PUT",
            )
            urllib.request.urlopen(put_req, timeout=15)
            print("Игрок добавлен на сервер")
        except Exception as e:
            print("Guild join error:", e)

        # === Выдаём роль ===
        try:
            role_req = urllib.request.Request(
                f"https://discord.com/api/v10/guilds/{DISCORD_GUILD_ID}/members/{discord_id}/roles/{DISCORD_ROLE_ID}",
                headers={"Authorization": f"Bot {DISCORD_BOT_TOKEN}"},
                method="PUT",
            )
            urllib.request.urlopen(role_req, timeout=15)
            print("Роль выдана")
        except Exception as e:
            print("Role add error:", e)

        # === Создаём сессию ===
        token = make_token(uid)
        res = redirect("/profile")
        res.set_cookie("token", token, httponly=True, samesite="Lax", max_age=60 * 60 * 24 * 7)
        return res

    except Exception as e:
        tb = traceback.format_exc()
        print("Discord auth error:", tb)
        return f"<pre>Ошибка: {type(e).__name__}: {e}\n\n{tb}</pre>", 500


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
    if cur.fetchone():
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

    send_discord(f"🆕 Новый игрок зарегистрировался: **{username}**")

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

    if user.get("is_banned"):
        return jsonify({"error": "Аккаунт заблокирован"}), 403

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

    send_discord(f"🛒 **{u['nickname'] or u['username']}** выставил: **{item}** за **{price} AP**")

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
    if buyer.get("balance", 0) < total:
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

    send_discord(f"💰 **{buyer['nickname'] or buyer['username']}** купил **{product['item']}** за **{total} AP**")

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


# ============ АДМИНКА ============
@app.route("/api/admin/users", methods=["GET"])
def admin_users():
    u = current_user()
    err = require_admin(u)
    if err: return err

    con = db()
    cur = con.cursor()
    cur.execute("""
        SELECT id, username, nickname, avatar, role, balance, is_banned, created_at
        FROM users ORDER BY id ASC
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
    return jsonify({"users": result})


@app.route("/api/admin/users/<int:uid>/password", methods=["POST"])
def admin_change_password(uid):
    u = current_user()
    err = require_admin(u)
    if err: return err

    data = request.get_json() or {}
    new_pass = (data.get("password") or "").strip()
    if len(new_pass) < 6:
        return jsonify({"error": "Пароль минимум 6 символов"}), 400

    con = db()
    cur = con.cursor()
    cur.execute("UPDATE users SET password = %s WHERE id = %s", (hash_pw(new_pass), uid))
    con.commit()
    cur.close()
    con.close()
    return jsonify({"success": True})


@app.route("/api/admin/users/<int:uid>/ban", methods=["POST"])
def admin_ban_user(uid):
    u = current_user()
    err = require_admin(u)
    if err: return err
    if uid == u["id"]:
        return jsonify({"error": "Нельзя забанить себя"}), 400

    data = request.get_json() or {}
    ban = bool(data.get("ban"))

    con = db()
    cur = con.cursor()
    cur.execute("UPDATE users SET is_banned = %s WHERE id = %s", (ban, uid))
    con.commit()
    cur.close()
    con.close()
    return jsonify({"success": True})


@app.route("/api/admin/users/<int:uid>/balance", methods=["POST"])
def admin_change_balance(uid):
    u = current_user()
    err = require_admin(u)
    if err: return err

    data = request.get_json() or {}
    try:
        amount = int(data.get("amount") or 0)
    except:
        return jsonify({"error": "Неверная сумма"}), 400

    con = db()
    cur = con.cursor()
    cur.execute("UPDATE users SET balance = balance + %s WHERE id = %s", (amount, uid))
    con.commit()
    cur.close()
    con.close()
    return jsonify({"success": True})


@app.route("/api/admin/users/<int:uid>", methods=["DELETE"])
def admin_delete_user(uid):
    u = current_user()
    err = require_admin(u)
    if err: return err
    if uid == u["id"]:
        return jsonify({"error": "Нельзя удалить себя"}), 400

    con = db()
    cur = con.cursor()
    cur.execute("DELETE FROM users WHERE id = %s", (uid,))
    con.commit()
    cur.close()
    con.close()
    return jsonify({"success": True})


@app.route("/api/admin/products/<int:pid>", methods=["DELETE"])
def admin_delete_product(pid):
    u = current_user()
    err = require_admin(u)
    if err: return err
    con = db()
    cur = con.cursor()
    cur.execute("DELETE FROM products WHERE id = %s", (pid,))
    con.commit()
    cur.close()
    con.close()
    return jsonify({"success": True})


@app.route("/api/admin/plots/<int:pid>", methods=["DELETE"])
def admin_delete_plot(pid):
    u = current_user()
    err = require_admin(u)
    if err: return err
    con = db()
    cur = con.cursor()
    cur.execute("DELETE FROM plots WHERE id = %s", (pid,))
    con.commit()
    cur.close()
    con.close()
    return jsonify({"success": True})


@app.route("/api/admin/places/<int:pid>", methods=["DELETE"])
def admin_delete_place(pid):
    u = current_user()
    err = require_admin(u)
    if err: return err
    con = db()
    cur = con.cursor()
    cur.execute("DELETE FROM places WHERE id = %s", (pid,))
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
        "discord_client_ready": bool(DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET),
        "discord_redirect": DISCORD_REDIRECT,
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


@app.route("/api/test-discord")
def test_discord():
    start = time.time()
    try:
        req = urllib.request.Request("https://discord.com/api/v10/gateway")
        urllib.request.urlopen(req, timeout=10)
        elapsed = time.time() - start
        return jsonify({"status": "OK", "time": elapsed})
    except Exception as e:
        elapsed = time.time() - start
        return jsonify({"status": "ERROR", "error": str(e), "time": elapsed}), 500


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
