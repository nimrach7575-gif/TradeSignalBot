import os
from datetime import datetime, timedelta, timezone

from flask import Flask, jsonify, render_template, request, session

import main


app = Flask(__name__)

# Secret used by Flask sessions.
# For local testing this fallback is fine.
# For deployment, put a strong FLASK_SECRET_KEY in .env.
app.config["SECRET_KEY"] = os.getenv(
    "FLASK_SECRET_KEY",
    "trade-signal-bot-local-secret-change-this"
)

# Session cookie settings
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


# ============================================================
# CONFIGURATION
# ============================================================

PAIR_OPTIONS = [
    "EUR/USD",
    "GBP/USD",
    "USD/JPY",
    "USD/CHF",
    "AUD/USD",
    "USD/CAD",
    "NZD/USD",
    "EUR/GBP",
    "EUR/JPY",
    "GBP/JPY",
]

TIMEFRAME_OPTIONS = [
    {
        "value": "1",
        "label": "1 Minute",
        "interval": "1min",
    },
    {
        "value": "2",
        "label": "5 Minutes",
        "interval": "5min",
    },
    {
        "value": "3",
        "label": "15 Minutes",
        "interval": "15min",
    },
    {
        "value": "4",
        "label": "30 Minutes",
        "interval": "30min",
    },
    {
        "value": "5",
        "label": "1 Hour",
        "interval": "1h",
    },
]

EXPIRY_OPTIONS = [
    {
        "value": "1",
        "seconds": 15,
        "label": "15 Seconds",
    },
    {
        "value": "2",
        "seconds": 30,
        "label": "30 Seconds",
    },
    {
        "value": "3",
        "seconds": 60,
        "label": "1 Minute",
    },
    {
        "value": "4",
        "seconds": 120,
        "label": "2 Minutes",
    },
    {
        "value": "5",
        "seconds": 180,
        "label": "3 Minutes",
    },
    {
        "value": "6",
        "seconds": 300,
        "label": "5 Minutes",
    },
    {
        "value": "7",
        "seconds": 900,
        "label": "15 Minutes",
    },
]


# ============================================================
# HELPERS
# ============================================================

def get_timeframe(value):
    """
    Convert website timeframe value into the value expected by main.py.
    """
    value = str(value)

    for option in TIMEFRAME_OPTIONS:
        if option["value"] == value:
            return option

    return None


def get_expiry(value):
    """
    Convert website expiry value into seconds.
    """
    value = str(value)

    for option in EXPIRY_OPTIONS:
        if option["value"] == value:
            return option

    return None


def utc_now():
    """
    Return timezone-aware UTC datetime.
    """
    return datetime.now(timezone.utc)


def parse_datetime(value):
    """
    Convert an ISO datetime string into a timezone-aware datetime.
    """
    if not value:
        return None

    try:
        value = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(value)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    except Exception:
        return None


def json_number(value):
    """
    Safely convert pandas/numpy numeric values to normal JSON numbers.
    """
    if value is None:
        return None

    try:
        if hasattr(value, "item"):
            value = value.item()

        return float(value)

    except Exception:
        return None


def json_safe_result(result):
    """
    Make the result returned by main.py safe for Flask JSON.
    """
    if not isinstance(result, dict):
        return result

    cleaned = {}

    for key, value in result.items():

        if key == "time":
            try:
                cleaned[key] = main.format_utc(value)
            except Exception:
                cleaned[key] = str(value)

        elif key in {
            "price",
            "ema9",
            "ema21",
            "ema50",
            "rsi",
            "up_score",
            "down_score",
            "score",
        }:
            cleaned[key] = json_number(value)

        elif key == "reasons":
            if isinstance(value, list):
                cleaned[key] = [str(item) for item in value]
            else:
                cleaned[key] = []

        else:
            cleaned[key] = value

    return cleaned


def get_active_signal():
    """
    Get the currently locked signal from the user's Flask session.
    """
    active = session.get("active_signal")

    if not active:
        return None

    return active


def set_active_signal(signal_data):
    """
    Save the current locked signal to the user's session.
    """
    session["active_signal"] = signal_data
    session.modified = True


def clear_active_signal():
    """
    Remove the current locked signal.
    """
    session.pop("active_signal", None)
    session.modified = True


def active_signal_is_expired(active):
    """
    Check whether the signal expiry time has been reached.
    """
    if not active:
        return False

    expires_at = parse_datetime(active.get("expires_at"))

    if expires_at is None:
        return True

    return utc_now() >= expires_at


