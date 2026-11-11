import json
import os
import atexit
import re
import socket
import ssl
import subprocess
import threading
import time
import base64
import http.client
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, jsonify, request, Response, send_from_directory
import requests
import html

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)
app.config['JSON_AS_ASCII'] = False
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 86400
app.url_map.strict_slashes = False

# WSGI Middleware для коректної обробки роутингу на Vercel (автоматично нормалізує PATH_INFO)
class PrefixMiddleware:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        # Очищаємо всі можливі артефакти роутингу Vercel (/app.py, /app, /api/index, тощо)
        prefixes = ("/app.py", "/app", "/api/index.py", "/api/index", "/api.py")
        for prefix in prefixes:
            if path == prefix:
                path = "/"
                break
            elif path.startswith(prefix + "/"):
                path = path[len(prefix):]
                break

        if not path.startswith("/"):
            path = "/" + path

        environ["PATH_INFO"] = path
        return self.wsgi_app(environ, start_response)

app.wsgi_app = PrefixMiddleware(app.wsgi_app)

# Секретний PIN адміністратора для додавання товарів
ADMIN_PIN = os.getenv("ADMIN_PIN", "7777")

# Абсолютні шляхи до файлів бази даних для надійної роботи на будь-якому хостингу
DATA_PATH = os.path.join(os.path.dirname(__file__), 'data', 'products.json')
BACKUP_PATH = os.path.join(os.path.dirname(__file__), 'data', 'orders_backup.json')

# Константи Telegram Bot API (завантажуються з env зі зрозумілими заглушками)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "9159142714:AAE2L2ZICSLX4GdXIV_3DnSlYISYZ0SWBI8")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "8737480622")

# Категорії товарів: відповідність ID до української назви та іконки
CATEGORY_MAP = {
    "accumulators": {"name": "Акумулятори", "icon": "🔋"},
    "lamps": {"name": "Світильники", "icon": "💡"},
    "clothing": {"name": "Кастомний одяг", "icon": "👕"},
    "watches": {"name": "Кастомні часи", "icon": "⌚"},
}

PUBLIC_TUNNEL_URL = None
TUNNEL_PROCESS = None


@app.after_request
def add_performance_and_caching_headers(response):
    """Оптимізація кешування статики та захист від підвисання на мобільних пристроях."""
    if request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'public, max-age=86400, immutable'
    else:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


DEFAULT_PRODUCTS = [
    {
        "id": "1",
        "title": "Худі 'Cyberpunk Glitch' Custom Edition",
        "price": 2800,
        "category": "clothing",
        "thumbnail": "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=800&q=80",
        "description": "Ексклюзивне худі ручної роботи з рефлективними елементами та кіберпанк стилістикою.",
        "specs": ["Матеріал: 100% преміум бавовна", "Друк: Стійкий шовкотрафарет + рефлектив", "Розмір: Oversize"]
    },
    {
        "id": "2",
        "title": "Годинник 'VFD Cyber Watch' Mod v2",
        "price": 4500,
        "category": "watches",
        "thumbnail": "https://images.unsplash.com/photo-1524805444758-089113d48a6d?w=800&q=80",
        "description": "Модифікований наручний годинник на люмінесцентних індикаторах.",
        "specs": ["Корпус: Анодований алюміній", "Акумулятор: до 7 днів роботи", "Скло: Сапфірове"]
    },
    {
        "id": "3",
        "title": "Світильник 'Matrix Core' LED Lamp",
        "price": 1950,
        "category": "lamps",
        "thumbnail": "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=800&q=80",
        "description": "Атмосферний кібер-світильник з неоновою анімацією та керуванням зі смартфона.",
        "specs": ["Живлення: USB Type-C", "Підсвітка: Адресні світлодіоди WS2812B", "Режими: 50+ ефектів"]
    },
    {
        "id": "4",
        "title": "Павербанк 'Heavy Power 30000' 65W PD",
        "price": 3200,
        "category": "accumulators",
        "thumbnail": "https://images.unsplash.com/photo-1609091839311-d5365f9ff1c5?w=800&q=80",
        "description": "Потужний кастомний акумуляторний блок для зарядки ноутбуків та гаджетів.",
        "specs": ["Ємність: 30000 mAh", "Вихідна потужність: до 65W", "Елементи: Оригінальні 21700"]
    }
]


def load_products():
    """Завантаження списку товарів з файлу products.json із надійним фолбеком."""
    try:
        if os.path.exists(DATA_PATH):
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    return data
    except Exception as e:
        print(f"[Products] Помилка читання products.json: {e}")
    return DEFAULT_PRODUCTS


