import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "1234")
DB_NAME = os.getenv("DB_NAME", "siat_dwh")

def apply_schema():
    schema_file = os.path.join("dwh", "sql", "schema.sql")
    if not os.path.exists(schema_file):
        print(f"[XATO] {schema_file} topilmadi!")
        return

    print("=" * 60)
    print(f"PostgreSQL '{DB_NAME}' bazasiga sxemani qo'llash boshlandi...")
    print("=" * 60)

    with open(schema_file, "r", encoding="utf-8") as f:
        sql_content = f.read()

    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            dbname=DB_NAME
        )
        conn.autocommit = True
        cursor = conn.cursor()

        cursor.execute(sql_content)
        print("[OK] schema.sql muvaffaqiyatli ishga tushirildi!")

        # Tekshirish: Yaratilgan sxemalar
        cursor.execute("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name IN ('raw', 'staging', 'dwh', 'mart')
            ORDER BY schema_name;
        """)
        schemas = [row[0] for row in cursor.fetchall()]
        print(f"\n[+] Sxemalar: {', '.join(schemas)}")

        # Tekshirish: Yaratilgan jadvallar
        cursor.execute("""
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'dwh'
            ORDER BY table_name;
        """)
        tables = [f"{row[0]}.{row[1]}" for row in cursor.fetchall()]
        print(f"[+] DWH jadvallari: {', '.join(tables)}")

        # Tekshirish: pg_trgm kengaytmasi
        cursor.execute("SELECT extname FROM pg_extension WHERE extname = 'pg_trgm';")
        ext = cursor.fetchone()
        if ext:
            print("[+] Kengaytma: 'pg_trgm' (Trigram) faol!")

        # Tekshirish: Indekslar
        cursor.execute("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE schemaname = 'dwh'
            ORDER BY indexname;
        """)
        indexes = [row[0] for row in cursor.fetchall()]
        print(f"[+] Indekslar soni: {len(indexes)} ta ({', '.join(indexes[:5])}...)")

        cursor.close()
        conn.close()
        print("\n" + "=" * 60)
        print("[MUVAFFAQIYAT] Baza strukturasi to'liq yaratildi va tekshirildi!")
        print("=" * 60)

    except Exception as e:
        print(f"\n[XATOLIK] Sxemani qo'llashda xatolik: {e}")
        sys.exit(1)

if __name__ == "__main__":
    apply_schema()
