import sqlite3
import  os
import time
import logging
from datetime import datetime
import threading

logger = logging.getLogger("VK_CERT_BOT.database")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "certificates.db")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")


class Data:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Data, cls).__new__(cls)
            cls._instance._init_connection()
        return cls._instance

    def _init_connection(self):
        self.conn = sqlite3.connect(
            DB_NAME,
            check_same_thread=False
        )
        self.cursor = self.conn.cursor()
        self.db_lock = threading.Lock()
        self.init_db()

    def init_db(self):
        with self.db_lock:
            self.cursor.execute("PRAGMA journal_mode=WAL;")
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS certificates (
                    user_id INTEGER PRIMARY KEY,
                    fio TEXT NOT NULL,
                    count INTEGER NOT NULL DEFAULT 1,
                    last_date TEXT NOT NULL
                )
            """)
            self.conn.commit()


    def save_certificate(self, user_id, fio):
        with self.db_lock:
            self.cursor.execute(
                "SELECT count FROM certificates WHERE user_id = ?",
                (user_id,)
            )
            row = self.cursor.fetchone()

            if row:
                self.cursor.execute("""
                    UPDATE certificates
                    SET count = count + 1,
                        fio = ?,
                        last_date = ?
                    WHERE user_id = ?
                """, (
                    fio,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    user_id
                ))
            else:
                self.cursor.execute("""
                    INSERT INTO certificates (user_id, fio, count, last_date)
                    VALUES (?, ?, 1, ?)
                """, (
                    user_id,
                    fio,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))

            self.conn.commit()


    def get_stats(self):
        with self.db_lock:
            self.cursor.execute("SELECT SUM(count) FROM certificates")
            total = self.cursor.fetchone()[0] or 0

            self.cursor.execute("SELECT COUNT(*) FROM certificates")
            users = self.cursor.fetchone()[0]

            return total, users

    def get_all_users(self):
        with self.db_lock:
            self.cursor.execute("""
                SELECT fio, user_id, count, last_date
                FROM certificates
                ORDER BY count DESC
            """)
            return self.cursor.fetchall()

    def cleanup_backups(self, max_files=10):
        if not os.path.exists(BACKUP_DIR):
            return

        backups = sorted(
            [f for f in os.listdir(BACKUP_DIR) if f.startswith("backup_")],
            reverse=True
        )

        for old in backups[max_files:]:
            path = os.path.join(BACKUP_DIR, old)

            if time.time() - os.path.getmtime(path) < 60:
                continue

            try:
                os.remove(path)
            except PermissionError:
                logger.warning(f"Skip deleting (file busy): {old}")
            except Exception as e:
                logger.error(f"Delete error {old}: {e}")

    def backup_database(self):
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(BACKUP_DIR, f"backup_{timestamp}.db")

        with self.db_lock:
            with sqlite3.connect(backup_path) as backup_conn:
                self.conn.backup(backup_conn)

        logger.info(f"Backup created: {backup_path}")

        self.cleanup_backups()
