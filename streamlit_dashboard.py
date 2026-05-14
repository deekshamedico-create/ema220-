"""
220 EMA Breakout Strategy — Live Streamlit Dashboard
Run: streamlit run streamlit_dashboard.py
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime, os, json

# ── Google Sheet Config ──────────────────────────────────────────────────────
SHEET_ID       = "1tT9NLUcpVqsVN7dFJ2O2v4I4lDwxZcHPAUStQff16OY"
POSITIONS_URL  = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Positions"
CLOSED_URL     = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Closed"
SHEET_EDIT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="220 EMA Strategy",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* ── Base ── */
    .stApp { background-color: #0d0d14; color: #f0f0f0; }

    /* ── High contrast metric cards ── */
    div[data-testid="metric-container"] {
        background: #1e1e30; border: 1px solid #4a4a70;
        border-radius: 10px; padding: 12px;
    }
    div[data-testid="metric-container"] label { color: #c8c8e8 !important; font-size: 13px !important; }
    div[data-testid="metric-container"] [data-testid="metric-value"] { color: #ffffff !important; font-weight: 700 !important; }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] { background-color: #0f0f1e !important; }
    section[data-testid="stSidebar"] label { color: #e0e0f0 !important; font-size: 14px !important; }
    section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span { color: #c0c0d8 !important; }
    section[data-testid="stSidebar"] .stButton button { background: #2a2a45 !important; color: #ffffff !important; border: 1px solid #5050a0 !important; }

    /* ── Alerts with high contrast ── */
    div[data-testid="stInfo"]    { background: #0d1f33 !important; border-left: 4px solid #4488ff !important; color: #c8e8ff !important; }
    div[data-testid="stSuccess"] { background: #0a2018 !important; border-left: 4px solid #34d399 !important; color: #a0ffd8 !important; }
    div[data-testid="stWarning"] { background: #281800 !important; border-left: 4px solid #fbbf24 !important; color: #ffe8a0 !important; }
    div[data-testid="stError"]   { background: #280808 !important; border-left: 4px solid #f87171 !important; color: #ffc8c8 !important; }

    /* ── Buttons ── */
    .stButton button { background: #2a2a45 !important; color: #ffffff !important; border: 1px solid #5050a0 !important; font-weight: 600 !important; }
    .stButton button:hover { background: #3a3a60 !important; }

    /* ── Inputs ── */
    .stTextInput input, .stNumberInput input { background: #1a1a2a !important; color: #ffffff !important; border: 1px solid #4a4a70 !important; }
    .stTextInput label, .stNumberInput label, .stDateInput label, .stSelectbox label { color: #c8c8e8 !important; font-weight: 600 !important; }

    /* ── Dataframe ── */
    .stDataFrame th { background: #1e1e30 !important; color: #ffffff !important; font-weight: 700 !important; }
    .stDataFrame td { color: #e8e8f0 !important; }

    /* ── Expanders ── */
    .streamlit-expanderHeader { color: #e8e8f0 !important; font-weight: 600 !important; background: #1a1a2a !important; }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab"] { color: #a0a0c0 !important; font-weight: 600 !important; font-size: 14px !important; }
    .stTabs [aria-selected="true"] { color: #ffffff !important; }

    /* ── Signal badges ── */
    .signal-badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 700; }
    .badge-green  { background: #0a3a1a; color: #4dffb0; border: 1px solid #34d399; }
    .badge-amber  { background: #3a2800; color: #ffd060; border: 1px solid #fbbf24; }
    .badge-teal   { background: #003840; color: #40f0ff; border: 1px solid #22d3ee; }
    .badge-purple { background: #18104a; color: #c0b0ff; border: 1px solid #a89cff; }
    .green { color: #4dffb0; } .red { color: #ff8888; } .amber { color: #ffd060; }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
EMA_PERIOD = 220
os.makedirs("data_cache", exist_ok=True)

NIFTY500 = [
    "RELIANCE","TCS","HDFCBANK","ICICIBANK","INFY","SBIN","BHARTIARTL","HINDUNILVR",
    "ITC","KOTAKBANK","LT","AXISBANK","BAJFINANCE","HCLTECH","MARUTI","SUNPHARMA",
    "TITAN","ULTRACEMCO","WIPRO","ADANIENT","NESTLEIND","POWERGRID","NTPC","TECHM",
    "BAJAJFINSV","ASIANPAINT","M&M","ADANIPORTS","COALINDIA","ONGC","TATASTEEL",
    "JSWSTEEL","HINDALCO","GRASIM","DIVISLAB","DRREDDY","CIPLA","APOLLOHOSP",
    "EICHERMOT","BAJAJ-AUTO","HEROMOTOCO","TATACONSUM","BRITANNIA","DABUR","MARICO",
    "PIDILITIND","BERGEPAINT","HAVELLS","SIEMENS","ABB","BOSCHLTD","CUMMINSIND",
    "AIAENG","ASTRAL","SUPREMEIND","BHEL","HAL","BEL","DATAPATTNS","SOLARINDS",
    "PERSISTENT","LTTS","COFORGE","MPHASIS","SONATSOFTW","INTELLECT","KPITTECH",
    "TATAELXSI","LATENTVIEW","HAPPYMINDS","BIRLASOFT","RATEGAIN","CYIENT","NEWGEN",
    "AARTIIND","CHAMBLFERT","COROMANDEL","DEEPAKNTR","NAVINFLUOR","TATACHEM","CLEAN",
    "JUBLFOOD","RADICO","UBL","VBL","COLPAL","EMAMILTD","GODREJCP","GODFRYPHLP",
    "IRCTC","RAILTEL","INDIAMART","NAUKRI","PAYTM","POLICYBZR","DELHIVERY","ZOMATO",
    "RVNL","IRFC","PFC","RECLTD","HUDCO","NHPC","SJVN","TATAPOWER","JSWENERGY",
    "SUZLON","ADANIGREEN","ADANIPOWER","INOXWIND","IDEA","HFCL","ZEEL","SUNTV",
    "PVRINOX","SAREGAMA","RAMCOCEM","JKCEMENT","SHREECEM","AMBUJACEM","ACC","DALBHARAT",
    "MOTHERSON","BALKRISIND","APOLLOTYRE","MRF","CEATLTD","EXIDEIND","ENDURANCE",
    "IDFCFIRSTB","BANDHANBNK","FEDERALBNK","INDUSINDBK","RBLBANK","AUBANK","KARURVYSYA",
    "PNB","BANKBARODA","CANBK","UNIONBANK","INDIANB","UCOBANK","MAHABANK",
    "CHOLAFIN","MUTHOOTFIN","MANAPPURAM","SHRIRAMFIN","SBILIFE","HDFCLIFE",
    "ICICIPRULI","STARHEALTH","GICRE","ICICIGI","LICI","HDFCAMC","ABSLAMC","ANGELONE",
    "HINDPETRO","BPCL","IOC","GAIL","MGL","IGL","PETRONET","GSPL","ATGL",
    "VEDL","HINDZINC","NMDC","SAIL","JINDALSTEL","GRAPHITE","CARBORUNIV","RATNAMANI",
    "TORNTPHARM","AUROPHARMA","LUPIN","ALKEM","IPCALAB","GRANULES","LAURUSLABS",
    "SYNGENE","BIOCON","GLAND","JUBLPHARMA","MANKIND","ERIS","AJANTPHARM","ZYDUSLIFE",
    "GLENMARK","WOCKPHARMA","PFIZER","ABBOTINDIA","MEDANTA","KIMS","MAXHEALTH",
    "FORTIS","LALPATHLAB","NH","RAINBOW","PAGEIND","TRENT","DMART","BATAINDIA",
    "DLF","GODREJPROP","OBEROIRLTY","PRESTIGE","BRIGADE","PHOENIXLTD","SOBHA",
    "ANANDRATHI","MCX","BSE","CDSL","CAMS","KFINTECH","KAYNES","DIXON","AMBER",
    "AFFLE","SCHAEFFLER","TIMKEN","CUMMINSIND","GRINDWELL","KAYNES","TIINDIA",
    "RVNL","IRCON","NBCC","ENGINERSIN","CONCOR","JSWINFRA","ADANIPORTS",
    "LICI","JIOFIN","BAJAJHLDNG","CHOLAHLDNG","MFSL","PIRAMALFIN",
]
NIFTY500 = list(dict.fromkeys(NIFTY500))

# ── Data functions ────────────────────────────────────────────────────────────

@st.cache_data(ttl=86400)  # cache 24 hours — one download per day max
def fetch_data(symbol_ns, period="2y"):
    """
    Downloads data with strict daily caching.
    - If cache exists and was written TODAY after 3:30 PM IST → use cache (final closing prices)
    - If cache exists but stale → re-download
    - Always falls back to cache if download fails
    This ensures the same data is used throughout a session and signals don't flip.
    """
    cache = f"data_cache/{symbol_ns.replace('.','_').replace('^','_').replace('&','_')}.csv"

    # Check if we have a fresh post-market cache for today
    now_ist = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    today   = now_ist.date()
    market_close_today = datetime.datetime.combine(today,
                         datetime.time(15, 30)) - datetime.timedelta(hours=5, minutes=30)

    if os.path.exists(cache):
        mtime     = datetime.datetime.utcfromtimestamp(os.path.getmtime(cache))
        cache_age = (datetime.datetime.utcnow() - mtime).total_seconds()
        # Use cache if: written today after market close (final data), OR written within last 24h on weekend
        is_weekend = now_ist.weekday() >= 5
        cache_is_today = mtime.date() == today
        cache_post_close = mtime > market_close_today

        if (cache_is_today and cache_post_close) or (is_weekend and cache_age < 172800):
            try:
                df = pd.read_csv(cache, index_col=0, parse_dates=True)
                if len(df) > 10:
                    return df
            except:
                pass

    # Download fresh data
    try:
        df = yf.download(symbol_ns, period=period, auto_adjust=True, progress=False)
        if df is None or df.empty:
            # Fall back to any existing cache
            if os.path.exists(cache):
                return pd.read_csv(cache, index_col=0, parse_dates=True)
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[["Open","High","Low","Close","Volume"]].dropna()
        if not df.empty:
            df.to_csv(cache)
        return df if not df.empty else None
    except:
        if os.path.exists(cache):
            try:
                return pd.read_csv(cache, index_col=0, parse_dates=True)
            except:
                pass
        return None

def add_indicators(df):
    df = df.copy()
    df["EMA220"] = df["Close"].ewm(span=220, adjust=False).mean()
    df["EMA50"]  = df["Close"].ewm(span=50,  adjust=False).mean()
    df["EMA20"]  = df["Close"].ewm(span=20,  adjust=False).mean()
    df["Vol20"]  = df["Volume"].rolling(20).mean()
    # RSI
    d = df["Close"].diff()
    g = d.clip(lower=0).rolling(14).mean()
    l = (-d.clip(upper=0)).rolling(14).mean()
    df["RSI"] = 100 - (100 / (1 + g / l.replace(0, np.nan)))
    # MACD
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"]        = ema12 - ema26
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"]   = df["MACD"] - df["MACD_signal"]
    return df

def compute_rs_score(stock_df, bench_df):
    """
    Composite RS Score vs Nifty 500 benchmark.
    rs_63  = stock 63-day return / nifty500 63-day return
    rs_126 = stock 126-day return / nifty500 126-day return
    RS Score = (rs_63 + rs_126) / 2
    Higher = stronger stock relative to market.
    """
    try:
        # Align both dataframes on common dates
        common = stock_df.index.intersection(bench_df.index)
        if len(common) < 126:
            return None
        s = stock_df["Close"].reindex(common)
        b = bench_df["Close"].reindex(common)

        s_now = float(s.iloc[-1])
        b_now = float(b.iloc[-1])

        # 63-day (3 month) relative return
        s63 = (s_now / float(s.iloc[-63]) - 1)
        b63 = (b_now / float(b.iloc[-63]) - 1)
        rs63 = s63 / abs(b63) if b63 != 0 else 0

        # 126-day (6 month) relative return
        s126 = (s_now / float(s.iloc[-126]) - 1)
        b126 = (b_now / float(b.iloc[-126]) - 1)
        rs126 = s126 / abs(b126) if b126 != 0 else 0

        return round((rs63 + rs126) / 2, 2)
    except:
        return None

# ── Google Sheet Functions ───────────────────────────────────────────────────

@st.cache_data(ttl=60)  # refresh every 60 seconds
def read_positions_from_sheet():
    """Read open positions from Google Sheet."""
    try:
        df = pd.read_csv(POSITIONS_URL)
        df.columns = [c.strip().lower().replace(" ","_") for c in df.columns]
        positions = []
        for _, row in df.iterrows():
            if pd.isna(row.get("symbol","")) or str(row.get("symbol","")).strip() == "":
                continue
            positions.append({
                "symbol"      : str(row["symbol"]).strip().upper(),
                "entry_price" : float(row.get("entry_price", 0)),
                "shares"      : int(row.get("shares", 0)),
                "entry_date"  : str(row.get("entry_date","")).strip(),
                "trailing_sl" : float(row.get("trailing_sl", 0)),
            })
        return positions
    except Exception as e:
        st.warning(f"Could not read positions from Google Sheet: {e}")
        return []

@st.cache_data(ttl=60)
def read_closed_from_sheet():
    """Read closed trades from Google Sheet Closed tab."""
    try:
        df = pd.read_csv(CLOSED_URL)
        df.columns = [c.strip().lower().replace(" ","_") for c in df.columns]

        # Critical check: if the sheet has exit_price column, it is truly the Closed tab
        # If not, it means Google returned the wrong sheet (Positions tab fallback)
        if "exit_price" not in df.columns:
            return []  # Closed tab is empty or wrong sheet returned

        trades = []
        for _, row in df.iterrows():
            sym = str(row.get("symbol","")).strip().upper()
            if not sym or sym == "NAN" or sym == "SYMBOL":
                continue
            ep   = float(row.get("entry_price", 0))
            xp   = float(row.get("exit_price",  0))
            sh   = int(float(row.get("shares", 0)))

            # Skip if exit price is 0 or missing — not a valid closed trade
            if xp == 0 or ep == 0:
                continue

            pnl  = round((xp - ep) * sh * 0.995, 2)
            pct  = round((xp - ep) / ep * 100, 2) if ep > 0 else 0
            try:
                edt  = pd.to_datetime(str(row.get("entry_date","")), dayfirst=True).date()
                xdt  = pd.to_datetime(str(row.get("exit_date","")),  dayfirst=True).date()
                hold = (xdt - edt).days
            except:
                hold = 0
            trades.append({
                "symbol"      : sym,
                "entry_price" : ep,
                "exit_price"  : xp,
                "shares"      : sh,
                "entry_date"  : str(row.get("entry_date","")),
                "exit_date"   : str(row.get("exit_date","")),
                "pnl_rs"      : pnl,
                "pnl_pct"     : pct,
                "hold_days"   : hold,
                "reason"      : str(row.get("reason","Manual Exit")),
            })
        return trades
    except Exception as e:
        return []  # Empty closed tab — no error needed

def get_sheet_link():
    """Return clickable Google Sheet link."""
    return SHEET_EDIT_URL

def get_signal_state(df):
    """
    Implements the exact 4-step signal state machine from the strategy:

    Step 1 — EMA Cross (Day 0):
      Close crosses above EMA 220 from below.
      On Day 0: lock w52_fixed = max(Close) for the 365 calendar days BEFORE Day 0.
      Start 60-trading-day clock.

    Step 2 — 52W High Break (Day X, X <= 60 trading days after Day 0):
      Close crosses above w52_fixed.
      Stock must have stayed above EMA 220 every day from Day 0 to Day X.
      If any day closes below EMA 220: reset state entirely.
      If 60 days pass without Step 2: reset entirely.

    Step 3 — 10-day Confirmation:
      Price stays above EMA 220 for 10 consecutive days after Step 2.
      On Day 10: close must still be above w52_fixed.

    Returns: (state, info_dict)
      state = 'none' | 'ema_cross' | 'watching' | 'near_52w' | 'breakout' | 'confirmed'
    """
    if df is None or len(df) < EMA_PERIOD + 5:
        return "none", {}

    row   = df.iloc[-1]; prev = df.iloc[-2]
    c     = float(row["Close"]); e = float(row["EMA220"])
    vol20 = float(row["Vol20"]) if not pd.isna(row["Vol20"]) else 0
    rsi   = float(row["RSI"])   if not pd.isna(row["RSI"])   else 50
    chg   = (c - float(prev["Close"])) / float(prev["Close"]) * 100

    # ── Find most recent EMA cross within last 60 trading days ──
    cross_idx   = None   # position in df (from end) where cross happened
    w52_fixed   = None   # 52W high locked on cross day
    cross_date  = None

    # Search from TODAY backwards — find most recent cross where stock
    # has stayed above EMA 220 continuously from that cross to today
    for i in range(1, min(62, len(df)-2)):
        c1 = float(df["Close"].iloc[-i]);   e1 = float(df["EMA220"].iloc[-i])
        c0 = float(df["Close"].iloc[-i-1]); e0 = float(df["EMA220"].iloc[-i-1])
        # Going back day by day — first day we find below EMA, stop
        if c1 <= e1:
            break
        # Found a cross (yesterday was below, today above)
        if c1 > e1 and c0 <= e0:
            cross_idx  = i
            cross_date = df.index[-i]
            cutoff     = cross_date - pd.Timedelta(days=365)
            hist       = df["Close"][(df.index >= cutoff) & (df.index < cross_date)]
            w52_fixed  = float(hist.max()) if not hist.empty else float(df["Close"].iloc[:-i].max())
            break

    # ── No cross found in last 60 days → no signal ──
    if cross_idx is None:
        return "none", {
            "close": round(c,2), "ema220": round(e,2),
            "w52_high": round(float(df["Close"].iloc[-252:].max()),2),
            "pct_from_52w": 0, "pct_above_ema": round((c-e)/e*100,2),
            "sl_level": round(max(e,c*0.85),2), "vol20": round(vol20),
            "rsi": round(rsi,1), "change_pct": round(chg,2), "above_ema": c>e,
        }

    # ── Check: stock stayed above EMA 220 every day from cross to today ──
    # Slice from cross day (inclusive) to today
    post_cross = df.iloc[-cross_idx:]   # rows from cross day onward
    stayed_above = all(
        float(post_cross["Close"].iloc[j]) > float(post_cross["EMA220"].iloc[j])
        for j in range(len(post_cross))
    )

    p52  = (c - w52_fixed) / w52_fixed * 100

    # ── If broke below EMA 220 any day after cross → reset, no signal ──
    if not stayed_above:
        return "none", {
            "close": round(c,2), "ema220": round(e,2),
            "w52_high": round(w52_fixed,2),
            "pct_from_52w": round(p52,2), "pct_above_ema": round((c-e)/e*100,2),
            "sl_level": round(max(e,c*0.85),2), "vol20": round(vol20),
            "rsi": round(rsi,1), "change_pct": round(chg,2), "above_ema": c>e,
            "reset_reason": "Broke below EMA 220 after cross",
        }

    # ── Determine state ──
    days_since_cross = cross_idx - 1   # trading days elapsed since cross

    # Step 1 just happened (cross was today or yesterday)
    if days_since_cross <= 1:
        state = "ema_cross"

    # Step 2: Has price broken above w52_fixed yet?
    # If yes AND stayed above EMA 220 every day since cross → CONFIRMED
    elif c > w52_fixed:
        # Find the day 52W high was first broken after EMA cross
        break_idx = None
        for j in range(len(post_cross)):
            if float(post_cross["Close"].iloc[j]) > w52_fixed:
                break_idx = j
                break
        days_since_break = (len(post_cross) - 1 - break_idx) if break_idx is not None else 0

        # Check all days since break stayed above EMA 220
        post_break  = post_cross.iloc[break_idx:] if break_idx is not None else post_cross
        break_ok    = all(
            float(post_break["Close"].iloc[j]) > float(post_break["EMA220"].iloc[j])
            for j in range(len(post_break))
        )

        if days_since_break >= 10 and break_ok:
            state = "confirmed"   # 10+ days above 52W high + above EMA every day
        else:
            state = "breakout"    # just crossed 52W high, in confirmation window

    # Step 2 not yet triggered — watching
    elif p52 > -3:
        state = "near_52w"    # within 3% of the locked 52W high
    else:
        state = "watching"    # above EMA, waiting for 52W break

    info = {
        "close"           : round(c, 2),
        "ema220"          : round(e, 2),
        "w52_high"        : round(w52_fixed, 2),
        "pct_from_52w"    : round(p52, 2),
        "pct_above_ema"   : round((c-e)/e*100, 2),
        "sl_level"        : round(max(e, c*0.85), 2),
        "vol20"           : round(vol20),
        "rsi"             : round(rsi, 1),
        "change_pct"      : round(chg, 2),
        "above_ema"       : c > e,
        "days_since_cross": days_since_cross,
        "days_since_break": days_since_break if c > w52_fixed and break_idx is not None else 0,
        "cross_date"      : str(cross_date.date()) if cross_date else "—",
        "w52_locked_on"   : str(cross_date.date()) if cross_date else "—",
    }
    return state, info

# ── Chart builder ─────────────────────────────────────────────────────────────

def build_chart(df, symbol, show_days=180):
    df = df.tail(show_days).copy()
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        row_heights=[0.6, 0.2, 0.2],
        vertical_spacing=0.03,
    )

    # ── Candlestick ──
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"],
        name="Price",
        increasing_fillcolor="#34d399", increasing_line_color="#34d399",
        decreasing_fillcolor="#f87171", decreasing_line_color="#f87171",
    ), row=1, col=1)

    # ── EMAs ──
    fig.add_trace(go.Scatter(x=df.index, y=df["EMA220"], name="EMA 220",
        line=dict(color="#7c6af7", width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["EMA50"], name="EMA 50",
        line=dict(color="#fbbf24", width=1.2, dash="dash")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["EMA20"], name="EMA 20",
        line=dict(color="#22d3ee", width=1, dash="dot")), row=1, col=1)

    # ── Volume ──
    colors = ["#34d399" if c >= o else "#f87171"
              for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume",
        marker_color=colors, opacity=0.7), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["Vol20"], name="Vol MA20",
        line=dict(color="#fbbf24", width=1.5)), row=2, col=1)

    # ── RSI ──
    fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI",
        line=dict(color="#a89cff", width=1.5)), row=3, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#f87171", opacity=0.5, row=3, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#34d399", opacity=0.5, row=3, col=1)
    fig.add_hline(y=50, line_dash="dot", line_color="#888",    opacity=0.3, row=3, col=1)

    fig.update_layout(
        title=dict(text=f"{symbol} — Daily Chart", font=dict(size=16, color="#e0e0f0")),
        paper_bgcolor="#0d0d14",
        plot_bgcolor="#0d0d14",
        font=dict(color="#888", size=12),
        xaxis_rangeslider_visible=False,
        legend=dict(bgcolor="#13131f", bordercolor="#2a2a3d", borderwidth=1,
                    font=dict(color="#888", size=11)),
        height=650,
        margin=dict(l=10, r=10, t=50, b=10),
    )
    for i in range(1, 4):
        fig.update_xaxes(gridcolor="#1a1a2e", row=i, col=1)
        fig.update_yaxes(gridcolor="#1a1a2e", row=i, col=1)

    fig.update_yaxes(title_text="Price (₹)", row=1, col=1, title_font=dict(color="#888"))
    fig.update_yaxes(title_text="Volume",    row=2, col=1, title_font=dict(color="#888"))
    fig.update_yaxes(title_text="RSI",       row=3, col=1, title_font=dict(color="#888"), range=[0,100])
    return fig

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ◆ 220 EMA Strategy")
    st.markdown("---")
    page = st.radio("Navigate", ["📊 Stock Chart", "🔍 Signal Scanner", "💼 My Positions", "📈 Nifty 500", "🧮 Position Sizer"])
    st.markdown("---")
    st.caption(f"Last updated: {datetime.datetime.now().strftime('%d %b %Y  %H:%M')}")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — STOCK CHART
# ══════════════════════════════════════════════════════════════════════════════
if page == "📊 Stock Chart":
    st.markdown("## Stock Chart & Analysis")

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        symbol = st.text_input("NSE Symbol", value="RELIANCE",
                               placeholder="e.g. KAYNES, TITAN, LUPIN").upper().strip()
    with col2:
        period = st.selectbox("Period", ["6mo","1y","2y","5y"], index=2)
    with col3:
        show_days = st.selectbox("Chart view", [60,90,180,365,730],
                                 index=2, format_func=lambda x: f"Last {x} days")

    if symbol:
        with st.spinner(f"Loading {symbol}..."):
            df_raw = fetch_data(f"{symbol}.NS", period)

        if df_raw is None or df_raw.empty:
            st.error(f"Could not load data for {symbol}. Check the symbol name.")
        else:
            df = add_indicators(df_raw)
            state, info = get_signal_state(df)
            row = df.iloc[-1]; prev = df.iloc[-2]
            cmp = float(row["Close"])
            chg = info.get("change_pct", 0)

            # ── Top metrics ──
            m1,m2,m3,m4,m5,m6 = st.columns(6)
            with m1:
                st.metric("CMP", f"₹{cmp:,.2f}", f"{chg:+.2f}%")
            with m2:
                st.metric("EMA 220", f"₹{info['ema220']:,.2f}",
                          f"{info['pct_above_ema']:+.2f}% {'above' if info['above_ema'] else 'below'}")
            with m3:
                st.metric("52W High", f"₹{info['w52_high']:,.2f}", f"{info['pct_from_52w']:+.2f}%")
            with m4:
                st.metric("RSI (14)", f"{info['rsi']}")
            with m5:
                st.metric("SL Level", f"₹{info['sl_level']:,.2f}")
            with m6:
                st.metric("Vol (20d avg)", f"{info['vol20']/1e5:.1f}L")

            # ── Signal badge ──
            state_map = {
                "confirmed" : ("✅ CONFIRMED SIGNAL — Strategy says: Ready to trade next day!", "badge-green"),
                "breakout"  : ("🔥 BREAKOUT — 52W High broken, in 10-day confirmation window", "badge-green"),
                "near_52w"  : ("⚡ NEAR 52W HIGH — within 3% of locked 52W high", "badge-amber"),
                "ema_cross" : ("📡 FRESH EMA CROSS — Day 0 triggered, 52W high locked", "badge-teal"),
                "watching"  : ("👁 WATCHING — above EMA 220, waiting for 52W break", "badge-purple"),
                "none"      : ("— No active signal (below EMA 220 or no recent cross)", ""),
            }
            label, cls = state_map.get(state, state_map["none"])
            if cls:
                st.markdown(f'<div class="signal-badge {cls}">{label}</div><br>',
                            unsafe_allow_html=True)

            # ── Chart ──
            fig = build_chart(df, symbol, show_days)
            st.plotly_chart(fig, use_container_width=True)

            # ── Key levels table ──
            st.markdown("#### Key Levels")
            c1, c2 = st.columns(2)
            with c1:
                levels = pd.DataFrame({
                    "Level": ["Current Price","EMA 220","EMA 50","EMA 20",
                              "52W High","SL (max of EMA220, -15%)"],
                    "Value (₹)": [
                        f"{cmp:,.2f}",
                        f"{info['ema220']:,.2f}",
                        f"{float(row['EMA50']):,.2f}",
                        f"{float(row['EMA20']):,.2f}",
                        f"{info['w52_high']:,.2f}",
                        f"{info['sl_level']:,.2f}",
                    ],
                    "% from CMP": [
                        "—",
                        f"{info['pct_above_ema']:+.2f}%",
                        f"{(cmp/float(row['EMA50'])-1)*100:+.2f}%",
                        f"{(cmp/float(row['EMA20'])-1)*100:+.2f}%",
                        f"{info['pct_from_52w']:+.2f}%",
                        f"{(cmp/info['sl_level']-1)*100:+.2f}%",
                    ]
                })
                st.dataframe(levels, hide_index=True, use_container_width=True)
            with c2:
                targets = pd.DataFrame({
                    "Target": ["+20%","+40% (Ver B sell 50%)","+100% (Ver B sell 25%)","+150%","+200%"],
                    "Price (₹)": [
                        f"{cmp*1.20:,.2f}", f"{cmp*1.40:,.2f}",
                        f"{cmp*2.00:,.2f}", f"{cmp*2.50:,.2f}", f"{cmp*3.00:,.2f}",
                    ]
                })
                st.dataframe(targets, hide_index=True, use_container_width=True)

            # ── Recent OHLCV ──
            with st.expander("Recent OHLCV Data"):
                display = df[["Open","High","Low","Close","Volume","EMA220","RSI"]].tail(20).copy()
                display = display.round(2)
                display.index = display.index.strftime("%d %b %Y")
                st.dataframe(display, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — SIGNAL SCANNER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔍 Signal Scanner":
    st.markdown("## Signal Scanner — Nifty 500")

    # ── Market day / time warning ──────────────────────────────────────────
    now_ist = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    is_weekend   = now_ist.weekday() >= 5          # Saturday=5, Sunday=6
    market_open  = datetime.time(9, 15)
    market_close = datetime.time(15, 30)
    is_market_hours = market_open <= now_ist.time() <= market_close
    is_post_close   = now_ist.time() > market_close

    if is_weekend:
        st.warning(
            f"⚠️ **Today is {'Saturday' if now_ist.weekday()==5 else 'Sunday'} — NSE is closed.**\n\n"
            "Signal results on weekends are **unreliable** because yfinance may return "
            "stale, partial, or Friday's closing data in inconsistent ways. "
            "\n\n**Run the scanner on Monday after 3:30 PM IST for accurate results.**"
        )
        st.info("You can still view results from your last weekday scan below if available.")
    elif is_market_hours:
        st.warning(
            f"⚠️ **Market is currently open (IST {now_ist.strftime('%H:%M')}).**\n\n"
            "Signals during market hours use intraday prices which change every minute. "
            "For strategy signals, scan **after 3:30 PM IST** when the day's close is final."
        )
    elif is_post_close:
        st.success(
            f"✅ **Market closed for today. IST {now_ist.strftime('%H:%M')}** — "
            "This is the best time to run the scanner. Results are based on today's final closing prices."
        )

    st.caption("Scans all Nifty 500 stocks for active 220 EMA breakout signals. First scan takes ~2 minutes.")

    filt = st.pills("Filter by signal type",
                    ["All","✅ Confirmed","🔥 Breakout","⚡ Near 52W High","📡 EMA Cross","👁 Watching"],
                    default="All")

    # Check if we already have a post-close scan for today
    last_scan_time = st.session_state.get("scan_time","")
    scan_locked    = False
    if last_scan_time and not is_weekend and is_post_close:
        try:
            scan_dt = datetime.datetime.strptime(last_scan_time, "%d %b %Y %H:%M IST")
            if scan_dt.date() == now_ist.date() and scan_dt.time() > market_close.replace():
                scan_locked = True
        except: pass

    if scan_locked:
        st.info(
            f"🔒 **Scan results are locked for today ({now_ist.strftime('%d %b %Y')}).**\n\n"
            "You already ran a post-market scan today. Results are frozen to prevent signal flipping. "
            "They will unlock tomorrow after market close."
        )

    # Disable scan button on weekends with a clear message
    scan_label = "🔍 Run Full Scan" if not is_weekend else "🔍 Run Full Scan (weekend — results may be unreliable)"
    if scan_locked:
        scan_label = "🔒 Re-scan (today's results already locked — not recommended)"

    if st.button(scan_label, type="primary", use_container_width=True):
        if is_weekend:
            st.warning("Running scan on weekend — treat results with caution. Best to re-run on Monday after market close.")
        if scan_locked:
            st.warning("⚠️ Re-scanning will overwrite today's locked results. Use only if you suspect a data error.")

        # Load benchmark for RS calculation
        bench_df_raw = fetch_data("^CRSLDX", "2y")
        if bench_df_raw is None or bench_df_raw.empty:
            bench_df_raw = fetch_data("^NSEI", "2y")

        results = []
        pb = st.progress(0, text="Scanning stocks...")
        total = len(NIFTY500)
        for i, ticker in enumerate(NIFTY500):
            pb.progress((i+1)/total, text=f"Scanning {ticker}... ({i+1}/{total})")
            df_raw = fetch_data(f"{ticker}.NS", "2y")
            if df_raw is None or len(df_raw) < 225: continue
            df = add_indicators(df_raw)
            state, info = get_signal_state(df)
            if state == "none" or info.get("vol20",0) < 100000 or info.get("close",0) < 50:
                continue
            # Calculate RS score vs Nifty 500
            rs = compute_rs_score(df_raw, bench_df_raw) if bench_df_raw is not None else None
            results.append({"Symbol": ticker, "Signal": state, "RS Score": rs, **info})

        # Sort confirmed stocks by RS score (highest first)
        results.sort(key=lambda x: (
            {"confirmed":0,"breakout":1,"near_52w":2,"ema_cross":3,"watching":4}.get(x["Signal"],5),
            -(x["RS Score"] or 0)
        ))
        pb.empty()
        # Tag results with whether market was open/closed/weekend
        market_status = "weekend" if is_weekend else "market_hours" if is_market_hours else "post_close"
        st.session_state["scan_results"] = results
        st.session_state["scan_time"]    = now_ist.strftime("%d %b %Y %H:%M IST")
        st.session_state["scan_status"]  = market_status

    if "scan_results" in st.session_state:
        results = st.session_state["scan_results"]
        scan_tag = st.session_state.get("scan_status","")
        tag_icon = {"post_close":"✅ After market close","weekend":"⚠️ Weekend scan","market_hours":"⚡ During market hours"}.get(scan_tag,"")
        st.caption(f"Last scan: {st.session_state.get('scan_time','')} · {tag_icon} · {len(NIFTY500)} stocks checked · {len(results)} signals found")

        # Filter
        state_map = {"All": None, "✅ Confirmed":"confirmed",
                     "🔥 Breakout":"breakout", "⚡ Near 52W High":"near_52w",
                     "📡 EMA Cross":"ema_cross", "👁 Watching":"watching"}
        sel = state_map.get(filt)
        filtered = [r for r in results if sel is None or r["Signal"] == sel]

        if not filtered:
            st.warning("No signals for this filter.")
        else:
            # Summary counts
            # counts rendered below with 5 columns
            counts = {r["Signal"] for r in results}
            c1,c2,c3,c4,c5 = st.columns(5)
            for col, sig, emoji, label in [
                (c1,"confirmed","✅","Confirmed"),
                (c2,"breakout","🔥","Breakout"),
                (c3,"near_52w","⚡","Near 52W"),
                (c4,"ema_cross","📡","EMA Cross"),
                (c5,"watching","👁","Watching"),
            ]:
                n = sum(1 for r in results if r["Signal"]==sig)
                col.metric(f"{emoji} {label}", n)

            st.markdown("---")

            # Table
            label_map = {
                "confirmed" :"✅ CONFIRMED — Trade Ready",
                "breakout"  :"🔥 Breakout — In Confirmation",
                "near_52w"  :"⚡ Near 52W High",
                "ema_cross" :"📡 Fresh EMA Cross",
                "watching"  :"👁 Watching",
            }
            rows = []
            for r in filtered:
                rs = r.get("RS Score")
                rows.append({
                    "Symbol"             : r["Symbol"],
                    "Signal"             : label_map.get(r["Signal"], r["Signal"]),
                    "RS Score"           : f"{rs:+.2f}" if rs is not None else "—",
                    "CMP ₹"              : r["close"],
                    "EMA 220 ₹"         : r["ema220"],
                    "% above EMA"       : f"{r['pct_above_ema']:+.2f}%",
                    "52W High ₹ (locked)": r["w52_high"],
                    "% from 52W"        : f"{r['pct_from_52w']:+.2f}%",
                    "SL ₹"              : r["sl_level"],
                    "RSI"               : r["rsi"],
                    "Change %"          : f"{r['change_pct']:+.2f}%",
                    "Days above 52W Hi" : r.get("days_since_break","—"),
                })
            df_results = pd.DataFrame(rows)
            st.dataframe(df_results, hide_index=True, use_container_width=True, height=500)

            # Click to chart
            st.markdown("#### View chart for a signal stock")
            pick = st.selectbox("Select symbol", [r["Symbol"] for r in filtered])
            if pick:
                df_raw = fetch_data(f"{pick}.NS","2y")
                if df_raw is not None:
                    df = add_indicators(df_raw)
                    fig = build_chart(df, pick, 180)
                    st.plotly_chart(fig, use_container_width=True)

        # ── Debug any stock ──
        st.markdown("---")
        st.markdown("#### 🔎 Debug any stock — see exactly why it passed or failed")
        debug_sym = st.text_input("Enter NSE symbol to debug", placeholder="e.g. NESTLEIND").upper().strip()
        if debug_sym:
            df_dbg = fetch_data(f"{debug_sym}.NS", "2y")
            if df_dbg is None:
                st.error(f"Could not load {debug_sym}")
            else:
                df_dbg = add_indicators(df_dbg)
                state_dbg, info_dbg = get_signal_state(df_dbg)

                st.markdown(f"**Signal state: `{state_dbg}`**")
                d1,d2,d3,d4 = st.columns(4)
                d1.metric("CMP", f"₹{info_dbg.get('close','—')}")
                d2.metric("EMA 220", f"₹{info_dbg.get('ema220','—')}")
                d3.metric("52W High (locked)", f"₹{info_dbg.get('w52_high','—')}")
                d4.metric("% from 52W", f"{info_dbg.get('pct_from_52w','—')}%")

                d5,d6,d7,d8 = st.columns(4)
                d5.metric("EMA Cross Date", info_dbg.get("cross_date","—"))
                d6.metric("Days since cross", info_dbg.get("days_since_cross","—"))
                d7.metric("Days since 52W break", info_dbg.get("days_since_break","—"))
                d8.metric("Above EMA 220", "✅ Yes" if info_dbg.get("above_ema") else "❌ No")

                # Show last 20 days close vs EMA
                st.markdown("**Last 20 days — Close vs EMA 220 (check for any day below EMA):**")
                last20 = df_dbg[["Close","EMA220"]].tail(20).copy()
                last20["Above EMA?"] = last20["Close"] > last20["EMA220"]
                last20["Close"] = last20["Close"].round(2)
                last20["EMA220"] = last20["EMA220"].round(2)
                last20.index = last20.index.strftime("%d %b %Y")
                st.dataframe(last20, use_container_width=True)

                if "reset_reason" in info_dbg:
                    st.error(f"❌ Reset reason: {info_dbg['reset_reason']}")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — MY POSITIONS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💼 My Positions":
    st.markdown("## My Positions")
    positions     = read_positions_from_sheet()
    closed_trades = read_closed_from_sheet()
    st.markdown(f'Data source: [Open Google Sheet]({get_sheet_link()})')
    if st.button("Reload from Sheet"):
        st.cache_data.clear()
        st.rerun()
    if not positions:
        st.info("No positions. Add trades to Google Sheet.")
    else:
        live = []
        with st.spinner("Fetching prices..."):
            for pos in positions:
                sym = pos.get("symbol","").upper()
                df_raw = fetch_data(f"{sym}.NS")
                if df_raw is None: continue
                df_ind = add_indicators(df_raw)
                row = df_ind.iloc[-1]; prev = df_ind.iloc[-2]
                cmp = float(row["Close"]); ema = float(row["EMA220"])
                ep  = float(pos.get("entry_price", cmp))
                sh  = int(float(pos.get("shares", 0)))
                sl  = float(pos.get("trailing_sl", max(ema, ep*0.85)))
                pct = (cmp - ep) / ep * 100
                chg = (cmp - float(prev["Close"])) / float(prev["Close"]) * 100
                nsl = round(max(ema, cmp*0.85), 2)
                estr = str(pos.get("entry_date","")).strip()
                try:
                    edt = datetime.datetime.strptime(estr, "%Y-%m-%d")
                except:
                    try: edt = datetime.datetime.strptime(estr, "%d/%m/%Y")
                    except: edt = datetime.datetime.now()
                days = (datetime.datetime.now() - edt).days
                live.append({"symbol":sym,"entry_price":ep,"shares":sh,"entry_date":estr,
                    "hold_days":days,"cmp":round(cmp,2),"ema220":round(ema,2),
                    "pnl_pct":round(pct,2),"pnl_rs":round((cmp-ep)*sh,2),
                    "change_pct":round(chg,2),"trailing_sl":round(sl,2),"new_sl":nsl,
                    "sl_updated":nsl>sl,"near_sl":cmp<sl*1.05,
                    "target_40":round(ep*1.4,2),"target_100":round(ep*2.0,2),
                    "hit_40":pct>=40,"hit_100":pct>=100,"near_40pct":pct>=35})
        st.session_state["_live_cache"] = live
        if not live:
            st.error("Could not fetch prices.")
        else:
            total_inv = sum(p["entry_price"]*p["shares"] for p in live)
            total_cur = sum(p["cmp"]*p["shares"] for p in live)
            total_pnl = total_cur - total_inv
            total_pct = total_pnl/total_inv*100 if total_inv>0 else 0
            day_pnl   = sum(p["change_pct"]/100*p["cmp"]*p["shares"] for p in live)

            s1,s2,s3,s4,s5,s6 = st.columns(6)
            s1.metric("Invested",      f"Rs.{total_inv:,.0f}")
            s2.metric("Current Value", f"Rs.{total_cur:,.0f}")
            s3.metric("Total P&L",     f"Rs.{total_pnl:+,.0f}", f"{total_pct:+.2f}%")
            s4.metric("Day P&L",       f"Rs.{day_pnl:+,.0f}")
            s5.metric("Positions",     f"{len(live)} / 8")
            s6.metric("Best",          max(live,key=lambda x:x["pnl_pct"])["symbol"],
                      f"{max(live,key=lambda x:x['pnl_pct'])['pnl_pct']:+.2f}%")

            for p in live:
                if p["near_sl"]:   st.error(f"WARNING: {p['symbol']} near SL Rs.{p['trailing_sl']}")
                if p["hit_40"]:    st.success(f"TARGET: {p['symbol']} up +{p['pnl_pct']:.1f}% - consider booking 50%")
                if p["sl_updated"]:st.info(f"UPDATE SL: {p['symbol']} raise from Rs.{p['trailing_sl']} to Rs.{p['new_sl']}")

            st.markdown("---")
            st.markdown("#### Holdings Overview")
            rows = []
            for p in sorted(live, key=lambda x:x["pnl_pct"], reverse=True):
                inv = p["entry_price"]*p["shares"]
                rows.append({"Stock":p["symbol"],"Qty":p["shares"],
                    "Buy Price":f"Rs.{p['entry_price']:,.2f}",
                    "CMP":f"Rs.{p['cmp']:,.2f}",
                    "Invested":f"Rs.{inv:,.0f}",
                    "Current":f"Rs.{p['cmp']*p['shares']:,.0f}",
                    "Day %":f"{p['change_pct']:+.2f}%",
                    "Total P&L":f"Rs.{p['pnl_rs']:+,.0f}",
                    "Total %":f"{p['pnl_pct']:+.2f}%",
                    "SL":f"Rs.{p['trailing_sl']:,.0f}",
                    "Days":p["hold_days"]})
            st.dataframe(rows, hide_index=True, use_container_width=True)

            st.markdown("---")
            st.markdown("#### Individual Holdings")
            htabs = st.tabs([p["symbol"] for p in live])
            for htab, p in zip(htabs, live):
                with htab:
                    inv      = p["entry_price"]*p["shares"]
                    curr     = p["cmp"]*p["shares"]
                    day_p    = p["change_pct"]/100*p["cmp"]*p["shares"]
                    dist_pct = (p["cmp"]-p["trailing_sl"])/p["cmp"]*100
                    pnl_c    = "normal" if p["pnl_pct"] >= 0 else "inverse"
                    chg_c    = "normal" if p["change_pct"] >= 0 else "inverse"

                    m1,m2,m3,m4 = st.columns(4)
                    m1.metric("CMP",         f"Rs.{p['cmp']:,.2f}", f"{p['change_pct']:+.2f}% today")
                    m2.metric("Buying Price", f"Rs.{p['entry_price']:,.2f}")
                    m3.metric("Total P&L",   f"Rs.{p['pnl_rs']:+,.0f}", f"{p['pnl_pct']:+.2f}%")
                    m4.metric("Days Held",   str(p["hold_days"]))

                    st.markdown("---")
                    c1,c2,c3 = st.columns(3)

                    with c1:
                        st.markdown("**Position**")
                        st.metric("Shares",        str(p["shares"]))
                        st.metric("Invested",      f"Rs.{inv:,.0f}")
                        st.metric("Current Value", f"Rs.{curr:,.0f}", f"Rs.{p['pnl_rs']:+,.0f}")

                    with c2:
                        st.markdown("**P&L**")
                        st.metric("Today Change",  f"{p['change_pct']:+.2f}%")
                        st.metric("Today P&L",     f"Rs.{day_p:+,.0f}")
                        st.metric("Total P&L",     f"Rs.{p['pnl_rs']:+,.0f}", f"{p['pnl_pct']:+.2f}%")

                    with c3:
                        st.markdown("**Stop Loss**")
                        st.metric("Trailing SL",   f"Rs.{p['trailing_sl']:,.2f}")
                        st.metric("Updated SL",    f"Rs.{p['new_sl']:,.2f}", "raise it!" if p["sl_updated"] else "")
                        st.metric("Distance",      f"{dist_pct:.1f}% above SL")

                    st.markdown("---")
                    t1,t2,t3 = st.columns(3)
                    t1.metric("+40% target (sell 50%)",  f"Rs.{p['target_40']:,.2f}",
                        "HIT!" if p["hit_40"] else f"Rs.{(p['target_40']-p['cmp'])*p['shares']:,.0f} away")
                    t2.metric("+100% target (sell 25%)", f"Rs.{p['target_100']:,.2f}",
                        "HIT!" if p["hit_100"] else f"Rs.{(p['target_100']-p['cmp'])*p['shares']:,.0f} away")
                    t3.metric("EMA 220", f"Rs.{p['ema220']:,.2f}",
                        f"{((p['cmp']/p['ema220'])-1)*100:+.1f}% from EMA")

                    if p["sl_updated"]: st.info(f"Update SL to Rs.{p['new_sl']} in Google Sheet")
                    if p["near_sl"]:    st.error(f"Only {dist_pct:.1f}% above SL - monitor closely!")
                    if p["hit_40"]:     st.success(f"+40% target hit! Consider selling {p['shares']//2} shares")

            st.markdown("---")

            cc1,cc2 = st.columns(2)
            with cc1:
                st.markdown("#### Allocation")
                fig_pie = go.Figure(data=[go.Pie(
                    labels=[p["symbol"] for p in live],
                    values=[round(p["cmp"]*p["shares"],0) for p in live],
                    hole=0.5, textinfo="label+percent",
                    marker=dict(colors=["#7c6af7","#34d399","#f87171","#fbbf24","#22d3ee","#a89cff","#6ee7b7","#fca5a5"]))])
                fig_pie.update_layout(paper_bgcolor="#0d0d14",plot_bgcolor="#0d0d14",
                    font=dict(color="#e0e0f0"),showlegend=False,height=280,
                    margin=dict(l=10,r=10,t=10,b=10),
                    annotations=[dict(text=f"Rs.{total_cur:,.0f}",x=0.5,y=0.5,
                        font_size=12,font_color="#fff",showarrow=False)])
                st.plotly_chart(fig_pie, use_container_width=True)
            with cc2:
                st.markdown("#### P&L by Stock")
                pnl_vals = [p["pnl_rs"] for p in live]
                fig_bar = go.Figure(data=[go.Bar(
                    x=[p["symbol"] for p in live],y=pnl_vals,
                    marker_color=["#34d399" if v>=0 else "#f87171" for v in pnl_vals],
                    text=[f"Rs.{v:+,.0f}" for v in pnl_vals],textposition="outside")])
                fig_bar.update_layout(paper_bgcolor="#0d0d14",plot_bgcolor="#0d0d14",
                    font=dict(color="#e0e0f0"),height=280,showlegend=False,
                    margin=dict(l=10,r=10,t=10,b=10),
                    xaxis=dict(gridcolor="#1a1a2e"),yaxis=dict(gridcolor="#1a1a2e"))
                fig_bar.add_hline(y=0,line_color="#888",line_dash="dot")
                st.plotly_chart(fig_bar, use_container_width=True)

            st.markdown("---")
            st.markdown("### Realised P&L")
            closed = read_closed_from_sheet()
            _live_data = st.session_state.get("_live_cache",[])
            _total_inv = sum(p["entry_price"]*p["shares"] for p in _live_data) if _live_data else 0

            with st.expander("Log a Closed Trade"):
                lc1,lc2,lc3,lc4,lc5,lc6 = st.columns(6)
                with lc1: ct_sym = st.text_input("Symbol",key="ct_sym").upper().strip()
                with lc2: ct_ep  = st.number_input("Entry Rs.",min_value=0.0,step=0.5,key="ct_ep")
                with lc3: ct_xp  = st.number_input("Exit Rs.", min_value=0.0,step=0.5,key="ct_xp")
                with lc4: ct_sh  = st.number_input("Shares",  min_value=1,step=1,key="ct_sh")
                with lc5: ct_edt = st.date_input("Entry Date",key="ct_edt")
                with lc6: ct_xdt = st.date_input("Exit Date", key="ct_xdt")
                ct_reason = st.selectbox("Reason",["Trailing SL","+40% Profit","+100% Profit","Manual Exit"],key="ct_reason")
                if st.button("Log Trade",type="primary",key="ct_add"):
                    if ct_sym and ct_ep>0 and ct_xp>0 and ct_sh>0:
                        pnl = round((ct_xp-ct_ep)*ct_sh*0.995,2)
                        pct2= round((ct_xp-ct_ep)/ct_ep*100,2)
                        st.success(f"{ct_sym} P&L: Rs.{pnl:+,.0f} ({pct2:+.2f}%)")
                        st.info(f"Add to Google Sheet Closed tab: {ct_sym} | {ct_ep} | {ct_xp} | {ct_sh} | {ct_edt} | {ct_xdt} | {ct_reason}")
                    else: st.error("Fill all fields")

            if closed:
                total_realised = sum(t["pnl_rs"] for t in closed)
                wins   = [t for t in closed if t["pnl_rs"]>0]
                losses = [t for t in closed if t["pnl_rs"]<=0]
                wr = len(wins)/len(closed)*100 if closed else 0
                pf = sum(t["pnl_rs"] for t in wins)/abs(sum(t["pnl_rs"] for t in losses)) if losses and sum(t["pnl_rs"] for t in losses)!=0 else 0
                rc1,rc2,rc3,rc4,rc5 = st.columns(5)
                rc1.metric("Realised P&L", f"Rs.{total_realised:+,.0f}")
                rc2.metric("Trades",       len(closed))
                rc3.metric("Win Rate",     f"{wr:.0f}%")
                rc4.metric("Avg Win",      f"{sum(t['pnl_pct'] for t in wins)/len(wins) if wins else 0:+.1f}%")
                rc5.metric("Profit Factor",f"{pf:.2f}" if pf else "N/A")
                total_unreal = sum(p["pnl_rs"] for p in _live_data) if _live_data else 0
                uc1,uc2,uc3 = st.columns(3)
                uc1.metric("Unrealised", f"Rs.{total_unreal:+,.0f}")
                uc2.metric("Realised",   f"Rs.{total_realised:+,.0f}")
                uc3.metric("Combined",   f"Rs.{total_unreal+total_realised:+,.0f}")
                trows = [{"Symbol":t["symbol"],"Entry Date":t["entry_date"],"Exit Date":t["exit_date"],
                    "Entry Rs.":t["entry_price"],"Exit Rs.":t["exit_price"],"Shares":t["shares"],
                    "P&L Rs.":f"Rs.{t['pnl_rs']:+,.0f}","P&L %":f"{t['pnl_pct']:+.2f}%",
                    "Days":t["hold_days"],"Reason":t["reason"]} for t in reversed(closed)]
                st.dataframe(trows, hide_index=True, use_container_width=True)
            else:
                st.info("No closed trades yet.")

            with st.expander("How to Add Positions"):
                st.markdown(f"All position management in [Google Sheet]({get_sheet_link()}). Add rows in Positions tab. Delete and move to Closed tab when exiting.")


elif page == "📁 Portfolio":
    st.markdown("## 📁 Portfolio")

    positions  = read_positions_from_sheet()
    if not positions:
        st.info("No positions found. Add trades to your Google Sheet.")
    else:
        live2 = []
        with st.spinner("Fetching prices..."):
            for pos in positions:
                sym = pos.get("symbol","").upper()
                df_raw = fetch_data(f"{sym}.NS")
                if df_raw is None: continue
                df_ind = add_indicators(df_raw)
                row = df_ind.iloc[-1]; prev = df_ind.iloc[-2]
                cmp = float(row["Close"]); ema = float(row["EMA220"])
                ep  = float(pos.get("entry_price", cmp))
                sh  = int(pos.get("shares", 0))
                sl  = float(pos.get("trailing_sl", max(ema, ep*0.85)))
                pct = (cmp - ep) / ep * 100
                chg = (cmp - float(prev["Close"])) / float(prev["Close"]) * 100
                live2.append({
                    "symbol"      : sym,
                    "entry_price" : ep,
                    "shares"      : sh,
                    "cmp"         : round(cmp, 2),
                    "pnl_pct"     : round(pct, 2),
                    "pnl_rs"      : round((cmp - ep) * sh, 2),
                    "change_pct"  : round(chg, 2),
                    "trailing_sl" : round(sl, 2),
                    "new_sl"      : round(max(ema, cmp*0.85), 2),
                    "sl_updated"  : max(ema, cmp*0.85) > sl,
                })

        if not live2:
            st.error("Could not fetch prices.")
        else:
            # ── Summary bar ──
            total_inv2 = sum(p["entry_price"]*p["shares"] for p in live2)
            total_cur2 = sum(p["cmp"]*p["shares"] for p in live2)
            total_pnl2 = total_cur2 - total_inv2
            total_pct2 = total_pnl2/total_inv2*100 if total_inv2>0 else 0
            day_pnl2   = sum(p["change_pct"]/100 * p["cmp"] * p["shares"] for p in live2)

            pc1,pc2,pc3,pc4 = st.columns(4)
            pc1.metric("Invested",     f"₹{total_inv2:,.2f}")
            pc2.metric("Current",      f"₹{total_cur2:,.2f}", f"{total_pct2:+.2f}%")
            pc3.metric("Total P&L",    f"₹{total_pnl2:+,.2f}")
            pc4.metric("Day's P&L",    f"₹{day_pnl2:+,.2f}")

            st.markdown("---")

            # ── Zerodha-style holdings list ──
            html = ['<div style="background:#13131f;border:1px solid #2a2a3d;border-radius:12px;overflow:hidden">']
            for i, p in enumerate(sorted(live2, key=lambda x: x["pnl_pct"], reverse=True)):
                invested   = p["entry_price"] * p["shares"]
                curr_val   = p["cmp"] * p["shares"]
                pnl_color  = "#34d399" if p["pnl_pct"] >= 0 else "#f87171"
                chg_color  = "#34d399" if p["change_pct"] >= 0 else "#f87171"
                pnl_sign   = "+" if p["pnl_pct"] >= 0 else ""
                chg_sign   = "+" if p["change_pct"] >= 0 else ""
                border     = "border-bottom:1px solid #2a2a3d;" if i < len(live2)-1 else ""
                sl_arrow   = " &#8593;" if p["sl_updated"] else ""

                html.append(
                    f'<div style="padding:14px 18px;{border}">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px">'
                    f'<div style="font-size:12px;color:#888">Qty {p["shares"]} &nbsp;&middot;&nbsp; Avg &#8377;{p["entry_price"]:,.2f}</div>'
                    f'<div style="font-size:13px;font-weight:700;color:{pnl_color}">{pnl_sign}{p["pnl_pct"]:.2f}%</div>'
                    f'</div>'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px">'
                    f'<div style="font-size:18px;font-weight:700;color:#e0e0f0;letter-spacing:-0.02em">{p["symbol"]}</div>'
                    f'<div style="font-size:18px;font-weight:700;color:{pnl_color}">{pnl_sign}&#8377;{abs(p["pnl_rs"]):,.2f}</div>'
                    f'</div>'
                    f'<div style="display:flex;justify-content:space-between;align-items:center">'
                    f'<div style="font-size:12px;color:#888">Invested &#8377;{invested:,.2f} &nbsp;&middot;&nbsp; '
                    f'<span style="color:#f87171">SL &#8377;{p["trailing_sl"]:,.2f}{sl_arrow}</span></div>'
                    f'<div style="font-size:12px;color:#888">LTP &#8377;{p["cmp"]:,.2f} '
                    f'<span style="color:{chg_color}">({chg_sign}{p["change_pct"]:.2f}%)</span></div>'
                    f'</div>'
                    f'</div>'
                )
            html.append('</div>')
            st.markdown("".join(html), unsafe_allow_html=True)

            # ── Day's P&L footer ──
            day_color = "#34d399" if day_pnl2 >= 0 else "#f87171"
            st.markdown(
                f'<div style="background:#13131f;border:1px solid #2a2a3d;border-radius:8px;'
                f'padding:12px 18px;margin-top:12px;display:flex;justify-content:space-between">'
                f'<span style="color:#888;font-size:14px">Days P&L</span>'
                f'<span style="color:{day_color};font-size:14px;font-weight:700">'
                f'{"+" if day_pnl2>=0 else ""}&#8377;{abs(day_pnl2):,.2f}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

elif page == "📈 Nifty 500":
    st.markdown("## Market Benchmark")

    # ── Load both indices ──
    with st.spinner("Loading benchmark data..."):
        df_n50  = fetch_data("^NSEI",   "5y")   # Nifty 50
        df_n500 = fetch_data("^CRSLDX", "5y")   # Nifty 500
        if df_n500 is None or df_n500.empty:
            df_n500 = fetch_data("^NSEI", "5y")

    # ── Tab selector ──
    idx_tab = st.radio("Select Index", ["Nifty 50", "Nifty 500", "Compare Both"],
                       horizontal=True)

    def index_section(df_raw, label):
        if df_raw is None:
            st.error(f"Could not load {label} data.")
            return
        df   = add_indicators(df_raw)
        row  = df.iloc[-1]; prev = df.iloc[-2]
        cmp  = float(row["Close"])
        chg  = (cmp - float(prev["Close"])) / float(prev["Close"]) * 100
        def ret(n):
            return round((cmp / float(df["Close"].iloc[-n]) - 1)*100, 2) if len(df) >= n else None

        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric(label,      f"{cmp:,.2f}",              f"{chg:+.2f}% today")
        c2.metric("1 Month",  f"{ret(21):+.2f}%"  if ret(21)  else "—")
        c3.metric("3 Months", f"{ret(63):+.2f}%"  if ret(63)  else "—")
        c4.metric("6 Months", f"{ret(126):+.2f}%" if ret(126) else "—")
        c5.metric("1 Year",   f"{ret(252):+.2f}%" if ret(252) else "—")

        fig = build_chart(df, label, 365)
        st.plotly_chart(fig, use_container_width=True)

        periods = [("1 Week",5),("1 Month",21),("3 Months",63),
                   ("6 Months",126),("1 Year",252),("2 Years",504),("5 Years",1260)]
        rows = []
        for name, n in periods:
            r = ret(n)
            rows.append({"Period": name, "Return": f"{r:+.2f}%" if r else "—",
                         "Direction": "📈" if r and r > 0 else "📉" if r else "—"})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    if idx_tab == "Nifty 50":
        st.markdown("### Nifty 50 (^NSEI)")
        index_section(df_n50, "Nifty 50")

    elif idx_tab == "Nifty 500":
        st.markdown("### Nifty 500 (^CRSLDX)")
        index_section(df_n500, "Nifty 500")

    else:
        # ── Side by side comparison ──
        st.markdown("### Nifty 50 vs Nifty 500")

        if df_n50 is None or df_n500 is None:
            st.error("Could not load one or both indices.")
        else:
            df50  = add_indicators(df_n50)
            df500 = add_indicators(df_n500)
            r50   = df50.iloc[-1];  p50  = df50.iloc[-2]
            r500  = df500.iloc[-1]; p500 = df500.iloc[-2]
            c50   = float(r50["Close"]);  c500  = float(r500["Close"])
            chg50 = (c50  - float(p50["Close"]))  / float(p50["Close"])  * 100
            chg500= (c500 - float(p500["Close"])) / float(p500["Close"]) * 100

            def ret_idx(df, n):
                return round((float(df["Close"].iloc[-1]) / float(df["Close"].iloc[-n]) - 1)*100, 2) if len(df) >= n else None

            # Comparison metrics
            periods_cmp = [("Today", None), ("1M", 21), ("3M", 63), ("6M", 126), ("1Y", 252), ("2Y", 504)]
            cols = st.columns(len(periods_cmp))
            for col, (label, n) in zip(cols, periods_cmp):
                if n is None:
                    v50  = f"{chg50:+.2f}%"
                    v500 = f"{chg500:+.2f}%"
                else:
                    r50v  = ret_idx(df50, n)
                    r500v = ret_idx(df500, n)
                    v50   = f"{r50v:+.2f}%"  if r50v  else "—"
                    v500  = f"{r500v:+.2f}%" if r500v else "—"
                col.markdown(f"""
                <div style="background:#13131f;border:1px solid #2a2a3d;border-radius:8px;padding:12px;text-align:center">
                    <div style="font-size:11px;color:#888;text-transform:uppercase;margin-bottom:6px">{label}</div>
                    <div style="font-size:13px;font-weight:700;color:#a89cff">N50</div>
                    <div style="font-size:16px;font-weight:700;color:{'#34d399' if '+' in v50 else '#f87171'}">{v50}</div>
                    <div style="font-size:13px;font-weight:700;color:#22d3ee;margin-top:6px">N500</div>
                    <div style="font-size:16px;font-weight:700;color:{'#34d399' if '+' in v500 else '#f87171'}">{v500}</div>
                </div>
                """, unsafe_allow_html=True)

            # Overlay chart — both indices normalised to 100
            st.markdown("#### Normalised Performance (base = 100)")
            common_start = max(df50.index[0], df500.index[0])
            d50  = df50[df50.index  >= common_start]["Close"].tail(365)
            d500 = df500[df500.index >= common_start]["Close"].tail(365)
            n50_norm  = d50  / float(d50.iloc[0])  * 100
            n500_norm = d500 / float(d500.iloc[0]) * 100

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=n50_norm.index,  y=n50_norm.values,
                name="Nifty 50",  line=dict(color="#a89cff", width=2)))
            fig.add_trace(go.Scatter(x=n500_norm.index, y=n500_norm.values,
                name="Nifty 500", line=dict(color="#22d3ee", width=2)))
            fig.add_hline(y=100, line_dash="dot", line_color="#888", opacity=0.4)
            fig.update_layout(
                paper_bgcolor="#0d0d14", plot_bgcolor="#0d0d14",
                font=dict(color="#888"), height=350,
                legend=dict(bgcolor="#13131f", bordercolor="#2a2a3d"),
                margin=dict(l=10,r=10,t=20,b=10),
                yaxis=dict(gridcolor="#1a1a2e", title="Indexed to 100"),
                xaxis=dict(gridcolor="#1a1a2e"),
            )
            st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — POSITION SIZER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🧮 Position Sizer":
    st.markdown("## 🧮 Position Size Calculator")
    st.markdown("Calculates exact shares and capital to deploy using the 1.5% risk rule.")

    # ── Inputs ──
    st.markdown("### Enter Trade Details")
    c1, c2 = st.columns(2)
    with c1:
        capital = st.number_input(
            "Current Capital (₹)",
            min_value=10000, max_value=10000000,
            value=500000, step=5000,
            help="Your total available trading capital right now"
        )
    with c2:
        sym_input = st.text_input(
            "NSE Symbol (auto-fetches CMP & EMA 220)",
            placeholder="e.g. AARTIIND",
            value=""
        ).upper().strip()

    # Manual override toggle
    manual = st.toggle("Enter price manually instead of auto-fetch", value=False)

    if manual or not sym_input:
        c1, c2 = st.columns(2)
        with c1:
            entry_price = st.number_input("Entry Price ₹ (tomorrow's expected open)", min_value=1.0, step=0.5, value=500.0)
        with c2:
            ema220_val  = st.number_input("EMA 220 ₹", min_value=1.0, step=0.5, value=430.0)
        cmp_live = entry_price
        fetched  = False
    else:
        with st.spinner(f"Fetching live data for {sym_input}..."):
            df_raw = fetch_data(f"{sym_input}.NS")
        if df_raw is None:
            st.error(f"Could not fetch data for {sym_input}. Check symbol.")
            st.stop()
        df_ind     = add_indicators(df_raw)
        row_live   = df_ind.iloc[-1]
        prev_live  = df_ind.iloc[-2]
        cmp_live   = float(row_live["Close"])
        ema220_val = float(row_live["EMA220"])
        chg_live   = (cmp_live - float(prev_live["Close"])) / float(prev_live["Close"]) * 100
        fetched    = True

        # Show live quote
        st.success(f"✅ Live data fetched for **{sym_input}**")
        q1,q2,q3,q4 = st.columns(4)
        q1.metric("CMP",      f"₹{cmp_live:,.2f}", f"{chg_live:+.2f}%")
        q2.metric("EMA 220",  f"₹{ema220_val:,.2f}")
        q3.metric("Open",     f"₹{float(row_live['Open']):,.2f}")
        q4.metric("RSI",      f"{float(row_live['RSI']):.1f}" if not pd.isna(row_live['RSI']) else "—")

        # Entry price = use CMP as estimate (actual entry = next day open)
        entry_price = st.number_input(
            "Expected Entry Price ₹ (next day open — adjust if needed)",
            min_value=1.0, step=0.5,
            value=round(cmp_live, 2),
            help="Strategy enters at next day's open price. Adjust based on your expectation."
        )

    st.markdown("---")

    # ── Core Calculations ──
    risk_pct    = 0.01                                     # 1% risksk
    risk_amount = capital * risk_pct                       # Rs at risk
    sl_15pct    = entry_price * 0.85                       # 15% below entry below entry
    initial_sl  = round(max(ema220_val, sl_15pct), 2)     # strategy SL
    risk_per_sh = entry_price - initial_sl                 # risk per share

    if risk_per_sh <= 0:
        st.error("⚠️ Entry price is below or equal to SL — invalid trade setup.")
        st.stop()

    import math
    shares_raw  = risk_amount / risk_per_sh
    shares      = math.floor(shares_raw)
    deploy      = shares * entry_price
    deploy_pct  = deploy / capital * 100

    # Max 20% cap
    max_deploy  = capital * 0.20
    if deploy > max_deploy:
        shares  = math.floor(max_deploy / entry_price)
        deploy  = shares * entry_price
        deploy_pct = deploy / capital * 100
        capped  = True
    else:
        capped  = False

    # Checks
    check_min   = deploy >= 20000
    check_max   = deploy <= capital * 0.20
    check_valid = shares > 0

    # ── Results ──
    st.markdown("### 📊 Position Sizing Result")

    # Main result card
    if check_valid and check_min:
        st.success(f"✅ **BUY {shares} shares of {sym_input or 'stock'} at ₹{entry_price:,.2f} — Deploy ₹{deploy:,.0f}**")
    elif not check_min:
        st.error(f"❌ Deploy amount ₹{deploy:,.0f} is below minimum ₹20,000 — **SKIP THIS TRADE**")
    else:
        st.error("❌ Invalid position — skip trade")

    if capped:
        st.warning(f"⚠️ Position was capped at 20% of capital. Original shares would have been {math.floor(risk_amount/risk_per_sh)} but capped to {shares}.")

    st.markdown("#### Calculation Breakdown")
    r1,r2,r3 = st.columns(3)

    with r1:
        st.markdown("**Step 1 — Stop Loss**")
        sl_data = {
            "Rule"       : ["15% below entry", "EMA 220 level", "Initial SL (higher of both)"],
            "Value ₹"    : [f"₹{sl_15pct:,.2f}", f"₹{ema220_val:,.2f}", f"₹{initial_sl:,.2f}"],
            "Used?"      : ["✓" if sl_15pct >= ema220_val else "—",
                            "✓" if ema220_val > sl_15pct else "—",
                            "✅"]
        }
        st.dataframe(pd.DataFrame(sl_data), hide_index=True, use_container_width=True)

    with r2:
        st.markdown("**Step 2 — Shares**")
        sh_data = {
            "Item"       : ["Capital", "Risk %", "Risk Amount", "Risk per Share", "Raw Shares", "Final Shares"],
            "Value"      : [
                f"₹{capital:,.0f}",
                "1%",
                f"₹{risk_amount:,.0f}",
                f"₹{risk_per_sh:,.2f}",
                f"{shares_raw:.1f}",
                f"{shares} (floor)"
            ]
        }
        st.dataframe(pd.DataFrame(sh_data), hide_index=True, use_container_width=True)

    with r3:
        st.markdown("**Step 3 — Checks**")
        chk_data = {
            "Rule"          : ["Min deploy ≥ ₹20,000", "Max deploy ≤ 20% capital", "Shares > 0"],
            "Required"      : ["₹20,000", f"₹{max_deploy:,.0f}", "> 0"],
            "Actual"        : [f"₹{deploy:,.0f}", f"₹{deploy:,.0f}", str(shares)],
            "Status"        : ["✅" if check_min else "❌",
                               "✅" if check_max else "❌",
                               "✅" if check_valid else "❌"]
        }
        st.dataframe(pd.DataFrame(chk_data), hide_index=True, use_container_width=True)

    st.markdown("---")
    st.markdown("#### 💰 Trade Summary")

    m1,m2,m3,m4,m5,m6 = st.columns(6)
    m1.metric("Shares to Buy",   f"{shares}")
    m2.metric("Capital Deploy",  f"₹{deploy:,.0f}")
    m3.metric("% of Capital",    f"{deploy_pct:.1f}%")
    m4.metric("Initial SL",      f"₹{initial_sl:,.2f}")
    m5.metric("Max Loss (₹)",    f"₹{shares * risk_per_sh:,.0f}")
    m6.metric("Max Loss (%)",    f"{risk_pct*100:.0f}%")

    st.markdown("---")
    st.markdown("#### 🎯 Profit Targets")

    t1,t2,t3,t4 = st.columns(4)
    t1.metric("+20%",  f"₹{entry_price*1.20:,.2f}", f"+₹{shares*entry_price*0.20:,.0f}")
    t2.metric("+40% → Sell 50%", f"₹{entry_price*1.40:,.2f}",
              f"Receive ₹{math.floor(shares*0.5)*entry_price*1.40:,.0f}")
    t3.metric("+100% → Sell 25%", f"₹{entry_price*2.00:,.2f}",
              f"Receive ₹{math.floor(shares*0.25)*entry_price*2.00:,.0f}")
    t4.metric("Remaining 25% held", f"{math.ceil(shares*0.25)} shares",
              "Hold until trailing SL")

    st.markdown("---")
    st.markdown("#### 📅 Trailing SL Schedule (Version B)")
    st.caption("Updated every Friday. New SL = max(EMA 220, Friday close × 0.85). Only moves UP.")

    # Simulate trailing SL at different price levels
    levels = [1.05, 1.10, 1.20, 1.30, 1.40, 1.60, 1.80, 2.00]
    trail_rows = []
    for mult in levels:
        price     = entry_price * mult
        trail_sl  = round(price * 0.85, 2)
        locked_in = round((trail_sl - entry_price) / entry_price * 100, 2)
        trail_rows.append({
            "If Friday Close"   : f"₹{price:,.2f} ({(mult-1)*100:+.0f}%)",
            "New Trailing SL"   : f"₹{trail_sl:,.2f}",
            "Locked-in Gain %"  : f"{locked_in:+.2f}%",
            "Status"            : "🔒 Profit locked!" if locked_in > 0 else "📉 Still at risk"
        })
    st.dataframe(pd.DataFrame(trail_rows), hide_index=True, use_container_width=True)

    # ── Multi-stock batch calculator ──
    st.markdown("---")
    st.markdown("### 📋 Batch Calculator — All 8 Positions")
    st.caption("Enter up to 8 symbols to see capital allocation across full portfolio.")

    batch_syms = st.text_input(
        "Enter symbols separated by commas",
        placeholder="AARTIIND, KAYNES, LUPIN, SUNPHARMA",
        value=""
    )

    if batch_syms and st.button("Calculate All", type="primary"):
        symbols_list = [s.strip().upper() for s in batch_syms.split(",") if s.strip()][:8]
        batch_rows   = []
        total_deploy = 0

        with st.spinner("Fetching prices..."):
            for s in symbols_list:
                df_b = fetch_data(f"{s}.NS")
                if df_b is None:
                    batch_rows.append({"Symbol":s,"CMP":"—","EMA220":"—","SL":"—",
                                       "Shares":"—","Deploy":"—","% Capital":"—","Status":"❌ Not found"})
                    continue
                df_b     = add_indicators(df_b)
                rb       = df_b.iloc[-1]
                cb       = float(rb["Close"]); eb = float(rb["EMA220"])
                sl_b     = round(max(eb, cb*0.85), 2)
                rps_b    = cb - sl_b
                if rps_b <= 0:
                    batch_rows.append({"Symbol":s,"CMP":f"₹{cb:,.2f}","EMA220":f"₹{eb:,.2f}",
                                       "SL":f"₹{sl_b:,.2f}","Shares":"—","Deploy":"—",
                                       "% Capital":"—","Status":"❌ Price below SL"})
                    continue
                sh_b     = math.floor((capital*0.01) / rps_b)
                dep_b    = sh_b * cb
                if dep_b > capital*0.20:
                    sh_b  = math.floor(capital*0.20 / cb)
                    dep_b = sh_b * cb
                total_deploy += dep_b
                status = "✅ Valid" if dep_b >= 20000 else "⚠️ Below min"
                batch_rows.append({
                    "Symbol"    : s,
                    "CMP ₹"     : f"₹{cb:,.2f}",
                    "EMA 220 ₹" : f"₹{eb:,.2f}",
                    "SL ₹"      : f"₹{sl_b:,.2f}",
                    "Shares"    : sh_b,
                    "Deploy ₹"  : f"₹{dep_b:,.0f}",
                    "% Capital" : f"{dep_b/capital*100:.1f}%",
                    "Status"    : status,
                })

        st.dataframe(pd.DataFrame(batch_rows), hide_index=True, use_container_width=True)

        b1, b2, b3 = st.columns(3)
        b1.metric("Total Deployed",   f"₹{total_deploy:,.0f}")
        b2.metric("% of Capital",     f"{total_deploy/capital*100:.1f}%")
        b3.metric("Remaining Cash",   f"₹{capital-total_deploy:,.0f}")