def build_active_signal(
    signal_id,
    symbol,
    timeframe,
    expiry_seconds,
    expiry_label,
    result,
    issued_at,
):
    """
    Create the session object used to lock a signal until expiry.
    """

    expires_at = issued_at + timedelta(seconds=expiry_seconds)

    return {
        "signal_id": int(signal_id),
        "symbol": symbol,
        "timeframe": timeframe,
        "expiry_seconds": int(expiry_seconds),
        "expiry_label": expiry_label,
        "direction": result.get("direction"),
        "score": json_number(result.get("score")),
        "entry_price": json_number(result.get("price")),
        "issued_at": issued_at.isoformat(),
        "expires_at": expires_at.isoformat(),
    }


# ============================================================
# FINALIZE EXPIRED SIGNAL
# ============================================================

def finalize_active_signal():
    """
    When an active signal reaches expiry:

    1. Get the latest/expiry price.
    2. Determine WIN/LOSS/FLAT.
    3. Update signal_history.csv through main.py.
    4. Clear the session lock.
    5. Return the completed result.

    Returns:
        (success, response_data)
    """

    active = get_active_signal()

    if not active:
        return False, {
            "success": False,
            "error": "No active signal."
        }

    if not active_signal_is_expired(active):
        expires_at = parse_datetime(active.get("expires_at"))

        return False, {
            "success": False,
            "locked": True,
            "signal_id": active.get("signal_id"),
            "direction": active.get("direction"),
            "score": active.get("score"),
            "entry_price": active.get("entry_price"),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "message": "Signal is still locked until expiry."
        }

    signal_id = active.get("signal_id")
    symbol = active.get("symbol")
    timeframe = active.get("timeframe")
    expiry_seconds = int(active.get("expiry_seconds", 60))
    issued_at = parse_datetime(active.get("issued_at"))

    if issued_at is None:
        issued_at = utc_now() - timedelta(seconds=expiry_seconds)

    entry_price = active.get("entry_price")
    direction = active.get("direction")

    try:
        # Get the exit price using the same engine from main.py.
        exit_price = main.get_exit_price(
            symbol,
            timeframe,
            expiry_seconds,
            issued_at
        )

        if exit_price is None:
            return False, {
                "success": False,
                "locked": True,
                "pending": True,
                "signal_id": signal_id,
                "message": (
                    "Expiry has been reached, but the exit price "
                    "is not available yet. Please check again."
                )
            }

        exit_price = float(exit_price)

        # Determine WIN / LOSS / FLAT using main.py logic.
        result_status = main.determine_result(
            direction,
            entry_price,
            exit_price
        )

        # Update persistent history.
        main.update_signal_result(
            signal_id,
            result_status,
            exit_price
        )

        # Prepare response before clearing session.
        response = {
            "success": True,
            "completed": True,
            "locked": False,
            "signal_id": signal_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "expiry_seconds": expiry_seconds,
            "expiry_label": active.get("expiry_label"),
            "direction": direction,
            "score": active.get("score"),
            "entry_price": entry_price,
            "exit_price": exit_price,
            "result": result_status,
            "issued_at": active.get("issued_at"),
            "expires_at": active.get("expires_at"),
            "result_time": utc_now().isoformat(),
        }

        # Signal is now complete, so unlock it.
        clear_active_signal()

        return True, response

    except Exception as exc:

        return False, {
            "success": False,
            "locked": True,
            "pending": True,
            "signal_id": signal_id,
            "message": f"Unable to finalize signal yet: {str(exc)}"
        }


# ============================================================
# ROUTES
# ============================================================

@app.route("/")
def home():
    """
    Main website page.
    """
    return render_template("index.html")


# ------------------------------------------------------------
# OPTIONS
# ------------------------------------------------------------

@app.route("/api/options", methods=["GET"])
def api_options():
    """
    Send selectable pairs, timeframes and expiries to the frontend.
    """

    return jsonify({
        "success": True,
        "pairs": PAIR_OPTIONS,
        "timeframes": TIMEFRAME_OPTIONS,
        "expiries": EXPIRY_OPTIONS,
        "minimum_score": main.MIN_SCORE,
    })


# ------------------------------------------------------------
# STATUS
# ------------------------------------------------------------

