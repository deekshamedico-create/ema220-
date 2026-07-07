"""
220 EMA Breakout Strategy — Nasdaq 100 Live Dashboard
Run: streamlit run nasdaq_dashboard.py
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import os
import math

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="220 EMA — Nasdaq 100",
    page_icon="🇺🇸",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stApp { background-color: #0a0f0d; color: #f0f0f0; }
    div[data-testid="metric-container"] {
        background: #0f1a14; border: 1px solid #1a3a2a;
        border-radius: 10px; padding: 12px;
    }
    div[data-testid="metric-container"] label { color: #a0c8b0 !important; font-size: 13px !important; }
    div[data-testid="metric-container"] [data-testid="metric-value"] { color: #ffffff !important; font-weight: 700 !important; }
    section[data-testid="stSidebar"] { background-color: #060e09 !important; }
    section[data-testid="stSidebar"] label { color: #e0f0e8 !important; font-size: 14px !important; }
    div[data-testid="stInfo"]    { background: #0d1f33 !important; border-left: 4px solid #4488ff !important; color: #c8e8ff !important; }
    div[data-testid="stSuccess"] { background: #0a2018 !important; border-left: 4px solid #34d399 !important; color: #a0ffd8 !important; }
    div[data-testid="stWarning"] { background: #281800 !important; border-left: 4px solid #fbbf24 !important; color: #ffe8a0 !important; }
    div[data-testid="stError"]   { background: #280808 !important; border-left: 4px solid #f87171 !important; color: #ffc8c8 !important; }
    .stButton button { background: #0f2a1a !important; color: #ffffff !important; border: 1px solid #1a5a30 !important; font-weight: 600 !important; }
    .stTextInput input, .stNumberInput input { background: #0f1a14 !important; color: #ffffff !important; border: 1px solid #1a3a2a !important; }
    .stDataFrame th { background: #0f1a14 !important; color: #ffffff !important; font-weight: 700 !important; }
    .stTabs [data-baseweb="tab"] { color: #80a890 !important; font-weight: 600 !important; }
    .stTabs [aria-selected="true"] { color: #ffffff !important; }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
EMA_PERIOD = 220
os.makedirs("data_cache_nasdaq", exist_ok=True)

# Official Nasdaq 100 components (deduplicated at source)
NASDAQ100 = [
    "AAPL","MSFT","NVDA","AMZN","META","GOOGL","GOOG","TSLA","AVGO","COST",
    "NFLX","AMD","ADBE","QCOM","CSCO","INTU","AMAT","MU","LRCX","KLAC",
    "MRVL","SNPS","CDNS","ADI","ON","MCHP","NXPI","FTNT","PANW","CRWD",
    "ZS","DDOG","TEAM","WDAY","SNOW","OKTA","MDB","HUBS","VEEV","ANSS",
    "ENPH","FSLR","ALGN","IDXX","ILMN","BIIB","GILD","VRTX","REGN","AMGN",
    "MRNA","DXCM","ISRG","GEHC","EXC","XEL","SBUX","MDLZ","PEP","KDP",
    "MNST","CELH","DLTR","ROST","ORLY","CTAS","PAYX","FAST","ODFL","VRSK",
    "CPRT","CTSH","TTWO","EA","CMCSA","CHTR","LULU","EBAY","MELI","PDD",
    "BIDU","TCOM","ABNB","PYPL","COIN","FICO","SMCI","DELL","STX","NTAP",
    "PSTG","ANET","KEYS","EXPE","BKNG","UBER","DASH","SPOT","RBLX","CDW",
    "CSGP","GFS","HON","KHC","LCID","LOGI","MAR","NDAQ",
    "PCAR","PODD","POOL","RIVN","SIRI","SWKS","TECH",
    "TMUS","TXN","VRSN","WBA","ZBRA","ZM",
]
NASDAQ100 = list(dict.fromkeys(NASDAQ100))  # safety dedup

BENCHMARK = "QQQ"

# ── NYSE/Nasdaq market hours (ET) ─────────────────────────────────────────────
def get_market_status():
    _tz_utc       = datetime.timezone.utc
    now_utc       = datetime.datetime.now(_tz_utc)
    now_et        = (now_utc - datetime.timedelta(hours=4)).replace(tzinfo=None)  # EDT naive
    is_weekend    = now_et.weekday() >= 5
    market_open   = datetime.time(9, 30)
    market_close  = datetime.time(16, 0)
    is_mkt_hours  = market_open <= now_et.time() <= market_close
    is_post_close = now_et.time() > market_close
    return now_et, is_weekend, is_mkt_hours, is_post_close

# ── Data fetch with strict daily caching ──────────────────────────────────────
@st.cache_data(ttl=86400)
def fetch_data(symbol, period="2y"):
    cache = f"data_cache_nasdaq/{symbol.replace('.','_').replace('^','_')}.csv"
    now_et, is_weekend, _, _ = get_market_status()
    today            = now_et.date()
    now_utc_naive    = (datetime.datetime.now(datetime.timezone.utc)).replace(tzinfo=None)
    market_close_utc = datetime.datetime.combine(today, datetime.time(20, 0))  # 4PM ET = 8PM UTC

    if os.path.exists(cache):
        mtime            = datetime.datetime.fromtimestamp(os.path.getmtime(cache), tz=datetime.timezone.utc).replace(tzinfo=None)
        cache_age        = (now_utc_naive - mtime).total_seconds()
        cache_is_today   = mtime.date() == today
        cache_post_close = now_utc_naive > market_close_utc

        if (cache_is_today and cache_post_close) or (is_weekend and cache_age < 172800):
            try:
                df = pd.read_csv(cache, index_col=0, parse_dates=True)
                if len(df) > 10:
                    return df
            except Exception:
                pass

    try:
        df = yf.download(symbol, period=period, auto_adjust=True, progress=False)
        if df is None or df.empty:
            if os.path.exists(cache):
                return pd.read_csv(cache, index_col=0, parse_dates=True)
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
        if not df.empty:
            df.to_csv(cache)
        return df if not df.empty else None
    except Exception:
        if os.path.exists(cache):
            try:
                return pd.read_csv(cache, index_col=0, parse_dates=True)
            except Exception:
                pass
        return None


def add_indicators(df):
    df = df.copy()
    df["EMA220"] = df["Close"].ewm(span=220, adjust=False).mean()
    df["EMA50"]  = df["Close"].ewm(span=50,  adjust=False).mean()
    df["EMA20"]  = df["Close"].ewm(span=20,  adjust=False).mean()
    df["Vol20"]  = df["Volume"].rolling(20).mean()
    d = df["Close"].diff()
    g = d.clip(lower=0).rolling(14).mean()
    l = (-d.clip(upper=0)).rolling(14).mean()
    df["RSI"]         = 100 - (100 / (1 + g / l.replace(0, np.nan)))
    ema12             = df["Close"].ewm(span=12, adjust=False).mean()
    ema26             = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"]        = ema12 - ema26
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"]   = df["MACD"] - df["MACD_signal"]
    return df


# FIX: RS score uses outperformance (difference), not ratio with abs()
def compute_rs_score(stock_df, bench_df):
    """
    RS Score = avg of:
      (stock 3M return - QQQ 3M return)
      (stock 6M return - QQQ 6M return)
    Positive = outperforming QQQ.
    """
    try:
        common = stock_df.index.intersection(bench_df.index)
        if len(common) < 126:
            return None
        s = stock_df["Close"].reindex(common)
        b = bench_df["Close"].reindex(common)
        s_now = float(s.iloc[-1]); b_now = float(b.iloc[-1])
        s63  = (s_now / float(s.iloc[-63])  - 1) * 100
        b63  = (b_now / float(b.iloc[-63])  - 1) * 100
        s126 = (s_now / float(s.iloc[-126]) - 1) * 100
        b126 = (b_now / float(b.iloc[-126]) - 1) * 100
        return round(((s63 - b63) + (s126 - b126)) / 2, 2)
    except Exception:
        return None


def get_signal_state(df):
    """
    4-step signal state machine (identical to NSE dashboard):
    Step 1: EMA 220 cross → lock 52W high on that day
    Step 2: Break locked 52W high within 60 days, staying above EMA 220
    Step 3 (breakout): 10-day confirmation window after 52W break
    Step 4 (confirmed): 10+ days elapsed since 52W break

    Returns: (state, info_dict)
      state = 'none' | 'ema_cross' | 'watching' | 'near_52w' | 'breakout' | 'confirmed'
    """
    # FIX: Guard against dataframes with fewer than 2 usable rows
    if df is None or len(df) < max(EMA_PERIOD + 5, 2):
        return "none", {}

    row   = df.iloc[-1]
    prev  = df.iloc[-2]
    c     = float(row["Close"])
    e     = float(row["EMA220"])
    vol20 = float(row["Vol20"]) if not pd.isna(row["Vol20"]) else 0
    rsi   = float(row["RSI"])   if not pd.isna(row["RSI"])   else 50
    chg   = (c - float(prev["Close"])) / float(prev["Close"]) * 100

    _w52_display = round(float(df["Close"].iloc[-252:].max()), 2) if len(df) >= 252 else round(c, 2)

    # Search backwards for most recent EMA cross within 60 trading days
    cross_idx  = None
    w52_fixed  = None
    cross_date = None

    for i in range(1, min(62, len(df) - 2)):
        c1 = float(df["Close"].iloc[-i]);   e1 = float(df["EMA220"].iloc[-i])
        c0 = float(df["Close"].iloc[-i-1]); e0 = float(df["EMA220"].iloc[-i-1])
        if c1 <= e1:
            break
        if c1 > e1 and c0 <= e0:
            cross_idx  = i
            cross_date = df.index[-i]
            cutoff     = cross_date - pd.Timedelta(days=365)
            hist       = df["Close"][(df.index >= cutoff) & (df.index < cross_date)]
            w52_fixed  = float(hist.max()) if not hist.empty else float(df["Close"].iloc[:-i].max())
            break

    if cross_idx is None:
        return "none", {
            "close": round(c, 2), "ema220": round(e, 2),
            "w52_high": _w52_display,
            "pct_from_52w": round((c - _w52_display) / _w52_display * 100, 2),
            "pct_above_ema": round((c - e) / e * 100, 2),
            "sl_level": round(max(e, c * 0.90), 2),
            "vol20": round(vol20), "rsi": round(rsi, 1),
            "change_pct": round(chg, 2), "above_ema": c > e,
        }

    post_cross   = df.iloc[-cross_idx:]
    stayed_above = all(
        float(post_cross["Close"].iloc[j]) > float(post_cross["EMA220"].iloc[j])
        for j in range(len(post_cross))
    )
    p52 = (c - w52_fixed) / w52_fixed * 100

    if not stayed_above:
        return "none", {
            "close": round(c, 2), "ema220": round(e, 2),
            "w52_high": round(w52_fixed, 2), "pct_from_52w": round(p52, 2),
            "pct_above_ema": round((c - e) / e * 100, 2),
            "sl_level": round(max(e, c * 0.90), 2),
            "vol20": round(vol20), "rsi": round(rsi, 1),
            "change_pct": round(chg, 2), "above_ema": c > e,
            "reset_reason": "Broke below EMA 220 after cross",
        }

    days_since_cross = cross_idx - 1

    # FIX: Always initialise days_since_break before branching
    # FIX: Implement proper "breakout" state (10-day confirmation window)
    days_since_break = 0
    break_idx        = None

    if days_since_cross <= 1:
        state = "ema_cross"
    elif c > w52_fixed:
        for j in range(len(post_cross)):
            if float(post_cross["Close"].iloc[j]) > w52_fixed:
                break_idx = j
                break
        if break_idx is not None:
            days_since_break = len(post_cross) - 1 - break_idx
        state = "confirmed" if days_since_break >= 10 else "breakout"
    elif p52 > -3:
        state = "near_52w"
    else:
        state = "watching"

    return state, {
        "close"           : round(c, 2),
        "ema220"          : round(e, 2),
        "w52_high"        : round(w52_fixed, 2),
        "pct_from_52w"    : round(p52, 2),
        "pct_above_ema"   : round((c - e) / e * 100, 2),
        "sl_level"        : round(max(e, c * 0.90), 2),
        "vol20"           : round(vol20),
        "rsi"             : round(rsi, 1),
        "change_pct"      : round(chg, 2),
        "above_ema"       : c > e,
        "days_since_cross": days_since_cross,
        "days_since_break": days_since_break,  # always defined
        "cross_date"      : str(cross_date.date()) if cross_date else "—",
    }


def build_chart(df, symbol, show_days=180):
    # FIX: Guard against too-short dataframes
    if df is None or len(df) < 2:
        return go.Figure()

    df  = df.tail(show_days).copy()
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        row_heights=[0.6, 0.2, 0.2], vertical_spacing=0.03)

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name="Price",
        increasing_fillcolor="#34d399", increasing_line_color="#34d399",
        decreasing_fillcolor="#f87171", decreasing_line_color="#f87171",
    ), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["EMA220"], name="EMA 220",
        line=dict(color="#22d3ee", width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["EMA50"], name="EMA 50",
        line=dict(color="#fbbf24", width=1.2, dash="dash")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["EMA20"], name="EMA 20",
        line=dict(color="#a89cff", width=1, dash="dot")), row=1, col=1)

    colors = ["#34d399" if c >= o else "#f87171" for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume",
        marker_color=colors, opacity=0.7), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["Vol20"], name="Vol MA20",
        line=dict(color="#fbbf24", width=1.5)), row=2, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI",
        line=dict(color="#a89cff", width=1.5)), row=3, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#f87171", opacity=0.5, row=3, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#34d399", opacity=0.5, row=3, col=1)
    fig.add_hline(y=50, line_dash="dot", line_color="#888",    opacity=0.3, row=3, col=1)

    fig.update_layout(
        title=dict(text=f"{symbol} — Daily Chart", font=dict(size=16, color="#e0e0f0")),
        paper_bgcolor="#0a0f0d", plot_bgcolor="#0a0f0d",
        font=dict(color="#888", size=12),
        xaxis_rangeslider_visible=False,
        legend=dict(bgcolor="#0f1a14", bordercolor="#1a3a2a", borderwidth=1,
                    font=dict(color="#888", size=11)),
        height=650, margin=dict(l=10, r=10, t=50, b=10),
    )
    for i in range(1, 4):
        fig.update_xaxes(gridcolor="#0f1a14", row=i, col=1)
        fig.update_yaxes(gridcolor="#0f1a14", row=i, col=1)
    fig.update_yaxes(title_text="Price ($)", row=1, col=1)
    fig.update_yaxes(title_text="Volume",    row=2, col=1)
    fig.update_yaxes(title_text="RSI",       row=3, col=1, range=[0, 100])
    return fig


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🇺🇸 220 EMA — Nasdaq 100")
    st.markdown("---")
    page = st.radio("Navigate", [
        "📊 Stock Chart",
        "🔍 Signal Scanner",
        "💼 My Positions",
        "📈 QQQ Benchmark",
        "🧮 Position Sizer",
    ])
    st.markdown("---")
    now_et, is_weekend, is_mkt_hours, is_post_close = get_market_status()
    st.caption(f"🕐 ET: {now_et.strftime('%d %b %Y %H:%M')}")
    if is_weekend:
        st.warning("Weekend — market closed")
    elif is_mkt_hours:
        st.info("Market open")
    else:
        st.success("Market closed — best time to scan")
    st.caption(f"Universe: {len(NASDAQ100)} stocks · Benchmark: QQQ")

    # FIX: Separate refresh buttons — don't nuke all caches together
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        if st.button("🔄 Prices", width="stretch", help="Re-download price data"):
            fetch_data.clear()
            st.rerun()
    with col_r2:
        if st.button("🗑 Cache", width="stretch", help="Clear all cached data"):
            st.cache_data.clear()
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — STOCK CHART
# ══════════════════════════════════════════════════════════════════════════════
if page == "📊 Stock Chart":
    st.markdown("## Stock Chart & Analysis")

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        symbol = st.text_input("Nasdaq Symbol", value="AAPL",
                               placeholder="e.g. NVDA, MSFT, TSLA").upper().strip()
    with c2:
        period    = st.selectbox("Period", ["6mo", "1y", "2y", "5y"], index=2)
    with c3:
        show_days = st.selectbox("Chart view", [60, 90, 180, 365, 730],
                                 index=2, format_func=lambda x: f"Last {x} days")

    if symbol:
        with st.spinner(f"Loading {symbol}..."):
            df_raw = fetch_data(symbol, period)

        if df_raw is None or df_raw.empty:
            st.error(f"Could not load data for {symbol}.")
        else:
            df = add_indicators(df_raw)
            # FIX: Guard before accessing iloc[-2]
            if len(df) < 2:
                st.error("Not enough data to analyse.")
            else:
                state, info = get_signal_state(df)
                cmp = float(df.iloc[-1]["Close"])
                chg = info.get("change_pct", 0)

                m1, m2, m3, m4, m5, m6 = st.columns(6)
                m1.metric("Price",       f"${cmp:,.2f}",              f"{chg:+.2f}%")
                m2.metric("EMA 220",     f"${info['ema220']:,.2f}",   f"{info['pct_above_ema']:+.2f}%")
                m3.metric("52W High",    f"${info['w52_high']:,.2f}", f"{info['pct_from_52w']:+.2f}%")
                m4.metric("RSI (14)",    f"{info['rsi']}")
                m5.metric("SL Level",   f"${info['sl_level']:,.2f}")
                m6.metric("Vol 20d avg", f"{info['vol20']/1e6:.1f}M")

                state_map = {
                    "confirmed": ("✅ CONFIRMED SIGNAL — Ready to trade tomorrow!", "success"),
                    "breakout" : ("🔥 BREAKOUT — In 10-day confirmation window",    "success"),
                    "near_52w" : ("⚡ NEAR 52W HIGH — within 3% of locked 52W high","warning"),
                    "ema_cross": ("📡 FRESH EMA CROSS — Day 0, 52W high locked",    "info"),
                    "watching" : ("👁 WATCHING — Above EMA 220, awaiting 52W break","info"),
                    "none"     : ("— No active signal", None),
                }
                label, kind = state_map.get(state, ("—", None))
                if kind == "success": st.success(label)
                elif kind == "warning": st.warning(label)
                elif kind == "info": st.info(label)

                fig = build_chart(df, symbol, show_days)
                st.plotly_chart(fig, width="stretch")

                st.markdown("#### Key Levels")
                row = df.iloc[-1]
                col1, col2 = st.columns(2)
                with col1:
                    levels = pd.DataFrame({
                        "Level"     : ["Current Price","EMA 220","EMA 50","EMA 20","52W High (locked)","SL Level"],
                        "Value ($)" : [f"${cmp:,.2f}", f"${info['ema220']:,.2f}",
                                       f"${float(row['EMA50']):,.2f}", f"${float(row['EMA20']):,.2f}",
                                       f"${info['w52_high']:,.2f}", f"${info['sl_level']:,.2f}"],
                        "% from CMP": ["—", f"{info['pct_above_ema']:+.2f}%",
                                       f"{(cmp/float(row['EMA50'])-1)*100:+.2f}%",
                                       f"{(cmp/float(row['EMA20'])-1)*100:+.2f}%",
                                       f"{info['pct_from_52w']:+.2f}%",
                                       f"{(cmp/info['sl_level']-1)*100:+.2f}%"],
                    })
                    st.dataframe(levels, hide_index=True, width="stretch")
                with col2:
                    targets = pd.DataFrame({
                        "Target"   : ["+20%", "+40% (sell 50%)", "+100% (sell 25%)", "+200%"],
                        "Price ($)": [f"${cmp*1.20:,.2f}", f"${cmp*1.40:,.2f}",
                                      f"${cmp*2.00:,.2f}", f"${cmp*3.00:,.2f}"],
                    })
                    st.dataframe(targets, hide_index=True, width="stretch")

                with st.expander("Recent OHLCV Data"):
                    disp = df[["Open","High","Low","Close","Volume","EMA220","RSI"]].tail(20).round(2).copy()
                    disp.index = disp.index.strftime("%d %b %Y")
                    st.dataframe(disp, width="stretch")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — SIGNAL SCANNER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔍 Signal Scanner":
    st.markdown("## Signal Scanner — Nasdaq 100")

    now_et, is_weekend, is_mkt_hours, is_post_close = get_market_status()

    if is_weekend:
        st.warning(
            f"⚠️ **Today is {'Saturday' if now_et.weekday()==5 else 'Sunday'} — US markets closed.**\n\n"
            "Run the scanner Monday–Friday after 4:00 PM ET for accurate results."
        )
    elif is_mkt_hours:
        st.warning(f"⚠️ **Market open (ET {now_et.strftime('%H:%M')}).** Scan after 4:00 PM ET.")
    elif is_post_close:
        st.success(f"✅ **Market closed. ET {now_et.strftime('%H:%M')}** — Best time to scan.")

    filt = st.pills("Filter", ["All","✅ Confirmed","🔥 Breakout",
                                "⚡ Near 52W High","📡 EMA Cross","👁 Watching"],
                    default="All")

    last_scan_time = st.session_state.get("nasdaq_scan_time", "")
    scan_locked    = False
    if last_scan_time and not is_weekend and is_post_close:
        try:
            scan_dt = datetime.datetime.strptime(last_scan_time, "%d %b %Y %H:%M ET")
            if scan_dt.date() == now_et.date():
                scan_locked = True
        except Exception:
            pass

    if scan_locked:
        st.info("🔒 Scan results locked for today. Re-run tomorrow after market close.")

    scan_label = "🔍 Run Full Scan"
    if is_weekend:    scan_label = "🔍 Run Full Scan (weekend — use with caution)"
    if scan_locked:   scan_label = "🔒 Re-scan (today's results already locked)"

    if st.button(scan_label, type="primary", width="stretch"):
        bench_df_raw = fetch_data("QQQ", "2y")
        results = []
        pb    = st.progress(0, text="Scanning Nasdaq 100...")
        total = len(NASDAQ100)
        for i, ticker in enumerate(NASDAQ100):
            pb.progress((i + 1) / total, text=f"Scanning {ticker}... ({i+1}/{total})")
            df_raw = fetch_data(ticker, "2y")
            if df_raw is None or len(df_raw) < 225:
                continue
            df = add_indicators(df_raw)
            state, info = get_signal_state(df)
            if state == "none" or info.get("vol20", 0) < 500000 or info.get("close", 0) < 5:
                continue
            rs = compute_rs_score(df_raw, bench_df_raw) if bench_df_raw is not None else None
            results.append({"Symbol": ticker, "Signal": state, "RS Score": rs, **info})

        results.sort(key=lambda x: (
            {"confirmed":0,"breakout":1,"near_52w":2,"ema_cross":3,"watching":4}.get(x["Signal"], 5),
            -(x["RS Score"] or 0)
        ))
        pb.empty()
        st.session_state["nasdaq_scan_results"] = results
        st.session_state["nasdaq_scan_time"]    = now_et.strftime("%d %b %Y %H:%M ET")
        st.session_state["nasdaq_scan_status"]  = (
            "weekend" if is_weekend else "market_hours" if is_mkt_hours else "post_close"
        )

    if "nasdaq_scan_results" in st.session_state:
        results  = st.session_state["nasdaq_scan_results"]
        scan_tag = st.session_state.get("nasdaq_scan_status", "")
        tag_icon = {"post_close":"✅ After market close","weekend":"⚠️ Weekend",
                    "market_hours":"⚡ During market hours"}.get(scan_tag, "")
        st.caption(
            f"Last scan: {st.session_state.get('nasdaq_scan_time','')} · "
            f"{tag_icon} · {len(NASDAQ100)} stocks · {len(results)} signals"
        )

        state_map_filter = {
            "All": None, "✅ Confirmed": "confirmed", "🔥 Breakout": "breakout",
            "⚡ Near 52W High": "near_52w", "📡 EMA Cross": "ema_cross", "👁 Watching": "watching",
        }
        sel      = state_map_filter.get(filt)
        filtered = [r for r in results if sel is None or r["Signal"] == sel]

        if not filtered:
            st.warning("No signals for this filter.")
        else:
            c1, c2, c3, c4, c5 = st.columns(5)
            for col, sig, emoji, label in [
                (c1, "confirmed", "✅", "Confirmed"),
                (c2, "breakout",  "🔥", "Breakout"),
                (c3, "near_52w",  "⚡", "Near 52W"),
                (c4, "ema_cross", "📡", "EMA Cross"),
                (c5, "watching",  "👁", "Watching"),
            ]:
                col.metric(f"{emoji} {label}", sum(1 for r in results if r["Signal"] == sig))

            st.markdown("---")
            label_map = {
                "confirmed": "✅ Confirmed", "breakout": "🔥 Breakout",
                "near_52w" : "⚡ Near 52W",  "ema_cross": "📡 EMA Cross", "watching": "👁 Watching",
            }
            rows = []
            for r in filtered:
                rs = r.get("RS Score")
                rows.append({
                    "Symbol"              : r["Symbol"],
                    "Signal"              : label_map.get(r["Signal"], r["Signal"]),
                    "RS Score"            : f"{rs:+.2f}" if rs is not None else "—",
                    "Price $"             : r["close"],
                    "EMA 220 $"           : r["ema220"],
                    "% above EMA"         : f"{r['pct_above_ema']:+.2f}%",
                    "52W High $ (locked)" : r["w52_high"],
                    "% from 52W"          : f"{r['pct_from_52w']:+.2f}%",
                    "SL $"                : r["sl_level"],
                    "RSI"                 : r["rsi"],
                    "Change %"            : f"{r['change_pct']:+.2f}%",
                    "EMA Cross Date"      : r.get("cross_date", "—"),
                    "Days since cross"    : r.get("days_since_cross", "—"),
                    "Days since 52W break": r.get("days_since_break", "—"),
                })
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", height=500)

            st.markdown("#### View chart for a signal stock")
            pick = st.selectbox("Select symbol", [r["Symbol"] for r in filtered])
            if pick:
                df_raw = fetch_data(pick, "2y")
                if df_raw is not None and len(df_raw) >= 2:
                    fig = build_chart(add_indicators(df_raw), pick, 180)
                    st.plotly_chart(fig, width="stretch")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — MY POSITIONS  (Google Sheet backed)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💼 My Positions":
    st.markdown("## My Nasdaq Positions")

    NASDAQ_SHEET_ID   = "1_I2JEHn272zsVr_sWNmy_W0AmXROEFvtMppaCFS04rI"
    NASDAQ_POS_URL    = f"https://docs.google.com/spreadsheets/d/{NASDAQ_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Positions"
    NASDAQ_CLOSED_URL = f"https://docs.google.com/spreadsheets/d/{NASDAQ_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Closed"
    NASDAQ_SHEET_LINK = f"https://docs.google.com/spreadsheets/d/{NASDAQ_SHEET_ID}/edit"

    @st.cache_data(ttl=60)
    def read_nasdaq_positions():
        try:
            df = pd.read_csv(NASDAQ_POS_URL)
            df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
            positions = []
            for _, row in df.iterrows():
                if pd.isna(row.get("symbol", "")) or str(row.get("symbol", "")).strip() == "":
                    continue
                positions.append({
                    "symbol"      : str(row["symbol"]).strip().upper(),
                    "entry_price" : float(row.get("entry_price", 0)),
                    "shares"      : int(float(row.get("shares", 0))),
                    "entry_date"  : str(row.get("entry_date", "")).strip(),
                    "trailing_sl" : float(row.get("trailing_sl", 0)),
                })
            return positions
        except Exception as e:
            st.warning(f"Could not read Nasdaq positions from Google Sheet: {e}")
            return []

    @st.cache_data(ttl=60)
    def read_nasdaq_closed():
        try:
            df = pd.read_csv(NASDAQ_CLOSED_URL)
            df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
            if "exit_price" not in df.columns:
                return []
            trades = []
            for _, row in df.iterrows():
                sym = str(row.get("symbol", "")).strip().upper()
                if not sym or sym == "NAN" or sym == "SYMBOL":
                    continue
                ep  = float(row.get("entry_price", 0))
                xp  = float(row.get("exit_price",  0))
                sh  = int(float(row.get("shares",  0)))
                if xp == 0 or ep == 0:
                    continue
                pnl  = round((xp - ep) * sh * 0.995, 2)
                pct  = round((xp - ep) / ep * 100, 2) if ep > 0 else 0
                try:
                    edt  = pd.to_datetime(str(row.get("entry_date", "")), dayfirst=True).date()
                    xdt  = pd.to_datetime(str(row.get("exit_date",  "")), dayfirst=True).date()
                    hold = (xdt - edt).days
                except Exception:
                    hold = 0
                trades.append({
                    "symbol"      : sym,
                    "entry_price" : ep,
                    "exit_price"  : xp,
                    "shares"      : sh,
                    "entry_date"  : str(row.get("entry_date", "")),
                    "exit_date"   : str(row.get("exit_date",  "")),
                    "pnl_usd"     : pnl,
                    "pnl_pct"     : pct,
                    "hold_days"   : hold,
                    "reason"      : str(row.get("reason", "Manual Exit")),
                })
            return trades
        except Exception as e:
            st.warning(f"Could not read Nasdaq closed trades from Google Sheet: {e}")
            return []

    # ── Header ──
    st.markdown(f'Data source: [Open Google Sheet]({NASDAQ_SHEET_LINK})')
    col_r1, col_r2 = st.columns([1, 5])
    with col_r1:
        if st.button("🔄 Reload Sheet"):
            read_nasdaq_positions.clear()
            read_nasdaq_closed.clear()
            st.rerun()

    positions = read_nasdaq_positions()

    if not positions:
        st.info("No positions found. Add trades to the Google Sheet → Positions tab.")
        with st.expander("📋 Expected column format"):
            st.markdown("""
            Your **Positions** sheet needs these columns:
            `symbol | entry_price | shares | entry_date | trailing_sl`

            Your **Closed** sheet needs:
            `symbol | entry_price | exit_price | shares | entry_date | exit_date | reason`
            """)
    else:
        live = []
        with st.spinner("Fetching live prices..."):
            for pos in positions:
                sym    = pos.get("symbol", "").upper()
                df_raw = fetch_data(sym)
                if df_raw is None or len(df_raw) < 2:
                    continue
                df_ind = add_indicators(df_raw)
                row    = df_ind.iloc[-1]
                prev   = df_ind.iloc[-2]
                cmp    = float(row["Close"]); ema = float(row["EMA220"])
                ep     = float(pos.get("entry_price", cmp))
                sh     = int(float(pos.get("shares", 0)))
                sl     = float(pos.get("trailing_sl", max(ema, ep * 0.90)))
                pct    = (cmp - ep) / ep * 100
                chg    = (cmp - float(prev["Close"])) / float(prev["Close"]) * 100
                nsl    = round(max(ema, cmp * 0.90), 2)
                estr   = str(pos.get("entry_date", "")).strip()
                try:
                    edt = datetime.datetime.strptime(estr, "%Y-%m-%d")
                except Exception:
                    try:
                        edt = datetime.datetime.strptime(estr, "%d/%m/%Y")
                    except Exception:
                        edt = datetime.datetime.now()
                days = (datetime.datetime.now() - edt).days
                live.append({
                    "symbol"      : sym,
                    "entry_price" : ep,
                    "shares"      : sh,
                    "entry_date"  : estr,
                    "hold_days"   : days,
                    "cmp"         : round(cmp, 2),
                    "ema220"      : round(ema, 2),
                    "pnl_pct"     : round(pct, 2),
                    "pnl_usd"     : round((cmp - ep) * sh, 2),
                    "change_pct"  : round(chg, 2),
                    "trailing_sl" : round(sl, 2),
                    "new_sl"      : nsl,
                    "sl_updated"  : nsl > sl,
                    "near_sl"     : cmp < sl * 1.05,
                    "target_40"   : round(ep * 1.4, 2),
                    "target_100"  : round(ep * 2.0, 2),
                    "hit_40"      : pct >= 40,
                    "hit_100"     : pct >= 100,
                })
        st.session_state["_nasdaq_live_cache"] = live

        if not live:
            st.error("Could not fetch prices for any position.")
        else:
            # ── Alerts ──
            for p in live:
                if p["near_sl"]:    st.error(f"⚠️ {p['symbol']} — ${p['cmp']:.2f} near SL ${p['trailing_sl']:.2f}")
                if p["hit_40"]:     st.success(f"🎯 {p['symbol']} up +{p['pnl_pct']:.1f}% — consider booking 50%")
                if p["sl_updated"]: st.info(f"🔺 {p['symbol']}: raise SL from ${p['trailing_sl']} → ${p['new_sl']}")

            # ── Summary cards (no truncation) ──
            total_inv = sum(p["entry_price"] * p["shares"] for p in live)
            total_cur = sum(p["cmp"] * p["shares"] for p in live)
            total_pnl = total_cur - total_inv
            total_pct = total_pnl / total_inv * 100 if total_inv > 0 else 0
            day_pnl   = sum(p["change_pct"] / 100 * p["cmp"] * p["shares"] for p in live)
            best_p    = max(live, key=lambda x: x["pnl_pct"])
            pct_color = "#34d399" if total_pct >= 0 else "#f87171"
            day_color = "#34d399" if day_pnl   >= 0 else "#f87171"

            def _card(label, value, sub="", sub_color="#888"):
                return (
                    f'<div style="background:#0f1a14;border:1px solid #1a3a2a;border-radius:10px;'
                    f'padding:14px 16px;min-width:0;flex:1;">'
                    f'<div style="font-size:12px;color:#a0c8b0;margin-bottom:6px;">{label}</div>'
                    f'<div style="font-size:18px;font-weight:700;color:#fff;word-break:break-all;line-height:1.2;">{value}</div>'
                    + (f'<div style="font-size:12px;color:{sub_color};margin-top:4px;">{sub}</div>' if sub else "")
                    + "</div>"
                )

            st.markdown(
                '<div style="display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap;">'
                + _card("Invested",      f"${total_inv:,.0f}")
                + _card("Current Value", f"${total_cur:,.0f}")
                + _card("Total P&L",     f"${total_pnl:+,.0f}", f"{total_pct:+.2f}%", pct_color)
                + _card("Day P&L",       f"${day_pnl:+,.0f}", sub_color=day_color)
                + _card("Positions",     f"{len(live)} / 8")
                + _card("Best",          best_p["symbol"], f"{best_p['pnl_pct']:+.2f}%", "#34d399")
                + '</div>',
                unsafe_allow_html=True,
            )

            # ── Holdings table ──
            st.markdown("---")
            st.markdown("#### Holdings Overview")
            trows = []
            for p in sorted(live, key=lambda x: x["pnl_pct"], reverse=True):
                inv = p["entry_price"] * p["shares"]
                trows.append({
                    "Stock"    : p["symbol"],
                    "Qty"      : p["shares"],
                    "Buy $"    : f"${p['entry_price']:,.2f}",
                    "CMP $"    : f"${p['cmp']:,.2f}",
                    "Invested" : f"${inv:,.0f}",
                    "Current"  : f"${p['cmp']*p['shares']:,.0f}",
                    "Day %"    : f"{p['change_pct']:+.2f}%",
                    "P&L $"    : f"${p['pnl_usd']:+,.0f}",
                    "P&L %"    : f"{p['pnl_pct']:+.2f}%",
                    "SL $"     : f"${p['trailing_sl']:,.2f}",
                    "Days"     : p["hold_days"],
                })
            st.dataframe(trows, hide_index=True, width="stretch")

            # ── Individual tabs ──
            st.markdown("---")
            st.markdown("#### Individual Holdings")
            htabs = st.tabs([p["symbol"] for p in live])
            for htab, p in zip(htabs, live):
                with htab:
                    inv      = p["entry_price"] * p["shares"]
                    curr     = p["cmp"] * p["shares"]
                    day_p    = p["change_pct"] / 100 * p["cmp"] * p["shares"]
                    dist_pct = (p["cmp"] - p["trailing_sl"]) / p["cmp"] * 100

                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("CMP",          f"${p['cmp']:,.2f}",      f"{p['change_pct']:+.2f}% today")
                    m2.metric("Buying Price", f"${p['entry_price']:,.2f}")
                    m3.metric("Total P&L",    f"${p['pnl_usd']:+,.0f}", f"{p['pnl_pct']:+.2f}%")
                    m4.metric("Days Held",    str(p["hold_days"]))

                    st.markdown("---")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.markdown("**Position**")
                        st.metric("Shares",        str(p["shares"]))
                        st.metric("Invested",      f"${inv:,.0f}")
                        st.metric("Current Value", f"${curr:,.0f}", f"${p['pnl_usd']:+,.0f}")
                    with c2:
                        st.markdown("**P&L**")
                        st.metric("Today Change", f"{p['change_pct']:+.2f}%")
                        st.metric("Today P&L",    f"${day_p:+,.0f}")
                        st.metric("Total P&L",    f"${p['pnl_usd']:+,.0f}", f"{p['pnl_pct']:+.2f}%")
                    with c3:
                        st.markdown("**Stop Loss**")
                        st.metric("Trailing SL", f"${p['trailing_sl']:,.2f}")
                        st.metric("Updated SL",  f"${p['new_sl']:,.2f}", "raise it!" if p["sl_updated"] else "")
                        st.metric("Distance",    f"{dist_pct:.1f}% above SL")

                    st.markdown("---")
                    t1, t2, t3 = st.columns(3)
                    t1.metric("+40% target (sell 50%)",  f"${p['target_40']:,.2f}",
                              "HIT!" if p["hit_40"] else f"${(p['target_40']-p['cmp'])*p['shares']:,.0f} away")
                    t2.metric("+100% target (sell 25%)", f"${p['target_100']:,.2f}",
                              "HIT!" if p["hit_100"] else f"${(p['target_100']-p['cmp'])*p['shares']:,.0f} away")
                    t3.metric("EMA 220", f"${p['ema220']:,.2f}",
                              f"{((p['cmp']/p['ema220'])-1)*100:+.1f}% from EMA")

                    if p["sl_updated"]: st.info(f"Update SL to ${p['new_sl']} in Google Sheet")
                    if p["near_sl"]:    st.error(f"Only {dist_pct:.1f}% above SL — monitor closely!")
                    if p["hit_40"]:     st.success(f"+40% target hit! Consider selling {p['shares']//2} shares")

            # ── Charts ──
            st.markdown("---")
            cc1, cc2 = st.columns(2)
            with cc1:
                st.markdown("#### Allocation")
                fig_pie = go.Figure(data=[go.Pie(
                    labels=[p["symbol"] for p in live],
                    values=[round(p["cmp"] * p["shares"], 0) for p in live],
                    hole=0.5, textinfo="label+percent",
                    marker=dict(colors=["#22d3ee","#34d399","#f87171","#fbbf24","#a89cff","#6ee7b7","#fca5a5","#7c6af7"]))])
                fig_pie.update_layout(
                    paper_bgcolor="#0a0f0d", plot_bgcolor="#0a0f0d",
                    font=dict(color="#e0e0f0"), showlegend=False, height=280,
                    margin=dict(l=10, r=10, t=10, b=10),
                    annotations=[dict(text=f"${total_cur:,.0f}", x=0.5, y=0.5,
                                      font_size=12, font_color="#fff", showarrow=False)])
                st.plotly_chart(fig_pie, width="stretch")
            with cc2:
                st.markdown("#### P&L by Stock")
                pnl_vals = [p["pnl_usd"] for p in live]
                fig_bar  = go.Figure(data=[go.Bar(
                    x=[p["symbol"] for p in live], y=pnl_vals,
                    marker_color=["#34d399" if v >= 0 else "#f87171" for v in pnl_vals],
                    text=[f"${v:+,.0f}" for v in pnl_vals], textposition="outside")])
                fig_bar.update_layout(
                    paper_bgcolor="#0a0f0d", plot_bgcolor="#0a0f0d",
                    font=dict(color="#e0e0f0"), height=280, showlegend=False,
                    margin=dict(l=10, r=10, t=10, b=10),
                    xaxis=dict(gridcolor="#0f1a14"), yaxis=dict(gridcolor="#0f1a14"))
                fig_bar.add_hline(y=0, line_color="#888", line_dash="dot")
                st.plotly_chart(fig_bar, width="stretch")

            # ── Chart for individual stock ──
            st.markdown("---")
            pick = st.selectbox("View chart", [p["symbol"] for p in live])
            if pick:
                df_raw = fetch_data(pick, "2y")
                if df_raw is not None and len(df_raw) >= 2:
                    df_c  = add_indicators(df_raw)
                    pos_c = next(p for p in live if p["symbol"] == pick)
                    fig   = build_chart(df_c, pick, 180)
                    fig.add_hline(y=pos_c["entry_price"], line_dash="dash",
                                  line_color="#fbbf24", annotation_text="Entry",
                                  annotation_font_color="#fbbf24", row=1, col=1)
                    fig.add_hline(y=pos_c["trailing_sl"], line_dash="dash",
                                  line_color="#f87171", annotation_text="SL",
                                  annotation_font_color="#f87171", row=1, col=1)
                    st.plotly_chart(fig, width="stretch")

            # ── Realised P&L ──
            st.markdown("---")
            st.markdown("### Realised P&L")
            closed     = read_nasdaq_closed()
            _live_data = st.session_state.get("_nasdaq_live_cache", [])

            with st.expander("Log a Closed Trade"):
                lc1, lc2, lc3, lc4, lc5, lc6 = st.columns(6)
                with lc1: ct_sym  = st.text_input("Symbol",    key="nct_sym").upper().strip()
                with lc2: ct_ep   = st.number_input("Entry $", min_value=0.0, step=0.1, key="nct_ep")
                with lc3: ct_xp   = st.number_input("Exit $",  min_value=0.0, step=0.1, key="nct_xp")
                with lc4: ct_sh   = st.number_input("Shares",  min_value=1, step=1,     key="nct_sh")
                with lc5: ct_edt  = st.date_input("Entry Date", key="nct_edt")
                with lc6: ct_xdt  = st.date_input("Exit Date",  key="nct_xdt")
                ct_reason = st.selectbox("Reason",
                    ["Trailing SL", "+40% Profit", "+100% Profit", "Manual Exit"], key="nct_reason")
                if st.button("Log Trade", type="primary", key="nct_add"):
                    if ct_sym and ct_ep > 0 and ct_xp > 0 and ct_sh > 0:
                        pnl  = round((ct_xp - ct_ep) * ct_sh * 0.995, 2)
                        pct2 = round((ct_xp - ct_ep) / ct_ep * 100, 2)
                        st.success(f"{ct_sym} P&L: ${pnl:+,.0f} ({pct2:+.2f}%)")
                        st.info(f"Add to Google Sheet Closed tab: {ct_sym} | {ct_ep} | {ct_xp} | {ct_sh} | {ct_edt} | {ct_xdt} | {ct_reason}")
                    else:
                        st.error("Fill all fields")

            if closed:
                total_realised = sum(t["pnl_usd"] for t in closed)
                wins     = [t for t in closed if t["pnl_usd"] > 0]
                losses   = [t for t in closed if t["pnl_usd"] <= 0]
                wr       = len(wins) / len(closed) * 100 if closed else 0
                loss_sum = sum(t["pnl_usd"] for t in losses)
                pf       = sum(t["pnl_usd"] for t in wins) / abs(loss_sum) if loss_sum != 0 else 0

                rc1, rc2, rc3, rc4, rc5 = st.columns(5)
                rc1.metric("Realised P&L",  f"${total_realised:+,.0f}")
                rc2.metric("Trades",        len(closed))
                rc3.metric("Win Rate",      f"{wr:.0f}%")
                rc4.metric("Avg Win",       f"{sum(t['pnl_pct'] for t in wins)/len(wins) if wins else 0:+.1f}%")
                rc5.metric("Profit Factor", f"{pf:.2f}" if pf else "N/A")

                total_unreal = sum(p["pnl_usd"] for p in _live_data) if _live_data else 0
                uc1, uc2, uc3 = st.columns(3)
                uc1.metric("Unrealised", f"${total_unreal:+,.0f}")
                uc2.metric("Realised",   f"${total_realised:+,.0f}")
                uc3.metric("Combined",   f"${total_unreal + total_realised:+,.0f}")

                ctrows = [{
                    "Symbol"   : t["symbol"],
                    "Entry Date": t["entry_date"], "Exit Date": t["exit_date"],
                    "Entry $"  : t["entry_price"], "Exit $": t["exit_price"],
                    "Shares"   : t["shares"],
                    "P&L $"    : f"${t['pnl_usd']:+,.0f}",
                    "P&L %"    : f"{t['pnl_pct']:+.2f}%",
                    "Days"     : t["hold_days"],
                    "Reason"   : t["reason"],
                } for t in reversed(closed)]
                st.dataframe(ctrows, hide_index=True, width="stretch")
            else:
                st.info("No closed trades yet.")

            with st.expander("How to Add Positions"):
                st.markdown(
                    f"All position management in [Google Sheet]({NASDAQ_SHEET_LINK}). "
                    "Add rows to the **Positions** tab. When exiting, move the row to the **Closed** tab "
                    "and fill in exit_price, exit_date, and reason."
                )


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — QQQ BENCHMARK
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📈 QQQ Benchmark":
    st.markdown("## Market Benchmark")

    with st.spinner("Loading benchmark data..."):
        df_qqq = fetch_data("QQQ", "5y")
        df_spy = fetch_data("SPY", "5y")
        df_iwm = fetch_data("IWM", "5y")

    idx_tab = st.radio("Select", ["QQQ (Nasdaq 100)", "SPY (S&P 500)", "Compare All"],
                       horizontal=True)

    def index_section(df_raw, label):
        # FIX: Guard short data
        if df_raw is None or len(df_raw) < 2:
            st.error(f"Could not load enough data for {label}.")
            return
        df   = add_indicators(df_raw)
        row  = df.iloc[-1]; prev = df.iloc[-2]
        cmp  = float(row["Close"])
        chg  = (cmp - float(prev["Close"])) / float(prev["Close"]) * 100
        def ret(n):
            return round((cmp / float(df["Close"].iloc[-n]) - 1) * 100, 2) if len(df) >= n else None
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric(label,      f"${cmp:,.2f}",              f"{chg:+.2f}%")
        c2.metric("1 Month",  f"{ret(21):+.2f}%"  if ret(21)  else "—")
        c3.metric("3 Months", f"{ret(63):+.2f}%"  if ret(63)  else "—")
        c4.metric("6 Months", f"{ret(126):+.2f}%" if ret(126) else "—")
        c5.metric("1 Year",   f"{ret(252):+.2f}%" if ret(252) else "—")
        fig = build_chart(df, label, 365)
        st.plotly_chart(fig, width="stretch")
        periods = [("1 Week",5),("1 Month",21),("3 Months",63),
                   ("6 Months",126),("1 Year",252),("2 Years",504),("5 Years",1260)]
        rows = []
        for name, n in periods:
            r = ret(n)
            rows.append({"Period": name, "Return": f"{r:+.2f}%" if r else "—",
                         "Direction": "📈" if r and r > 0 else "📉" if r else "—"})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    if idx_tab == "QQQ (Nasdaq 100)":
        index_section(df_qqq, "QQQ — Nasdaq 100 ETF")
    elif idx_tab == "SPY (S&P 500)":
        index_section(df_spy, "SPY — S&P 500 ETF")
    else:
        st.markdown("### QQQ vs SPY vs IWM — Normalised (base = 100, last 1 year)")
        dfs = [("QQQ","#22d3ee",df_qqq), ("SPY","#34d399",df_spy), ("IWM","#fbbf24",df_iwm)]
        fig = go.Figure()
        for name, color, df_raw in dfs:
            if df_raw is None or len(df_raw) < 2:
                continue
            d = df_raw["Close"].tail(252)
            n = d / float(d.iloc[0]) * 100
            fig.add_trace(go.Scatter(x=n.index, y=n.values, name=name,
                          line=dict(color=color, width=2)))
        fig.add_hline(y=100, line_dash="dot", line_color="#888", opacity=0.4)
        fig.update_layout(
            paper_bgcolor="#0a0f0d", plot_bgcolor="#0a0f0d",
            font=dict(color="#888"), height=400,
            legend=dict(bgcolor="#0f1a14", bordercolor="#1a3a2a"),
            margin=dict(l=10, r=10, t=20, b=10),
            yaxis=dict(gridcolor="#0f1a14", title="Indexed to 100"),
            xaxis=dict(gridcolor="#0f1a14"),
        )
        st.plotly_chart(fig, width="stretch")

        rows = []
        for label, _, df_raw in dfs:
            if df_raw is None or len(df_raw) < 2:
                continue
            c = float(df_raw["Close"].iloc[-1])
            def r(n): return round((c / float(df_raw["Close"].iloc[-n]) - 1) * 100, 2) if len(df_raw) >= n else None
            rows.append({"Index": label,
                         "1M": f"{r(21):+.2f}%"  if r(21)  else "—",
                         "3M": f"{r(63):+.2f}%"  if r(63)  else "—",
                         "6M": f"{r(126):+.2f}%" if r(126) else "—",
                         "1Y": f"{r(252):+.2f}%" if r(252) else "—",
                         "2Y": f"{r(504):+.2f}%" if r(504) else "—"})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — POSITION SIZER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🧮 Position Sizer":
    st.markdown("## 🧮 Position Size Calculator")
    st.markdown("1% risk rule applied to USD capital.")

    c1, c2 = st.columns(2)
    with c1:
        capital = st.number_input("Current Capital ($)", min_value=1000,
                                  max_value=10000000, value=10000, step=500)
    with c2:
        sym_input = st.text_input("Symbol (auto-fetches price & EMA 220)",
                                  placeholder="e.g. NVDA", value="").upper().strip()

    manual = st.toggle("Enter price manually", value=False)

    if manual or not sym_input:
        c1, c2 = st.columns(2)
        with c1: entry_price = st.number_input("Entry Price $", min_value=0.1, step=0.1, value=100.0)
        with c2: ema220_val  = st.number_input("EMA 220 $",     min_value=0.1, step=0.1, value=85.0)
    else:
        with st.spinner(f"Fetching {sym_input}..."):
            df_raw = fetch_data(sym_input)
        # FIX: Guard short data
        if df_raw is None or len(df_raw) < 2:
            st.error(f"Could not fetch {sym_input}.")
            st.stop()
        df_ind     = add_indicators(df_raw)
        row_live   = df_ind.iloc[-1]; prev_live = df_ind.iloc[-2]
        cmp_live   = float(row_live["Close"]); ema220_val = float(row_live["EMA220"])
        chg_live   = (cmp_live - float(prev_live["Close"])) / float(prev_live["Close"]) * 100

        st.success(f"✅ Live data for **{sym_input}**")
        q1, q2, q3, q4 = st.columns(4)
        q1.metric("Price",   f"${cmp_live:,.2f}", f"{chg_live:+.2f}%")
        q2.metric("EMA 220", f"${ema220_val:,.2f}")
        q3.metric("Open",    f"${float(row_live['Open']):,.2f}")
        q4.metric("RSI",     f"{float(row_live['RSI']):.1f}" if not pd.isna(row_live["RSI"]) else "—")
        entry_price = st.number_input("Expected Entry Price $", min_value=0.1, step=0.1,
                                       value=round(cmp_live, 2))

    st.markdown("---")

    risk_pct   = 0.01
    sl_10pct   = entry_price * 0.90
    initial_sl = round(max(ema220_val, sl_10pct), 2)
    risk_amt   = capital * risk_pct
    risk_per_sh = entry_price - initial_sl

    if risk_per_sh <= 0:
        st.error("⚠️ Entry price is at or below SL — invalid setup.")
        st.stop()

    shares_raw = risk_amt / risk_per_sh
    shares     = math.floor(shares_raw)
    deploy     = shares * entry_price
    max_deploy = capital * 0.20
    capped     = False
    if deploy > max_deploy:
        shares = math.floor(max_deploy / entry_price)
        deploy = shares * entry_price
        capped = True

    check_min  = deploy >= 500
    deploy_pct = deploy / capital * 100

    st.markdown("### Result")
    if shares > 0 and check_min:
        st.success(f"✅ **BUY {shares} shares of {sym_input or 'stock'} at ${entry_price:,.2f} — Deploy ${deploy:,.0f}**")
    else:
        st.error(f"❌ Deploy ${deploy:,.0f} too small — skip this trade")
    if capped:
        st.warning(f"⚠️ Capped at 20% of capital. Original: {math.floor(risk_amt/risk_per_sh)} shares → capped to {shares}.")

    r1, r2, r3 = st.columns(3)
    with r1:
        st.markdown("**Stop Loss**")
        st.dataframe(pd.DataFrame({
            "Rule"   : ["10% below entry", "EMA 220", "Initial SL (higher)"],
            "Value $": [f"${sl_10pct:,.2f}", f"${ema220_val:,.2f}", f"${initial_sl:,.2f}"],
            "Used?"  : ["✓" if sl_10pct >= ema220_val else "—",
                        "✓" if ema220_val > sl_10pct  else "—", "✅"],
        }), hide_index=True, width="stretch")
    with r2:
        st.markdown("**Shares**")
        st.dataframe(pd.DataFrame({
            "Item" : ["Capital","Risk 1%","Risk Amount","Risk/Share","Shares"],
            "Value": [f"${capital:,.0f}", "1%", f"${risk_amt:,.0f}",
                      f"${risk_per_sh:,.2f}", f"{shares}"],
        }), hide_index=True, width="stretch")
    with r3:
        st.markdown("**Checks**")
        st.dataframe(pd.DataFrame({
            "Rule"    : ["Min $500", "Max 20% capital", "Shares > 0"],
            "Required": ["$500", f"${max_deploy:,.0f}", "> 0"],
            "Actual"  : [f"${deploy:,.0f}", f"${deploy:,.0f}", str(shares)],
            "Status"  : ["✅" if check_min else "❌",
                         "✅" if deploy <= max_deploy else "❌",
                         "✅" if shares > 0 else "❌"],
        }), hide_index=True, width="stretch")

    st.markdown("---")
    st.markdown("#### Trade Summary")
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Shares",       f"{shares}")
    m2.metric("Deploy",       f"${deploy:,.0f}")
    m3.metric("% of Capital", f"{deploy_pct:.1f}%")
    m4.metric("Initial SL",   f"${initial_sl:,.2f}")
    m5.metric("Max Loss $",   f"${shares*risk_per_sh:,.0f}")
    m6.metric("Max Loss %",   f"{risk_pct*100:.0f}%")

    st.markdown("#### Profit Targets")
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("+20%",             f"${entry_price*1.20:,.2f}")
    t2.metric("+40% — sell 50%",  f"${entry_price*1.40:,.2f}",
              f"Receive ${math.floor(shares*0.5)*entry_price*1.40:,.0f}")
    t3.metric("+100% — sell 25%", f"${entry_price*2.00:,.2f}",
              f"Receive ${math.floor(shares*0.25)*entry_price*2.00:,.0f}")
    t4.metric("Hold last 25%",    f"{math.ceil(shares*0.25)} shares", "Until trailing SL")

    st.markdown("#### Trailing SL Schedule")
    trail_rows = []
    for mult in [1.05, 1.10, 1.20, 1.30, 1.40, 1.60, 1.80, 2.00]:
        price    = entry_price * mult
        trail_sl = round(price * 0.90, 2)
        locked   = round((trail_sl - entry_price) / entry_price * 100, 2)
        trail_rows.append({
            "If Price"       : f"${price:,.2f} ({(mult-1)*100:+.0f}%)",
            "Trailing SL"    : f"${trail_sl:,.2f}",
            "Locked-in Gain" : f"{locked:+.2f}%",
            "Status"         : "🔒 Profit locked!" if locked > 0 else "📉 At risk",
        })
    st.dataframe(pd.DataFrame(trail_rows), hide_index=True, width="stretch")

    st.markdown("---")
    st.markdown("### Batch Calculator")
    batch = st.text_input("Symbols (comma separated)", placeholder="AAPL, NVDA, MSFT")
    if batch and st.button("Calculate All", type="primary"):
        syms = [s.strip().upper() for s in batch.split(",") if s.strip()][:8]
        rows = []; total_dep = 0
        with st.spinner("Fetching..."):
            for s in syms:
                df_b = fetch_data(s)
                # FIX: Guard short data
                if df_b is None or len(df_b) < 2:
                    rows.append({"Symbol":s,"Price":"—","EMA220":"—","SL":"—",
                                 "Shares":"—","Deploy":"—","% Cap":"—","Status":"❌ Not found"})
                    continue
                df_b   = add_indicators(df_b)
                rb     = df_b.iloc[-1]
                cb     = float(rb["Close"]); eb = float(rb["EMA220"])
                sl_b   = round(max(eb, cb * 0.90), 2)
                rps_b  = cb - sl_b
                if rps_b <= 0:
                    rows.append({"Symbol":s,"Price $":f"${cb:,.2f}","EMA220 $":f"${eb:,.2f}",
                                 "SL $":f"${sl_b:,.2f}","Shares":"—","Deploy":"—","% Cap":"—",
                                 "Status":"❌ Below SL"})
                    continue
                sh_b  = math.floor((capital * risk_pct) / rps_b)
                dep_b = sh_b * cb
                if dep_b > capital * 0.20:
                    sh_b = math.floor(capital * 0.20 / cb); dep_b = sh_b * cb
                total_dep += dep_b
                rows.append({
                    "Symbol"   : s, "Price $": f"${cb:,.2f}", "EMA 220 $": f"${eb:,.2f}",
                    "SL $"     : f"${sl_b:,.2f}", "Shares": sh_b,
                    "Deploy $" : f"${dep_b:,.0f}", "% Capital": f"{dep_b/capital*100:.1f}%",
                    "Status"   : "✅" if dep_b >= 500 else "⚠️ Small",
                })
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        b1, b2, b3 = st.columns(3)
        b1.metric("Total Deployed", f"${total_dep:,.0f}")
        b2.metric("% of Capital",   f"{total_dep/capital*100:.1f}%")
        b3.metric("Remaining Cash", f"${capital-total_dep:,.0f}")
