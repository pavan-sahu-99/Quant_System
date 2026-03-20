from dataclasses import dataclass
from datetime import datetime

# ── Order request — what goes INTO place_order ────────────────────────────────
@dataclass
class OrderRequest:

    symbol:         str         # "RELIANCE"
    instrument_key: str         # "NSE_EQ|INE002A01018" (Upstox) or "RELIANCE" (Kite)
    side:           str         # "BUY" or "SELL"
    quantity:       int
    exchange:       str         # "NSE", "NFO", "MCX"
    order_type:     str = "MARKET"   # "MARKET", "LIMIT", "SL", "SL-M"
    price:          float = 0.0      # required for LIMIT, SL
    trigger_price:  float = 0.0      # required for SL, SL-M

# ── Order response — what comes OUT of place_order ────────────────────────────
@dataclass
class OrderResponse:

    success:    bool
    order_id:   str
    broker:     str         # "upstox" or "kite" 
    symbol:     str
    side:       str
    quantity:   int
    price:      float       # actual LTP at time of order
    order_type: str
    mode:       str         # "MOCK" or "LIVE"
    timestamp:  str
    message:    str = ""    # error reason if success=False
