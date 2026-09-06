"use strict";

/* ============================================================
   TRADE SIGNAL BOT
   Frontend Controller
   ============================================================ */


/* ============================================================
   GLOBAL STATE
   ============================================================ */

const state = {
    optionsLoaded: false,
    busy: false,
    locked: false,

    activeSignalId: null,

    issuedAt: null,
    expiresAt: null,

    expiryTimer: null,
    resultPollTimer: null,

    pairs: [],
    timeframes: [],
    expiries: [],

    minimumScore: 60
};


/* ============================================================
   DOM ELEMENTS
   ============================================================ */

const pairSelect = document.getElementById("pairSelect");
const timeframeSelect = document.getElementById("timeframeSelect");
const expirySelect = document.getElementById("expirySelect");

const requestSignalBtn = document.getElementById(
    "requestSignalBtn"
);

const requestButtonText = document.getElementById(
    "requestButtonText"
);

const requestButtonIcon = document.getElementById(
    "requestButtonIcon"
);

const thresholdValue = document.getElementById(
    "thresholdValue"
);

const signalEmpty = document.getElementById(
    "signalEmpty"
);

const signalResult = document.getElementById(
    "signalResult"
);

const directionCard = document.getElementById(
    "directionCard"
);

const directionLabel = document.getElementById(
    "directionLabel"
);

const signalId = document.getElementById(
    "signalId"
);

const directionArrow = document.getElementById(
    "directionArrow"
);

const directionValue = document.getElementById(
    "directionValue"
);

const directionDescription = document.getElementById(
    "directionDescription"
);

const scoreValue = document.getElementById(
    "scoreValue"
);

const entryPriceValue = document.getElementById(
    "entryPriceValue"
);

const timeframeValue = document.getElementById(
    "timeframeValue"
);

const expiryValue = document.getElementById(
    "expiryValue"
);

const ema9Value = document.getElementById(
    "ema9Value"
);

const ema21Value = document.getElementById(
    "ema21Value"
);

const ema50Value = document.getElementById(
    "ema50Value"
);

const rsiValue = document.getElementById(
    "rsiValue"
);

const reasonsList = document.getElementById(
    "reasonsList"
);

const lockPanel = document.getElementById(
    "lockPanel"
);

const lockTitle = document.getElementById(
    "lockTitle"
);

const lockDescription = document.getElementById(
    "lockDescription"
);

const lockStatusBadge = document.getElementById(
    "lockStatusBadge"
);

const finalResultPanel = document.getElementById(
    "finalResultPanel"
);

const resultBadge = document.getElementById(
    "resultBadge"
);

const resultEntryPrice = document.getElementById(
    "resultEntryPrice"
);

const resultExitPrice = document.getElementById(
    "resultExitPrice"
);

const marketPair = document.getElementById(
    "marketPair"
);

const marketTimeframe = document.getElementById(
    "marketTimeframe"
);

const marketExpiry = document.getElementById(
    "marketExpiry"
);

const errorMessage = document.getElementById(
    "errorMessage"
);

const errorMessageText = document.getElementById(
    "errorMessageText"
);

const loadingOverlay = document.getElementById(
    "loadingOverlay"
);

const loadingText = document.getElementById(
    "loadingText"
);

const loadingProgressBar = document.getElementById(
    "loadingProgressBar"
);

const toast = document.getElementById(
    "toast"
);

const toastIcon = document.getElementById(
    "toastIcon"
);

const toastTitle = document.getElementById(
    "toastTitle"
);

const toastMessage = document.getElementById(
    "toastMessage"
);

const toastClose = document.getElementById(
    "toastClose"
);

const statusDot = document.getElementById(
    "statusDot"
);

const statusText = document.getElementById(
    "statusText"
);

const footerStatusDot = document.getElementById(
    "footerStatusDot"
);

const footerStatusText = document.getElementById(
    "footerStatusText"
);


/* ============================================================
   INITIALIZATION
   ============================================================ */

document.addEventListener("DOMContentLoaded", () => {

    initializeEventListeners();

    initializeApplication();

});


