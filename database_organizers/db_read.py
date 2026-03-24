# database/db_read.py
import sqlite3
import os
import sys
from datetime import datetime
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

DB_PATH = "database\quant_system.db"

# ── Connection ────────────────────────────────────────────────────────────────
def get_connection():
    os.makedirs("database", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── Orders ────────────────────────────────────────────────────────────────────
def get_orders(strategy=None, status=None, mode=None):
    """Fetch orders with optional filters."""
    conn   = get_connection()
    query  = "SELECT * FROM orders WHERE 1=1"
    params = []
    if strategy:
        query += " AND strategy=?"
        params.append(strategy)
    if status:
        query += " AND status=?"
        params.append(status)
    if mode:
        query += " AND mode=?"
        params.append(mode)
    query += " ORDER BY timestamp DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def count_orders_today(strategy):
    """Count total entries+exits today for daily trade limit check."""
    conn  = get_connection()
    today = datetime.now().strftime('%Y-%m-%d')
    count = conn.execute("""
        SELECT COUNT(*) FROM orders
        WHERE strategy=? AND timestamp LIKE ? AND status != 'REJECTED'
    """, (strategy, f"{today}%")).fetchone()[0]
    conn.close()
    return count

# ── Positions ─────────────────────────────────────────────────────────────────

def get_open_positions(strategy=None):
    conn   = get_connection()
    query  = "SELECT * FROM positions WHERE status='OPEN'"
    params = []
    if strategy:
        query += " AND strategy=?"
        params.append(strategy)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── Prices ────────────────────────────────────────────────────────────────────

def get_candles_db(instrument_key, limit=100):
    """Fetch last N candles from DB — useful for strategy warmup at startup."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM prices
        WHERE instrument_key=? AND timeframe='1min'
        ORDER BY timestamp DESC LIMIT ?
    """, (instrument_key, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows][::-1] 

if __name__ == '__main__':
    print("\n--- Orders ---")
    for o in get_orders():
        print(o)

    print("\n--- Open Positions ---")
    for p in get_open_positions():
        print(p)

    print("\n--- Today's trade count ---")
    print(count_orders_today("strategy_01"))

    print("\n--- Last candles ---")
    for c in get_candles_db("NSE_INDEX|Nifty 50"):
        print(c)