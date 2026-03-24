# database_organizers\db.py
import sqlite3
import os
import sys
from datetime import datetime
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

DB_PATH = "database\\quant_system.db"

# ── Connection ────────────────────────────────────────────────────────────────
def get_connection():
    os.makedirs("database", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Run once at startup — creates all tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS orders (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id       TEXT NOT NULL,
            broker         TEXT NOT NULL,
            strategy       TEXT NOT NULL,
            symbol         TEXT NOT NULL,
            instrument_key TEXT NOT NULL,
            side           TEXT NOT NULL,
            quantity       INTEGER NOT NULL,
            order_type     TEXT NOT NULL,
            price          REAL NOT NULL,
            status         TEXT NOT NULL,
            mode           TEXT NOT NULL,
            message        TEXT DEFAULT '',
            timestamp      TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS positions (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy       TEXT NOT NULL,
            symbol         TEXT NOT NULL,
            instrument_key TEXT NOT NULL,
            side           TEXT NOT NULL,
            quantity       INTEGER NOT NULL,
            entry_price    REAL NOT NULL,
            entry_time     TEXT NOT NULL,
            status         TEXT NOT NULL DEFAULT 'OPEN',
            pnl            REAL DEFAULT 0.0
        );

        CREATE TABLE IF NOT EXISTS prices (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            instrument_key TEXT NOT NULL,
            timestamp      TEXT NOT NULL,
            open           REAL NOT NULL,
            high           REAL NOT NULL,
            low            REAL NOT NULL,
            close          REAL NOT NULL,
            ltp            REAL NOT NULL,
            timeframe      TEXT DEFAULT '1min'
        );

        CREATE TABLE IF NOT EXISTS system_log (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            event          TEXT NOT NULL,
            broker         TEXT DEFAULT '',
            message        TEXT NOT NULL,
            timestamp      TEXT NOT NULL
        );
    """)

    conn.commit()
    conn.close()
    print("[DB] Tables ready")

if __name__ == "__main__":
    init_db()

