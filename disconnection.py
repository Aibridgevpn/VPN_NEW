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
from telegram.error import TelegramError
import os

# Настройка логирования

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
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

async def update_vpn_user(session: aiohttp.ClientSession, email: str, uuid: str) -> bool:
    """Отключает пользователя в VPN-панели. Возвращает True при успехе."""
    client_payload = {
        "email": email,
        "totalGB": 32212254720,  # 30 ГБ
        "expiryTime": 0,
        "flow": "xtls-rprx-vision",
        "Id": uuid,
        "tgId": 0,
        "limitIp": 1,
        "enable": False,
    }

    url = f"{API_URL}/panel/api/clients/update/{email}"

    try:
        async with session.post(url, headers=headers, json=client_payload) as response:
            body = await response.text()

            if response.status >= 400:
                logging.error(
                    f"Ошибка API для {email} (ID: {uuid}): "
                    f"HTTP {response.status}, ответ: {body[:500]}"
                )
                return False

            logging.info(f"Пользователь {email} (ID: {uuid}) отключён в VPN")
            return True

    except aiohttp.ClientError as e:
        logging.error(f"Сетевая ошибка для {email}: {e}")
        return False
    except asyncio.TimeoutError:
        logging.error(f"Таймаут при запросе к API для {email}")
        return False
    except Exception as e:
        logging.error(f"Неизвестная ошибка для {email}: {e}", exc_info=True)
        return False
async def main():
    """Основная функция."""
    logging.info("=" * 50)
    logging.info("Запуск скрипта отключения VPN")

    conn = None
    cursor = None
    bot = None

    try:
        # Подключение к БД
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Получаем пользователей, у которых VPN активен и подписка истекает
        # в ближайшие 4 дня (или уже истекла).
        cursor.execute(
            "SELECT * FROM t_main "
            "WHERE vpn_enable = 1 AND date_close < date('now', '+4 days')"
        )
        users = cursor.fetchall()

        logging.info(f"Найдено пользователей для обработки: {len(users)}")

        if not users:
            logging.info("Нет пользователей для отключения")
            return

        # Бот создаём только если есть кому писать.
        bot = Bot(token=TOKEN_BOT)

        success_count = 0
        fail_count = 0
        notify_fail_count = 0

        timeout = aiohttp.ClientTimeout(total=20, connect=10)

        # Одна HTTP-сессия на весь прогон.
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for user in users:
                date_close = user["date_close"]
                telegram_id = user["telegram_id"]
                uuid = user["uuid"]
                email = user["email"]

                try:
                    diff = (
                        datetime.strptime(date_close, "%Y-%m-%d").date()
                        - date.today()
                    ).days
                except (TypeError, ValueError) as e:
                    logging.error(
                        f"Некорректная дата '{date_close}' у {email}: {e}"
                    )
                    fail_count += 1
                    continue

                if diff < 1:
                    logging.info(
                        f"Обработка пользователя ID: {uuid}, "
                        f"Email: {email}, Дата окончания: {date_close}"
                    )

                    success = await update_vpn_user(session, email, uuid)

                    if success is True:
                        cursor.execute(
                            "UPDATE t_main SET vpn_enable = 0 "
                            "WHERE telegram_id = ?",
                            (telegram_id,),
                        )
                        conn.commit()
                        success_count += 1
                        logging.info(f"Пользователь {email} успешно отключён")

                        text = (
                            "🚨 VPN отключен, для продления подписки "
                            "нажмите 💸 Продлить 💸 в главном меню"
                        )
                        if not await _safe_send(bot, telegram_id, text):
                            notify_fail_count += 1
                    else:
                        fail_count += 1
                        logging.warning(
                            f"Не удалось отключить пользователя {email}"
                        )

                    # Пауза между запросами к API.
                    await asyncio.sleep(0.5)
                else:
                    days = get_day_word(diff)
                    text = (
                        f"🚨 VPN будет отключен через {days}, "
                        f"не забудьте продлить 💰 подписку"
                    )
                    if not await _safe_send(bot, telegram_id, text):
                        notify_fail_count += 1

        # Сохраняем изменения
        #conn.commit()
        logging.info(
            f"Итог: успешно - {success_count}, "
            f"ошибок отключения - {fail_count}, "
            f"ошибок уведомлений - {notify_fail_count}"
        )

    except sqlite3.Error as e:
        logging.error(f"Ошибка базы данных: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)

    except Exception as e:
        logging.error(f"Критическая ошибка: {e}", exc_info=True)
        if conn:
            conn.rollback()
        sys.exit(1)

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        if bot is not None:
            try:
                await bot.close()
            except Exception as e:
                logging.warning(f"Не удалось закрыть Telegram-бота: {e}")
        logging.info("Скрипт завершён")
        logging.info("=" * 50)


async def _safe_send(bot: Bot, chat_id: int, text: str) -> bool:
    """Отправляет сообщение, не роняя основной цикл при ошибке Telegram."""
    try:
        await bot.send_message(chat_id=chat_id, text=text)
        return True
    except TelegramError as e:
        logging.warning(f"Telegram не смог отправить сообщение {chat_id}: {e}")
        return False
    except Exception as e:
        logging.warning(f"Неизвестная ошибка при отправке в {chat_id}: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(main())