@app.route("/api/status", methods=["GET"])
def api_status():
    """
    Return application/backend status.

    This endpoint does not make a Twelve Data request every time,
    so refreshing the page will not unnecessarily consume API calls.
    """

    active = get_active_signal()

    if active:
        expires_at = parse_datetime(active.get("expires_at"))

        if expires_at:
            locked = utc_now() < expires_at
        else:
            locked = False

        return jsonify({
            "success": True,
            "online": True,
            "api_key_configured": bool(main.API_KEY),
            "locked": locked,
            "signal_id": active.get("signal_id"),
            "direction": active.get("direction"),
            "score": active.get("score"),
            "entry_price": active.get("entry_price"),
            "expires_at": (
                expires_at.isoformat()
                if expires_at
                else None
            ),
        })

    return jsonify({
        "success": True,
        "online": True,
        "api_key_configured": bool(main.API_KEY),
        "locked": False,
        "signal_id": None,
        "direction": None,
        "score": None,
        "entry_price": None,
        "expires_at": None,
    })


# ------------------------------------------------------------
# REQUEST SIGNAL
# ------------------------------------------------------------

@app.route("/api/request-signal", methods=["POST"])
def api_request_signal():
    """
    Generate exactly one signal.

    The request does NOT wait for expiry.

    UP/DOWN:
        Save signal -> lock -> return immediately.

    WAIT:
        Return WAIT -> user remains unlocked.

    This is intentionally manual:
        no Quotex connection
        no automatic trade
        no automatic repeated signals
    """

    try:
        data = request.get_json(silent=True) or {}

        symbol = str(data.get("symbol", "")).strip()
        timeframe_value = str(data.get("timeframe", "")).strip()
        expiry_value = str(data.get("expiry", "")).strip()

        # ----------------------------------------------------
        # Validate pair
        # ----------------------------------------------------

        if symbol not in PAIR_OPTIONS:
            return jsonify({
                "success": False,
                "error": "Invalid currency pair."
            }), 400

        # ----------------------------------------------------
        # Validate timeframe
        # ----------------------------------------------------

        timeframe_option = get_timeframe(timeframe_value)

        if timeframe_option is None:
            return jsonify({
                "success": False,
                "error": "Invalid timeframe."
            }), 400

        # ----------------------------------------------------
        # Validate expiry
        # ----------------------------------------------------

        expiry_option = get_expiry(expiry_value)

        if expiry_option is None:
            return jsonify({
                "success": False,
                "error": "Invalid expiry."
            }), 400

        timeframe = timeframe_option["interval"]
        expiry_seconds = expiry_option["seconds"]
        expiry_label = expiry_option["label"]

        # ----------------------------------------------------
        # Check existing active signal
        # ----------------------------------------------------

        active = get_active_signal()

        if active:

            if not active_signal_is_expired(active):

                expires_at = parse_datetime(
                    active.get("expires_at")
                )

                return jsonify({
                    "success": False,
                    "locked": True,
                    "signal_id": active.get("signal_id"),
                    "direction": active.get("direction"),
                    "score": active.get("score"),
                    "entry_price": active.get("entry_price"),
                    "expires_at": (
                        expires_at.isoformat()
                        if expires_at
                        else None
                    ),
                    "message": (
                        "A signal is already active. "
                        "Wait until its expiry."
                    )
                }), 409

            # ------------------------------------------------
            # Previous signal expired.
            #
            # Finalize it before allowing a new signal.
            # ------------------------------------------------

            finalized, previous_result = finalize_active_signal()

            if not finalized:

                return jsonify(previous_result), 409

        # ----------------------------------------------------
        # Generate the signal using existing main.py engine.
        # ----------------------------------------------------

        result = main.generate_one_signal(
            symbol,
            timeframe,
            expiry_seconds
        )

        if not isinstance(result, dict):
            return jsonify({
                "success": False,
                "error": "Signal engine returned an invalid response."
            }), 500

        result = json_safe_result(result)

        direction = result.get("direction")
        score = result.get("score")

        # ----------------------------------------------------
        # WAIT
        # ----------------------------------------------------

        if direction == "WAIT":

            return jsonify({
                "success": True,
                "signal_created": False,
                "locked": False,
                "symbol": symbol,
                "timeframe": timeframe,
                "timeframe_label": timeframe_option["label"],
                "expiry_seconds": expiry_seconds,
                "expiry_label": expiry_label,
                "signal": result,
                "message": (
                    "No confirmed signal. "
                    "You can request another signal."
                )
            })

        # ----------------------------------------------------
        # UP / DOWN
        # ----------------------------------------------------

        if direction not in ("UP", "DOWN"):

            return jsonify({
                "success": False,
                "error": "Unknown signal direction returned by engine."
            }), 500

        # ----------------------------------------------------
        # Issue time must be NOW.
        #
        # This is important because the market-data candle time
        # is not the same thing as the actual website request time.
        # ----------------------------------------------------

        issued_at = utc_now()

        # ----------------------------------------------------
        # Save signal into existing signal_history.csv
        # ----------------------------------------------------

        signal_id = main.save_signal(
            symbol,
            timeframe,
            expiry_seconds,
            result
        )

        if signal_id is None:

            return jsonify({
                "success": False,
                "error": "Signal could not be saved."
            }), 500

        # ----------------------------------------------------
        # Create active lock.
        # ----------------------------------------------------

        active_signal = build_active_signal(
            signal_id=signal_id,
            symbol=symbol,
            timeframe=timeframe,
            expiry_seconds=expiry_seconds,
            expiry_label=expiry_label,
            result=result,
            issued_at=issued_at,
        )

        set_active_signal(active_signal)

        expires_at = parse_datetime(
            active_signal["expires_at"]
        )

        # ----------------------------------------------------
        # Return immediately.
        #
        # We DO NOT sleep here.
        # The browser can continue working normally.
        # ----------------------------------------------------

        return jsonify({
            "success": True,
            "signal_created": True,
            "locked": True,
            "signal_id": signal_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "timeframe_label": timeframe_option["label"],
            "expiry_seconds": expiry_seconds,
            "expiry_label": expiry_label,
            "signal": result,
            "direction": direction,
            "score": score,
            "entry_price": result.get("price"),
            "issued_at": issued_at.isoformat(),
            "expires_at": (
                expires_at.isoformat()
                if expires_at
                else None
            ),
            "message": (
                f"{direction} signal generated and locked "
                f"until expiry."
            )
        })

    except Exception as exc:

        print("ERROR /api/request-signal:", exc)

        return jsonify({
            "success": False,
            "error": str(exc)
        }), 500