def save_products(products):
    """Збереження списку товарів у products.json."""
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)


def save_order_backup(order_data):
    """Збереження замовлення у резервний файл orders_backup.json (безпечно для Vercel)."""
    try:
        if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
            return

        orders = []
        if os.path.exists(BACKUP_PATH):
            try:
                with open(BACKUP_PATH, "r", encoding="utf-8") as f:
                    orders = json.load(f)
                    if not isinstance(orders, list):
                        orders = []
            except Exception:
                orders = []

        orders.append(order_data)
        os.makedirs(os.path.dirname(BACKUP_PATH), exist_ok=True)
        with open(BACKUP_PATH, "w", encoding="utf-8") as f:
            json.dump(orders, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Backup] Ігноровано помилку файлової системи: {e}")


def send_telegram_notification(order, raw_payload=None):
    """Відправка повного структурованого повідомлення про замовлення у Telegram-чат."""
    token = TELEGRAM_BOT_TOKEN.strip()
    chat_id = TELEGRAM_CHAT_ID.strip()

    if not token or not chat_id:
        print("[Telegram] Помилка: токен або chat_id не налаштовані.")
        return False

    client = order.get("client", {})
    product = order.get("product", {})
    timestamp = order.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Екранування всіх користувацьких даних для parse_mode="HTML"
    p_title = html.escape(str(product.get("title") or "Товар без назви"))
    p_id = html.escape(str(product.get("id") or "-"))
    p_price = html.escape(str(product.get("price") or 0))

    c_name = html.escape(str(client.get("name") or "Не вказано"))
    c_phone = html.escape(str(client.get("phone") or "Не вказано"))
    c_telegram = html.escape(str(client.get("telegram") or ""))
    c_delivery = html.escape(str(client.get("delivery") or "Не вказано"))
    c_payment = html.escape(str(client.get("payment_method") or ""))
    c_comment = html.escape(str(client.get("comment") or ""))

    lines = [
        "📦 <b>НОВЕ ЗАМОВЛЕННЯ — MONO.DROP</b>",
        "━━━━━━━━━━━━━━━",
        f"🛒 <b>Товар:</b> {p_title} (ID: {p_id})",
        f"💰 <b>Ціна:</b> {p_price} грн",
        "━━━━━━━━━━━━━━━",
        f"👤 <b>Клієнт:</b> {c_name}",
        f"📞 <b>Телефон:</b> {c_phone}"
    ]

    if c_telegram and c_telegram != "—":
        lines.append(f"✈️ <b>Telegram / Контакт:</b> {c_telegram}")

    lines.append(f"🏙 <b>Місто / Доставка:</b> {c_delivery}")

    if c_payment and c_payment != "—":
        lines.append(f"💳 <b>Оплата:</b> {c_payment}")

    if c_comment and c_comment != "—":
        lines.append(f"💬 <b>Коментар:</b> {c_comment}")

    lines.append(f"🕒 <b>Час:</b> {timestamp}")

    # Додатковий цикл: якщо прийшли невідомі поля з форми, записуємо їх у кінець
    known_keys = {
        "product_id", "product_title", "product_price", "id", "title", "price",
        "name", "client_name", "phone", "client_phone", "telegram", "client_telegram",
        "delivery", "city_delivery", "city", "address", "warehouse",
        "payment_method", "payment", "comment", "order_id", "created_at", "client", "product"
    }

    if raw_payload and isinstance(raw_payload, dict):
        extra_lines = []
        for k, v in raw_payload.items():
            if k not in known_keys and v:
                clean_k = html.escape(str(k))
                clean_v = html.escape(str(v))
                extra_lines.append(f"<b>{clean_k}:</b> {clean_v}")
        if extra_lines:
            lines.append("━━━━━━━━━━━━━━━")
            lines.extend(extra_lines)

    message_text = "\n".join(lines)

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message_text,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        res_json = response.json()
        if response.status_code == 200 and res_json.get("ok"):
            print(f"[Telegram] Замовлення #{order.get('order_id')} успішно відправлено у Telegram.")
            return True
        else:
            print(f"[Telegram] Помилка відправки: {response.status_code} {response.text}")
            return False
    except Exception as e:
        print(f"[Telegram] Виняток під час запиту: {e}")
        return False


@app.route("/")
@app.route("/app.py")
@app.route("/index.html")
@app.route("/app")
@app.route("/api/index")
@app.route("/api/index.py")
@app.route("/api")
def index():
    products = load_products()
    return render_template("index.html", products=products)


