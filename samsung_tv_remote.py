#!/usr/bin/env python3
"""
Samsung TV Remote Control
Модель: UE43M5513
IP: 192.168.0.103
Токен: 10718851
"""

import asyncio
import json
import base64
import ssl
import websockets

# === КОНФИГУРАЦИЯ ===
TV_IP = "192.168.0.103"
TOKEN = "10718851"
APP_NAME = "HomeApp"

async def send_key(key_name, label=""):
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
            status = f" ({label})" if label else ""
            print(f"  ✅ Отправлена: {key_name}{status}")
            await asyncio.sleep(0.3)
    except Exception as e:
        print(f"  ❌ Ошибка {key_name}: {e}")

async def set_volume(level):
    """Установить уровень громкости (0-100)"""
    print(f"  ⚙️  Установка громкости: {level}")
    # Samsung TV использует KEY_VOLUP/VOLDOWN, поэтому эмулируем
    current = 0  # Начальное значение (предположение)
    for _ in range(level - current):
        await send_key("KEY_VOLUP")
    for _ in range(current - level):
        await send_key("KEY_VOLDOWN")

async def channel_up():
    """Переключить канал вверх"""
    await send_key("KEY_CHUP", "канал +")

async def channel_down():
    """Переключить канал вниз"""
    await send_key("KEY_CHDN", "канал -")

async def input_channel_number(channel_num):
    """Ввести номер канала цифрами"""
    channel_str = str(channel_num)
    print(f"  ⚙️  Ввод канала: {channel_str}")
    for digit in channel_str:
        key_map = {
            '0': 'KEY_0', '1': 'KEY_1', '2': 'KEY_2', '3': 'KEY_3',
            '4': 'KEY_4', '5': 'KEY_5', '6': 'KEY_6', '7': 'KEY_7',
            '8': 'KEY_8', '9': 'KEY_9'
        }
        await send_key(key_map[digit])
    await send_key("KEY_ENTER", "подтвердить")

async def turn_off():
    """Выключить ТВ"""
    await send_key("KEY_POWER", "выключение")

async def turn_on():
    """Включить ТВ"""
    await send_key("KEY_POWER", "включение")

async def mute():
    """Вкл/выкл мьют"""
    await send_key("KEY_MUTE", "мьют")

async def menu():
    """Показать меню управления"""
    print("""
╔══════════════════════════════════════════╗
║       SAMSUNG TV REMOTE CONTROL          ║
╠══════════════════════════════════════════╣
║                                          ║
║  1 — Громкость +                         ║
║  2 — Громкость -                         ║
║  3 — Мьют                                ║
║  4 — Канал +                             ║
║  5 — Канал -                             ║
║  6 — Ввести номер канала                 ║
║  7 — Включить ТВ                         ║
║  8 — Выключить ТВ                        ║
║  9 — Домой                               ║
║  0 — Выход                               ║
║                                          ║
╚══════════════════════════════════════════╝
    """)

async def main():
    print("=" * 50)
    print("  SAMSUNG TV UE43M5513 — Пульт управления")
    print("=" * 50)
    print()
    
    while True:
        await menu()
        choice = input("Выберите действие (0-9): ").strip()
        
        if choice == '1':
            await send_key("KEY_VOLUP", "громкость +")
        elif choice == '2':
            await send_key("KEY_VOLDOWN", "громкость -")
        elif choice == '3':
            await mute()
        elif choice == '4':
            await channel_up()
        elif choice == '5':
            await channel_down()
        elif choice == '6':
            channel = input("Введите номер канала: ").strip()
            if channel:
                await input_channel_number(int(channel))
        elif choice == '7':
            await turn_on()
        elif choice == '8':
            await turn_off()
        elif choice == '9':
            await send_key("KEY_HOME", "домой")
        elif choice == '0':
            print("\n👋 До свидания!")
            break
        else:
            print("❌ Неверный выбор")
        
        print()

if __name__ == "__main__":
    asyncio.run(main())
