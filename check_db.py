import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# .env faylidan o'qish
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "1234")
DB_NAME = os.getenv("DB_NAME", "siat_dwh")

def check_and_setup_db():
    print("=" * 60)
    print("PostgreSQL ulanishini tekshirish boshlandi...")
    print(f"Host: {DB_HOST}:{DB_PORT} | Foydalanuvchi: {DB_USER}")
    print("=" * 60)

    # 1. Asosiy 'postgres' bazasiga ulanib ko'rish
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            dbname="postgres",
            connect_timeout=5
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        print("[OK] PostgreSQL serveriga muvaffaqiyatli ulandi (standart 'postgres' bazasi orqali).")

        # 2. 'siat_dwh' bazasi mavjudligini tekshirish
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (DB_NAME,))
        exists = cursor.fetchone()

        if not exists:
            print(f"[!] '{DB_NAME}' bazasi topilmadi. Yangi baza yaratilmoqda...")
            cursor.execute(f'CREATE DATABASE "{DB_NAME}";')
            print(f"[+] '{DB_NAME}' bazasi muvaffaqiyatli yaratildi!")
        else:
            print(f"[OK] '{DB_NAME}' bazasi allaqachon mavjud.")

        cursor.close()
        conn.close()

    except psycopg2.OperationalError as e:
        print("\n[XATOLIK] PostgreSQL serveriga ulanib bo'lmadi!")
        print(f"Xato xabari: {e}")
        print("Iltimos, .env faylidagi DB_PASSWORD, DB_USER, DB_PORT parametrlarini tekshiring.")
        sys.exit(1)

    # 3. 'siat_dwh' bazasiga bevosita ulanib ko'rish
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            dbname=DB_NAME,
            connect_timeout=5
        )
        cursor = conn.cursor()
        cursor.execute("SELECT current_database(), current_user, version();")
        db_curr, user_curr, ver = cursor.fetchone()

        print("\n" + "=" * 60)
        print("BOG'LANISH TO'LIQ ISHLAMOQDA:")
        print(f"  * Joriy baza: {db_curr}")
        print(f"  * Foydalanuvchi: {user_curr}")
        print(f"  * PostgreSQL versiyasi: {ver.split(',')[0]}")
        print("=" * 60)

        cursor.close()
        conn.close()
        print("[MUVAFFAQIYAT] 1-bosqich: Baza bilan bog'lanish to'liq tayyor!\n")

    except Exception as e:
        print(f"\n[XATOLIK] '{DB_NAME}' bazasiga ulanishda muammo yuz berdi: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_and_setup_db()
