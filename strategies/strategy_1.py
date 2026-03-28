# strategies\strategy_1.py
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandas as pd
import numpy as np
import sqlite3
from database_organizers.db_read import get_candles_db


RESAMPLE_MAP = {
    '1min': '1T',
    '3min': '3T',
    '5min': '5T',
}

def trix(price: pd.Series, length: int = 14) -> pd.Series:
    """
    TRIX indicator
    :param price: pd.Series of prices (close)
    :param length: period
    :return: TRIX series
    """

    # log price
    log_price = np.log(price)

    # triple EMA
    ema1 = log_price.ewm(span=length, adjust=False).mean()
    ema2 = ema1.ewm(span=length, adjust=False).mean()
    ema3 = ema2.ewm(span=length, adjust=False).mean()

    # rate of change
    trix_val = (ema3 - ema3.shift(1)) * 10000

    return trix_val

def rsi(price: pd.Series, length: int = 14) -> pd.Series:
    delta = price.diff()

    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)

    gain = pd.Series(gain, index=price.index)
    loss = pd.Series(loss, index=price.index)

    avg_gain = gain.ewm(alpha=1/length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/length, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)

    return 100 - (100 / (1 + rs))

def resample_df(df: pd.DataFrame, tf: str = '3min') -> pd.DataFrame:
    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    df = df.set_index('timestamp')

    tf_resample = RESAMPLE_MAP[tf]

    df = df.resample(tf_resample, closed='left', label='left').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'ltp': 'last',
        'instrument_key': 'first',
    })
    df['timeframe'] = tf
    df = df.dropna().reset_index()
    return df


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate trading signals based on TRIX and RSI crossovers.

    Parameters :
        OverSold  = 25
        OverBought= 75
        Length    = 15   (RSI)
        Length_Trix = 9  (TRIX)

    Signal Logic:
        LONG  ( 1): TRIX crosses above 0 
                 OR RSI crosses above OverSold (25)
        SHORT (-1): TRIX crosses below 0 
                 OR RSI crosses below OverBought (75)
        HOLD  ( 0): no crossover on that bar
        Forward-filled: signal holds until a new one fires.

    """
    OVERSOLD   = 25
    OVERBOUGHT = 75

    df = df.copy()

    # TRIX crosses above 0: previous bar <= 0, current bar > 0
    trix_cross_up   = (df['trix'].shift(1) <= 0) & (df['trix'] > 0)
    trix_cross_down = (df['trix'].shift(1) >= 0) & (df['trix'] < 0)

    # RSI crosses above OverSold (25): was below, now above → LONG
    rsi_cross_up_oversold    = (df['rsi'].shift(1) <= OVERSOLD)  & (df['rsi'] > OVERSOLD)
    # RSI crosses below OverBought (75): was above, now below → SHORT
    rsi_cross_down_overbought = (df['rsi'].shift(1) >= OVERBOUGHT) & (df['rsi'] < OVERBOUGHT)

    # --- 0 = no event on this bar
    # Start with RSI signals, then overwrite with TRIX
    raw_signal = pd.Series(0, index=df.index)

    raw_signal[rsi_cross_up_oversold]      =  1   # RSI → LONG
    raw_signal[rsi_cross_down_overbought]  = -1   # RSI → SHORT
    raw_signal[trix_cross_up]              =  1   # TRIX → LONG  
    raw_signal[trix_cross_down]            = -1   # TRIX → SHORT

    # hold last signal until a new one fires
    # Replace 0s with NaN so ffill carries the last non-zero signal forward
    signal_ffill = raw_signal.replace(0, np.nan).ffill().fillna(0).astype(int)

    df['signal'] = signal_ffill

    return df


if __name__ == "__main__":
    df = get_candles_db()
    df = resample_df(df, tf='3min')
    df['trix'] = trix(df['close'], length=9)
    df['rsi']  = rsi(df['close'], length=15)
    df = generate_signals(df)
    df = df[['instrument_key', 'timestamp', 'open', 'high', 'low', 'close',
             'ltp', 'trix', 'rsi', 'signal', 'timeframe']]
    print(df)


