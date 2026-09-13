import sqlite3
import os
from dotenv import load_dotenv
load_dotenv()
DATABASE=os.getenv("DATABASE")

def update_date_close_batch(telegram_ids, new_date_close='2030-07-09'):

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    try:
        # Проверяем, сколько записей найдено
        placeholders = ','.join(['?' for _ in telegram_ids])
        cursor.execute(f"SELECT telegram_id FROM t_main WHERE telegram_id IN ({placeholders})", telegram_ids)
        found_ids = [row[0] for row in cursor.fetchall()]

        if not found_ids:
            print(f"Ни одна запись с указанными telegram_id не найдена")
            return False

        # Показываем, какие ID найдены, а какие нет
        not_found = set(telegram_ids) - set(found_ids)
        if not_found:
            print(f"⚠️ Следующие telegram_id не найдены: {not_found}")

        # Обновляем все найденные записи
        cursor.execute(
            f"UPDATE t_main SET date_close = ? WHERE telegram_id IN ({placeholders})",
            [new_date_close] + telegram_ids
        )
        conn.commit()

        print(f"✅ Обновлено {cursor.rowcount} записей")
        print(f"   Новое значение date_close: {new_date_close}")
        print(f"   Обновлены telegram_id: {found_ids}")
        return True

    except sqlite3.Error as e:
        print(f"❌ Ошибка SQLite: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


# Использование
if __name__ == "__main__":
    # Список ID для обновления
    ids_to_update = [
        853346482,
        475819439,
        8379631563
    ]

    # Обновить с датой '2030-07-09'
    update_date_close_batch(ids_to_update)
