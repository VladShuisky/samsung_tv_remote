#!/usr/bin/env python3
"""Тест browser endpoint через наш сервис."""

import asyncio
import websockets
import ssl
import json
import base64

TV_IP = "192.168.0.103"
TOKEN = "10718851"
APP_NAME = "MyPythonApp"

async def test():
    encoded_name = base64.b64encode(APP_NAME.encode()).decode()
    url = f"wss://{TV_IP}:8002/api/v2/channels/samsung.remote.control?name={encoded_name}&token={TOKEN}"
    
    ssl_context = ssl._create_unverified_context()
    
    async with websockets.connect(url, ssl=ssl_context) as ws:
        # Отправляем команду открытия браузера
        payload = json.dumps({
            "method": "ms.channel.emit",
            "params": {
                "event": "ed.apps.launch",
                "to": "host",
                "data": {
                    "appId": "org.tizen.browser",
                    "action_type": "NATIVE_LAUNCH",
                    "metaTag": "https://duckduckgo.com",
                },
            },
        })
        print(f"Sending: {payload}")
        await ws.send(payload)
        print("Sent!")
        await asyncio.sleep(1)

asyncio.run(test())
