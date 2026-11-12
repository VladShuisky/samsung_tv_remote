#!/usr/bin/env python3
"""Тест samsungtvws — базовое подключение и отправка клавиши."""

import logging
from samsungtvws import SamsungTVWS

logging.basicConfig(level=logging.DEBUG)

TV_IP = "192.168.0.103"
TOKEN = "10718851"

print(f"Подключение к {TV_IP}...")
tv = SamsungTVWS(TV_IP, token=TOKEN)

print("Отправляем KEY_HOME...")
tv.send_key("KEY_HOME")

print("Готово!")
