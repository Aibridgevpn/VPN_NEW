from telegram import Bot
import requests
import sqlite3
import json
import logging
from datetime import datetime, timedelta
import sys
import time
import asyncio
from pathlib import Path
from dotenv import load_dotenv
import os
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
OWNER_ID=os.getenv("OWNER_ID")

DATABASE = BASE_DIR / os.getenv("DATABASE")
LOG_FILE = BASE_DIR / "transactions.log"

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),  # Путь к логу
        logging.StreamHandler()  # Вывод в консоль
    ]
)
TOKEN_BOT = os.getenv("TOKEN")
API_URL = os.getenv("API_URL")
TOKEN_API = os.getenv("TOKEN_API")

headers = {
    "Authorization": f"Bearer {TOKEN_API}",
    "Content-Type": "application/json"
}
def check_payload(transactionId):
    response = requests.get(
        f"https://app.platega.io/transaction/{transactionId}",

        timeout=20
    )
    response.raise_for_status()
    data = response.json()
    return data["status"]

def reset_trafic(email):
    client_payload = {

        "emails": [
            email
        ]
    }

    resp = requests.post(
        f"{API_URL}/panel/api/clients/bulkResetTraffic",
        headers=headers,
        data=json.dumps(client_payload)
    )
    resp.raise_for_status()

def update_vpn_user(email, uuid, Gb):
    """Обновление пользователя в VPN"""
    client_payload = {
        "email": email,
        "totalGB": Gb,#32212254720,  # 30 ГБ
        "expiryTime": 0,
        "flow": "xtls-rprx-vision",
        "Id": uuid,
        "tgId": 0,
        "limitIp": 1,
        "enable": True
    }

    try:
        resp = requests.post(
            f"{API_URL}/panel/api/clients/update/{email}",
            headers=headers,
            data=json.dumps(client_payload),
            timeout=30  # Таймаут 30 секунд
        )

        if resp.status_code == 200:
            logging.info(f"Пользователь {email} (ID: {uuid}) продлен на 30 дней")
            return True, resp.json()
        else:
            logging.error(f"Ошибка API для {email}: {resp.status_code} - {resp.text}")
            return False, resp.text

    except requests.exceptions.Timeout:
        logging.error(f"Таймаут при запросе для {email}")
        return False, "Timeout"
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка запроса для {email}: {e}")
        return False, str(e)
    except Exception as e:
        logging.error(f"Неизвестная ошибка для {email}: {e}")
        return False, str(e)


async def main():
    """Основная функция"""
    logging.info("=" * 50)
    logging.info("Запуск скрипта проверки оплаты")


    try:
        # Подключение к БД
        conn = sqlite3.connect(DATABASE, timeout=20)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Получаем пользователей с истекшим VPN
        cursor.execute(
            """SELECT t.transactionId, t.telegram_id, t.tarif, m.email, m.date_close, m.uuid FROM transactions AS t
               JOIN t_main AS m ON t.telegram_id = m.telegram_id WHERE t.status = 0"""
        )
        transactions= cursor.fetchall()
        conn.close()
        logging.info(f"Найдено {len(transactions)} транзакций ожидающих оплаты.")

        if not transactions:
            logging.info("Нет транзакций ожидающих оплату.")
            return

        for transaction in transactions:
            transactionId = transaction['transactionId']
            logging.info(f"Транзакция ID: {transactionId}")
            status=check_payload(transactionId)

            conn = sqlite3.connect(DATABASE, timeout=20)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Получаем пользователей с истекшим VPN

            match status:
                case "PENDING":
                    x=0
                case "CONFIRMED":

                    cursor.execute(
                        "UPDATE transactions SET status = 1 WHERE transactionId = ?",
                        (transactionId,)
                    )
                    uuid=transaction['uuid']
                    telegram_id = transaction['telegram_id']
                    date_close =transaction['date_close']
                    email = transaction['email']
                    tarif = transaction['tarif']

                    db_date = datetime.strptime(date_close, "%Y-%m-%d").date()
                    current_date = datetime.now().date()

                    # Берем максимальную дату и прибавляем 30 дней
                    result_date = max(db_date, current_date) + timedelta(days=30)
                    result_date_str = result_date.strftime("%Y-%m-%d")

                    cursor.execute(
                        "UPDATE t_main SET vpn_enable = 1, date_close=? WHERE telegram_id = ?",
                        (result_date_str,telegram_id,)
                    )
                    conn.commit()
                    reset_trafic(email)
                    success, response = update_vpn_user(email, uuid,tarif)
                    bot = Bot(token=TOKEN_BOT)
                    tr="Базовый"
                    if tarif==0:
                        tr="Безлимитный"
                    text=f"Поздравляем🎉🎉🎉\nТариф {tr} продлен на 30 дней!"
                    await bot.send_message(chat_id=telegram_id, text=text)
                    text_for_owner=f"Клиент {email} оплатил {tr} тариф."
                    await bot.send_message(chat_id=OWNER_ID, text=text_for_owner)
                case _:
                    cursor.execute(
                        "UPDATE transactions SET status = 2 WHERE transactionId = ?",
                        (transactionId,)
                    )
                    conn.commit()
            conn.close()

            # Небольшая пауза между запросами, чтобы не перегружать API
            time.sleep(0.5)


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

        if conn:
            conn.close()
        logging.info("Скрипт завершен")
        logging.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())


