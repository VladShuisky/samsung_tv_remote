#!/usr/bin/env python3
"""
Samsung TV Remote — FastAPI Service
Одно постоянное WS-соединение с автопереподключением.
Samsung TV запрашивает подтверждение один раз при подключении.
"""

import asyncio
import base64
import json
import logging
import os
import ssl
from contextlib import asynccontextmanager

import websockets
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

# === ЛОГИРОВАНИЕ ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("samsung-tv")

# === КОНФИГУРАЦИЯ ===
TV_IP = "192.168.0.103"
TV_PORT = 8002
TOKEN = "10718851"
APP_NAME = "MyPythonApp"

# Таймауты
_WS_CONNECT_TIMEOUT = 5    # секунд на подключение
_WS_PING_INTERVAL = 30     # интервал ping-pong для проверки живости
_WS_RECONNECT_INTERVAL = 5 # секунд между попытками переподключения

# === СОСТОЯНИЕ ===
_ws: websockets.ClientConnection | None = None
_ws_connected = False
_ws_lock = asyncio.Lock()


# === PYDANTIA MODELS ===
class VolumeRequest(BaseModel):
    """Запрос на установку громкости."""
    level: int = Field(..., ge=0, le=100)


class ChannelRequest(BaseModel):
    """Запрос на переключение канала."""
    number: int = Field(..., ge=1, le=999)


# === WEBSOCKET СЛОЙ ===
def _ssl_context() -> ssl.SSLContext:
    return ssl._create_unverified_context()


def _build_url() -> str:
    encoded = base64.b64encode(APP_NAME.encode()).decode()
    return (
        f"wss://{TV_IP}:{TV_PORT}/api/v2/channels/samsung.remote.control"
        f"?name={encoded}&token={TOKEN}"
    )


def _remote_payload(key: str) -> str:
    """Сформировать JSON для ms.remote.control."""
    return json.dumps({
        "method": "ms.remote.control",
        "params": {
            "Cmd": "Click",
            "DataOfCmd": key,
            "Option": "false",
            "TypeOfRemote": "SendRemoteKey",
        },
    })


async def _send_key(key: str) -> None:
    """Отправить клавишу через постоянное WS-соединение."""
    async with _ws_lock:
        if not _ws_connected:
            raise RuntimeError("Нет соединения с ТВ")
        await _ws.send(_remote_payload(key))
        await asyncio.sleep(0.3)


async def _send_keys(keys: list[str]) -> None:
    """Отправить последовательность клавиш."""
    async with _ws_lock:
        if not _ws_connected:
            raise RuntimeError("Нет соединения с ТВ")
        for key in keys:
            await _ws.send(_remote_payload(key))
            await asyncio.sleep(0.3)


async def _ensure_ws() -> None:
    """Подключиться к ТВ (с таймаутом)."""
    global _ws, _ws_connected
    async with _ws_lock:
        if _ws_connected:
            return
        try:
            _ws = await asyncio.wait_for(
                websockets.connect(_build_url(), ssl=_ssl_context()),
                timeout=_WS_CONNECT_TIMEOUT,
            )
            _ws_connected = True
            log.info("Connected to Samsung TV %s:%d", TV_IP, TV_PORT)
        except (asyncio.TimeoutError, OSError, websockets.WebSocketException) as e:
            _ws_connected = False
            log.warning("Cannot connect to TV: %s", e)
            raise


async def _reconnect_loop() -> None:
    """Переподключаться к ТВ при разрыве."""
    global _ws_connected
    while True:
        try:
            await _ensure_ws()
            # Ping-pong для проверки живости соединения
            while _ws_connected:
                try:
                    await asyncio.wait_for(_ws.ping(), timeout=10)
                    await asyncio.sleep(_WS_PING_INTERVAL)
                except Exception:
                    _ws_connected = False
                    log.warning("TV connection lost")
                    break
        except (asyncio.TimeoutError, OSError, websockets.WebSocketException) as e:
            _ws_connected = False
            log.warning("Reconnect failed: %s", e)
        await asyncio.sleep(_WS_RECONNECT_INTERVAL)


# === LIFESPAN ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _ws_connected
    task = asyncio.create_task(_reconnect_loop())
    yield
    task.cancel()
    async with _ws_lock:
        if _ws_connected and _ws:
            try:
                await _ws.close()
            except Exception:
                pass
            _ws_connected = False


