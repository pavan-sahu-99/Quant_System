# oms\oms.py
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, time
from brokers.base import OrderRequest
from brokers.connection_manager import place_order
from database_organizers.db_load import insert_order, insert_position, close_position
from database_organizers.db_read import get_open_positions
from brokers.connection_manager import init_brokers

MARKET_CLOSE    = time(15, 29, 30)
STRATEGY_NAME   = "strategy_1"
QUANTITY        = 1
EXCHANGE        = "NSE"

def _build_request(symbol: str, instrument_key: str, side: str) -> OrderRequest:
    return OrderRequest(
        symbol=symbol,
        instrument_key=instrument_key,
        side=side,
        quantity=QUANTITY,
        exchange=EXCHANGE,
        order_type="MARKET",
    )

def _save_order(response, strategy: str, instrument_key: str, trade_type: str):

    insert_order(
        order_id=response.order_id,
        broker=response.broker,
        strategy=strategy,
        symbol=response.symbol,
        instrument_key=instrument_key,
        side=response.side,
        quantity=response.quantity,
        order_type=response.order_type,
        price=response.price,
        status="PLACED" if response.success else "REJECTED",
        mode=response.mode,
        message=f"{trade_type} | {response.message}",
    )

def _square_off(position: dict, brokers: list, mode: str):
    """Exit Open Positions"""
    exit_side = "SELL" if position["side"] == "BUY" else "BUY"
    request   = _build_request(
        symbol=position["symbol"],
        instrument_key=position["instrument_key"],
        side=exit_side,
    )
    response = place_order(brokers, request, mode=mode)
    _save_order(response, position["strategy"], position["instrument_key"], trade_type="EXIT")
    
    if response.success:
        pnl = (response.price - position["entry_price"]) * position["quantity"]
        if exit_side == "BUY":   # flip PnL
            pnl = -pnl
        close_position(position["id"], round(pnl, 2))
        print(f"[OMS] Position closed -> {position['symbol']} | pnl=₹{round(pnl, 2)}")
    else:
        print(f"[OMS] Square-off FAILED for position id={position['id']}")

    return response

def process_signal(signal: int, symbol: str, instrument_key: str, brokers: list, mode: str = "MOCK"):
    """
    OMS entry point. Called on every new bar with the latest signal.
    signal : 1 = LONG, -1 = SHORT, 0 = HOLD
    """
    now = datetime.now().time()

    # -- EOD exit -- force square off at 3:29:30 PM irrespective of signal --
    if now >= MARKET_CLOSE:
        open_positions = get_open_positions(strategy=STRATEGY_NAME)
        for pos in open_positions:
            print(f"[OMS] EOD exit -> {pos['symbol']}")
            _square_off(pos, brokers, mode)
        return

    # -- HOLD --
    if signal == 0:
        return

    open_positions = get_open_positions(strategy=STRATEGY_NAME)
    current_pos    = open_positions[0] if open_positions else None

    # -- Determine side from signal --
    desired_side = "BUY" if signal == 1 else "SELL"

    # -- Already in the same direction --
    if current_pos and current_pos["side"] == desired_side:
        return

    # -- Square off existing position first (signal flipped) --
    if current_pos:
        print(f"[OMS] Signal flipped -> squaring off {current_pos['side']} first")
        _square_off(current_pos, brokers, mode)

    # -- Enter new position --
    request  = _build_request(symbol, instrument_key, desired_side)
    response = place_order(brokers, request, mode=mode)
    _save_order(response, STRATEGY_NAME, instrument_key, trade_type="ENTRY")

    if response.success:
        insert_position(
            strategy=STRATEGY_NAME,
            symbol=symbol,
            instrument_key=instrument_key,
            side=desired_side,
            quantity=QUANTITY,
            entry_price=response.price,
        )
        print(f"[OMS] {'LONG' if signal == 1 else 'SHORT'} entered -> {symbol} @ Rs.{response.price}")
    else:
        print(f"[OMS] Entry order FAILED -> {response.message}")

if __name__ == "__main__":
    brokers = init_brokers()

    # Simulation
    print("\n--- Simulate LONG entry ---")
    process_signal(1, "NIFTY", "NSE_INDEX|Nifty 50", brokers, mode="MOCK")

    print("\n--- Simulate signal flip to SHORT (should square off LONG first) ---")
    process_signal(-1, "NIFTY", "NSE_INDEX|Nifty 50", brokers, mode="MOCK")

    print("\n--- Simulate HOLD ---")
    process_signal(0, "NIFTY", "NSE_INDEX|Nifty 50", brokers, mode="MOCK")