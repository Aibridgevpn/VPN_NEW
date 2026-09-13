import sqlite3
import json
import logging
import sys
import time
from datetime import datetime, date
import aiohttp
from pathlib import Path
import asyncio
from telegram import Bot
from dotenv import load_dotenv
import os
load_dotenv()
# Настройка логирования

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / os.getenv("DATABASE")
LOG_FILE = BASE_DIR / "disconnection.log"


TOKEN_BOT = os.getenv("TOKEN")
API_URL = os.getenv("API_URL")
TOKEN_API = os.getenv("TOKEN_API")

headers = {
    "Authorization": f"Bearer {TOKEN_API}",
    "Content-Type": "application/json"
}
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),  # Путь к логу
        logging.StreamHandler()  # Вывод в консоль
    ]
)

async def update_vpn_user(email, uuid):
    """Обновление пользователя в VPN"""
    client_payload = {
        "email": email,
        "totalGB": 32212254720,  # 30 ГБ
        "expiryTime": 0,
        "flow": "xtls-rprx-vision",
        "Id": uuid,
        "tgId": 0,
        "limitIp": 1,
        "enable": False
    }

    try:
        http_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=20)
        )

        async with http_session.post(
            f"{API_URL}/panel/api/clients/update/{email}",
            headers=headers,
            data=json.dumps(client_payload)
        ) as response:
            response.raise_for_status()
            logging.info(f"Пользователь {email} (ID: {uuid}) отключен в VPN")
            return True

    except Exception as e:
        logging.error(f"Неизвестная ошибка для {email}: {e}")
        return False, str(e)
    finally:
        await http_session.close()

def get_day_word(number):
    """Возвращает слово 'день' с правильным окончанием"""
    if number % 10 == 1 and number % 100 != 11:
        return f"{number} день"
    elif 2 <= number % 10 <= 4 and (number % 100 < 10 or number % 100 >= 20):
        return f"{number} дня"
    else:
        return f"{number} дней"
async def main():
    """Основная функция"""
    logging.info("=" * 50)
    logging.info("Запуск скрипта отключения VPN")

    conn = None
    cursor = None

    try:
        bot = Bot(token=TOKEN_BOT)
        # Подключение к БД
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Получаем пользователей с истекшим VPN
        cursor.execute(
            "SELECT * FROM t_main WHERE vpn_enable=1 AND date_close < date('now', '+4 days')"
        )
        users = cursor.fetchall()

        logging.info(f"Найдено пользователей с истекшим VPN: {len(users)}")

        if not users:
            logging.info("Нет пользователей для отключения")
            return

        success_count = 0
        fail_count = 0

        for user in users:
            date_close = user['date_close']
            telegram_id = user['telegram_id']
            diff = (datetime.strptime(date_close, '%Y-%m-%d').date() - date.today()).days

            if diff < 1:

                uuid = user['uuid']
                email = user['email']


                logging.info(f"Обработка пользователя ID: {uuid}, Email: {email}, Дата окончания: {date_close}")

                # Обновляем в VPN
                success =await update_vpn_user(email, uuid)

                if success:
                    # Обновляем статус в БД только если API ответил успешно
                    cursor.execute(
                        "UPDATE t_main SET vpn_enable = 0 WHERE telegram_id = ?",
                        (telegram_id,)
                    )
                    success_count += 1
                    logging.info(f"Пользователь {email} успешно отключен")
                    text = f"🚨 VPN отключен, для продления подписки нажмите 💸 Продлить 💸 в главном меню"
                    await bot.send_message(chat_id=telegram_id, text=text)
                else:
                    fail_count += 1
                    logging.warning(f"Не удалось отключить пользователя {email}")

                # Небольшая пауза между запросами, чтобы не перегружать API
                time.sleep(0.5)
            else:
                days=get_day_word(diff)
                text=f"🚨 VPN будет отключен через {days}, незабудьте продлить 💰 подписку"
                await bot.send_message(chat_id=telegram_id, text=text)
        # Сохраняем изменения
        conn.commit()
        logging.info(f"Итог: успешно - {success_count}, ошибок - {fail_count}")

    except sqlite3.Error as e:
        logging.error(f"Ошибка базы данных: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)

    except Exception as e:
        logging.error(f"Критическая ошибка: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)

    finally:
        # Закрываем соединение с БД
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        logging.info("Скрипт завершен")
        logging.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())


