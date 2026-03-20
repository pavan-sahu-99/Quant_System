import requests
import pandas as pd
import upstox_client
from datetime import datetime

def gen_session():
    with open("config\\upstox_access_token.txt", "r") as f:
        access_token = f.read().strip()
    configuration = upstox_client.Configuration()
    configuration.access_token = access_token
    api_client = upstox_client.ApiClient(configuration)
    return api_client, access_token

def get_upstox_instruments():
    url = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
    df = pd.read_json(url)
    df.to_csv("config\\upstox_instruments.csv")
    print(f"Instruments loaded: {len(df)} rows")
    return df

def get_instrument_key(df, segment, symbol):
    result = df[(df['segment'] == segment) & (df['trading_symbol'] == symbol)]
    if result.empty:
        print(f"Not found: segment={segment}, symbol={symbol}")
        return None
    return result.iloc[0]['instrument_key']

def get_last_price(instrument_key, token, flag='i'):
    if flag == 'm':
        symbol_str = ",".join(instrument_key)
    else:
        symbol_str = instrument_key
    url = f"https://api.upstox.com/v2/market-quote/quotes?instrument_key={symbol_str}"
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    quote = response.json()["data"]
    return quote[list(quote.keys())[0]]['last_price']

def place_order_upstox(api_client, symbol, instrument_key, side, quantity,
                       order_type="MARKET", price=0.0, trigger_price=0.0,
                       mode="MOCK"):
    """
    api_client    : from gen_session()
    instrument_key: from get_instrument_key()
    side          : "BUY" or "SELL"
    quantity      : int
    order_type    : "MARKET", "LIMIT", "SL", "SL-M"
    price         : required for LIMIT and SL
    trigger_price : required for SL and SL-M
    #mode          : "MOCK" or "LIVE"
    """
    order_type_map = {
        "MARKET": "MARKET",
        "LIMIT":  "LIMIT",
        "SL":     "SL",
        "SL-M":   "SL-M",
    }

    if order_type not in order_type_map:
        raise ValueError(f"Invalid order_type: {order_type}. Choose from MARKET, LIMIT, SL, SL-M")

    if order_type in ("LIMIT", "SL") and price == 0.0:
        raise ValueError(f"price required for order_type={order_type}")

    if order_type in ("SL", "SL-M") and trigger_price == 0.0:
        raise ValueError(f"trigger_price required for order_type={order_type}")

    if mode == "MOCK":
        '''
        mock_order_id = f"MOCK-{datetime.now().strftime('%H%M%S%f')}"
        print(f"[MOCK] Upstox order simulated")
        print(f"       symbol        : {symbol}")
        print(f"       instrument    : {instrument_key}")
        print(f"       side          : {side}")
        print(f"       quantity      : {quantity}")
        print(f"       order_type    : {order_type}")
        print(f"       price         : ₹{price}")
        print(f"       trigger_price : ₹{trigger_price}")
        print(f"       order_id      : {mock_order_id}")
        print(f"       timestamp     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return mock_order_id
        '''
        pass

    elif mode == "LIVE":
        order_api = upstox_client.OrderApi(api_client)
        order_request = upstox_client.PlaceOrderRequest(
            quantity=quantity,
            product="I",
            validity="DAY",
            price=price,
            instrument_token=instrument_key,
            order_type=order_type_map[order_type],
            transaction_type=side,
            disclosed_quantity=0,
            trigger_price=trigger_price,
            is_amo=False,
        )
        response = order_api.place_order(order_request, api_version="2.0")
        print(f"[LIVE] Upstox order placed")
        print(f"       symbol        : {symbol}")
        print(f"       instrument    : {instrument_key}")
        print(f"       side          : {side}")
        print(f"       quantity      : {quantity}")
        print(f"       order_type    : {order_type}")
        print(f"       price         : ₹{price}")
        print(f"       trigger_price : ₹{trigger_price}")
        print(f"       order_id      : {response.data.order_id}")
        return response.data.order_id

def cancel_order_upstox(api_client, order_id):
    order_api = upstox_client.OrderApi(api_client)
    order_api.cancel_order(order_id, api_version="2.0")
    print(f"[UPSTOX] Order cancelled → {order_id}")

def get_order_status_upstox(api_client, order_id):
    order_api = upstox_client.OrderApi(api_client)
    response  = order_api.get_order_details(api_version="2.0", order_id=order_id)
    status    = response.data.status
    print(f"[UPSTOX] Order {order_id} status → {status}")
    return status


if __name__ == "__main__":
    api_client, access_token = gen_session()
    #get_upstox_instruments()
    instruments = pd.read_csv(r"config\\upstox_instruments.csv")

    symbol = "RELIANCE"
    key    = get_instrument_key(instruments, "NSE_EQ", symbol)
    print("Instrument key:", key)

    ltp = get_last_price(key, access_token)
    print(f"LTP: ₹{ltp}")

    # Test MARKET order (MOCK)
    order_id = place_order_upstox(api_client, symbol, key, "BUY", 1,
                                   order_type="MARKET", mode="LIVE")

    # Test LIMIT order (MOCK)
    # order_id = place_order_upstox(api_client, symbol, key, "BUY", 1,
    #                                order_type="LIMIT", price=1380.0, mode="MOCK")

    # Test SL order (MOCK)
    # order_id = place_order_upstox(api_client, symbol, key, "BUY", 1,
    #                                order_type="SL", price=1385.0,
    #                                trigger_price=1383.0, mode="MOCK")
