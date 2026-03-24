# database_organizers\db_load.py
import sqlite3
import os
import sys
from datetime import datetime
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
DB_PATH = "database\quant_system.db"

#── Connection ────────────────────────────────────────────────────────

def get_connection():
    os.makedirs("database", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ── Orders ────────────────────────────────────────────────────────────────────
def insert_order(order_id, broker, strategy, symbol, instrument_key,
                 side, quantity, order_type, price, status, mode, message=""):
    conn = get_connection()
    conn.execute("""
        INSERT INTO orders
        (order_id, broker, strategy, symbol, instrument_key,
         side, quantity, order_type, price, status, mode, message, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        order_id, broker, strategy, symbol, instrument_key,
        side, quantity, order_type, price, status, mode, message,
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ))
    conn.commit()
    conn.close()
    print(f"[DB] Order saved → {order_id} | {symbol} | {side} | {status}")

def update_order_status(order_id, status, message=""):
    conn = get_connection()
    conn.execute("""
        UPDATE orders SET status=?, message=? WHERE order_id=?
    """, (status, message, order_id))
    conn.commit()
    conn.close()
    print(f"[DB] Order updated → {order_id} | {status}")

# ── Positions ─────────────────────────────────────────────────────────────────
def insert_position(strategy, symbol, instrument_key, side,
                    quantity, entry_price):
    conn = get_connection()
    conn.execute("""
        INSERT INTO positions
        (strategy, symbol, instrument_key, side, quantity, entry_price, entry_time)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        strategy, symbol, instrument_key, side,
        quantity, entry_price,
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ))
    conn.commit()
    conn.close()
    print(f"[DB] Position opened → {symbol} | {side} | qty={quantity} @ ₹{entry_price}")

def close_position(position_id, pnl):
    conn = get_connection()
    conn.execute("""
        UPDATE positions SET status='CLOSED', pnl=? WHERE id=?
    """, (pnl, position_id))
    conn.commit()
    conn.close()
    print(f"[DB] Position closed → id={position_id} | pnl=₹{pnl}")

# ── Prices ────────────────────────────────────────────────────────────────────
def insert_candle(instrument_key, timestamp, open_, high, low, close, ltp):
    conn = get_connection()
    
    # Check if this candle already exists
    existing = conn.execute("""
        SELECT id FROM prices 
        WHERE instrument_key=? AND timestamp=? AND timeframe='1min'
    """, (instrument_key, timestamp.strftime('%Y-%m-%d %H:%M:%S'))).fetchone()
    
    if existing:
        conn.close()
        return  # already saved, skip
    
    conn.execute("""
        INSERT INTO prices
        (instrument_key, timestamp, open, high, low, close, ltp, timeframe)
        VALUES (?, ?, ?, ?, ?, ?, ?, '1min')
    """, (
        instrument_key,
        timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        open_, high, low, close, ltp
    ))
    conn.commit()
    conn.close()

# ── System log ────────────────────────────────────────────────────────────────
def log_event(event, message, broker=""):
    conn = get_connection()
    conn.execute("""
        INSERT INTO system_log (event, broker, message, timestamp)
        VALUES (?, ?, ?, ?)
    """, (
        event, broker, message,
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ))
    conn.commit()
    conn.close()
    print(f"[DB] Event logged → {event} | {message}")

if __name__ == "__main__":
    # Test insert order
    insert_order(
        order_id="MOCK-123456",
        broker="upstox",
        strategy="strategy_01",
        symbol="NIFTY",
        instrument_key="NSE_INDEX|Nifty 50",
        side="BUY",
        quantity=50,
        order_type="MARKET",
        price=23114.5,
        status="PLACED",
        mode="MOCK",
    )

    # Test insert position
    insert_position(
        strategy="strategy_01",
        symbol="NIFTY",
        instrument_key="NSE_INDEX|Nifty 50",
        side="BUY",
        quantity=50,
        entry_price=23114.5,
    )

    # Test insert candle
    insert_candle(
        instrument_key="NSE_INDEX|Nifty 50",
        timestamp=datetime.now(),
        open_=23110.0,
        high=23134.95,
        low=23067.6,
        close=23114.5,
        ltp=23114.5,
    )

    # Test log event
    log_event("BROKER_FAILOVER", "Switched from upstox to kite", broker="upstox")