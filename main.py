import asyncio
import json
import logging
import os
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from urllib.parse import parse_qsl

import aiohttp
from dotenv import load_dotenv

from quart import Quart, Response, request, send_file, websocket
from quart_cors import cors
from quart_minify import Minify
from quart_rate_limiter import RateLimiter

from hypercorn.config import Config
from hypercorn.asyncio import serve

from starlette.middleware.trustedhost import TrustedHostMiddleware

from router.base_bp import base_bp
from endpoints.api.feeds import feeds_api
from services.background_tasks import BackgroundTaskManager
from services.database import Database
from utility.orjson_provider import OrjsonProvider
from utility.utils import ProxyHeadersMiddleware, get_client_ip, get_client_ip_ws, mask_query

load_dotenv()


dev_bot = False if os.getenv('DEV') == "False" else True

if dev_bot:
    config_quart = json.load(open("config_dev.json", "r", encoding="utf8"))
else:
    config_quart = json.load(open("config.json", "r", encoding="utf8"))

config_quart['dev_bot'] = dev_bot

app = Quart(__name__, static_folder=config_quart['static_folder'])
app = cors(app, websocket_cors_enabled=not config_quart['dev_bot'])
app.json = OrjsonProvider(app)
Minify(app=app, js=True, cssless=False, remove_console=True)

rate_limiter = RateLimiter(app)


app.config["SERVER_NAME"] = config_quart['SERVER_NAME']
app.config["TEMPLATES_AUTO_RELOAD"] = config_quart['TEMPLATES_AUTO_RELOAD']

app.config_quart = config_quart

if not os.path.isdir("logs"):
    os.mkdir("logs")

logger = logging.getLogger('it_monitoring')
logger.setLevel(logging.INFO)

handler = RotatingFileHandler(
    filename=f"logs/it_monitoring.log",
    encoding='utf-8',
    maxBytes=120 * 1024 * 1024,  # 120 MiB
    backupCount=5,  # Rotate through five files
)
dt_fmt = '%d/%m/%Y %H:%M:%S'
formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
handler.setFormatter(formatter)
logger.addHandler(handler)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(formatter)
logger.addHandler(consoleHandler)

config_quart['logger'] = logger
app.config.logger = logger


if not config_quart['dev_bot']:
    app.asgi_app = ProxyHeadersMiddleware(app.asgi_app, trusted_hosts=config_quart['ProxyHeadersMiddleware'])
    app.asgi_app = TrustedHostMiddleware(app.asgi_app, allowed_hosts=config_quart['TrustedHostMiddleware'])

app.register_blueprint(base_bp)
app.register_blueprint(feeds_api)

@app.before_serving
async def startup():
    # Initialize database
    db_path = config_quart['storage'].get('db_file', 'data/feeds.db')
    database = Database(db_path)
    await database.connect()
    config_quart['database'] = database

    session_aio = aiohttp.ClientSession()
    config_quart['session'] = session_aio

    background_manager = BackgroundTaskManager(config_quart)
    config_quart['background_manager'] = background_manager
    await background_manager.start(session_aio)

@app.after_serving
async def shutdown():
    if 'background_manager' in config_quart:
        await config_quart['background_manager'].stop()
    if 'database' in config_quart:
        await config_quart['database'].close()
    await config_quart['session'].close()

@app.before_request
async def log_start():
    request._start_time = time.perf_counter()

@app.before_websocket
async def log_ws_start():
    websocket._start_time = time.perf_counter()
    ip = get_client_ip_ws()
    path = websocket.path
    masked_query = mask_query(websocket.query_string.decode("utf-8"))
    safe_url = f"{path}?{masked_query}" if masked_query else path
    websocket._safe_url = safe_url
    logger.info(f"{ip} WS CONNECT {safe_url}")

@app.teardown_websocket
async def log_ws_end(exc):
    start_time = getattr(websocket, "_start_time", time.perf_counter())
    duration = (time.perf_counter() - start_time) * 1000
    ip = get_client_ip_ws()
    safe_url = getattr(websocket, "_safe_url", websocket.path)
    status = "ERROR" if exc else "OK"
    logger.info(f"{ip} WS DISCONNECT {safe_url} {status} {duration:.2f}ms")

async def log_end(response: Response):
    duration = (time.perf_counter() - getattr(request, "_start_time", time.perf_counter())) * 1000
    ip = get_client_ip()

    path = request.path
    params = parse_qsl(request.query_string.decode("utf-8"), keep_blank_values=True)

    if request.method == "GET" and (
        path.startswith(f"/{config_quart['static_folder']}")
        or path.startswith("/assets")
        or path.startswith("/.well-known")
        or path.startswith("/favicon.ico")
    ):
        return response

    if params:
        masked_query = "&".join(f"{key}=***" for key, _ in params)
        safe_url = f"{path}?{masked_query}"
    else:
        safe_url = path

    logger.info(f"{ip} {request.method} {safe_url} {response.status_code} {duration:.2f}ms")
    return response

@app.after_request
async def set_security_headers(response: Response):
    """Ajoute des en-têtes de sécurité après chaque requête."""
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    await log_end(response)
    return response

@app.route("/favicon.ico")
async def favicon():
    try:
        return await send_file(Path(app.static_folder) / "assets" / "img" / "favicon.ico")
    except FileNotFoundError:
        return "", 404

async def main(app, config):
    await serve(app, config)

if __name__ == "__main__":
    config = Config()

    if config_quart['dev_bot']:
        config.bind = ['127.0.0.1:25567']
        config.loglevel = 'DEBUG'
        config.debug = True
        config.use_reloader = True
    else:
        config.bind = ['0.0.0.0:25567']
        config.loglevel = 'INFO'

    loop = asyncio.new_event_loop()
    loop.run_until_complete(main(app, config))