# === APP ===
app = FastAPI(
    title="Samsung TV Remote",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статические файлы
_base_dir = os.path.dirname(os.path.abspath(__file__))
_static_dir = os.path.join(_base_dir, "static")
log.info("Static dir: %s", _static_dir)
log.info("HTML exists: %s", os.path.isfile(os.path.join(_static_dir, "index.html")))


@app.get("/", response_class=HTMLResponse)
async def remote_page():
    """Отдать HTML-страницу пульта."""
    path = os.path.join(_static_dir, "index.html")
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            html = f.read()
        log.info("Serving index.html (%d bytes)", len(html))
        return html
    log.error("index.html not found at %s", path)
    return "<h1>Samsung TV Remote</h1><p>static/index.html не найден</p>"


# === Обёртка для обработки ошибок ===
def _handle_tv_errors(fn):
    import functools

    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except RuntimeError as e:
            log.warning("TV not connected: %s", e)
            raise HTTPException(status_code=503, detail="ТВ недоступен — нет соединения")
        except Exception as e:
            log.warning("TV error: %s", e)
            raise HTTPException(status_code=503, detail="Ошибка отправки на ТВ")
    return wrapper


# --- Power ---
@app.post("/power/on")
@_handle_tv_errors
async def power_on():
    await _send_key("KEY_POWER")
    return {"status": "ok", "action": "power_on"}


@app.post("/power/off")
@_handle_tv_errors
async def power_off():
    await _send_key("KEY_POWER")
    return {"status": "ok", "action": "power_off"}


# --- Volume ---
@app.post("/volume/up")
@_handle_tv_errors
async def volume_up():
    await _send_key("KEY_VOLUP")
    return {"status": "ok", "action": "volume_up"}


@app.post("/volume/down")
@_handle_tv_errors
async def volume_down():
    await _send_key("KEY_VOLDOWN")
    return {"status": "ok", "action": "volume_down"}


@app.post("/volume/set")
@_handle_tv_errors
async def volume_set(req: VolumeRequest):
    await _send_key("KEY_VOLUP")
    return {"status": "ok", "action": "volume_set", "level": req.level}


@app.post("/volume/mute")
@_handle_tv_errors
async def volume_mute():
    await _send_key("KEY_MUTE")
    return {"status": "ok", "action": "mute"}


# --- Channel ---
@app.post("/channel/up")
@_handle_tv_errors
async def channel_up():
    await _send_key("KEY_CHUP")
    return {"status": "ok", "action": "channel_up"}


@app.post("/channel/down")
@_handle_tv_errors
async def channel_down():
    await _send_key("KEY_CHDOWN")
    return {"status": "ok", "action": "channel_down"}


@app.post("/channel/set")
@_handle_tv_errors
async def channel_set(req: ChannelRequest):
    log.info("channel/set: number=%d", req.number)
    digit_map = {str(i): f"KEY_{i}" for i in range(10)}
    keys = [digit_map[d] for d in str(req.number)] + ["KEY_ENTER"]
    log.info("channel/set: keys=%s", keys)
    await _send_keys(keys)
    return {"status": "ok", "action": "channel_set", "number": req.number}


# --- Navigation ---
@app.post("/keys/up")
@_handle_tv_errors
async def key_up():
    await _send_key("KEY_UP")
    return {"status": "ok", "action": "up"}


@app.post("/keys/down")
@_handle_tv_errors
async def key_down():
    await _send_key("KEY_DOWN")
    return {"status": "ok", "action": "down"}


@app.post("/keys/left")
@_handle_tv_errors
async def key_left():
    await _send_key("KEY_LEFT")
    return {"status": "ok", "action": "left"}


@app.post("/keys/right")
@_handle_tv_errors
async def key_right():
    await _send_key("KEY_RIGHT")
    return {"status": "ok", "action": "right"}


@app.post("/keys/enter")
@_handle_tv_errors
async def key_enter():
    await _send_key("KEY_ENTER")
    return {"status": "ok", "action": "enter"}


@app.post("/keys/home")
@_handle_tv_errors
async def go_home():
    await _send_key("KEY_HOME")
    return {"status": "ok", "action": "home"}


@app.post("/keys/back")
@_handle_tv_errors
async def go_back():
    await _send_key("KEY_RETURN")
    return {"status": "ok", "action": "back"}


@app.post("/keys/menu")
@_handle_tv_errors
async def go_menu():
    await _send_key("KEY_MENU")
    return {"status": "ok", "action": "menu"}


# --- Health ---
@app.get("/health")
async def health():
    """Статус соединения с ТВ."""
    return {"tv": TV_IP, "connected": _ws_connected}
