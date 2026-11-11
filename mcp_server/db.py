"""
=============================================================================
SIAT STAT DWH: Database Connection Pool Layer (mcp_server/db.py)
Loyiha: siat.stat.uz MCP Server
Muallif: Siddiq (Backend & Database Lead)
Tavsif:
  PostgreSQL bazasiga ThreadedConnectionPool orqali yuqori unumdorlikdagi
  bog'lanish havzasi (min 2, max 10) va RealDictCursor context manageri.
=============================================================================
"""

import os
from contextlib import contextmanager
from typing import Generator
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# .env faylidan sozlamalarni yuklash
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "1234")
DB_NAME = os.getenv("DB_NAME", "siat_dwh")

# Global havza obyekti
_pool: ThreadedConnectionPool = None


def get_pool() -> ThreadedConnectionPool:
    """Thread-safe connection pool singleton obyektini qaytaradi."""
    global _pool
    if _pool is None or _pool.closed:
        _pool = ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            dbname=DB_NAME,
            connect_timeout=5
        )
    return _pool


@contextmanager
def get_db_cursor() -> Generator[RealDictCursor, None, None]:
    """
    Baza ulanishini havzadan olib, natijalarni RealDictCursor orqali
    lug'at (dict) ko'rinishida beruvchi context manager.
    Xatolik bo'lsa rollback, muvaffaqiyatda commit qiladi va ulanishni havzaga qaytaradi.
    """
    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def close_pool() -> None:
    """Ilova yopilganda havzadagi barcha bog'lanishlarni xavfsiz to'xtatadi."""
    global _pool
    if _pool and not _pool.closed:
        _pool.closeall()
        _pool = None
