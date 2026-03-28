# main.py
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import time
import pandas as pd
from datetime import datetime, time as dtime

from database_organizers.db_init import init_db
from database_organizers.db_read import get_candles_db
from brokers.connection_manager import init_brokers, place_order
from strategies.strategy_1 import resample_df, trix, rsi, generate_signals
from oms.oms import process_signal

#--CONFIG---
TIMEFRAME       = '3min'
SYMBOL          = 'NIFTY'
INSTRUMENT_KEY  = 'NSE_INDEX|Nifty 50'
MODE            = 'MOCK'
NOISE_CUTOFF    = dtime(9, 45)
WARMUP_CANDLES  = 14

# -- REPLAY MODE:- Interate bar by bar through DB ---
def run_replay(brokers):
    print("\n[MAIN] Starting REPLAY mode...")

    df = get_candles_db()
    if df.empty:
        print("[MAIN] No data in DB. Exiting.")
        return

    df = resample_df(df, tf=TIMEFRAME)

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df[df['timestamp'].dt.time >= NOISE_CUTOFF].reset_index(drop=True)

    if len(df) < WARMUP_CANDLES:
        print(f"[MAIN] Not enough candles after noise filter "
              f"({len(df)}/{WARMUP_CANDLES}). Exiting.")
        return

    print(f"[MAIN] {len(df)} candles loaded. Replaying bar by bar...\n")

    prev_signal = 0

    # Replay: feed data incrementally
    for i in range(WARMUP_CANDLES, len(df) + 1):
        window = df.iloc[:i].copy()

        window['trix'] = trix(window['close'], length=9)
        window['rsi']  = rsi(window['close'],  length=15)
        window = generate_signals(window)

        latest       = window.iloc[-1]
        current_sig  = int(latest['signal'])
        timestamp    = latest['timestamp']

        if current_sig != prev_signal:
            print(f"[{timestamp}] Signal changed: {prev_signal} → {current_sig}")
            process_signal(
                current_sig, SYMBOL, INSTRUMENT_KEY, brokers,
                mode=MODE,
                bar_time=latest['timestamp'].to_pydatetime(),  
                bar_price=float(latest['close'])
            )
            prev_signal = current_sig

    print("\n[MAIN] Replay complete.")

# -- LIVE MODE --- 
def run_live(brokers):
    print("\n[MAIN] Starting LIVE mode...")

    BAR_SECONDS = int(TIMEFRAME.replace('min', '')) * 60
    prev_signal = 0

    while True:
        now = datetime.now().time()

        # Stop at EOD
        if now >= dtime(15, 29, 30):
            print("[MAIN] Market closed. EOD exit triggered.")
            process_signal(0, SYMBOL, INSTRUMENT_KEY, brokers, mode=MODE)
            break

        # Skip before noise cutoff
        if now < NOISE_CUTOFF:
            print(f"[MAIN] Waiting for noise cutoff (9:45 AM)...")
            time.sleep(30)
            continue

        df = get_candles_db()
        if df.empty:
            time.sleep(10)
            continue

        df = resample_df(df, tf=TIMEFRAME)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df[df['timestamp'].dt.time >= NOISE_CUTOFF].reset_index(drop=True)

        if len(df) < WARMUP_CANDLES:
            remaining = WARMUP_CANDLES - len(df)
            print(f"[MAIN] Warming up — {len(df)}/{WARMUP_CANDLES} candles. "
                  f"~{remaining * int(TIMEFRAME.replace('min', ''))} mins left.")
            time.sleep(BAR_SECONDS)
            continue

        df['trix'] = trix(df['close'], length=9)
        df['rsi']  = rsi(df['close'],  length=15)
        df = generate_signals(df)

        latest      = df.iloc[-1]
        current_sig = int(latest['signal'])
        timestamp   = latest['timestamp']

        if current_sig != prev_signal:
            print(f"[{timestamp}] Signal changed: {prev_signal} → {current_sig}")
            process_signal(current_sig, SYMBOL, INSTRUMENT_KEY, brokers, mode=MODE)
            prev_signal = current_sig
        else:
            print(f"[{timestamp}] Signal: {current_sig} (no change) | "
                  f"TRIX: {latest['trix']:.4f} | RSI: {latest['rsi']:.2f}")

        time.sleep(BAR_SECONDS)

if __name__ == "__main__":
    init_db()
    brokers = init_brokers()

    RUN_MODE = "REPLAY"   

    if RUN_MODE == "REPLAY":
        run_replay(brokers)
    elif RUN_MODE == "LIVE":
        run_live(brokers)