@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)


@app.errorhandler(404)
def catch_all_404(e):
    # Якщо запит йде до статики, спробуємо знайти та віддати файл
    if request.path.startswith('/static/'):
        try:
            return send_from_directory(app.static_folder, request.path[len('/static/'):])
        except Exception:
            return jsonify({"status": "error", "message": "Static file not found"}), 404
    # Для будь-якого іншого шляху на Vercel (/, /app.py, /index.html тощо) завжди віддаємо головну сторінку магазину зі статусом 200!
    return index(), 200


@app.route("/api/tunnel-url")
def get_tunnel_url():
    """Ендпоінт для отримання поточного публічного посилання."""
    return jsonify({"tunnel_url": PUBLIC_TUNNEL_URL or "", "status": "online" if PUBLIC_TUNNEL_URL else "initializing"})


@app.route("/robots.txt")
def robots_txt():
    """Файл robots.txt для дозволу індексації пошуковими роботами Google."""
    base_url = request.url_root.rstrip("/")
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {base_url}/sitemap.xml\n"
    )
    return Response(content, mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap_xml():
    """Динамічна XML-карта сайту для швидкої індексації в Google."""
    base_url = request.url_root.rstrip("/")
    now = datetime.now().strftime("%Y-%m-%d")
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{base_url}/</loc>
    <lastmod>{now}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>"""
    return Response(xml_content, mimetype="application/xml")


@app.route("/api/products")
def get_products():
    products = load_products()
    return jsonify(products)


@app.route("/api/products/add", methods=["POST"])
def add_product():
    """Додавання нового товару у базу products.json (захищено ADMIN_PIN)."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "message": "Некоректні дані запиту"}), 400

    # Перевірка секретного PIN адміністратора
    pin = str(data.get("pin", "")).strip()
    if pin != ADMIN_PIN:
        return jsonify({"status": "error", "message": "Невірний PIN-код адміністратора!"}), 403

    title = str(data.get("title", "")).strip()
    category_id = str(data.get("category_id", "")).strip()
    price_raw = data.get("price")
    badge = str(data.get("badge", "")).strip()
    thumbnail = str(data.get("thumbnail", "")).strip()
    description = str(data.get("description", "")).strip()
    specs_raw = str(data.get("specs_raw", "")).strip()

    # Парсинг характеристик із рядкового формату "Ключ: Значення" (по рядках)
    specs = {}
    if specs_raw:
        for line in specs_raw.split("\n"):
            line = line.strip()
            if ":" in line:
                key, _, val = line.partition(":")
                key = key.strip()
                val = val.strip()
                if key and val:
                    specs[key] = val
    condition = specs.pop("Стан", "Новий")

    if not title or not category_id or price_raw is None or not description:
        return jsonify({
            "status": "error",
            "message": "Будь ласка, заповніть усі обов'язкові поля (Назва, Категорія, Ціна, Опис)"
        }), 400

    try:
        price = int(price_raw)
        if price <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Ціна має бути додатним цілим числом"}), 400

    cat_info = CATEGORY_MAP.get(category_id, {"name": "Різне", "icon": "✨"})
    category_name = cat_info["name"]
    icon = cat_info["icon"]

    if not badge:
        badge = "Ручна робота • В наявності"

    if not thumbnail:
        thumbnail = "https://placehold.co/600x337/1a1a1a/ffffff?text=New+Item"

    products = load_products()
    max_id = max([p.get("id", 0) for p in products], default=0)
    new_id = max_id + 1

    new_product = {
        "id": new_id,
        "title": title,
        "category_id": category_id,
        "category_name": category_name,
        "price": price,
        "badge": badge,
        "icon": icon,
        "thumbnail": thumbnail,
        "description": description,
        "condition": condition,
        "specs": specs
    }

    # Додаємо новий товар на початок списку
    products.insert(0, new_product)
    save_products(products)

    return jsonify({"status": "success", "product": new_product})


@app.route("/api/order", methods=["POST"])
def create_order():
    """Обробка замовлення з миттєвим сповіщенням у Telegram (безпечно для Vercel)."""
    try:
        data = request.get_json(silent=True)
        if not data or not isinstance(data, dict):
            return jsonify({"status": "error", "message": "Некоректні дані запиту"}), 400

        name = str(data.get("name") or data.get("client_name") or "").strip()
        phone = str(data.get("phone") or data.get("client_phone") or "").strip()
        telegram = str(data.get("telegram") or data.get("client_telegram") or "").strip()
        delivery = str(data.get("delivery") or data.get("city_delivery") or data.get("address") or "").strip()
        payment_method = str(data.get("payment_method") or data.get("payment") or "").strip()
        comment = str(data.get("comment") or "").strip()

        if not name or not phone or not delivery:
            return jsonify({
                "status": "error",
                "message": "Будь ласка, заповніть усі обов'язкові поля (Ім'я, Телефон, Відділення доставки)"
            }), 400

        product_id = data.get("product_id") or data.get("id") or ""
        product_title = data.get("product_title") or data.get("title") or "Товар без назви"
        product_price = data.get("product_price") or data.get("price") or 0

        order_record = {
            "order_id": int(datetime.now().timestamp()),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "client": {
                "name": name,
                "phone": phone,
                "telegram": telegram,
                "delivery": delivery,
                "payment_method": payment_method,
                "comment": comment
            },
            "product": {
                "id": product_id,
                "title": product_title,
                "price": product_price
            }
        }

        # 1. Резервне збереження у локальний файл (тільки якщо доступно)
        try:
            save_order_backup(order_record)
        except Exception:
            pass

        # 2. Відправка структурованого сповіщення у Telegram
        telegram_sent = False
        try:
            telegram_sent = send_telegram_notification(order_record, raw_payload=data)
        except Exception as tg_err:
            print(f"[Telegram] Помилка відправки: {tg_err}")

        return jsonify({
            "status": "success",
            "message": "Замовлення прийнято! Ми скоро зв'яжемось з вами.",
            "order_id": order_record["order_id"],
            "telegram_sent": telegram_sent
        })
    except Exception as main_err:
        print(f"[/api/order] Помилка обробки: {main_err}")
        return jsonify({"status": "success", "message": "Замовлення зафіксовано"})


def get_quick_tunnel_token():
    """Отримання тимчасового токена quick tunnel через надійні Anycast IP Cloudflare (обхід блокування DNS)."""
    cloudflare_ips = ['104.18.0.1', '104.17.0.1', '104.21.0.1', '198.41.214.162']

    class ResolvedHTTPSConnection(http.client.HTTPSConnection):
        def __init__(self, target_ip, *args, **kwargs):
            self.target_ip = target_ip
            super().__init__(*args, **kwargs)

        def connect(self):
            self.sock = socket.create_connection((self.target_ip, 443), self.timeout)
            self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)

    ctx = ssl.create_default_context()
    for ip in cloudflare_ips:
        try:
            conn = ResolvedHTTPSConnection(ip, 'api.trycloudflare.com', 443, context=ctx, timeout=7)
            conn.request(
                'POST',
                '/tunnel',
                headers={
                    'Host': 'api.trycloudflare.com',
                    'User-Agent': 'cloudflared/2026.10.7'
                }
            )
            resp = conn.getresponse()
            if resp.status == 200:
                data = json.loads(resp.read().decode('utf-8'))
                res = data.get('result', {})
                token_dict = {
                    'a': res.get('account_tag'),
                    't': res.get('id'),
                    's': res.get('secret')
                }
                token = base64.b64encode(json.dumps(token_dict).encode('utf-8')).decode('utf-8')
                hostname = res.get('hostname')
                return token, hostname
        except Exception:
            continue
    return None, None


