import sqlite3
from datetime import datetime

DB_NAME = "certificates.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS certificates (
            user_id INTEGER PRIMARY KEY,
            fio TEXT NOT NULL,
            count INTEGER NOT NULL DEFAULT 1,
            last_date TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_certificate(user_id, fio):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT count FROM certificates WHERE user_id = ?",
        (user_id,)
    )
    row = cursor.fetchone()

    if row:
        cursor.execute("""
            UPDATE certificates
            SET count = count + 1,
                fio = ?,
                last_date = ?
            WHERE user_id = ?
        """, (fio, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
    else:
        cursor.execute("""
            INSERT INTO certificates (user_id, fio, count, last_date)
            VALUES (?, ?, 1, ?)
        """, (user_id, fio, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()


def get_stats():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT SUM(count) FROM certificates")
    total = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM certificates")
    users = cursor.fetchone()[0]

    conn.close()
    return total, users


def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT fio, user_id, count, last_date
        FROM certificates
        ORDER BY count DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows
