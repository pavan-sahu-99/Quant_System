# feeds/feed.py
import upstox_client
import time
import sys
import os
import pandas as pd
from datetime import datetime
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database_organizers.db_load import insert_candle

candles_1min = {} 

def gen_session():
    with open("config\\upstox_access_token.txt", "r") as f:
        access_token = f.read().strip()
    configuration = upstox_client.Configuration()
    configuration.access_token = access_token
    api_client = upstox_client.ApiClient(configuration)
    return api_client, access_token

# Get Instrumenst for streaming------------------------------------------------------------  

def get_instrument_key(df, segment = 'NSE_INDEX', symbol = 'NIFTY'):
    """
    segment : 'NSE_EQ', 'NSE_FO', 'NSE_INDEX', 'NCD_FO', 'NSE_COM'
    symbol  : trading_symbol e.g. 'RELIANCE'
    """
    result = df[
        (df['segment'] == segment) &
        (df['trading_symbol'] == symbol)
    ]
    if result.empty:
        print(f"[INSTRUMENTS] Not found: segment={segment}, symbol={symbol}")
        return None
    return result.iloc[0]['instrument_key']

def get_instruments_for_segment(df, segment):
    """Returns all instruments for a given segment."""
    return df[df['segment'] == segment]

# Tick Level Processing -----------------------------------------------------------------
def process_tick(message):
    if "feeds" not in message:
        return

    for instrument_key, feed_data in message["feeds"].items():
        try:
            full_feed = feed_data["fullFeed"]

            # Handle both index and equity/FO feed formats
            if "indexFF" in full_feed:
                market_data = full_feed["indexFF"]
            elif "marketFF" in full_feed:
                market_data = full_feed["marketFF"]
            else:
                continue

            # ── LTP ───────────────────────────────────────────────────────────
            ltp = market_data["ltpc"]["ltp"]

            # ── 1-min candle ──────────────────────────────────────────────────
            ohlc_list = market_data["marketOHLC"]["ohlc"]
            candle_1min = next(
                (o for o in ohlc_list if o.get("interval") == "I1"), None
            )
            if candle_1min is None:
                continue

            candle = {
                "timestamp" : datetime.fromtimestamp(int(candle_1min["ts"]) / 1000),
                "open"      : candle_1min["open"],
                "high"      : candle_1min["high"],
                "low"       : candle_1min["low"],
                "close"     : candle_1min["close"],
                "ltp"       : ltp,
            }

            # ── Store candle ──────────────────────────────────────────────────
            if instrument_key not in candles_1min:
                candles_1min[instrument_key] = []

            existing = candles_1min[instrument_key]

            if not existing or existing[-1]["timestamp"] != candle["timestamp"]:
                # New candle — append
                existing.append(candle)
                print(f"[CANDLE] {instrument_key} | "
                      f"{candle['timestamp'].strftime('%H:%M')} | "
                      f"O:{candle['open']} H:{candle['high']} "
                      f"L:{candle['low']} C:{candle['close']} "
                      f"LTP:{ltp}")
                insert_candle(instrument_key, candle["timestamp"], candle["open"], candle["high"], candle["low"], candle["close"], ltp)
            else:
                # Same candle still forming — update
                existing[-1] = candle

        except (KeyError, TypeError):
            continue


# ── Resample 1-min → any timeframe ───────────────────────────────────────────
def get_candles(instrument_key, timeframe="1min"):
    """
    Returns DataFrame of candles for requested timeframe.
    timeframe : "1min", "3min", "5min", "15min"
    """
    if instrument_key not in candles_1min or not candles_1min[instrument_key]:
        return pd.DataFrame()

    df = pd.DataFrame(candles_1min[instrument_key])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp")

    if timeframe == "1min":
        return df

    df_resampled = df.resample(timeframe).agg({
        "open" : "first",
        "high" : "max",
        "low"  : "min",
        "close": "last",
        "ltp"  : "last",
    }).dropna()

    return df_resampled.reset_index()



# Web Socket Streamer ------------------------------------------------------------------- 
def start_feed(access_token, instrument_keys):
    configuration = upstox_client.Configuration()
    configuration.access_token = access_token

    streamer = upstox_client.MarketDataStreamerV3(upstox_client.ApiClient(configuration))

    def on_open():
        print("[FEED] WebSocket connected")
        streamer.subscribe(instrument_keys, "full") # full, ltp, option_greeks
        print(f"[FEED] Subscribed to {instrument_keys}")

    def on_message(message):
        process_tick(message)

    def on_error(error):
        print(f"[ERROR] {error}")

    def on_close():
        print("[FEED] WebSocket closed")

    streamer.on("open",    on_open)
    streamer.on("message", on_message)
    streamer.on("error",   on_error)
    streamer.on("close",   on_close)

    try:
        streamer.connect()
    except KeyboardInterrupt:
        print("\n[FEED] Stopping feed...")
        streamer.disconnect()
        print("[FEED] Disconnected cleanly")


if __name__ == "__main__":
    api_client, access_token = gen_session()
    #get_instruments()
    df = pd.read_csv(r"config\\upstox_instruments.csv")
    instrument_key = get_instrument_key(df)
    #instruments = ["NSE_EQ|INE002A01018"]

    print("[FEED] Starting WebSocket...")
    start_feed(access_token, [instrument_key])