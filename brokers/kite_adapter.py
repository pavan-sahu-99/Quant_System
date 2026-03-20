from kiteconnect import KiteConnect
import pandas as pd
from datetime import datetime

def gen_ses():
    key = open(r"config\\kite_api.txt", "r").read().split()
    kite = KiteConnect(api_key=key[0])
    kite.set_access_token(key[2])
    return kite

def get_kite_instruments(kite):
    df = pd.DataFrame(kite.instruments())
    print(f"Instruments loaded: {len(df)} rows")
    df.to_csv("config\\kite_instruments.csv")
    return df

def get_instrument_key(df, inst_type, symbol):
    """
    inst_type : 'EQ', 'FUT', 'CE', 'PE'
    symbol    : e.g. 'RELIANCE'
    """
    result = df[(df['instrument_type'] == inst_type) &(df['tradingsymbol'] == symbol)]
    if result.empty:
        print(f"Not found: inst_type={inst_type}, symbol={symbol}")
        return None
    return result.iloc[0]['instrument_token']

def get_last_price_kite(kite, trading_symbol, exchange="NSE"):
    """Fetch LTP for a symbol via Kite quote API."""
    instrument = f"{exchange}:{trading_symbol}"
    quote = kite.quote(instrument)
    ltp = quote[instrument]["last_price"]
    return ltp

def place_order_kite(kite, trading_symbol, side, quantity, exchange="NSE", order_type="MARKET",price=0.0, trigger_price=0.0):
    """
    kite          : from gen_ses()
    trading_symbol: e.g. "RELIANCE"
    side          : "BUY" or "SELL"
    quantity      : int
    exchange      : "NSE" for equity, "NFO" for F&O
    order_type    : "MARKET", "LIMIT", "SL", "SL-M"
    price         : required for LIMIT and SL
    trigger_price : required for SL and SL-M
    """
    # Map order_type string to Kite constant
    order_type_map = {
        "MARKET": kite.ORDER_TYPE_MARKET,
        "LIMIT":  kite.ORDER_TYPE_LIMIT,
        "SL":     kite.ORDER_TYPE_SL,
        "SL-M":   kite.ORDER_TYPE_SLM,
    }

    if order_type not in order_type_map:
        raise ValueError(f"Invalid order_type: {order_type}. Choose from MARKET, LIMIT, SL, SL-M")

    if order_type in ("LIMIT", "SL") and price == 0.0:
        raise ValueError(f"price required for order_type={order_type}")

    # trigger_price is required for SL and SL-M
    if order_type in ("SL", "SL-M") and trigger_price == 0.0:
        raise ValueError(f"trigger_price required for order_type={order_type}")

    order_id = kite.place_order(
        variety=kite.VARIETY_REGULAR,
        exchange=exchange,
        tradingsymbol=trading_symbol,
        transaction_type=side,
        quantity=quantity,
        product=kite.PRODUCT_MIS,
        order_type=order_type_map[order_type],
        price=price,
        trigger_price=trigger_price,
    )
    print(f"[LIVE] Kite order placed")
    print(f"       symbol        : {trading_symbol}")
    print(f"       side          : {side}")
    print(f"       quantity      : {quantity}")
    print(f"       order_type    : {order_type}")
    print(f"       price         : ₹{price}")
    print(f"       trigger_price : ₹{trigger_price}")
    print(f"       order_id      : {order_id}")
    return order_id

def cancel_order_kite(kite, order_id):
    kite.cancel_order(variety=kite.VARIETY_REGULAR, order_id=order_id)
    print(f"[KITE] Order cancelled → {order_id}")

def get_order_status_kite(kite, order_id):
    orders = kite.order_history(order_id)
    status = orders[-1]["status"]
    print(f"[KITE] Order {order_id} status → {status}")
    return status


if __name__ == "__main__":
    kite = gen_ses()
    #get_kite_instruments(kite)
    df   = pd.read_csv(r"config\\kite_instruments.csv")

    token = get_instrument_key(df, "EQ", "RELIANCE")
    print("Instrument token:", token)

    ltp = get_last_price_kite(kite, "RELIANCE", exchange="NSE")
    print(f"LTP: Rs {ltp}")

    # MARKET order
    # order_id = place_order_kite(kite, "RELIANCE", "BUY", 10,exchange="NSE", order_type="MARKET")

    # Test LIMIT order
    # order_id = place_order_kite(kite, "RELIANCE", "BUY", 1, exchange="NSE", order_type="LIMIT", price=1423.0)

    # Test SL order
    # order_id = place_order_kite(kite, "RELIANCE", "BUY", 1, exchange="NSE", order_type="SL",price=1433.0, trigger_price=1432.0)