/* ============================================================
   EVENT LISTENERS
   ============================================================ */

function initializeEventListeners() {

    if (pairSelect) {
        pairSelect.addEventListener(
            "change",
            handleConfigurationChange
        );
    }


    if (timeframeSelect) {
        timeframeSelect.addEventListener(
            "change",
            handleConfigurationChange
        );
    }


    if (expirySelect) {
        expirySelect.addEventListener(
            "change",
            handleConfigurationChange
        );
    }


    if (requestSignalBtn) {
        requestSignalBtn.addEventListener(
            "click",
            requestSignal
        );
    }


    if (toastClose) {
        toastClose.addEventListener(
            "click",
            hideToast
        );
    }

}


/* ============================================================
   APPLICATION START
   ============================================================ */

async function initializeApplication() {

    setRequestButton(
        "disabled",
        "Loading...",
        "↗"
    );

    try {

        await loadOptions();

        await checkServerStatus();

        await restoreActiveSignal();

        updateMarketSnapshot();

        updateRequestButtonState();

    } catch (error) {

        console.error(
            "Application initialization error:",
            error
        );

        showError(
            "Unable to initialize the dashboard. "
            + "Please refresh the page."
        );

        setSystemStatus(
            false,
            "System unavailable"
        );

    }

}


/* ============================================================
   LOAD OPTIONS
   ============================================================ */

async function loadOptions() {

    try {

        const response = await fetch(
            "/api/options",
            {
                method: "GET",
                headers: {
                    "Accept": "application/json"
                },
                cache: "no-store"
            }
        );

        const data = await parseJsonResponse(response);

        if (!response.ok || !data.success) {

            throw new Error(
                data.error ||
                "Could not load configuration options."
            );

        }


        state.pairs = data.pairs || [];
        state.timeframes = data.timeframes || [];
        state.expiries = data.expiries || [];

        state.minimumScore =
            Number(data.minimum_score ?? 60);


        populatePairOptions();
        populateTimeframeOptions();
        populateExpiryOptions();


        thresholdValue.textContent =
            `${state.minimumScore}`;


        state.optionsLoaded = true;


        // Set sensible defaults.
        if (state.pairs.length > 0) {
            pairSelect.value = state.pairs[0];
        }

        if (state.timeframes.length > 0) {
            timeframeSelect.value =
                state.timeframes[0].value;
        }

        if (state.expiries.length > 0) {
            expirySelect.value =
                state.expiries[2]
                    ? state.expiries[2].value
                    : state.expiries[0].value;
        }


        updateMarketSnapshot();

    } catch (error) {

        console.error(
            "Options loading error:",
            error
        );

        showError(
            error.message ||
            "Could not load trading options."
        );

        throw error;
    }

}


/* ============================================================
   POPULATE PAIRS
   ============================================================ */

function populatePairOptions() {

    pairSelect.innerHTML = "";

    state.pairs.forEach((pair) => {

        const option =
            document.createElement("option");

        option.value = pair;
        option.textContent = pair;

        pairSelect.appendChild(option);

    });

}


/* ============================================================
   POPULATE TIMEFRAMES
   ============================================================ */

function populateTimeframeOptions() {

    timeframeSelect.innerHTML = "";

    state.timeframes.forEach((timeframe) => {

        const option =
            document.createElement("option");

        option.value = timeframe.value;
        option.textContent = timeframe.label;

        timeframeSelect.appendChild(option);

    });

}


/* ============================================================
   POPULATE EXPIRIES
   ============================================================ */

function populateExpiryOptions() {

    expirySelect.innerHTML = "";

    state.expiries.forEach((expiry) => {

        const option =
            document.createElement("option");

        option.value = expiry.value;
        option.textContent = expiry.label;

        expirySelect.appendChild(option);

    });

}


/* ============================================================
   SERVER STATUS
   ============================================================ */

async function checkServerStatus() {

    try {

        const response = await fetch(
            "/api/status",
            {
                method: "GET",
                headers: {
                    "Accept": "application/json"
                },
                cache: "no-store"
            }
        );

        const data =
            await parseJsonResponse(response);


        if (!response.ok || !data.success) {

            throw new Error(
                data.error ||
                "Backend status check failed."
            );

        }


        if (data.online && data.api_key_configured) {

            setSystemStatus(
                true,
                "System Online"
            );

        } else if (data.online) {

            setSystemStatus(
                false,
                "API key not configured"
            );

        } else {

            setSystemStatus(
                false,
                "System Offline"
            );

        }


        if (data.locked) {

            state.locked = true;
            state.activeSignalId =
                data.signal_id;

            state.expiresAt =
                data.expires_at;

            updateRequestButtonState();

        }

    } catch (error) {

        console.error(
            "Status check error:",
            error
        );

        setSystemStatus(
            false,
            "Connection error"
        );

    }

}


/* ============================================================
   RESTORE ACTIVE SIGNAL
   ============================================================ */

async function restoreActiveSignal() {

    try {

        const response = await fetch(
            "/api/check-result",
            {
                method: "GET",
                headers: {
                    "Accept": "application/json"
                },
                cache: "no-store"
            }
        );


        const data =
            await parseJsonResponse(response);


        if (!data.success) {
            return;
        }


        if (data.completed) {

            displayCompletedResult(data);

            return;
        }


        if (data.locked) {

            state.locked = true;

            state.activeSignalId =
                data.signal_id;

            state.issuedAt =
                data.issued_at;

            state.expiresAt =
                data.expires_at;


            displayRestoredLockedSignal(data);

            startExpiryWatcher();

            updateRequestButtonState();

        }

    } catch (error) {

        console.error(
            "Active signal restoration error:",
            error
        );

    }

}


/* ============================================================
   HANDLE CONFIGURATION CHANGE
   ============================================================ */

function handleConfigurationChange() {

    updateMarketSnapshot();

    hideError();

    if (!state.locked) {
        updateRequestButtonState();
    }

}


/* ============================================================
   UPDATE MARKET SNAPSHOT
   ============================================================ */

function updateMarketSnapshot() {

    if (!pairSelect ||
        !timeframeSelect ||
        !expirySelect) {

        return;
    }


    const selectedPair =
        pairSelect.options[
            pairSelect.selectedIndex
        ];


    const selectedTimeframe =
        timeframeSelect.options[
            timeframeSelect.selectedIndex
        ];


    const selectedExpiry =
        expirySelect.options[
            expirySelect.selectedIndex
        ];


    marketPair.textContent =
        selectedPair
            ? selectedPair.textContent
            : "--";


    marketTimeframe.textContent =
        selectedTimeframe
            ? selectedTimeframe.textContent
            : "--";


    marketExpiry.textContent =
        selectedExpiry
            ? selectedExpiry.textContent
            : "--";

}


/* ============================================================
   REQUEST BUTTON STATE
   ============================================================ */

function updateRequestButtonState() {

    if (!requestSignalBtn) {
        return;
    }


    if (state.busy) {

        setRequestButton(
            "loading",
            "Analyzing...",
            ""
        );

        return;
    }


    if (state.locked) {

        setRequestButton(
            "disabled",
            "Signal Locked",
            "🔒"
        );

        return;
    }


    if (!state.optionsLoaded) {

        setRequestButton(
            "disabled",
            "Loading...",
            "↗"
        );

        return;
    }


    const validConfiguration =
        pairSelect.value &&
        timeframeSelect.value &&
        expirySelect.value;


    if (!validConfiguration) {

        setRequestButton(
            "disabled",
            "Select Options",
            "↗"
        );

        return;
    }


    setRequestButton(
        "enabled",
        "Request Signal",
        "↗"
    );

}


/* ============================================================
   SET REQUEST BUTTON
   ============================================================ */

function setRequestButton(
    status,
    text,
    icon
) {

    if (!requestSignalBtn) {
        return;
    }


    requestButtonText.textContent = text;

    requestButtonIcon.textContent = icon;


    requestSignalBtn.classList.remove(
        "loading-button"
    );


    if (status === "loading") {

        requestSignalBtn.disabled = true;

        requestSignalBtn.classList.add(
            "loading-button"
        );

        return;
    }


    if (status === "disabled") {

        requestSignalBtn.disabled = true;

        return;
    }


    requestSignalBtn.disabled = false;

}


/* ============================================================
   REQUEST SIGNAL
   ============================================================ */

async function requestSignal() {

    if (state.busy) {
        return;
    }


    if (state.locked) {

        showToast(
            "Signal Locked",
            "Wait until the current signal expires.",
            "warning"
        );

        return;
    }


    const symbol =
        pairSelect.value;

    const timeframe =
        timeframeSelect.value;

    const expiry =
        expirySelect.value;


    if (!symbol ||
        !timeframe ||
        !expiry) {

        showError(
            "Please select a currency pair, "
            + "timeframe and expiry."
        );

        return;
    }


    hideError();


    state.busy = true;

    updateRequestButtonState();

    showLoading();


    try {

        updateLoadingText(
            "Downloading market data..."
        );


        await smallDelay(250);


        updateLoadingText(
            "Calculating EMA and RSI indicators..."
        );


        const response = await fetch(
            "/api/request-signal",
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json",

                    "Accept":
                        "application/json"
                },

                body: JSON.stringify({
                    symbol: symbol,
                    timeframe: timeframe,
                    expiry: expiry
                })
            }
        );


        updateLoadingText(
            "Evaluating signal confirmation..."
        );


        const data =
            await parseJsonResponse(response);


        hideLoading();


        if (response.status === 409) {

            handleLockedResponse(data);

            return;
        }


        if (!response.ok ||
            !data.success) {

            throw new Error(
                data.error ||
                "Signal request failed."
            );

        }


        // ------------------------------------------------
        // WAIT
        // ------------------------------------------------

        if (data.signal_created === false) {

            state.busy = false;

            state.locked = false;

            updateRequestButtonState();

            displayWaitSignal(data);

            showToast(
                "No Confirmed Signal",
                "The market did not meet the confirmation threshold.",
                "warning"
            );

            return;
        }


        // ------------------------------------------------
        // UP / DOWN
        // ------------------------------------------------

        if (data.signal_created) {

            state.busy = false;

            state.locked = true;

            state.activeSignalId =
                data.signal_id;

            state.issuedAt =
                data.issued_at;

            state.expiresAt =
                data.expires_at;


            displayActiveSignal(data);

            updateRequestButtonState();

            startExpiryWatcher();


            showToast(
                `${data.direction} Signal Generated`,
                `Signal #${data.signal_id} is now locked until expiry.`,
                "success"
            );

        }

    } catch (error) {

        hideLoading();

        state.busy = false;

        state.locked = false;

        updateRequestButtonState();


        console.error(
            "Signal request error:",
            error
        );


        showError(
            error.message ||
            "Unable to generate signal."
        );


        showToast(
            "Request Failed",
            error.message ||
                "Unable to generate signal.",
            "error"
        );

    }

}


/* ============================================================
   DISPLAY ACTIVE SIGNAL
   ============================================================ */

function displayActiveSignal(data) {

    const signal =
        data.signal || {};


    signalEmpty.hidden = true;

    signalResult.hidden = false;

    finalResultPanel.hidden = true;


    const direction =
        data.direction ||
        signal.direction ||
        "WAIT";


    setDirectionAppearance(
        direction
    );


    directionValue.textContent =
        direction;


    directionDescription.textContent =
        direction === "UP"
            ? "Bullish market confirmation"
            : "Bearish market confirmation";


    directionLabel.textContent =
        direction === "UP"
            ? "UP SIGNAL"
            : "DOWN SIGNAL";


    signalId.textContent =
        `#${data.signal_id ?? "----"}`;


    directionArrow.textContent =
        direction === "UP"
            ? "↑"
            : "↓";


    scoreValue.textContent =
        formatNumber(
            data.score ??
            signal.score
        );


    entryPriceValue.textContent =
        formatPrice(
            data.entry_price ??
            signal.price
        );


    timeframeValue.textContent =
        data.timeframe_label ||
        getTimeframeLabel(
            data.timeframe
        );


    expiryValue.textContent =
        data.expiry_label ||
        getExpiryLabel(
            data.expiry_seconds
        );


    ema9Value.textContent =
        formatPrice(signal.ema9);


    ema21Value.textContent =
        formatPrice(signal.ema21);


    ema50Value.textContent =
        formatPrice(signal.ema50);


    rsiValue.textContent =
        formatRSI(signal.rsi);


    renderReasons(
        signal.reasons
    );


    showLockPanel(
        data
    );


    updateMarketSnapshot();


    // Scroll gently to signal.
    scrollToSignal();

}


/* ============================================================
   DISPLAY RESTORED LOCKED SIGNAL
   ============================================================ */

function displayRestoredLockedSignal(data) {

    signalEmpty.hidden = true;

    signalResult.hidden = false;

    finalResultPanel.hidden = true;


    setDirectionAppearance(
        data.direction
    );


    directionValue.textContent =
        data.direction || "--";


    directionDescription.textContent =
        data.direction === "UP"
            ? "Bullish market confirmation"
            : "Bearish market confirmation";


    directionLabel.textContent =
        data.direction === "UP"
            ? "UP SIGNAL"
            : "DOWN SIGNAL";


    signalId.textContent =
        `#${data.signal_id ?? "----"}`;


    directionArrow.textContent =
        data.direction === "UP"
            ? "↑"
            : "↓";


    scoreValue.textContent =
        formatNumber(data.score);


    entryPriceValue.textContent =
        formatPrice(data.entry_price);


    timeframeValue.textContent =
        getTimeframeLabel(
            data.timeframe
        );


    expiryValue.textContent =
        getExpiryLabel(
            data.expiry_seconds
        );


    renderReasons([
        "Active signal restored.",
        "Signal remains locked until expiry.",
        "Result will be calculated automatically after expiry."
    ]);


    showLockPanel(data);

}


/* ============================================================
   DISPLAY WAIT
   ============================================================ */

function displayWaitSignal(data) {

    const signal =
        data.signal || {};


    signalEmpty.hidden = true;

    signalResult.hidden = false;

    finalResultPanel.hidden = true;


    directionCard.classList.remove(
        "down"
    );


    directionLabel.textContent =
        "NO SIGNAL";


    signalId.textContent =
        "WAIT";


    directionArrow.textContent =
        "—";


    directionValue.textContent =
        "WAIT";


    directionDescription.textContent =
        "Confirmation strength below threshold";


    scoreValue.textContent =
        formatNumber(
            signal.score
        );


    entryPriceValue.textContent =
        formatPrice(
            signal.price
        );


    timeframeValue.textContent =
        data.timeframe_label ||
        getTimeframeLabel(
            data.timeframe
        );


    expiryValue.textContent =
        data.expiry_label ||
        getExpiryLabel(
            data.expiry_seconds
        );


    ema9Value.textContent =
        formatPrice(signal.ema9);


    ema21Value.textContent =
        formatPrice(signal.ema21);


    ema50Value.textContent =
        formatPrice(signal.ema50);


    rsiValue.textContent =
        formatRSI(signal.rsi);


    renderReasons(
        signal.reasons
    );


    hideLockPanel();


    updateMarketSnapshot();


    scrollToSignal();

}


/* ============================================================
   DIRECTION APPEARANCE
   ============================================================ */

function setDirectionAppearance(
    direction
) {

    directionCard.classList.remove(
        "down"
    );


    if (direction === "DOWN") {

        directionCard.classList.add(
            "down"
        );

    }

}


/* ============================================================
   SHOW LOCK PANEL
   ============================================================ */

function showLockPanel(data) {

    lockPanel.hidden = false;

    lockPanel.classList.remove(
        "completed"
    );


    lockTitle.textContent =
        "Signal Locked";


    lockDescription.textContent =
        "This signal remains locked until its expiry period is complete.";


    lockStatusBadge.textContent =
        "ACTIVE";

}


/* ============================================================
   HIDE LOCK PANEL
   ============================================================ */

function hideLockPanel() {

    lockPanel.hidden = true;

}


/* ============================================================
   START EXPIRY WATCHER
   ============================================================ */

function startExpiryWatcher() {

    stopExpiryWatcher();


    if (!state.expiresAt) {
        return;
    }


    const expiryTime =
        new Date(
            state.expiresAt
        ).getTime();


    if (!Number.isFinite(expiryTime)) {
        return;
    }


    // --------------------------------------------------------
    // No visible countdown.
    //
    // The user only sees "Signal Locked".
    // --------------------------------------------------------

    const checkNow = () => {

        const remaining =
            expiryTime -
            Date.now();


        if (remaining <= 0) {

            stopExpiryWatcher();

            checkSignalResult();

            return;
        }


        state.expiryTimer =
            setTimeout(
                checkNow,
                Math.min(
                    remaining,
                    1000
                )
            );

    };


    checkNow();

}


/* ============================================================
   STOP EXPIRY WATCHER
   ============================================================ */

function stopExpiryWatcher() {

    if (state.expiryTimer) {

        clearTimeout(
            state.expiryTimer
        );

        state.expiryTimer = null;

    }


    if (state.resultPollTimer) {

        clearTimeout(
            state.resultPollTimer
        );

        state.resultPollTimer = null;

    }

}


/* ============================================================
   CHECK SIGNAL RESULT
   ============================================================ */

async function checkSignalResult() {

    if (!state.activeSignalId) {
        return;
    }


    try {

        const response = await fetch(
            "/api/check-result",
            {
                method: "GET",
                headers: {
                    "Accept": "application/json"
                },
                cache: "no-store"
            }
        );


        const data =
            await parseJsonResponse(response);


        // ----------------------------------------------------
        // Still locked
        // ----------------------------------------------------

        if (data.locked) {

            state.resultPollTimer =
                setTimeout(
                    checkSignalResult,
                    2000
                );

            return;
        }


        // ----------------------------------------------------
        // Result completed
        // ----------------------------------------------------

        if (data.completed) {

            displayCompletedResult(data);

            return;
        }


        // ----------------------------------------------------
        // No active signal
        // ----------------------------------------------------

        state.locked = false;

        state.activeSignalId = null;

        state.issuedAt = null;

        state.expiresAt = null;


        updateRequestButtonState();

    } catch (error) {

        console.error(
            "Result check error:",
            error
        );


        // Retry silently.
        state.resultPollTimer =
            setTimeout(
                checkSignalResult,
                3000
            );

    }

}


/* ============================================================
   DISPLAY COMPLETED RESULT
   ============================================================ */

function displayCompletedResult(data) {

    stopExpiryWatcher();


    state.locked = false;

    state.activeSignalId = null;

    state.issuedAt = null;

    state.expiresAt = null;

    state.busy = false;


    signalEmpty.hidden = true;

    signalResult.hidden = false;

    finalResultPanel.hidden = false;


    resultEntryPrice.textContent =
        formatPrice(
            data.entry_price
        );


    resultExitPrice.textContent =
        formatPrice(
            data.exit_price
        );


    const result =
        String(
            data.result || ""
        ).toUpperCase();


    resultBadge.textContent =
        result;


    resultBadge.classList.remove(
        "loss",
        "flat"
    );


    if (result === "WIN") {

        resultBadge.classList.remove(
            "loss",
            "flat"
        );

        lockPanel.classList.add(
            "completed"
        );


        lockTitle.textContent =
            "Signal Completed";


        lockDescription.textContent =
            "The expiry period has completed and the result has been recorded.";


        lockStatusBadge.textContent =
            "COMPLETE";


        showToast(
            "Signal Result: WIN",
            `Signal #${data.signal_id} closed successfully.`,
            "success"
        );

    } else if (result === "LOSS") {

        resultBadge.classList.add(
            "loss"
        );


        lockPanel.classList.add(
            "completed"
        );


        lockTitle.textContent =
            "Signal Completed";


        lockDescription.textContent =
            "The expiry period has completed and the result has been recorded.";


        lockStatusBadge.textContent =
            "COMPLETE";


        showToast(
            "Signal Result: LOSS",
            `Signal #${data.signal_id} has been completed.`,
            "error"
        );

    } else {

        resultBadge.classList.add(
            "flat"
        );


        lockPanel.classList.add(
            "completed"
        );


        lockTitle.textContent =
            "Signal Completed";


        lockDescription.textContent =
            "The entry and exit prices were equal at expiry.";


        lockStatusBadge.textContent =
            "FLAT";


        showToast(
            "Signal Result: FLAT",
            `Signal #${data.signal_id} has been completed.`,
            "warning"
        );

    }


    updateRequestButtonState();


    scrollToSignal();

}


/* ============================================================
   HANDLE LOCKED RESPONSE
   ============================================================ */

function handleLockedResponse(data) {

    state.busy = false;

    state.locked = true;

    state.activeSignalId =
        data.signal_id;


    state.expiresAt =
        data.expires_at;


    hideLoading();


    updateRequestButtonState();


    showToast(
        "Signal Locked",
        data.message ||
            "A signal is already active.",
        "warning"
    );


    startExpiryWatcher();

}


/* ============================================================
   RENDER REASONS
   ============================================================ */

function renderReasons(reasons) {

    reasonsList.innerHTML = "";


    if (!Array.isArray(reasons) ||
        reasons.length === 0) {

        const item =
            document.createElement("div");

        item.className =
            "reason-item";


        item.innerHTML = `
            <span class="reason-bullet"></span>
            <span>No additional analysis details available.</span>
        `;


        reasonsList.appendChild(item);

        return;
    }


    reasons.forEach((reason) => {

        const item =
            document.createElement("div");

        item.className =
            "reason-item";


        const bullet =
            document.createElement("span");

        bullet.className =
            "reason-bullet";


        const text =
            document.createElement("span");

        text.textContent =
            String(reason);


        item.appendChild(bullet);
        item.appendChild(text);

        reasonsList.appendChild(item);

    });

}


/* ============================================================
   LOADING UI
   ============================================================ */

function showLoading() {

    if (!loadingOverlay) {
        return;
    }


    loadingOverlay.hidden = false;

    loadingProgressBar.style.width =
        "35%";


    updateLoadingText(
        "Preparing market analysis..."
    );

}


function hideLoading() {

    if (!loadingOverlay) {
        return;
    }


    loadingOverlay.hidden = true;

}


function updateLoadingText(text) {

    if (loadingText) {
        loadingText.textContent = text;
    }

}


/* ============================================================
   ERROR
   ============================================================ */

function showError(message) {

    errorMessage.hidden = false;

    errorMessageText.textContent =
        message ||
        "An unexpected error occurred.";

}


function hideError() {

    errorMessage.hidden = true;

}


/* ============================================================
   TOAST
   ============================================================ */

let toastTimer = null;


function showToast(
    title,
    message,
    type = "success"
) {

    if (!toast) {
        return;
    }


    if (toastTimer) {

        clearTimeout(
            toastTimer
        );

        toastTimer = null;

    }


    toast.classList.remove(
        "error",
        "warning"
    );


    if (type === "error") {

        toast.classList.add(
            "error"
        );

        toastIcon.textContent =
            "!";

    } else if (type === "warning") {

        toast.classList.add(
            "warning"
        );

        toastIcon.textContent =
            "!";

    } else {

        toastIcon.textContent =
            "✓";

    }


    toastTitle.textContent =
        title || "Notification";


    toastMessage.textContent =
        message || "";


    toast.hidden = false;


    toastTimer =
        setTimeout(
            hideToast,
            5500
        );

}


function hideToast() {

    if (!toast) {
        return;
    }


    toast.hidden = true;


    if (toastTimer) {

        clearTimeout(
            toastTimer
        );

        toastTimer = null;

    }

}


/* ============================================================
   SYSTEM STATUS
   ============================================================ */

function setSystemStatus(
    online,
    text
) {

    statusText.textContent =
        text;


    footerStatusText.textContent =
        online
            ? "System Online"
            : "System Offline";


    statusDot.classList.toggle(
        "offline",
        !online
    );


    footerStatusDot.classList.toggle(
        "offline",
        !online
    );

}


/* ============================================================
   FORMAT NUMBER
   ============================================================ */

function formatNumber(value) {

    if (
        value === null ||
        value === undefined ||
        value === "" ||
        Number.isNaN(Number(value))
    ) {

        return "--";
    }


    const number =
        Number(value);


    if (
        Number.isInteger(number)
    ) {

        return String(number);
    }


    return number.toFixed(2);

}


/* ============================================================
   FORMAT PRICE
   ============================================================ */

function formatPrice(value) {

    if (
        value === null ||
        value === undefined ||
        value === "" ||
        Number.isNaN(Number(value))
    ) {

        return "--";
    }


    const number =
        Number(value);


    // Forex prices normally need several decimal places.
    if (Math.abs(number) < 10) {

        return number.toFixed(5);
    }


    return number.toFixed(3);

}


/* ============================================================
   FORMAT RSI
   ============================================================ */

function formatRSI(value) {

    if (
        value === null ||
        value === undefined ||
        value === "" ||
        Number.isNaN(Number(value))
    ) {

        return "--";
    }


    return Number(value).toFixed(2);

}


/* ============================================================
   GET TIMEFRAME LABEL
   ============================================================ */

function getTimeframeLabel(value) {

    const found =
        state.timeframes.find(
            (item) =>
                String(item.value) ===
                String(value)
        );


    if (found) {
        return found.label;
    }


    return String(value || "--");

}


/* ============================================================
   GET EXPIRY LABEL
   ============================================================ */

function getExpiryLabel(seconds) {

    const found =
        state.expiries.find(
            (item) =>
                Number(item.seconds) ===
                Number(seconds)
        );


    if (found) {
        return found.label;
    }


    if (Number(seconds) === 15) {
        return "15 Seconds";
    }


    if (Number(seconds) === 30) {
        return "30 Seconds";
    }


    if (Number(seconds) === 60) {
        return "1 Minute";
    }


    return `${seconds || "--"} Seconds`;

}


/* ============================================================
   PARSE JSON RESPONSE
   ============================================================ */

async function parseJsonResponse(response) {

    const text =
        await response.text();


    if (!text) {

        return {
            success: false,
            error:
                `Server returned HTTP ${response.status}.`
        };

    }


    try {

        return JSON.parse(text);

    } catch (error) {

        console.error(
            "Invalid JSON response:",
            text
        );


        return {
            success: false,
            error:
                `Server returned an invalid response (HTTP ${response.status}).`
        };

    }

}


/* ============================================================
   SMALL DELAY
   ============================================================ */

function smallDelay(milliseconds) {

    return new Promise(
        (resolve) =>
            setTimeout(
                resolve,
                milliseconds
            )
    );

}


/* ============================================================
   SCROLL TO SIGNAL
   ============================================================ */

function scrollToSignal() {

    if (!signalResult) {
        return;
    }


    // Don't force scrolling on very small actions.
    if (window.innerWidth < 760) {

        setTimeout(() => {

            signalResult.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });

        }, 120);

    }

}


/* ============================================================
   PAGE VISIBILITY
   ============================================================ */

document.addEventListener(
    "visibilitychange",
    () => {

        if (
            document.visibilityState ===
            "visible"
        ) {

            if (state.locked) {

                checkSignalResult();

            } else {

                checkServerStatus();

            }

        }

    }
);


/* ============================================================
   WINDOW FOCUS
   ============================================================ */

window.addEventListener(
    "focus",
    () => {

        if (state.locked) {

            checkSignalResult();

        }

    }
);


/* ============================================================
   PREVENT ACCIDENTAL DOUBLE SUBMISSION
   ============================================================ */

window.addEventListener(
    "beforeunload",
    () => {

        stopExpiryWatcher();

    }
);
