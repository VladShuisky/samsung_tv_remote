#!/usr/bin/env python3
"""
Samsung TV Browser URL Opener
Открывает URL в браузере Samsung TV (браузер должен быть уже открыт)

Использование:
    python3 samsung_tv_open_url.py https://google.com
    python3 samsung_tv_open_url.py https://youtube.com
    python3 samsung_tv_open_url.py https://wikipedia.org
"""

import asyncio
import json
import base64
import ssl
import websockets
import sys

# === КОНФИГУРАЦИЯ ===
TV_IP = "192.168.0.103"
TOKEN = "10718851"
APP_NAME = "MyPythonApp"

# Маппинг символов в клавиши Samsung TV
KEY_MAP = {
    # Буквы
    'a': 'KEY_A', 'b': 'KEY_B', 'c': 'KEY_C', 'd': 'KEY_D',
    'e': 'KEY_E', 'f': 'KEY_F', 'g': 'KEY_G', 'h': 'KEY_H',
    'i': 'KEY_I', 'j': 'KEY_J', 'k': 'KEY_K', 'l': 'KEY_L',
    'm': 'KEY_M', 'n': 'KEY_N', 'o': 'KEY_O', 'p': 'KEY_P',
    'q': 'KEY_Q', 'r': 'KEY_R', 's': 'KEY_S', 't': 'KEY_T',
    'u': 'KEY_U', 'v': 'KEY_V', 'w': 'KEY_W', 'x': 'KEY_X',
    'y': 'KEY_Y', 'z': 'KEY_Z',
    
    # Цифры
    '0': 'KEY_0', '1': 'KEY_1', '2': 'KEY_2', '3': 'KEY_3',
    '4': 'KEY_4', '5': 'KEY_5', '6': 'KEY_6', '7': 'KEY_7',
    '8': 'KEY_8', '9': 'KEY_9',
    
    # Специальные символы
    '.': 'KEY_DOT',
    '/': 'KEY_SLASH',
    ':': 'KEY_COLON',
    '-': 'KEY_MINUS',
    '=': 'KEY_EQUAL',
    '&': 'KEY_AMPERSAND',
    '*': 'KEY_ASTERISK',
    '#': 'KEY_HASH',
    '@': 'KEY_AT',
    '+': 'KEY_PLUS',
    '[': 'KEY_LEFT_BRACKET',
    ']': 'KEY_RIGHT_BRACKET',
    '_': 'KEY_UNDERSCORE',
    "'": 'KEY_QUOTE',
    '\\': 'KEY_BACKSLASH',
    ';': 'KEY_SEMICOLON',
    ',': 'KEY_COMMA',
    '?': 'KEY_QUESTION',
    '!': 'KEY_EXCLAIM',
    '"': 'KEY_DQUOTE',
    '%': 'KEY_PERCENT',
    ' ': 'KEY_SPACE',
}

async def send_key(key_name, delay=0.5):
    """Отправить клавишу на ТВ"""
    encoded_name = base64.b64encode(APP_NAME.encode()).decode()
    url = f"wss://{TV_IP}:8002/api/v2/channels/samsung.remote.control?name={encoded_name}&token={TOKEN}"
    ssl_context = ssl._create_unverified_context()
    
    try:
        async with websockets.connect(url, ssl=ssl_context) as ws:
            payload = json.dumps({
                "method": "ms.remote.control",
                "params": {
                    "Cmd": "Click",
                    "DataOfCmd": key_name,
                    "Option": "false",
                    "TypeOfRemote": "SendRemoteKey"
                }
            })
            await ws.send(payload)
            await asyncio.sleep(delay)
    except Exception as e:
        print(f"  ❌ Ошибка {key_name}: {e}")

async def open_url(url):
    """Открыть URL в браузере Samsung TV"""
    print("=" * 60)
    print("  SAMSUNG TV — ОТКРЫТИЕ URL В БРАУЗЕРЕ")
    print("=" * 60)
    print(f"\n  URL: {url}\n")
    
    # Переводим URL в клавиши
    url_lower = url.lower()
    keys = []
    
    for char in url_lower:
        if char in KEY_MAP:
            keys.append((KEY_MAP[char], char))
        else:
            print(f"  ⚠️  Символ '{char}' не найден в маппинге, пропускаем")
    
    print(f"  📝 Вводим {len(keys)} клавиш:")
    print(f"     {''.join([c for _, c in keys])}\n")
    
    # Вводим каждую клавишу с паузой
    for i, (key, char) in enumerate(keys, 1):
        print(f"  {i:3d}/{len(keys)}  {key:25s} → '{char}'")
        await send_key(key, delay=0.8)
    
    # Нажимаем Enter
    print(f"\n  🚀 Переходим по URL...")
    await send_key("KEY_ENTER", delay=5)
    
    print("\n" + "=" * 60)
    print("  ✅ URL открыт!")
    print("=" * 60)

async def main():
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python3 samsung_tv_open_url.py <URL>")
        print("\nПримеры:")
        print("  python3 samsung_tv_open_url.py https://google.com")
        print("  python3 samsung_tv_open_url.py https://youtube.com")
        print("  python3 samsung_tv_open_url.py https://wikipedia.org")
        sys.exit(1)
    
    url = sys.argv[1]
    await open_url(url)

if __name__ == "__main__":
    asyncio.run(main())
