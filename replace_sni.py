import re
import sqlite3
import logging
import aiohttp
from pathlib import Path
import asyncio
from telegram import Bot
from dotenv import load_dotenv
import os
load_dotenv()

NEW_SNI="www.github.com"
BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / os.getenv("DATABASE")
LOG_FILE = BASE_DIR / "replace_sni.log"

TOKEN_BOT = os.getenv("TOKEN")
API_URL = os.getenv("API_URL")
TOKEN_API = os.getenv("TOKEN_API")

headers = {
    "Authorization": f"Bearer {TOKEN_API}",
    "Content-Type": "application/json"
}
# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),  # Путь к логу
        logging.StreamHandler()  # Вывод в консоль
    ]
)


def replace_sni_simple(vless_url):
    # Ищем параметр sni в строке
    return re.sub(r'sni=[^&]+', f'sni={NEW_SNI}', vless_url)


async def main():
    """Основная функция"""
    try:
        http_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=20)
        )
        bot = Bot(token=TOKEN_BOT)
        # Подключение к БД
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Получаем активных пользователей
        cursor.execute(
            "SELECT email, telegram_id FROM t_main WHERE vpn_enable=1"
        )
        users = cursor.fetchall()

        logging.info(f"Найдено: {len(users)} активных пользователей")

        if not users:
            logging.info("Нет активных пользователей")
            return

        for user in users:
            email = user['email']
            telegram_id = user['telegram_id']
            async with http_session.get(
                    f"{API_URL}/panel/api/clients/links/{email}",
                    headers=headers
            ) as response:
                response.raise_for_status()

                data = await response.json()
                links = data.get("obj", [])
                if not links:
                    connect = "❌ Не удалось получить ссылку для подключения, попробуйте еще раз."
                else:
                    connect = f"{links[0]}_{email}"
                    new_vless = replace_sni_simple(connect)
                    text="🚧🚧🚧ВНИМАНИЕ🚧🚧🚧\nДля обеспечения более устойчивой работы VPN, в ближайшее время будет перенастроен сервер.\n🛑 После того как VPN перестанет работать, удалите текущее подключение в приложении HIDDIFY и создайте новое по ссылке из сообщения 👇"
                    await bot.send_message(chat_id=telegram_id, text=text)
                    await bot.send_message(chat_id=telegram_id, text=new_vless)

    except:
        connect = f"❌ Не удалось получить ссылку для подключения {email}"
    finally:
        if conn:  # проверяем, не закрыто ли уже
            conn.close()
        await http_session.close()



if __name__ == "__main__":
    asyncio.run(main())
