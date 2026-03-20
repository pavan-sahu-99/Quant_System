import pandas as pd
from datetime import datetime
from base import OrderRequest, OrderResponse
import time

# ── Import adapters ───────────────────────────────────────────────────────────
from upstox_adapter import (
    gen_session as upstox_gen_session,
    get_last_price as upstox_get_ltp,
    place_order_upstox,
    cancel_order_upstox,
    get_order_status_upstox,
)
from kite_adapter import (
    gen_ses as kite_gen_session,
    get_last_price_kite,
    place_order_kite,
    cancel_order_kite,
    get_order_status_kite,
)


# ── LTP fetcher — uses broker which  is active ─────────────────────────────
def get_ltp(broker, request: OrderRequest) -> float:
    """
    Fetches LTP from broker which is currently active.
    broker : the active broker dict from the brokers list
    """
    if broker["name"] == "upstox":
        return upstox_get_ltp(request.instrument_key, broker["token"])
    elif broker["name"] == "kite":
        return get_last_price_kite(broker["client"], request.symbol, request.exchange)


# ── MOCK handler ──────────────────────────────────────────────────────────────
def _handle_mock(broker, request: OrderRequest) -> OrderResponse:
    """
    Single MOCK handler for all brokers.
    Fetches LTP from active broker and simulates the order.
    """
    ltp = get_ltp(broker, request)
    mock_order_id = f"MOCK-{datetime.now().strftime('%H%M%S%f')}"
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    print(f"[MOCK] Order simulated via {broker['name'].upper()}")
    print(f"       symbol        : {request.symbol}")
    print(f"       instrument    : {request.instrument_key}")
    print(f"       side          : {request.side}")
    print(f"       quantity      : {request.quantity}")
    print(f"       order_type    : {request.order_type}")
    print(f"       price (LTP)   : ₹{ltp}")
    print(f"       order_id      : {mock_order_id}")
    print(f"       timestamp     : {timestamp}")

    return OrderResponse(
        success=True,
        order_id=mock_order_id,
        broker=broker["name"],
        symbol=request.symbol,
        side=request.side,
        quantity=request.quantity,
        price=ltp,
        order_type=request.order_type,
        mode="MOCK",
        timestamp=timestamp,
    )


# ── LIVE handler — routes to correct broker ───────────────────────────────────
def _handle_live(broker, request: OrderRequest) -> OrderResponse:
    """
    Routes a LIVE order to the correct broker adapter.
    Raises exception on failure and connection_manager catches it.
    """
    ltp = get_ltp(broker, request)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Use LTP as price for MARKET orders
    # For LIMIT/SL use the price from the request
    price = ltp if request.order_type == "MARKET" else request.price

    if broker["name"] == "upstox":
        order_id = place_order_upstox(
            api_client=broker["client"],
            symbol=request.symbol,
            instrument_key=request.instrument_key,
            side=request.side,
            quantity=request.quantity,
            order_type=request.order_type,
            price=price,
            trigger_price=request.trigger_price,
            mode="LIVE",
        )
        success = True
        message = ""
    
    elif broker["name"] == "kite":
        order_id = place_order_kite(
            kite=broker["client"],
            trading_symbol=request.symbol,
            side=request.side,
            quantity=request.quantity,
            exchange=request.exchange,
            order_type=request.order_type,
            price=price,
            trigger_price=request.trigger_price,
        )
        time.sleep(0.5)   # small wait for exchange to update status
        status = get_order_status_kite(broker["client"], str(order_id))

        if status == "REJECTED":
            history = broker["client"].order_history(str(order_id))
            reason  = history[-1].get("status_message", "Rejected by exchange")
            print(f"[REJECTED] Kite order rejected: {reason}")
            return OrderResponse(
                success=False,
                order_id=str(order_id),
                broker="kite",
                symbol=request.symbol,
                side=request.side,
                quantity=request.quantity,
                price=ltp,
                order_type=request.order_type,
                mode="LIVE",
                timestamp=timestamp,
                message=reason,
            )

        success = True
        message = ""

    return OrderResponse(
        success=True,
        order_id=str(order_id),
        broker=broker["name"],
        symbol=request.symbol,
        side=request.side,
        quantity=request.quantity,
        price=price,
        order_type=request.order_type,
        mode="LIVE",
        timestamp=timestamp,
        message=message,
    )


# ── Round-robin router — the main function ────────────────────────────────────
def place_order(brokers, request: OrderRequest, mode="MOCK") -> OrderResponse:
    """
    brokers : priority-ordered list of broker dicts
    request : OrderRequest
    mode    : "MOCK" or "LIVE"

    Broker dict structure:
    {
        "name"   : "upstox" or "kite",
        "status" : "healthy" or "unhealthy",
        "client" : api_client object,
        "token"  : access_token string (Upstox only, None for Kite),
    }
    """
    for broker in brokers:
        if broker["status"] == "unhealthy":
            print(f"[SKIP] {broker['name'].upper()} is unhealthy, trying next...")
            continue

        try:
            if mode == "MOCK":
                return _handle_mock(broker, request)
            elif mode == "LIVE":
                return _handle_live(broker, request)

        except Exception as e:
            print(f"[FAIL] {broker['name'].upper()} failed: {e}")
            broker["status"] = "unhealthy"
            print(f"[ALERT] {broker['name'].upper()} marked unhealthy. Trying next broker...")
            continue

    # All brokers failed
    print(f"[CRITICAL] All brokers failed — order dropped.")
    print(f"           {request.symbol} | {request.side} | qty={request.quantity}")
    return OrderResponse(
        success=False,
        order_id="",
        broker="none",
        symbol=request.symbol,
        side=request.side,
        quantity=request.quantity,
        price=0.0,
        order_type=request.order_type,
        mode=mode,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        message="All brokers failed",
    )


# ── Cancel and status — routed to active broker ───────────────────────────────
def cancel_order(brokers, order_id: str):
    for broker in brokers:
        if broker["status"] == "healthy":
            if broker["name"] == "upstox":
                cancel_order_upstox(broker["client"], order_id)
            elif broker["name"] == "kite":
                cancel_order_kite(broker["client"], order_id)
            return
    print("[CRITICAL] No healthy broker to cancel order.")

def get_order_status(brokers, order_id: str):
    for broker in brokers:
        if broker["status"] == "healthy":
            if broker["name"] == "upstox":
                return get_order_status_upstox(broker["client"], order_id)
            elif broker["name"] == "kite":
                return get_order_status_kite(broker["client"], order_id)
    print("[CRITICAL] No healthy broker to fetch order status.")
    return None


# ── Startup — initialise all brokers ─────────────────────────────────────────
def init_brokers() -> list:
    """
    Call once at startup. Returns the brokers list ready to pass to place_order.
    """
    upstox_client, upstox_token = upstox_gen_session()
    kite_client                 = kite_gen_session()

    brokers = [
        {
            "name":   "upstox",
            "status": "healthy",
            "client": upstox_client,
            "token":  upstox_token,
        },
        {
            "name":   "kite",
            "status": "healthy",
            "client": kite_client,
            "token":  None,          
        },
    ]
    print("Brokers initialised:")
    for b in brokers:
        print(f"  {b['name'].upper()} → {b['status']}")
    return brokers


# ── Test ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":

    brokers = init_brokers()

    # Build a standard order request
    request = OrderRequest(
        symbol="RELIANCE",
        instrument_key="NSE_EQ|INE002A01018",
        side="BUY",
        quantity=10,
        exchange="NSE",
        order_type="MARKET",
    )

    print("\n--- Test 1: Normal — Upstox healthy ---")
    response = place_order(brokers, request, mode="MOCK")
    print(f"Response: success={response.success}, broker={response.broker}, order_id={response.order_id}\n")

    print("--- Test 2: Upstox down — switches to Kite ---")
    brokers[0]["status"] = "unhealthy"
    response = place_order(brokers, request, mode="MOCK")
    print(f"Response: success={response.success}, broker={response.broker}, order_id={response.order_id}\n")

    print("--- Test 3: All brokers down ---")
    brokers[1]["status"] = "unhealthy"
    response = place_order(brokers, request, mode="MOCK")
    print(f"Response: success={response.success}, broker={response.broker}, message={response.message}")
