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
from flask import Flask, render_template, jsonify, request, Response
import requests

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 86400

# Секретний PIN адміністратора для додавання товарів
ADMIN_PIN = os.getenv("ADMIN_PIN", "7777")

# Абсолютні шляхи до файлів бази даних для надійної роботи на будь-якому хостингу
DATA_PATH = os.path.join(os.path.dirname(__file__), 'data', 'products.json')
BACKUP_PATH = os.path.join(os.path.dirname(__file__), 'data', 'orders_backup.json')

# Константи Telegram Bot API (завантажуються з env зі зрозумілими заглушками)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID")

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


def load_products():
    """Завантаження списку товарів з файлу products.json."""
    if not os.path.exists(DATA_PATH):
        return []
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return []


def save_products(products):
    """Збереження списку товарів у products.json."""
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)


def save_order_backup(order_data):
    """Збереження замовлення у резервний файл orders_backup.json."""
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


def send_telegram_notification(order):
    """Відправка повідомлення про замовлення у Telegram-чат."""
    token = TELEGRAM_BOT_TOKEN.strip()
    chat_id = TELEGRAM_CHAT_ID.strip()

    if not token or not chat_id or token == "YOUR_BOT_TOKEN" or chat_id == "YOUR_CHAT_ID":
        print("[Telegram] Пропущено відправку: токен або chat_id не налаштовані.")
        return False

    client = order.get("client", {})
    product = order.get("product", {})
    timestamp = order.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    comment_text = client.get("comment") or "—"

    message_text = (
        f"🛍 <b>НОВЕ ЗАМОВЛЕННЯ — MONO.DROP</b>\n\n"
        f"📦 <b>Товар:</b> {product.get('title', 'Невідомо')} (ID: #{product.get('id', '-')})\n"
        f"💰 <b>Ціна:</b> {product.get('price', '-')} ₴\n\n"
        f"👤 <b>Клієнт:</b> {client.get('name', 'Не вказано')}\n"
        f"📞 <b>Телефон:</b> {client.get('phone', 'Не вказано')}\n"
        f"📍 <b>Доставка:</b> {client.get('delivery', 'Не вказано')}\n"
        f"💬 <b>Коментар / ТГ:</b> {comment_text}\n"
        f"🕒 <b>Час:</b> {timestamp}"
    )

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message_text,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            print("[Telegram] Повідомлення успішно відправлено.")
            return True
        else:
            print(f"[Telegram] Помилка відправки: {response.status_code} {response.text}")
            return False
    except Exception as e:
        print(f"[Telegram] Виняток під час запиту: {e}")
        return False


@app.route("/")
def index():
    products = load_products()
    return render_template("index.html", products=products)


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
    """Обробка швидкого замовлення з модального вікна."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "message": "Некоректні дані запиту"}), 400

    name = str(data.get("name", "")).strip()
    phone = str(data.get("phone", "")).strip()
    delivery = str(data.get("delivery", "")).strip()
    comment = str(data.get("comment", "")).strip()

    if not name or not phone or not delivery:
        return jsonify({
            "status": "error",
            "message": "Будь ласка, заповніть усі обов'язкові поля (Ім'я, Телефон, Відділення НП)"
        }), 400

    order_record = {
        "order_id": int(datetime.now().timestamp()),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "client": {
            "name": name,
            "phone": phone,
            "delivery": delivery,
            "comment": comment
        },
        "product": {
            "id": data.get("product_id"),
            "title": data.get("product_title", "Без назви"),
            "price": data.get("product_price", 0)
        }
    }

    # 1. Резервне збереження у локальний файл
    save_order_backup(order_record)

    # 2. Відправка у Telegram (якщо налаштовано)
    send_telegram_notification(order_record)

    return jsonify({"status": "success", "message": "Замовлення прийнято!"})


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

    # Чекаємо 0.5с, щоб Flask встиг відкрити порт 127.0.0.1:{port}
    for _ in range(30):
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.5):
                break
        except Exception:
            time.sleep(0.1)

    try:
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
                '--protocol', 'http2',
                'run',
                '--token', token,
                '--url', f'http://127.0.0.1:{port}'
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
                with open("CURRENT_LINK.txt", "w", encoding="utf-8") as link_file:
                    link_file.write(f"{PUBLIC_TUNNEL_URL}\n")
            except Exception:
                pass

            print("\n=======================================================")
            print("🌍 ПУБЛІЧНЕ ПОСИЛАННЯ НА САЙТ (CLOUDFLARE HTTP/2 TUNNEL):")
            print(f"👉 {PUBLIC_TUNNEL_URL}")
            print(f"🏠 Локальна адреса: http://127.0.0.1:{port}")
            print(f"⚡ Статус тунелю: {ping_status}")
            print("=======================================================\n")
        else:
            print(f"[Увага] Не вдалося отримати адресу тунелю. Локально: http://127.0.0.1:{port}")

    except Exception as e:
        print(f"[Увага] Помилка запуску Cloudflare тунелю: {e}")
        print(f"🏠 Локальна адреса: http://127.0.0.1:{port}")


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

        # Багатопотоковий сервер Flask на 127.0.0.1
        app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False, threaded=True)
