
import os
import time
from datetime import datetime, timezone, timedelta

import requests
import pandas as pd
from dotenv import load_dotenv


# ============================================================
#                    ENVIRONMENT / CONFIG
# ============================================================

load_dotenv()

API_KEY = os.getenv("TWELVE_DATA_API_KEY")

HISTORY_FILE = "signal_history.csv"

DATA_CANDLES = 200

MIN_SCORE = 60

REQUEST_TIMEOUT = 20

# We only use this for checking data/result timing.
CHECK_SECONDS = 2


# ============================================================
#                    AVAILABLE PAIRS
# ============================================================

PAIRS = [
    "EUR/USD",
    "GBP/USD",
    "USD/JPY",
    "USD/CHF",
    "AUD/USD",
    "USD/CAD",
    "NZD/USD",
    "EUR/GBP",
    "EUR/JPY",
    "GBP/JPY"
]


# ============================================================
#                    TIMEFRAMES
# ============================================================

TIMEFRAMES = {
    "1": "1min",
    "2": "5min",
    "3": "15min",
    "4": "30min",
    "5": "1h"
}


# ============================================================
#                    EXPIRIES
# ============================================================

# Key = menu choice
# Value = number of seconds

EXPIRIES = {
    "1": 15,
    "2": 30,
    "3": 60,
    "4": 120,
    "5": 180,
    "6": 300,
    "7": 900
}


# ============================================================
#                    EXPIRY LABELS
# ============================================================

EXPIRY_LABELS = {
    15: "15 seconds",
    30: "30 seconds",
    60: "1 minute",
    120: "2 minutes",
    180: "3 minutes",
    300: "5 minutes",
    900: "15 minutes"
}


# ============================================================
#                    CSV COLUMNS
# ============================================================

HISTORY_COLUMNS = [
    "signal_id",
    "signal_time",
    "symbol",
    "timeframe",
    "expiry_seconds",
    "expiry_label",
    "entry_price",
    "ema9",
    "ema21",
    "ema50",
    "rsi",
    "up_score",
    "down_score",
    "signal",
    "result",
    "result_time",
    "exit_price"
]


# ============================================================
#                    TIME FUNCTIONS
# ============================================================

def utc_now():
    """
    Always return timezone-aware UTC datetime.
    """
    return datetime.now(timezone.utc)


def format_utc(value):
    """
    Convert datetime-like value to readable UTC text.
    """
    try:
        timestamp = pd.Timestamp(value)

        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize("UTC")
        else:
            timestamp = timestamp.tz_convert("UTC")

        return timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")

    except Exception:
        return str(value)


# ============================================================
#                    CLEAR SCREEN
# ============================================================

def clear_screen():
    """
    Clear terminal screen.
    """
    os.system("cls" if os.name == "nt" else "clear")


# ============================================================
#                    CHECK API KEY
# ============================================================

def check_api_key():

    if not API_KEY:
        print()
        print("==============================================")
        print("              API KEY ERROR")
        print("==============================================")
        print()
        print("TWELVE_DATA_API_KEY was not found.")
        print()
        print("Open your .env file and add:")
        print()
        print("TWELVE_DATA_API_KEY=YOUR_API_KEY")
        print()
        print("Then restart the program.")
        print("==============================================")
        return False

    return True


# ============================================================
#                    SELECT PAIR
# ============================================================

def choose_pair():

    print()
    print("==============================================")
    print("                 SELECT PAIR")
    print("==============================================")

    for index, pair in enumerate(PAIRS, 1):
        print(f"{index}. {pair}")

    while True:

        choice = input("\nEnter pair number: ").strip()

        try:
            number = int(choice)

            if 1 <= number <= len(PAIRS):
                return PAIRS[number - 1]

        except ValueError:
            pass

        print("Invalid choice. Please try again.")


# ============================================================
#                    SELECT TIMEFRAME
# ============================================================

def choose_timeframe():

    print()
    print("==============================================")
    print("              SELECT TIMEFRAME")
    print("==============================================")

    print("1. 1 minute")
    print("2. 5 minutes")
    print("3. 15 minutes")
    print("4. 30 minutes")
    print("5. 1 hour")

    while True:

        choice = input("\nEnter timeframe: ").strip()

        if choice in TIMEFRAMES:
            return TIMEFRAMES[choice]

        print("Invalid choice. Please try again.")


# ============================================================
#                    SELECT EXPIRY
# ============================================================

def choose_expiry():

    print()
    print("==============================================")
    print("                 SELECT EXPIRY")
    print("==============================================")

    print("1. 15 seconds")
    print("2. 30 seconds")
    print("3. 1 minute")
    print("4. 2 minutes")
    print("5. 3 minutes")
    print("6. 5 minutes")
    print("7. 15 minutes")

    while True:

        choice = input("\nEnter expiry: ").strip()

        if choice in EXPIRIES:

            seconds = EXPIRIES[choice]

            return seconds

        print("Invalid choice. Please try again.")


# ============================================================
#                    EXPIRY DISPLAY
# ============================================================

def expiry_label(seconds):

    return EXPIRY_LABELS.get(
        seconds,
        f"{seconds} seconds"
    )


# ============================================================
#                    GET MARKET DATA
# ============================================================

def get_market_data(symbol, interval):

    url = "https://api.twelvedata.com/time_series"

    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": DATA_CANDLES,
        "apikey": API_KEY
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=REQUEST_TIMEOUT
        )

        data = response.json()

        if data.get("status") != "ok":

            print()
            print("API ERROR:")
            print(data)

            return None

        values = data.get("values", [])

        if not values:
            print("No market data received.")
            return None

        df = pd.DataFrame(values)

        required = [
            "datetime",
            "open",
            "high",
            "low",
            "close"
        ]

        for column in required:

            if column not in df.columns:

                print(
                    f"Missing market-data column: {column}"
                )

                return None

        for column in [
            "open",
            "high",
            "low",
            "close"
        ]:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

        # ----------------------------------------------------
        # IMPORTANT:
        # Twelve Data may return timestamps without timezone.
        # We explicitly treat them as UTC.
        # ----------------------------------------------------

        df["datetime"] = pd.to_datetime(
            df["datetime"],
            errors="coerce",
            utc=True
        )

        df = df.dropna(
            subset=[
                "datetime",
                "open",
                "high",
                "low",
                "close"
            ]
        )

        df = df.sort_values(
            "datetime"
        )

        df = df.reset_index(
            drop=True
        )

        return df

    except requests.RequestException as error:

        print()
        print("Network error:")
        print(error)

        return None

    except Exception as error:

        print()
        print("Market-data error:")
        print(error)

        return None


# ============================================================
#                    GET CURRENT QUOTE
# ============================================================

def get_current_quote(symbol):

    url = "https://api.twelvedata.com/quote"

    params = {
        "symbol": symbol,
        "apikey": API_KEY
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=REQUEST_TIMEOUT
        )

        data = response.json()

        if data.get("status") == "error":

            print()
            print("QUOTE API ERROR:")
            print(data)

            return None

        close_value = data.get("close")

        if close_value is None:
            close_value = data.get("price")

        if close_value is None:
            return None

        return float(close_value)

    except Exception as error:

        print()
        print("Quote error:")
        print(error)

        return None


# ============================================================
#                    CALCULATE INDICATORS
# ============================================================

def calculate_indicators(df):

    df = df.copy()

    # --------------------------------------------------------
    # EMA
    # --------------------------------------------------------

    df["EMA9"] = df["close"].ewm(
        span=9,
        adjust=False
    ).mean()

    df["EMA21"] = df["close"].ewm(
        span=21,
        adjust=False
    ).mean()

    df["EMA50"] = df["close"].ewm(
        span=50,
        adjust=False
    ).mean()

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    delta = df["close"].diff()

    gain = delta.clip(
        lower=0
    )

    loss = -delta.clip(
        upper=0
    )

    avg_gain = gain.rolling(
        14
    ).mean()

    avg_loss = loss.rolling(
        14
    ).mean()

    rs = avg_gain / avg_loss

    df["RSI"] = (
        100
        -
        (
            100
            /
            (1 + rs)
        )
    )

    # --------------------------------------------------------
    # Candle
    # --------------------------------------------------------

    df["body"] = (
        df["close"]
        -
        df["open"]
    )

    df["range"] = (
        df["high"]
        -
        df["low"]
    )

    df["body_strength"] = 0.0

    valid = df["range"] > 0

    df.loc[
        valid,
        "body_strength"
    ] = (
        abs(
            df.loc[
                valid,
                "body"
            ]
        )
        /
        df.loc[
            valid,
            "range"
        ]
    )

    # --------------------------------------------------------
    # Momentum
    # --------------------------------------------------------

    df["momentum"] = (
        df["close"]
        -
        df["close"].shift(3)
    )

    return df


# ============================================================
#                    ANALYZE MARKET
# ============================================================

def analyze_market(df):

    if df is None:
        return None

    if len(df) < 60:
        return None

    # --------------------------------------------------------
    # IMPORTANT:
    # Latest row may still be forming.
    # We analyze the previous completed candle.
    # --------------------------------------------------------

    candle = df.iloc[-2]

    previous = df.iloc[-3]

    price = float(candle["close"])

    ema9 = float(candle["EMA9"])

    ema21 = float(candle["EMA21"])

    ema50 = float(candle["EMA50"])

    rsi = float(candle["RSI"])

    body = float(candle["body"])

    body_strength = float(
        candle["body_strength"]
    )

    momentum = float(
        candle["momentum"]
    )

    previous_body = float(
        previous["body"]
    )

    up = 0

    down = 0

    up_reasons = []

    down_reasons = []

    # --------------------------------------------------------
    # EMA 9 / 21
    # --------------------------------------------------------

    if ema9 > ema21:

        up += 20

        up_reasons.append(
            "EMA 9 > EMA 21"
        )

    elif ema9 < ema21:

        down += 20

        down_reasons.append(
            "EMA 9 < EMA 21"
        )

    # --------------------------------------------------------
    # EMA 21 / 50
    # --------------------------------------------------------

    if ema21 > ema50:

        up += 20

        up_reasons.append(
            "EMA 21 > EMA 50"
        )

    elif ema21 < ema50:

        down += 20

        down_reasons.append(
            "EMA 21 < EMA 50"
        )

    # --------------------------------------------------------
    # Price / EMA 50
    # --------------------------------------------------------

    if price > ema50:

        up += 10

        up_reasons.append(
            "Price above EMA 50"
        )

    elif price < ema50:

        down += 10

        down_reasons.append(
            "Price below EMA 50"
        )

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    if 50 < rsi < 68:

        up += 15

        up_reasons.append(
            f"RSI bullish ({rsi:.2f})"
        )

    elif 32 < rsi < 50:

        down += 15

        down_reasons.append(
            f"RSI bearish ({rsi:.2f})"
        )

    # Extreme RSI caution

    if rsi >= 70:

        up -= 10
        down += 5

    elif rsi <= 30:

        down -= 10
        up += 5

    # --------------------------------------------------------
    # Candle direction
    # --------------------------------------------------------

    if body > 0:

        up += 10

        up_reasons.append(
            "Bullish candle"
        )

    elif body < 0:

        down += 10

        down_reasons.append(
            "Bearish candle"
        )

    # --------------------------------------------------------
    # Candle strength
    # --------------------------------------------------------

    if body_strength >= 0.60:

        if body > 0:

            up += 5

            up_reasons.append(
                "Strong bullish candle"
            )

        elif body < 0:

            down += 5

            down_reasons.append(
                "Strong bearish candle"
            )

    # --------------------------------------------------------
    # Two candle confirmation
    # --------------------------------------------------------

    if body > 0 and previous_body > 0:

        up += 10

        up_reasons.append(
            "Two bullish candles"
        )

    elif body < 0 and previous_body < 0:

        down += 10

        down_reasons.append(
            "Two bearish candles"
        )

    # --------------------------------------------------------
    # Momentum
    # --------------------------------------------------------

    if momentum > 0:

        up += 5

        up_reasons.append(
            "Positive momentum"
        )

    elif momentum < 0:

        down += 5

        down_reasons.append(
            "Negative momentum"
        )

    # --------------------------------------------------------
    # Keep scores sane
    # --------------------------------------------------------

    up = max(
        0,
        min(
            100,
            up
        )
    )

    down = max(
        0,
        min(
            100,
            down
        )
    )

    # --------------------------------------------------------
    # Direction
    # --------------------------------------------------------

    if up > down:

        direction = "UP"

        score = up

        reasons = up_reasons

    elif down > up:

        direction = "DOWN"

        score = down

        reasons = down_reasons

    else:

        direction = "WAIT"

        score = 0

        reasons = [
            "Market direction is unclear"
        ]

    # --------------------------------------------------------
    # Minimum score
    # --------------------------------------------------------

    if score < MIN_SCORE:

        direction = "WAIT"

        reasons = [
            "Confirmation strength below threshold"
        ]

    return {
        "time": candle["datetime"],
        "price": price,
        "ema9": ema9,
        "ema21": ema21,
        "ema50": ema50,
        "rsi": rsi,
        "up_score": up,
        "down_score": down,
        "score": score,
        "direction": direction,
        "reasons": reasons
    }


# ============================================================
#                    HISTORY INITIALIZATION
# ============================================================

def initialize_history():

    if not os.path.exists(HISTORY_FILE):

        pd.DataFrame(
            columns=HISTORY_COLUMNS
        ).to_csv(
            HISTORY_FILE,
            index=False
        )

        return

    try:

        history = pd.read_csv(
            HISTORY_FILE,
            dtype=str
        )

        # ----------------------------------------------------
        # If old CSV has incompatible columns,
        # create a safe backup.
        # ----------------------------------------------------

        if list(history.columns) != HISTORY_COLUMNS:

            backup = (
                "signal_history_backup_"
                +
                utc_now().strftime(
                    "%Y%m%d_%H%M%S"
                )
                +
                ".csv"
            )

            os.rename(
                HISTORY_FILE,
                backup
            )

            print()
            print(
                "Old signal history detected."
            )

            print(
                "Backup created:",
                backup
            )

            pd.DataFrame(
                columns=HISTORY_COLUMNS
            ).to_csv(
                HISTORY_FILE,
                index=False
            )

    except Exception as error:

        print()
        print("History file could not be read safely.")
        print("Creating a new history file.")
        print(error)

        try:

            backup = (
                "signal_history_backup_"
                +
                utc_now().strftime(
                    "%Y%m%d_%H%M%S"
                )
                +
                ".csv"
            )

            os.rename(
                HISTORY_FILE,
                backup
            )

        except Exception:
            pass

        pd.DataFrame(
            columns=HISTORY_COLUMNS
        ).to_csv(
            HISTORY_FILE,
            index=False
        )


# ============================================================
#                    READ HISTORY SAFELY
# ============================================================

def read_history():

    initialize_history()

    try:

        history = pd.read_csv(
            HISTORY_FILE,
            dtype=str
        )

    except Exception:

        history = pd.DataFrame(
            columns=HISTORY_COLUMNS
        )

    # --------------------------------------------------------
    # Guarantee every column exists.
    # --------------------------------------------------------

    for column in HISTORY_COLUMNS:

        if column not in history.columns:

            history[column] = ""

    history = history[
        HISTORY_COLUMNS
    ]

    # --------------------------------------------------------
    # CRITICAL FIX:
    # Result is explicitly string/object.
    # This prevents:
    #
    # TypeError:
    # Invalid value 'WIN' for dtype float64
    # --------------------------------------------------------

    history["result"] = (
        history["result"]
        .fillna("")
        .astype("object")
    )

    return history


# ============================================================
#                    SAVE HISTORY
# ============================================================

def save_history(history):

    # Make absolutely sure result remains text.
    history["result"] = (
        history["result"]
        .fillna("")
        .astype("object")
    )

    history.to_csv(
        HISTORY_FILE,
        index=False
    )


# ============================================================
#                    SAVE SIGNAL
# ============================================================

def save_signal(
    symbol,
    timeframe,
    expiry_seconds,
    result
):

    history = read_history()

    signal_id = (
        utc_now().strftime(
            "%Y%m%d%H%M%S%f"
        )
    )

    signal_time = pd.Timestamp(
        result["time"]
    )

    if signal_time.tzinfo is None:

        signal_time = signal_time.tz_localize(
            "UTC"
        )

    else:

        signal_time = signal_time.tz_convert(
            "UTC"
        )

    row = {
        "signal_id": signal_id,

        "signal_time":
            signal_time.isoformat(),

        "symbol":
            symbol,

        "timeframe":
            timeframe,

        "expiry_seconds":
            str(expiry_seconds),

        "expiry_label":
            expiry_label(
                expiry_seconds
            ),

        "entry_price":
            str(result["price"]),

        "ema9":
            str(result["ema9"]),

        "ema21":
            str(result["ema21"]),

        "ema50":
            str(result["ema50"]),

        "rsi":
            str(result["rsi"]),

        "up_score":
            str(result["up_score"]),

        "down_score":
            str(result["down_score"]),

        "signal":
            result["direction"],

        "result":
            "",

        "result_time":
            "",

        "exit_price":
            ""
    }

    new_row = pd.DataFrame(
        [row],
        columns=HISTORY_COLUMNS
    )

    history = pd.concat(
        [
            history,
            new_row
        ],
        ignore_index=True
    )

    save_history(
        history
    )

    return signal_id


# ============================================================
#                    GET SIGNAL RECORD
# ============================================================

def get_signal_record(signal_id):

    history = read_history()

    if history.empty:
        return None

    matches = history[
        history["signal_id"].astype(str)
        ==
        str(signal_id)
    ]

    if matches.empty:
        return None

    return matches.iloc[-1]


# ============================================================
#                    CALCULATE RESULT
# ============================================================

def determine_result(
    signal,
    entry_price,
    exit_price
):

    if exit_price > entry_price:

        market_direction = "UP"

    elif exit_price < entry_price:

        market_direction = "DOWN"

    else:

        market_direction = "FLAT"

    if market_direction == "FLAT":

        return "FLAT"

    if signal == market_direction:

        return "WIN"

    return "LOSS"


# ============================================================
#                    WAIT FOR EXPIRY
# ============================================================

def wait_for_expiry(
    expiry_seconds
):

    target = (
        utc_now()
        +
        timedelta(
            seconds=expiry_seconds
        )
    )

    print()
    print("----------------------------------------------")
    print(
        "🔒 SIGNAL LOCKED"
    )

    print(
        "No new signal will be generated."
    )

    print(
        "The signal remains locked for:",
        expiry_label(expiry_seconds)
    )

    print("----------------------------------------------")

    # --------------------------------------------------------
    # IMPORTANT:
    # No countdown is shown.
    # No new signal is generated.
    # --------------------------------------------------------

    while True:

        remaining = (
            target
            -
            utc_now()
        )

        if remaining.total_seconds() <= 0:
            break

        time.sleep(
            min(
                CHECK_SECONDS,
                max(
                    0.1,
                    remaining.total_seconds()
                )
            )
        )

    return target


# ============================================================
#                    GET EXIT PRICE
# ============================================================

def get_exit_price(
    symbol,
    timeframe,
    expiry_seconds,
    entry_time
):

    # --------------------------------------------------------
    # For short expiries, use the current quote at the
    # actual expiry time.
    #
    # This is more appropriate than pretending a 1-minute
    # candle can provide a true 15-second candle.
    # --------------------------------------------------------

    if expiry_seconds < 60:

        price = get_current_quote(
            symbol
        )

        if price is not None:
            return price

    # --------------------------------------------------------
    # For 1m+ expiries, try to find a candle at/after
    # the expiry point.
    # --------------------------------------------------------

    df = get_market_data(
        symbol,
        timeframe
    )

    if df is not None and not df.empty:

        expiry_time = (
            entry_time
            +
            timedelta(
                seconds=expiry_seconds
            )
        )

        df = df.copy()

        df["datetime"] = pd.to_datetime(
            df["datetime"],
            errors="coerce",
            utc=True
        )

        candidates = df[
            df["datetime"] >=
            pd.Timestamp(
                expiry_time
            )
        ]

        if not candidates.empty:

            return float(
                candidates.iloc[0]["close"]
            )

        # ----------------------------------------------------
        # If exact expiry candle isn't available,
        # use the latest available quote.
        # ----------------------------------------------------

        price = get_current_quote(
            symbol
        )

        if price is not None:
            return price

    # --------------------------------------------------------
    # Final fallback
    # --------------------------------------------------------

    return get_current_quote(
        symbol
    )


# ============================================================
#                    UPDATE RESULT
# ============================================================

def update_signal_result(
    signal_id,
    result,
    exit_price
):

    history = read_history()

    if history.empty:
        return False

    matches = history[
        history["signal_id"].astype(str)
        ==
        str(signal_id)
    ]

    if matches.empty:
        return False

    index = matches.index[-1]

    # --------------------------------------------------------
    # CRITICAL:
    # Assign strings into explicitly object/string columns.
    # --------------------------------------------------------

    history["result"] = (
        history["result"]
        .fillna("")
        .astype("object")
    )

    history["exit_price"] = (
        history["exit_price"]
        .fillna("")
        .astype("object")
    )

    history["result_time"] = (
        history["result_time"]
        .fillna("")
        .astype("object")
    )

    history.at[
        index,
        "result"
    ] = str(result)

    history.at[
        index,
        "exit_price"
    ] = str(exit_price)

    history.at[
        index,
        "result_time"
    ] = utc_now().isoformat()

    save_history(
        history
    )

    return True


# ============================================================
#                    DISPLAY SETTINGS
# ============================================================

def display_settings(
    symbol,
    timeframe,
    expiry_seconds
):

    print()
    print("==============================================")
    print("                 SETTINGS")
    print("==============================================")

    print(
        "Pair:",
        symbol
    )

    print(
        "Chart timeframe:",
        timeframe
    )

    print(
        "Trade expiry:",
        expiry_label(
            expiry_seconds
        )
    )

    print(
        "Minimum signal score:",
        MIN_SCORE
    )

    print("==============================================")


# ============================================================
#                    DISPLAY SIGNAL
# ============================================================

def display_signal(
    symbol,
    timeframe,
    expiry_seconds,
    result
):

    print()
    print("==============================================")
    print("              MARKET SIGNAL")
    print("==============================================")

    print(
        "Pair:",
        symbol
    )

    print(
        "Chart:",
        timeframe
    )

    print(
        "Expiry:",
        expiry_label(
            expiry_seconds
        )
    )

    print(
        "Signal candle:",
        format_utc(
            result["time"]
        )
    )

    print(
        "Price:",
        f"{result['price']:.5f}"
    )

    print("----------------------------------------------")

    print(
        "EMA 9:",
        f"{result['ema9']:.5f}"
    )

    print(
        "EMA 21:",
        f"{result['ema21']:.5f}"
    )

    print(
        "EMA 50:",
        f"{result['ema50']:.5f}"
    )

    print(
        "RSI:",
        f"{result['rsi']:.2f}"
    )

    print("----------------------------------------------")

    if result["direction"] == "UP":

        print(
            "🟢 SIGNAL: UP"
        )

    elif result["direction"] == "DOWN":

        print(
            "🔴 SIGNAL: DOWN"
        )

    else:

        print(
            "⚪ SIGNAL: WAIT"
        )

    print(
        "Signal score:",
        result["score"]
    )

    print("----------------------------------------------")

    print("Reasons:")

    for reason in result["reasons"]:

        print(
            " •",
            reason
        )

    print("----------------------------------------------")

    if result["direction"] in [
        "UP",
        "DOWN"
    ]:

        print(
            "🔒 SIGNAL WILL BE LOCKED"
        )

    else:

        print(
            "No trade signal."
        )

    print("----------------------------------------------")

    print(
        "MANUAL TRADING ONLY"
    )

    print(
        "No Quotex connection"
    )

    print(
        "No automatic trading"
    )

    print("==============================================")


# ============================================================
#                    DISPLAY LOCKED SIGNAL
# ============================================================

def display_locked_signal(
    symbol,
    timeframe,
    expiry_seconds,
    result
):

    print()
    print("==============================================")
    print("              🔒 SIGNAL LOCKED")
    print("==============================================")

    print(
        "Pair:",
        symbol
    )

    print(
        "Chart:",
        timeframe
    )

    print(
        "Expiry:",
        expiry_label(
            expiry_seconds
        )
    )

    print("----------------------------------------------")

    if result["direction"] == "UP":

        print(
            "🟢 SIGNAL: UP"
        )

    else:

        print(
            "🔴 SIGNAL: DOWN"
        )

    print(
        "Signal score:",
        result["score"]
    )

    print(
        "Entry price:",
        f"{result['price']:.5f}"
    )

    print(
        "Signal candle:",
        format_utc(
            result["time"]
        )
    )

    print("----------------------------------------------")

    print(
        "🔒 THIS SIGNAL IS LOCKED"
    )

    print(
        "No new signal will be generated"
    )

    print(
        "until the expiry period is completed."
    )

    print(
        "After expiry, the client can request"
    )

    print(
        "a completely new signal."
    )

    print("==============================================")


# ============================================================
#                    DISPLAY RESULT
# ============================================================

def display_result(
    symbol,
    timeframe,
    expiry_seconds,
    signal,
    entry_price,
    exit_price,
    outcome
):

    print()
    print("==============================================")
    print("                SIGNAL RESULT")
    print("==============================================")

    print(
        "Pair:",
        symbol
    )

    print(
        "Chart:",
        timeframe
    )

    print(
        "Expiry:",
        expiry_label(
            expiry_seconds
        )
    )

    print("----------------------------------------------")

    print(
        "Signal:",
        signal
    )

    print(
        "Entry price:",
        f"{entry_price:.5f}"
    )

    print(
        "Exit price:",
        f"{exit_price:.5f}"
    )

    print("----------------------------------------------")

    if outcome == "WIN":

        print(
            "✅ RESULT: WIN"
        )

    elif outcome == "LOSS":

        print(
            "❌ RESULT: LOSS"
        )

    else:

        print(
            "⚪ RESULT: FLAT"
        )

    print("----------------------------------------------")

    print(
        "The previous signal is now closed."
    )

    print(
        "No signal will be generated automatically."
    )

    print("==============================================")


# ============================================================
#                    PERFORMANCE
# ============================================================

def show_statistics(
    symbol,
    timeframe,
    expiry_seconds
):

    history = read_history()

    if history.empty:
        return

    filtered = history[
        (
            history["symbol"].astype(str)
            ==
            symbol
        )
        &
        (
            history["timeframe"].astype(str)
            ==
            timeframe
        )
        &
        (
            pd.to_numeric(
                history["expiry_seconds"],
                errors="coerce"
            )
            ==
            expiry_seconds
        )
    ]

    if filtered.empty:
        return

    completed = filtered[
        filtered["result"].isin(
            [
                "WIN",
                "LOSS",
                "FLAT"
            ]
        )
    ]

    if completed.empty:
        return

    wins = (
        completed["result"]
        ==
        "WIN"
    ).sum()

    losses = (
        completed["result"]
        ==
        "LOSS"
    ).sum()

    flats = (
        completed["result"]
        ==
        "FLAT"
    ).sum()

    decided = (
        wins
        +
        losses
    )

    if decided > 0:

        accuracy = (
            wins
            /
            decided
        ) * 100

    else:

        accuracy = 0

    print()
    print("==============================================")
    print("                PERFORMANCE")
    print("==============================================")

    print(
        "Pair:",
        symbol
    )

    print(
        "Timeframe:",
        timeframe
    )

    print(
        "Expiry:",
        expiry_label(
            expiry_seconds
        )
    )

    print("----------------------------------------------")

    print(
        "Completed:",
        len(completed)
    )

    print(
        "Wins:",
        wins
    )

    print(
        "Losses:",
        losses
    )

    print(
        "Flat:",
        flats
    )

    print(
        "Accuracy:",
        f"{accuracy:.2f}%"
    )

    print("==============================================")


# ============================================================
#                    REQUEST NEW SIGNAL
# ============================================================

def request_new_signal():

    print()
    print("==============================================")
    print("             NEW SIGNAL REQUEST")
    print("==============================================")

    print(
        "The client is requesting ONE new signal."
    )

    print(
        "The client must select the settings again."
    )

    print("==============================================")


# ============================================================
#                    GENERATE ONE SIGNAL
# ============================================================

def generate_one_signal(
    symbol,
    timeframe,
    expiry_seconds
):

    print()
    print("----------------------------------------------")
    print(
        "Downloading market data..."
    )

    df = get_market_data(
        symbol,
        timeframe
    )

    if df is None:

        print(
            "Unable to download market data."
        )

        return None

    if len(df) < 60:

        print(
            "Not enough candles for analysis."
        )

        return None

    df = calculate_indicators(
        df
    )

    result = analyze_market(
        df
    )

    return result


# ============================================================
#                    PROCESS SIGNAL
# ============================================================

def process_signal_request():

    request_new_signal()

    # --------------------------------------------------------
    # Client selects everything again.
    # --------------------------------------------------------

    symbol = choose_pair()

    timeframe = choose_timeframe()

    expiry_seconds = choose_expiry()

    display_settings(
        symbol,
        timeframe,
        expiry_seconds
    )

    print()
    print(
        "Analyzing latest completed candle..."
    )

    result = generate_one_signal(
        symbol,
        timeframe,
        expiry_seconds
    )

    if result is None:

        print()
        print(
            "Signal generation failed."
        )

        input(
            "\nPress Enter to return to the request menu..."
        )

        return

    # --------------------------------------------------------
    # Display ONE signal.
    # --------------------------------------------------------

    display_signal(
        symbol,
        timeframe,
        expiry_seconds,
        result
    )

    # --------------------------------------------------------
    # WAIT is not a trade.
    #
    # We do not continuously generate WAIT signals.
    # Client must request another signal.
    # --------------------------------------------------------

    if result["direction"] == "WAIT":

        print()
        print(
            "⚪ WAIT — no trade signal."
        )

        print(
            "No new signal will be generated automatically."
        )

        print(
            "The client can request another signal"
        )

        print(
            "from the main menu."
        )

        input(
            "\nPress Enter to request another signal..."
        )

        return

    # --------------------------------------------------------
    # Save signal.
    # --------------------------------------------------------

    signal_id = save_signal(
        symbol,
        timeframe,
        expiry_seconds,
        result
    )

    # --------------------------------------------------------
    # Show locked signal.
    # --------------------------------------------------------

    display_locked_signal(
        symbol,
        timeframe,
        expiry_seconds,
        result
    )

    # --------------------------------------------------------
    # Calculate actual expiry moment.
    #
    # We intentionally DO NOT display a countdown.
    # --------------------------------------------------------

    signal_time = pd.Timestamp(
        result["time"]
    )

    if signal_time.tzinfo is None:

        signal_time = signal_time.tz_localize(
            "UTC"
        )

    else:

        signal_time = signal_time.tz_convert(
            "UTC"
        )

    expiry_target = (
        signal_time
        +
        pd.Timedelta(
            seconds=expiry_seconds
        )
    )

    # --------------------------------------------------------
    # If signal candle is already old, don't wait from the
    # historical candle timestamp. Instead, use current UTC
    # time when the signal was actually issued.
    #
    # This fixes the "old candle / huge remaining time"
    # problem.
    # --------------------------------------------------------

    issued_at = utc_now()

    real_expiry = (
        issued_at
        +
        timedelta(
            seconds=expiry_seconds
        )
    )

    print()
    print(
        "🔒 Signal issued at:",
        format_utc(
            issued_at
        )
    )

    print(
        "🔒 Signal will remain locked until:",
        format_utc(
            real_expiry
        )
    )

    print()
    print(
        "The bot will NOT generate another signal."
    )

    print(
        "Waiting silently for the selected expiry..."
    )

    # --------------------------------------------------------
    # Wait.
    # --------------------------------------------------------

    while utc_now() < real_expiry:

        remaining = (
            real_expiry
            -
            utc_now()
        )

        sleep_seconds = min(
            CHECK_SECONDS,
            max(
                0.1,
                remaining.total_seconds()
            )
        )

        time.sleep(
            sleep_seconds
        )

    print()
    print(
        "🔓 SIGNAL EXPIRY COMPLETED"
    )

    # --------------------------------------------------------
    # Get exit price.
    # --------------------------------------------------------

    print()
    print(
        "Checking expiry price..."
    )

    exit_price = get_exit_price(
        symbol,
        timeframe,
        expiry_seconds,
        issued_at
    )

    if exit_price is None:

        print()
        print(
            "Could not obtain an expiry price."
        )

        print(
            "The signal remains recorded as pending."
        )

        input(
            "\nPress Enter to return to the menu..."
        )

        return

    # --------------------------------------------------------
    # Determine result.
    # --------------------------------------------------------

    entry_price = float(
        result["price"]
    )

    outcome = determine_result(
        result["direction"],
        entry_price,
        exit_price
    )

    # --------------------------------------------------------
    # Save result.
    # --------------------------------------------------------

    update_signal_result(
        signal_id,
        outcome,
        exit_price
    )

    # --------------------------------------------------------
    # Display result.
    # --------------------------------------------------------

    display_result(
        symbol,
        timeframe,
        expiry_seconds,
        result["direction"],
        entry_price,
        exit_price,
        outcome
    )

    # --------------------------------------------------------
    # Statistics.
    # --------------------------------------------------------

    show_statistics(
        symbol,
        timeframe,
        expiry_seconds
    )

    print()
    print(
        "=============================================="
    )

    print(
        "Ready for a new client request."
    )

    print(
        "No signal will be generated automatically."
    )

    print(
        "=============================================="
    )

    input(
        "\nPress Enter to request a NEW SIGNAL..."
    )


# ============================================================
#                    MAIN MENU
# ============================================================

def main_menu():

    while True:

        clear_screen()

        print()
        print("==============================================")
        print("            FINAL SIGNAL ASSISTANT")
        print("==============================================")

        print(
            "Manual trading only."
        )

        print(
            "No Quotex connection."
        )

        print(
            "No automatic trading."
        )

        print(
            "One signal per client request."
        )

        print(
            "Signals remain locked during expiry."
        )

        print(
            "No automatic repeated signals."
        )

        print("==============================================")

        print()
        print("1. REQUEST NEW SIGNAL")
        print("2. EXIT")

        choice = input(
            "\nChoose option: "
        ).strip()

        if choice == "1":

            try:

                process_signal_request()

            except KeyboardInterrupt:

                print()
                print()
                print(
                    "Program stopped by user."
                )

                break

            except Exception as error:

                print()
                print("==============================================")
                print("                 PROGRAM ERROR")
                print("==============================================")

                print(
                    type(error).__name__
                )

                print(
                    error
                )

                print("==============================================")

                input(
                    "\nPress Enter to return to the menu..."
                )

        elif choice == "2":

            print()
            print(
                "Signal assistant closed."
            )

            break

        else:

            print(
                "Invalid option."
            )

            time.sleep(1)


# ============================================================
#                    PROGRAM START
# ============================================================

if __name__ == "__main__":

    initialize_history()

    if not check_api_key():

        input(
            "\nPress Enter to exit..."
        )

    else:

        main_menu()