# ------------------------------------------------------------
# CHECK RESULT
# ------------------------------------------------------------

@app.route("/api/check-result", methods=["GET", "POST"])
def api_check_result():
    """
    Check whether the current signal has reached expiry.

    Before expiry:
        returns locked=True.

    After expiry:
        calculates exit price and WIN/LOSS/FLAT,
        updates signal_history.csv,
        unlocks the user.
    """

    try:

        active = get_active_signal()

        if not active:

            return jsonify({
                "success": True,
                "locked": False,
                "completed": False,
                "signal_id": None,
                "message": "No active signal."
            })

        # ----------------------------------------------------
        # Still locked
        # ----------------------------------------------------

        if not active_signal_is_expired(active):

            expires_at = parse_datetime(
                active.get("expires_at")
            )

            return jsonify({
                "success": True,
                "locked": True,
                "completed": False,
                "signal_id": active.get("signal_id"),
                "symbol": active.get("symbol"),
                "timeframe": active.get("timeframe"),
                "expiry_seconds": active.get("expiry_seconds"),
                "expiry_label": active.get("expiry_label"),
                "direction": active.get("direction"),
                "score": active.get("score"),
                "entry_price": active.get("entry_price"),
                "issued_at": active.get("issued_at"),
                "expires_at": (
                    expires_at.isoformat()
                    if expires_at
                    else None
                ),
                "message": "Signal is still locked."
            })

        # ----------------------------------------------------
        # Expired -> finalize
        # ----------------------------------------------------

        finalized, result = finalize_active_signal()

        if finalized:
            return jsonify(result)

        return jsonify(result), 409

    except Exception as exc:

        print("ERROR /api/check-result:", exc)

        return jsonify({
            "success": False,
            "error": str(exc)
        }), 500


# ------------------------------------------------------------
# CANCEL / RESET SESSION
# ------------------------------------------------------------

@app.route("/api/reset", methods=["POST"])
def api_reset():
    """
    Development/reset endpoint.

    This does NOT delete the signal from CSV.
    It only clears the browser's active session lock.

    Do not expose this as a normal user feature in production.
    """

    clear_active_signal()

    return jsonify({
        "success": True,
        "locked": False,
        "message": "Session reset."
    })


# ============================================================
# STARTUP
# ============================================================

def initialize_app():
    """
    Prepare signal history when Flask starts.
    """

    try:
        main.initialize_history()
        print("Signal history initialized.")

    except Exception as exc:
        print("WARNING: Could not initialize signal history:", exc)

    if main.API_KEY:
        print("Twelve Data API key detected.")
    else:
        print(
            "WARNING: TWELVE_DATA_API_KEY is not configured."
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    initialize_app()

    print("")
    print("==============================================")
    print("        TRADE SIGNAL BOT - WEB APP")
    print("==============================================")
    print("Manual signal mode")
    print("No Quotex connection")
    print("No automatic trading")
    print("No automatic repeated signals")
    print("")
    print("Open:")
    print("http://127.0.0.1:5000")
    print("==============================================")
    print("")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )