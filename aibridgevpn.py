import sqlite3
import aiohttp
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
from aiogram.client.session.aiohttp import AiohttpSession
import os
from dotenv import load_dotenv
import uuid
load_dotenv()

MERCHANT_ID=os.getenv("MERCHANT_ID")
API_SECRET=os.getenv("API_SECRET")
PROXY_URL = os.getenv("PROXY_URL")

API_URL = os.getenv("API_URL")
TOKEN_API = os.getenv("TOKEN_API")
DATABASE=os.getenv("DATABASE")
TOKEN = os.getenv("TOKEN")
vpn_headers = {
    "Authorization": f"Bearer {TOKEN_API}",
    "Content-Type": "application/json"
}
bot = Bot(token=TOKEN)

dp = Dispatcher()
http_session: aiohttp.ClientSession | None = None

def get_db_connection():
    conn = sqlite3.connect(DATABASE, timeout=20)
    conn.row_factory = sqlite3.Row
    return conn

def get_day_word(number):
    """Возвращает слово 'день' с правильным окончанием"""
    if number % 10 == 1 and number % 100 != 11:
        return f"{number} день"
    elif 2 <= number % 10 <= 4 and (number % 100 < 10 or number % 100 >= 20):
        return f"{number} дня"
    else:
        return f"{number} дней"

async def create_user(telegram_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        email = f"bridge{telegram_id}"
        UUID = str(uuid.uuid4())
        #connect = f"vless://{UUID}@31.76.13.238:443?encryption=none&flow=xtls-rprx-vision&fp=chrome&pbk=o_wUd8jghEqMWu45MJY9mRocIBT6QIkNiGvwN9_B0SI&pqv=OP2snwtH2Udt7IShGkfRaZ6L494k5XODla1coB_-kK9DEv0tBuysrWRjV8DMg-GhHvDxVXI4dgqZ7ry18-Ga_uMX8pk2LhzIVZL_7Y6pSB4kSvrS7RgcaMhfBWU5-EQ758gGLiIClY_RWX3JQmAJlMv8bNqFjGyu-1qaCl5bUzfrxRpPmkEeO3rtpDqstmPMBhwLSq0J6MvoRx9yj4CCNlP-vfWCBV9w4oYQyqT6ghMk6NKSCRp7UMkVgjIo4k2H7Lcdf9LFfOWyfQl9DwGtdUS7hEQ-yUYkOqr7GsbvUHNoPIhEAGgQ4SfARs6HfJvqMkdp9dUWTmyqhm07GOdNE9s9UHr8qEJ9L2wKMwUAJDoY8hZFs7VlLgnAU66hFX-Qhc3DmJfYYmod29y0sIJuZwS1eNNl-zthyQHuuoDSS09FDLzRmxFNopJlWywYaQeHXLY2Z6s2cF8jQfU2mcCfHvHgeLXLi4rqEiAwOT_U1WhMlWHt_OJDMx0szFecLODXHluGcAxiteInvLrr9zXGF3m-Wo0wlnuUKqJkEPJwgCIoqDA4xaPhufWTrrNOcF09PsSx4t_aLDLxfyFGa5QzSywzibOjRRU3blX7NDGZH2NqdYu3N3y7KN3FJH19mg24ezECB6fcxakAH2mVLEqp7bT05c6S9aQufGs2EYiy7M67n1NUrh6mwstn3FMBfppG7OUTtm9YJI9ccZ0BrXRDy1ldNk5cOVFDN9ZAFO45pRkJjaI2CJsRlG_8-jMtlasvRpRJsG7zdVen2-PWO8ErUUuCK3eDLXhQj7AqzPQkHPSYmnyEXkY-9l_5rdioHPsyGsMRc8lksMvuIwmuRme-AwcHCLsKz-TmCtfEGdv4iQGP-F6xxoUmBlH_QNnUFLQSX9wcriIncJxngRYKJm9a4OINpJbC8no5L9Mfv2dFSMWN22QcSFui4HHmGKO5lrLBqKT42jnEABcGHePJ_mDSXdtiE_SGCEYEgFRxXmildOavVvHvqfadyYtDW2QPs5jY7DwKTtHXXV3M-eBhnWZ5vv5WsrYSw936k7u-Hg23p57pkjt4OvSWE3zjdI3192u0WYlxYu2rZrV5qdHWj4OahxX8w1nfAZeAzqjqkIFfbLVtyH6xkngvS-8enenmfj5LapMZKZq8aGe2Yw1b6VnTAR-fFzEYsZvhkS82Xcluzlcv3XYfOPPMDZDM4Ah83yjdNVqjSadceYa6DK3lxAs3YXN49oLUDalHp9gLTGViEdmQzwooIGwMzgd1gqiWX3HSvG3WmXj48x8qreDl5BmLOvSPpBrkubzF8gM1ABlWH9fHK2y1wDHMS5qNxF_Q2dKMREVfaoP_Htw819QqXTTUKCMH0kceJoKuNcTtk_qRLaPzifVM53f-S4z49qUYWtVKq9Enuw7gKON3Ch0WxThE5rIb23ynqEOgiD_49nbGrDxCTmiVumJ7rhm8ne4C36RKwfnkuPNlnyon5C1lOe-AVxNri31Vo-Y4nkpTn8p6jyFrM9lNohG4Nz88LQDVtZBALxtoD-GLHHF9ZeKDzSATq25aQ4IjpkWwC1Q-mdGHAT61w2BE39eSeJMeyNeVTo9YuPkWkmlc8lkUH0XgxF-SW099lkPunALM5oXBTPePUNnzO_XTMOpKdvC-AaAbGAd76Cj8iwyBOrCOr8EbdvZ4NbmirfMXjA7dp3cxZh9NZv3QJQcPtXSNfQzuxDOvhgWm97KiyE4kZw_SXITYqgvzIROVKhwVAofrtXgaIj1IZu4khWRWoQi6RGBFhOYTm5RuOe7ANvdB02NbZ3amc5KI6A252UpQoo_4OVwt0eI30WzYZ_Rr7pjaMB04FzaWOeT7tUDKuapt4sgV3hYnX22b5L-I6yyT4kBTu4h2v-4ubq65AgWskf-I9zmDW1pujU0MlvFNpARFSEL-eNsskIH0lZ_4T_yBUEwlTSziOgKD8GddhQom9zbfYSaJbBS2dJCCrZU1usWJ5yK_OWLNGv86ZBlG1HpCOMlaTI6UDJ6yDLKHUiq63rCap_X3sjzo8VVebP248-2PexU0xGDvC2RdiBOpH_VSWqFVVraMYlX3ooD7F3pPPEa5McenElnGI0lI9kwU9npwiHSlxVf2V5KI_aXs6D8sxNYtB-wcMx6nU7NDewGTnH_y3_XdPH9LyRb0JT2Eia4QacJGZj6Z4j1CJNRIOaU4A-SQpgY0NjyFq1G2leLTcVe-dkQTKv-ojnYDA8ESvNfoEp6vPP1PFc2QdhVQxbte8MEXF5qWXOBG-n3nhFRHV9R1803pE1HaJa_XCyWA49gCLziKL4pZl6FvdF8dGBlRe4ykmdkhY9uQchAQuYknin-sdZRXwkOvcrfieKHGML1XwJElse0qUJ3G763uxR1Ct3f9N6S1spbLrXieFbYt2mjEL-Pu-9INiR195J6tttW0wTeIYUMVT_GuPtVCkSChdqTogEg_tg6o6ZQ8C-E0p0esZoX6IClMNqFLks5egaTvRmjV-4gYH5puXqo10debtTAM6MfkX-epF4umlyXsEB4H1dT32JQJsMBAwnIPXNoZl8bk7atZqbu8prB0pXyK10bJHZBQvCDV-Ok&security=reality&sid=afe794&sni=www.sony.com&spx=%2FxPpdnjCPHwbikhA&type=tcp#VPN-{email}"
        tomorrow = (
                datetime.now() + timedelta(days=3)
        ).strftime("%Y-%m-%d")

        cursor.execute("""
                                        INSERT INTO t_main (telegram_id,date_close,email,uuid) 
                                        VALUES (?,?,?,?)""", (
            telegram_id, tomorrow, email, UUID,
        ))
        conn.commit()
        conn.close()
        client_payload = {
            "client": {
                "email": email,
                "totalGB": 32212254720,
                "expiryTime": 0,
                "Id": UUID,
                "flow": "xtls-rprx-vision",
                "tgId": 0,
                "limitIp": 1,
                "enable": True
            },
            "inboundIds": [
                1
            ]
        }

        async with http_session.post(
                f"{API_URL}/panel/api/clients/add",
                headers=vpn_headers,
                json=client_payload
        ) as resp:
            print(resp.status)
            print(await resp.text())
        return email
    finally:
        if conn:  # проверяем, не закрыто ли уже
            conn.close()
async def get_traffic(email):
    async with http_session.get(
        f"{API_URL}/panel/api/clients/traffic/{email}",
            headers=vpn_headers
    ) as response:
        data = await response.json()

        traffic = data["obj"]

        total = traffic["total"]
        up = traffic["up"]
        down = traffic["down"]

        if total == 0:
            total_text = "∞"
        else:
            used_gb = (32212254720-up - down) / (1024 ** 3)
            total_text = f"{used_gb:.2f} ГБ"
        return total_text
def create_keyboard(days_left, gb):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📖 Инструкция 📖",
                    callback_data="instruction"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🌐 Ссылка для подключения 🌐",
                    callback_data="connection"
                )
            ],

            [
                InlineKeyboardButton(
                    text="💸 Продлить 💸",
                    callback_data="payment"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📌 Информация 📌",
                    callback_data="information"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🕓 Осталось {get_day_word(days_left)}/ {gb} 🕟",
                    callback_data="days_left"
                )
            ]
        ]
    )
    return keyboard

@dp.message(CommandStart())
async def start_handler(message: Message):
    telegram_id = message.from_user.id

    conn = get_db_connection()
    cursor = conn.cursor()

    # Проверяем наличие пользователя
    cursor.execute(
        "SELECT * FROM t_main WHERE telegram_id = ?",
        (telegram_id,)
    )
    user = cursor.fetchone()
    conn.close()
    if user:
        try:
            date_close = datetime.strptime(
                user["date_close"],
                "%Y-%m-%d"
            ).date()

            days_left = (date_close - datetime.now().date()).days

            if days_left < 0:
                days_left = 0
            gb=await get_traffic(user["email"])
        except Exception:
            days_left = 0

        keyboard=create_keyboard(days_left,gb)
        await message.answer(
            "Добро пожаловать!",
            reply_markup=keyboard
        )

    else:
        email=await create_user(telegram_id)
        gb=await get_traffic(email)
        keyboard = create_keyboard(3,gb)
        await message.answer("Вам предоставлено 3 дня бесплатно.\nНажмите на 📖 Инструкция 📖 для получения информации о подключении",reply_markup=keyboard)

@dp.callback_query(F.data == "base_tarif")
async def base_tarif(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    try:
        payment_url, data = await create_payment(
            callback.from_user.id,
            10,
            32212254720)

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💳 Оплатить 150 Руб.",
                        url=payment_url
                    )
                ]
            ]
        )

        await callback.message.answer(
            "Для оплаты нажмите кнопку ниже.",
            reply_markup=keyboard
        )

    except Exception as e:
        print(e)
        await callback.message.answer(
            "Не удалось создать платеж."
        )

    await callback.answer()

@dp.callback_query(F.data == "all_tarif")
async def all_tarif(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    try:

        payment_url, data =await create_payment(
            callback.from_user.id,
            15,
            0
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💳 Оплатить 300 Руб.",
                        url=payment_url
                    )
                ]
            ]
        )

        await callback.message.answer(
            "Для оплаты нажмите кнопку ниже.",
            reply_markup=keyboard
        )

    except Exception as e:
        print(e)
        await callback.message.answer(
            "Не удалось создать платеж."
        )

    await callback.answer()

def create_transaction(transactionId, telegram_id, tarif):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO transactions (transactionId,telegram_id,tarif) 
        VALUES (?,?,?)""", (
        transactionId, telegram_id, tarif,
    ))
    conn.commit()
    conn.close()

async def create_payment(user_id, amount, description):

    payload = {
        "paymentDetails": {
            "amount": amount,
            "currency": "RUB"
        },
        "description": str(description),
        "return": "https://t.me/platega_support",
        "failedUrl": "https://t.me/platega_support",
        "payload": str(user_id),
        "metadata": {
            "userId": str(user_id)
        }
    }

    platega_headers = {
        "X-MerchantId": MERCHANT_ID,
        "X-Secret": API_SECRET,
        "Content-Type": "application/json"
    }

    async with http_session.post(
        "https://app.platega.io/v2/transaction/process",
        headers=platega_headers,
        json=payload,
        timeout=20
    ) as response:
            response.raise_for_status()

            data = await response.json()
            transactionId = data["transactionId"]
            if transactionId:
                create_transaction(transactionId,user_id,description)
            return data.get("redirect") or data.get("url"), data

@dp.callback_query(F.data == "information")
async def instruction_handler(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Политика конфиденциальности",
                    callback_data="conf"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Пользовательское соглашение",
                    callback_data="sogl"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Техподдержка",
                    callback_data="tp"
                )
            ]
        ]
    )

    await callback.message.answer(
        "Информация:",
        reply_markup=keyboard
    )

    await callback.answer()

@dp.callback_query(F.data == "connection")
async def connection_handler(callback: CallbackQuery):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Проверяем наличие пользователя
        cursor.execute(
            "SELECT email FROM t_main WHERE telegram_id = ?",
            (callback.message.chat.id,)
        )
        email = cursor.fetchone()[0]
        conn.close()
        async with http_session.get(
                f"{API_URL}/panel/api/clients/links/{email}",
                headers=vpn_headers,
                timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            response.raise_for_status()

            data = await response.json()
            links = data.get("obj", [])
            if not links:
                connect="❌ Не удалось получить ссылку для подключения, попробуйте еще раз."
            else:
                connect=f"{links[0]}_{email}"
    except:
        connect = "❌ Не удалось получить ссылку для подключения, попробуйте еще раз."
    finally:
        if conn:  # проверяем, не закрыто ли уже
            conn.close()
    await callback.message.answer(
        connect
    )
    await callback.answer()

@dp.callback_query(F.data == "instruction")
async def instruction_handler(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🤖 Android 🤖",
                    callback_data="instr_android"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🍎 iPhone / iPad 🍎",
                    callback_data="instr_ios"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🖥️ Windows 🖥️",
                    callback_data="instr_windows"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💻 macOS 💻",
                    callback_data="instr_mac"
                )
            ]
        ]
    )

    await callback.message.answer(
        "Выберите вашу платформу:",
        reply_markup=keyboard
    )

    await callback.answer()

@dp.callback_query(F.data == "conf")
async def conf(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    text = (
        "Политика конфиденциальности\n\n   1. Общие положения\n1.1. Настоящая Политика конфиденциальности (далее — «Политика») регулирует порядок обработки и защиты информации, которую Пользователь передаёт при использовании сервиса (далее — «Сервис»).\n1.2. Используя Сервис, Пользователь подтверждает своё согласие с условиями Политики. Если Пользователь не согласен с условиями — он обязан прекратить использование Сервиса.\n\n   2. Сбор информации\n2.1. Сервис может собирать следующие типы данных:\nидентификаторы аккаунта (логин, ID, никнейм и т.п.);\nтехническую информацию (IP-адрес, данные о браузере, устройстве и операционной системе);\nисторию взаимодействий с Сервисом.\n2.2. Сервис не требует от Пользователя предоставления паспортных данных, документов, фотографий или другой личной информации, кроме минимально необходимой для работы.\n\n   3. Использование информации\n3.1. Сервис может использовать полученную информацию исключительно для:\nобеспечения работы функционала;\nсвязи с Пользователем (в том числе для уведомлений и поддержки);\nанализа и улучшения работы Сервиса.\n\n   4. Передача информации третьим лицам\n4.1. Администрация не передаёт полученные данные третьим лицам, за исключением случаев:\nесли это требуется по закону;\nесли это необходимо для исполнения обязательств перед Пользователем (например, при работе с платёжными системами);\nесли Пользователь сам дал на это согласие.\n\n   5. Хранение и защита данных\n5.1. Данные хранятся в течение срока, необходимого для достижения целей обработки.\n5.2. Администрация принимает разумные меры для защиты данных, но не гарантирует абсолютную безопасность информации при передаче через интернет.\n\n   6. Отказ от ответственности\n6.1. Пользователь понимает и соглашается, что передача информации через интернет всегда сопряжена с рисками.\n6.2. Администрация не несёт ответственности за утрату, кражу или раскрытие данных, если это произошло по вине третьих лиц или самого Пользователя.\n\n   7. Изменения в Политике\n7.1. Администрация вправе изменять условия Политики без предварительного уведомления.\n7.2. Продолжение использования Сервиса после внесения изменений означает согласие Пользователя с новой редакцией Политики.")

    await callback.message.answer(text)
    await callback.answer()

@dp.callback_query(F.data == "sogl")
async def sogl(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    text = (
        "Пользовательское соглашение\n\n   1. Общие положения\n1.1. Настоящее Пользовательское соглашение (далее — «Соглашение») является юридически обязательным документом, регулирующим порядок использования сервиса (далее — «Сервис»).\n1.2. Используя Сервис, Пользователь подтверждает полное согласие с условиями Соглашения. Если Пользователь не согласен с условиями, он обязан немедленно прекратить использование Сервиса.\n\n   2. Отказ от ответственности\n2.1. Сервис предоставляется «как есть» («AS IS»). Администрация не даёт никаких гарантий, явных или подразумеваемых, в том числе относительно работоспособности, безопасности, соответствия ожиданиям или пригодности для конкретных целей.\n2.2. Администрация не несёт ответственности за:\nлюбые убытки (включая потерю прибыли, данных, репутации), возникшие в результате использования или невозможности использования Сервиса;\nдействия или бездействие третьих лиц;\nсодержание, законность, качество, достоверность товаров, услуг или информации, полученных через Сервис;\nтехнические сбои, ошибки, задержки в работе или недоступность Сервиса.\n2.3. Все риски, связанные с использованием Сервиса, полностью возлагаются на Пользователя.\n\n   3. Ограничения\n3.1. Пользователь обязуется самостоятельно оценивать законность своих действий при использовании Сервиса.\n3.2. Запрещено использовать Сервис для деятельности, противоречащей применимому законодательству.\n3.3. Администрация вправе в любой момент, без уведомления и объяснения причин:\nограничить или заблокировать доступ Пользователя к Сервису;\nудалить любую информацию;\nприостановить или прекратить работу Сервиса полностью или частично.\n\n   4. Конфиденциальность\n4.1. Администрация может собирать минимальный объём технических данных, необходимых для работы Сервиса.\n4.2. Администрация не гарантирует полную безопасность или анонимность передаваемых данных.\n\n   5. Изменения в соглашении\n5.1. Администрация имеет право в одностороннем порядке изменять условия Соглашения в любое время без предварительного уведомления.\n5.2. Продолжение использования Сервиса после внесения изменений означает согласие Пользователя с новыми условиями.\n\n   6. Применимое право\n6.1. Все вопросы и споры, связанные с использованием Сервиса, регулируются законодательством юрисдикции, определяемой Администрацией.\n\n   7. Условия возврата\n7.1. Так как Сервис предоставляет цифровые товары и/или услуги нематериального характера, возврат и обмен после их предоставления невозможен.\n7.2. Возврат средств может быть осуществлён только в случаях:\nесли услуга не была оказана по техническим причинам со стороны Сервиса;\nесли доступ к цифровому товару не был предоставлен Пользователю.\n7.3. Для оформления возврата Пользователь обязан обратиться в службу поддержки Сервиса в течение 24 часов с момента оплаты, указав номер заказа и контактные данные.\n7.4. Решение о возврате средств принимается Администрацией индивидуально в каждом случае.\nНачиная использование сервиса (в том числе, запуская бота и/или вводя команду /start), Пользователь подтверждает, что ознакомлен с настоящим Соглашением и безусловно принимает его условия, даже если фактически не прочитал его."
    )

    await callback.message.answer(text)
    await callback.answer()

@dp.callback_query(F.data == "tp")
async def tp(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    text = (
        "По всем вопросам обращайтесь на почту aibridgevpn@gmail.com"
    )

    await callback.message.answer(text)
    await callback.answer()

@dp.callback_query(F.data == "instr_android")
async def android_instruction(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    text = (
        "📱 Инструкция для Android\n\n"
        "1\\. Установите приложение Hiddify из [Google Play](https://play.google.com/store/apps/details?id=app.hiddify.com&utm_source=emea_Med) или с [сайта разработчика](https://github.com/hiddify/hiddify-app/releases/download/v4.1.1/Hiddify-Android-arm64.apk)\\.\n"
        "2\\. Вернитеть в телеграм бот, нажмите кнопку «🌐 Ссылка для подключения 🌐» и скопируйте ссылку \\(всё сообщение\\)\\.\n"
        "3\\. Откройте Hiddify\\.\n"
        "4\\. Нажмите «\\+» в верхнем правом углу программы\\.\n"
        "5\\. Выберите «Добавить из буфера обмена»\\.\n"
        "6\\. Разрешите создание VPN \\(если запросит\\)\\.\n"
        "7\\. Нажмите кнопку подключения \\(Hi в центре экрана\\)\\."
    )
    await callback.message.answer(text, parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True)
    await callback.answer()

@dp.callback_query(F.data == "instr_ios")
async def ios_instruction(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    text = (
        "🍎 Инструкция для iPhone \\/ iPad\n\n"
        "1\\. Установите Hiddify из [App Store](https://apps.apple.com/us/app/hiddify-proxy-vpn/id6596777532)\\.\nЕсли приложение не доступно в вашем регионе, необходимо [изменить](https://modern-snap-nmjz.pagedrop.io/) регион\\.\n"
        "2\\. Вернитеть в телеграм бот, нажмите кнопку «🌐 Ссылка для подключения 🌐» и скопируйте ссылку\\(всё сообщение\\)\\.\n"
        "3\\. Откройте Hiddify\\.\n"
        "4\\. Нажмите «\\+» в верхнем правом углу программы\\.\n"
        "5\\. Выберите импорт из буфера обмена\\.\n"
        "6\\. Подтвердите создание VPN \\(если запросит\\)\\.\n"
        "7\\. Нажмите кнопку подключения \\(Hi в центре экрана\\)\\."
    )
    await callback.message.answer(text, parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True)
    await callback.answer()

@dp.callback_query(F.data == "instr_windows")
async def windows_instruction(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    text = (
        "🖥 Инструкция для установки на Windows\n\n" 
        "1\\. Скачайте приложение Hiddify для [Windows](https://github.com/hiddify/hiddify-app/releases/download/v4.1.1/Hiddify-Windows-Setup-x64.exe)\\.\n"
        "2\\. Скаченный файл скопируйте из телефона на ноутбук или ПК\\.\n"
        "3\\. Вернитеть в телеграм бот, нажмите кнопку «🌐 Ссылка для подключения 🌐» и скопируйте ссылку\\(всё сообщение\\)\\.\n"
        "4\\. Любым удобным Вам способом отправьте эту ссылку с телефона на свой ноутбук\\/ПК \\(напишите себе письмо на почту или через любой мессенджер, который есть у Вас в телефоне и ноутбуке\\/ПК\\)\nНаша цель \\- чтобы ссылка на подключение была скопирована в буфер обмена на ноутбуке\\/ПК\\.\n"
        "5\\. Запустите приложение Hiddify\\.\n"
        "6\\. Нажмите «\\+» в верхнем правом углу программы\\.\n"
        "7\\. Выберите импорт из буфера обмена\\.\n"
        "8\\. Подтвердите создание VPN \\(если запросит\\)\\.\n"
        "9\\. Перейдите на вкладку Главная, нажмите кнопку подключения \\(Hi в центре экрана\\)\\."
    )
    await callback.message.answer(text, parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True)
    await callback.answer()

@dp.callback_query(F.data == "instr_mac")
async def mac_instruction(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    text = (
        "💻 Инструкция для macOS\n\n"
        "1\\. Установите Hiddify из [App Store](https://apps.apple.com/us/app/hiddify-proxy-vpn/id6596777532)\\.\nили с [официального сайта](https://github.com/hiddify/hiddify-app/releases/download/v4.1.1/Hiddify-MacOS.dmg)\n"
        "2\\. Вернитеть в телеграм бот, нажмите кнопку «🌐 Ссылка для подключения 🌐» и скопируйте ссылку\\(всё сообщение\\)\\.\n"
        "3\\. Запустите приложение Hiddify\\.\n"
        "4\\. Нажмите «\\+» в верхнем правом углу программы\\.\n"
        "5\\. Выберите импорт из буфера обмена\\.\n"
        "6\\. Подтвердите создание VPN \\(если запросит\\)\\.\n"
        "7\\. Перейдите на вкладку Главная, нажмите кнопку подключения \\(Hi в центре экрана\\)\\."
    )

    await callback.message.answer(text, parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=True)
    await callback.answer()

@dp.callback_query(F.data == "payment")
async def payment(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💵Базовый 150 руб.💵",
                    callback_data="base_tarif"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💶Безлимитный 300 руб.💶",
                    callback_data="all_tarif"
                )
            ]
        ]
    )

    await callback.message.answer(
        "Покупка подписки на 1 месяц:\nБазовый тариф 150 рублей, ограничение траффика 30 Гб.\nБезлимитный тариф 300 рублей.",
        reply_markup=keyboard
    )

    await callback.answer()

@dp.callback_query(F.data == "days_left")
async def days_handler(callback: CallbackQuery):
    await callback.answer("Информация о сроке доступа и остатке Гб.")

async def main():
    global http_session
    # Создаем сессию с прокси
    #session = AiohttpSession(proxy=PROXY_URL)
    # Создаем бота с этой сессией
    #bot = Bot(token=TOKEN, session=session)

    http_session = aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=20)
    )

    try:
        await dp.start_polling(bot)
    finally:
        await http_session.close()


if __name__ == "__main__":
    asyncio.run(main())