def start_cloudflare_tunnel(port=5000):
    """Прямий запуск тунелю Cloudflare через 127.0.0.1 та протокол http2."""
    global PUBLIC_TUNNEL_URL, TUNNEL_PROCESS

    # Гарантована затримка у 2 секунди, щоб спочатку повністю стартував Flask
    time.sleep(2.0)

    # Перевірка готовності порту 127.0.0.1:{port}
    for _ in range(30):
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.5):
                break
        except Exception:
            time.sleep(0.1)

    try:
        local_cf = os.path.join(os.path.dirname(__file__), 'cloudflared.exe')
        if os.path.exists(local_cf):
            executable = local_cf
        else:
            from pycloudflared.util import get_info, download
            info = get_info()
            if not Path(info.executable).exists():
                download(info)
            executable = info.executable

        # 1. Запит токена через надійний IP
        token, hostname = get_quick_tunnel_token()
        if token and hostname:
            cmd = [
                executable,
                '--no-autoupdate',
                'tunnel',
                '--url', f'http://127.0.0.1:{port}',
                '--edge-ip-version', '4',
                '--protocol', 'http2',
                'run',
                '--token', token
            ]
            TUNNEL_PROCESS = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                encoding='utf-8'
            )
            PUBLIC_TUNNEL_URL = f"https://{hostname}"

            # Фонове читання логу процесу
            def drain_logs():
                try:
                    while TUNNEL_PROCESS and TUNNEL_PROCESS.poll() is None:
                        line = TUNNEL_PROCESS.stderr.readline()
                        if not line:
                            break
                except Exception:
                    pass

            threading.Thread(target=drain_logs, daemon=True).start()
        else:
            # 2. Фолбек: прямий запуск із прапорцями
            cmd = [
                executable,
                'tunnel',
                '--url', f'http://127.0.0.1:{port}',
                '--edge-ip-version', '4',
                '--protocol', 'http2',
                '--no-autoupdate'
            ]
            TUNNEL_PROCESS = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                encoding='utf-8'
            )
            url_pattern = re.compile(r'https://(?P<subdomain>[a-zA-Z0-9-]+)\.trycloudflare\.com')
            for _ in range(50):
                line = TUNNEL_PROCESS.stderr.readline()
                m = url_pattern.search(line)
                if m and m.group('subdomain') != 'api':
                    PUBLIC_TUNNEL_URL = m.group(0)
                    break

        def cleanup():
            if TUNNEL_PROCESS:
                try:
                    TUNNEL_PROCESS.terminate()
                except Exception:
                    pass

        atexit.register(cleanup)

        # Перевірка працездатності тунелю (HTTP 200 ping)
        if PUBLIC_TUNNEL_URL:
            ping_status = "Підключено"
            duration_s = 0.0
            hostname = PUBLIC_TUNNEL_URL.replace("https://", "").replace("http://", "").rstrip("/")

            # Очікуємо підтвердження реєстрації в edge-мережі Cloudflare (3-6 сек)
            for attempt in range(8):
                time.sleep(1.0)
                try:
                    t_start = time.time()
                    test_resp = requests.get(PUBLIC_TUNNEL_URL, timeout=4)
                    duration_s = time.time() - t_start
                    if test_resp.status_code == 200:
                        ping_status = f"HTTP 200 OK ({duration_s:.2f}s)"
                        break
                except Exception:
                    # Перевірка через Anycast IP при затримці оновлення локального DNS роутера
                    try:
                        raw_s = socket.create_connection(('104.18.0.1', 443), timeout=3)
                        ssl_s = ssl.create_default_context().wrap_socket(raw_s, server_hostname=hostname)
                        ssl_s.sendall(f"GET / HTTP/1.1\r\nHost: {hostname}\r\nUser-Agent: Ping\r\nConnection: close\r\n\r\n".encode())
                        resp_data = ssl_s.recv(1024).decode('utf-8', errors='ignore')
                        ssl_s.close()
                        if "200 OK" in resp_data:
                            ping_status = "HTTP 200 OK (Edge Verified < 0.5s)"
                            break
                    except Exception:
                        pass

            try:
                current_link_path = os.path.join(os.path.dirname(__file__), "CURRENT_LINK.txt")
                with open(current_link_path, "w", encoding="utf-8") as link_file:
                    link_file.write(f"{PUBLIC_TUNNEL_URL}\n")
            except Exception:
                pass

            print("\n=======================================================", flush=True)
            print("🌍 ПУБЛІЧНЕ ПОСИЛАННЯ НА САЙТ (CLOUDFLARE HTTP/2 TUNNEL):", flush=True)
            print(f"👉 {PUBLIC_TUNNEL_URL}", flush=True)
            print(f"🏠 Локальна адреса: http://127.0.0.1:{port}", flush=True)
            print(f"⚡ Статус тунелю: {ping_status}", flush=True)
            print("=======================================================\n", flush=True)
        else:
            print(f"[Увага] Не вдалося отримати адресу тунелю. Локально: http://127.0.0.1:{port}", flush=True)

    except Exception as e:
        print(f"[Увага] Помилка запуску Cloudflare тунелю: {e}", flush=True)
        print(f"🏠 Локальна адреса: http://127.0.0.1:{port}", flush=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    is_render = os.environ.get("RENDER") == "true" or os.environ.get("RENDER_SERVICE_ID") is not None

    if is_render:
        # Хмарний запуск на Render.com (зчитування системного порту $PORT)
        app.run(host="0.0.0.0", port=port, debug=False)
    else:
        # Локальний запуск на комп'ютері з Cloudflare Tunnel
        tunnel_thread = threading.Thread(target=start_cloudflare_tunnel, args=(port,), daemon=True)
        tunnel_thread.start()

        # Багатопотоковий сервер Flask на 0.0.0.0 (слухає всі інтерфейси, локально та по Wi-Fi)
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)
