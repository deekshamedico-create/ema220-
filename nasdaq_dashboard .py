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
import datetime, os, math

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="220 EMA — Nasdaq 100",
    page_icon="🇺🇸",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stApp { background-color: #0a0f0d; }
    div[data-testid="metric-container"] {
        background: #0f1a14; border: 1px solid #1a3a2a;
        border-radius: 10px; padding: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
EMA_PERIOD = 220
os.makedirs("data_cache_nasdaq", exist_ok=True)

# Official Nasdaq 100 components
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
    "CSGP","GEHC","GFS","HON","ILMN","KHC","LCID","LOGI","MAR","NDAQ",
    "ODFL","PCAR","PODD","POOL","QGEN","RIVN","SGEN","SIRI","SWKS","TECH",
    "TMUS","TXN","VRSK","VRSN","WBA","ZBRA","ZM","ZS",
]
NASDAQ100 = list(dict.fromkeys(NASDAQ100))

BENCHMARK = "QQQ"   # Nasdaq 100 ETF — most reliable proxy

# ── NYSE/Nasdaq market hours (ET) ─────────────────────────────────────────────
def get_market_status():
    now_et = datetime.datetime.utcnow() - datetime.timedelta(hours=4)  # EDT
    is_weekend    = now_et.weekday() >= 5
    market_open   = datetime.time(9, 30)
    market_close  = datetime.time(16, 0)
    is_mkt_hours  = market_open <= now_et.time() <= market_close
    is_post_close = now_et.time() > market_close
    return now_et, is_weekend, is_mkt_hours, is_post_close

# ── Data fetch with strict daily caching ──────────────────────────────────────
@st.cache_data(ttl=86400)
def fetch_data(symbol, period="2y"):
    """
    Fetches OHLCV with strict daily caching.
    Uses post-market cache if available — prevents signal flipping.
    No .NS suffix — these are US tickers.
    """
    cache = f"data_cache_nasdaq/{symbol.replace('.','_').replace('^','_')}.csv"
    now_et, is_weekend, _, _ = get_market_status()
    today = now_et.date()
    market_close_utc = datetime.datetime.combine(today, datetime.time(20, 0))  # 4PM ET = 8PM UTC

    if os.path.exists(cache):
        mtime     = datetime.datetime.utcfromtimestamp(os.path.getmtime(cache))
        cache_age = (datetime.datetime.utcnow() - mtime).total_seconds()
        cache_is_today    = mtime.date() == today
        cache_post_close  = datetime.datetime.utcnow() > market_close_utc

        if (cache_is_today and cache_post_close) or (is_weekend and cache_age < 172800):
            try:
                df = pd.read_csv(cache, index_col=0, parse_dates=True)
                if len(df) > 10: return df
            except: pass

    try:
        df = yf.download(symbol, period=period, auto_adjust=True, progress=False)
        if df is None or df.empty:
            if os.path.exists(cache):
                return pd.read_csv(cache, index_col=0, parse_dates=True)
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[["Open","High","Low","Close","Volume"]].dropna()
        if not df.empty: df.to_csv(cache)
        return df if not df.empty else None
    except:
        if os.path.exists(cache):
            try: return pd.read_csv(cache, index_col=0, parse_dates=True)
            except: pass
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
    df["RSI"] = 100 - (100 / (1 + g / l.replace(0, np.nan)))
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"]        = ema12 - ema26
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"]   = df["MACD"] - df["MACD_signal"]
    return df

def compute_rs_score(stock_df, bench_df):
    """
    Composite RS Score vs QQQ benchmark.
    rs_63  = stock 63-day return / QQQ 63-day return
    rs_126 = stock 126-day return / QQQ 126-day return
    RS Score = (rs_63 + rs_126) / 2
    Higher = stronger stock relative to Nasdaq 100.
    """
    try:
        common = stock_df.index.intersection(bench_df.index)
        if len(common) < 126:
            return None
        s = stock_df["Close"].reindex(common)
        b = bench_df["Close"].reindex(common)
        s_now = float(s.iloc[-1]); b_now = float(b.iloc[-1])
        s63  = (s_now / float(s.iloc[-63])  - 1)
        b63  = (b_now / float(b.iloc[-63])  - 1)
        rs63 = s63 / abs(b63) if b63 != 0 else 0
        s126  = (s_now / float(s.iloc[-126]) - 1)
        b126  = (b_now / float(b.iloc[-126]) - 1)
        rs126 = s126 / abs(b126) if b126 != 0 else 0
        return round((rs63 + rs126) / 2, 2)
    except:
        return None

def get_signal_state(df):
    """
    Exact same 4-step state machine as NSE dashboard.
    Step 1: EMA 220 cross → lock 52W high on that day
    Step 2: Break locked 52W high within 60 days, staying above EMA 220
    Step 3: 10-day confirmation above EMA 220 and still above 52W high
    Step 4: Gap-down filter at entry (checked manually next day)
    """
    if df is None or len(df) < EMA_PERIOD + 5:
        return "none", {}

    row   = df.iloc[-1]; prev = df.iloc[-2]
    c     = float(row["Close"]); e = float(row["EMA220"])
    vol20 = float(row["Vol20"]) if not pd.isna(row["Vol20"]) else 0
    rsi   = float(row["RSI"])   if not pd.isna(row["RSI"])   else 50
    chg   = (c - float(prev["Close"])) / float(prev["Close"]) * 100

    # Find most recent EMA cross within last 60 trading days
    cross_idx  = None
    w52_fixed  = None
    cross_date = None

    # Search from TODAY backwards — find most recent cross where stock
    # has stayed above EMA 220 continuously from that cross to today
    for i in range(1, min(62, len(df)-2)):
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
            "close": round(c,2), "ema220": round(e,2),
            "w52_high": round(float(df["Close"].iloc[-252:].max()),2) if len(df)>=252 else 0,
            "pct_from_52w": 0, "pct_above_ema": round((c-e)/e*100,2),
            "sl_level": round(max(e, c*0.85),2), "vol20": round(vol20),
            "rsi": round(rsi,1), "change_pct": round(chg,2), "above_ema": c>e,
        }

    # Check stayed above EMA 220 every day since cross
    post_cross  = df.iloc[-cross_idx:]
    stayed_above = all(
        float(post_cross["Close"].iloc[j]) > float(post_cross["EMA220"].iloc[j])
        for j in range(len(post_cross))
    )

    p52 = (c - w52_fixed) / w52_fixed * 100

    if not stayed_above:
        return "none", {
            "close": round(c,2), "ema220": round(e,2),
            "w52_high": round(w52_fixed,2), "pct_from_52w": round(p52,2),
            "pct_above_ema": round((c-e)/e*100,2), "sl_level": round(max(e,c*0.85),2),
            "vol20": round(vol20), "rsi": round(rsi,1), "change_pct": round(chg,2),
            "above_ema": c>e, "reset_reason": "Broke below EMA 220 after cross",
        }

    days_since_cross = cross_idx - 1
    state = "none"
    if days_since_cross <= 1:
        state = "ema_cross"
    elif c > w52_fixed:
        # Broke 52W high + stayed above EMA 220 every day since cross → CONFIRMED
        break_idx = None
        for j in range(len(post_cross)):
            if float(post_cross["Close"].iloc[j]) > w52_fixed:
                break_idx = j
                break
        days_since_break = (len(post_cross) - 1 - break_idx) if break_idx is not None else 0
        state = "confirmed"
    elif p52 > -3:
        state = "near_52w"
    else:
        state = "watching"

    return state, {
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
        "cross_date"      : str(cross_date.date()) if cross_date else "—",
    }

def build_chart(df, symbol, show_days=180):
    df  = df.tail(show_days).copy()
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        row_heights=[0.6,0.2,0.2], vertical_spacing=0.03)
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
    colors = ["#34d399" if c >= o else "#f87171"
              for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume",
        marker_color=colors, opacity=0.7), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["Vol20"], name="Vol MA20",
        line=dict(color="#fbbf24", width=1.5)), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI",
        line=dict(color="#a89cff", width=1.5)), row=3, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#f87171", opacity=0.5, row=3, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#34d399", opacity=0.5, row=3, col=1)
    fig.add_hline(y=50, line_dash="dot", line_color="#888", opacity=0.3, row=3, col=1)
    fig.update_layout(
        title=dict(text=f"{symbol} — Daily Chart", font=dict(size=16, color="#e0e0f0")),
        paper_bgcolor="#0a0f0d", plot_bgcolor="#0a0f0d",
        font=dict(color="#888", size=12),
        xaxis_rangeslider_visible=False,
        legend=dict(bgcolor="#0f1a14", bordercolor="#1a3a2a", borderwidth=1,
                    font=dict(color="#888", size=11)),
        height=650, margin=dict(l=10,r=10,t=50,b=10),
    )
    for i in range(1,4):
        fig.update_xaxes(gridcolor="#0f1a14", row=i, col=1)
        fig.update_yaxes(gridcolor="#0f1a14", row=i, col=1)
    fig.update_yaxes(title_text="Price ($)", row=1, col=1)
    fig.update_yaxes(title_text="Volume",   row=2, col=1)
    fig.update_yaxes(title_text="RSI",      row=3, col=1, range=[0,100])
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
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — STOCK CHART
# ══════════════════════════════════════════════════════════════════════════════
if page == "📊 Stock Chart":
    st.markdown("## Stock Chart & Analysis")

    c1, c2, c3 = st.columns([2,1,1])
    with c1:
        symbol = st.text_input("Nasdaq Symbol", value="AAPL",
                               placeholder="e.g. NVDA, MSFT, TSLA").upper().strip()
    with c2:
        period    = st.selectbox("Period", ["6mo","1y","2y","5y"], index=2)
    with c3:
        show_days = st.selectbox("Chart view", [60,90,180,365,730],
                                 index=2, format_func=lambda x: f"Last {x} days")

    if symbol:
        with st.spinner(f"Loading {symbol}..."):
            df_raw = fetch_data(symbol, period)

        if df_raw is None or df_raw.empty:
            st.error(f"Could not load data for {symbol}.")
        else:
            df = add_indicators(df_raw)
            state, info = get_signal_state(df)
            row  = df.iloc[-1]; prev = df.iloc[-2]
            cmp  = float(row["Close"])
            chg  = info.get("change_pct", 0)

            m1,m2,m3,m4,m5,m6 = st.columns(6)
            m1.metric("Price",    f"${cmp:,.2f}",           f"{chg:+.2f}%")
            m2.metric("EMA 220",  f"${info['ema220']:,.2f}", f"{info['pct_above_ema']:+.2f}%")
            m3.metric("52W High", f"${info['w52_high']:,.2f}",f"{info['pct_from_52w']:+.2f}%")
            m4.metric("RSI (14)", f"{info['rsi']}")
            m5.metric("SL Level", f"${info['sl_level']:,.2f}")
            m6.metric("Vol 20d avg", f"{info['vol20']/1e6:.1f}M")

            state_map = {
                "confirmed" : ("✅ CONFIRMED SIGNAL — Ready to trade tomorrow!", "success"),
                "breakout"  : ("🔥 BREAKOUT — In 10-day confirmation window", "success"),
                "near_52w"  : ("⚡ NEAR 52W HIGH — within 3% of locked 52W high", "warning"),
                "ema_cross" : ("📡 FRESH EMA CROSS — Day 0, 52W high locked", "info"),
                "watching"  : ("👁 WATCHING — Above EMA 220, awaiting 52W break", "info"),
                "none"      : ("— No active signal", None),
            }
            label, kind = state_map.get(state, ("—", None))
            if kind == "success": st.success(label)
            elif kind == "warning": st.warning(label)
            elif kind == "info": st.info(label)

            fig = build_chart(df, symbol, show_days)
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("#### Key Levels")
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
                st.dataframe(levels, hide_index=True, use_container_width=True)
            with col2:
                targets = pd.DataFrame({
                    "Target"   : ["+20%","+40% (sell 50%)","+100% (sell 25%)","+200%"],
                    "Price ($)": [f"${cmp*1.20:,.2f}", f"${cmp*1.40:,.2f}",
                                  f"${cmp*2.00:,.2f}", f"${cmp*3.00:,.2f}"],
                })
                st.dataframe(targets, hide_index=True, use_container_width=True)

            with st.expander("Recent OHLCV Data"):
                disp = df[["Open","High","Low","Close","Volume","EMA220","RSI"]].tail(20).round(2).copy()
                disp.index = disp.index.strftime("%d %b %Y")
                st.dataframe(disp, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — SIGNAL SCANNER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔍 Signal Scanner":
    st.markdown("## Signal Scanner — Nasdaq 100")

    now_et, is_weekend, is_mkt_hours, is_post_close = get_market_status()
    market_open  = datetime.time(9, 30)
    market_close = datetime.time(16, 0)

    if is_weekend:
        st.warning(
            f"⚠️ **Today is {'Saturday' if now_et.weekday()==5 else 'Sunday'} — US markets closed.**\n\n"
            "Signal results on weekends are unreliable. "
            "**Run the scanner on Monday–Friday after 4:00 PM ET for accurate results.**"
        )
    elif is_mkt_hours:
        st.warning(
            f"⚠️ **Market is currently open (ET {now_et.strftime('%H:%M')}).**\n\n"
            "Scan after 4:00 PM ET when closing prices are final."
        )
    elif is_post_close:
        st.success(
            f"✅ **Market closed. ET {now_et.strftime('%H:%M')}** — "
            "Best time to scan. Results based on today's final closing prices."
        )

    filt = st.pills("Filter", ["All","✅ Confirmed","🔥 Breakout",
                                "⚡ Near 52W High","📡 EMA Cross","👁 Watching"],
                    default="All")

    # Scan lock — same logic as NSE dashboard
    last_scan_time = st.session_state.get("nasdaq_scan_time", "")
    scan_locked    = False
    if last_scan_time and not is_weekend and is_post_close:
        try:
            scan_dt = datetime.datetime.strptime(last_scan_time, "%d %b %Y %H:%M ET")
            if scan_dt.date() == now_et.date():
                scan_locked = True
        except: pass

    if scan_locked:
        st.info("🔒 Scan results locked for today. Re-run tomorrow after market close.")

    scan_label = "🔍 Run Full Scan"
    if is_weekend: scan_label = "🔍 Run Full Scan (weekend — use with caution)"
    if scan_locked: scan_label = "🔒 Re-scan (today's results already locked)"

    if st.button(scan_label, type="primary", use_container_width=True):
        # Load QQQ benchmark for RS calculation
        bench_df_raw = fetch_data("QQQ", "2y")

        results = []
        pb    = st.progress(0, text="Scanning Nasdaq 100...")
        total = len(NASDAQ100)
        for i, ticker in enumerate(NASDAQ100):
            pb.progress((i+1)/total, text=f"Scanning {ticker}... ({i+1}/{total})")
            df_raw = fetch_data(ticker, "2y")
            if df_raw is None or len(df_raw) < 225: continue
            df = add_indicators(df_raw)
            state, info = get_signal_state(df)
            if state == "none" or info.get("vol20",0) < 500000 or info.get("close",0) < 5:
                continue
            # Calculate RS score vs QQQ
            rs = compute_rs_score(df_raw, bench_df_raw) if bench_df_raw is not None else None
            results.append({"Symbol": ticker, "Signal": state, "RS Score": rs, **info})

        # Sort by signal priority then RS score descending
        results.sort(key=lambda x: (
            {"confirmed":0,"breakout":1,"near_52w":2,"ema_cross":3,"watching":4}.get(x["Signal"],5),
            -(x["RS Score"] or 0)
        ))
        pb.empty()
        st.session_state["nasdaq_scan_results"] = results
        st.session_state["nasdaq_scan_time"]    = now_et.strftime("%d %b %Y %H:%M ET")
        st.session_state["nasdaq_scan_status"]  = "weekend" if is_weekend else "market_hours" if is_mkt_hours else "post_close"

    if "nasdaq_scan_results" in st.session_state:
        results  = st.session_state["nasdaq_scan_results"]
        scan_tag = st.session_state.get("nasdaq_scan_status","")
        tag_icon = {"post_close":"✅ After market close","weekend":"⚠️ Weekend",
                    "market_hours":"⚡ During market hours"}.get(scan_tag,"")
        st.caption(f"Last scan: {st.session_state.get('nasdaq_scan_time','')} · "
                   f"{tag_icon} · {len(NASDAQ100)} stocks · {len(results)} signals")

        state_map = {"All":None,"✅ Confirmed":"confirmed","🔥 Breakout":"breakout",
                     "⚡ Near 52W High":"near_52w","📡 EMA Cross":"ema_cross","👁 Watching":"watching"}
        sel      = state_map.get(filt)
        filtered = [r for r in results if sel is None or r["Signal"]==sel]

        if not filtered:
            st.warning("No signals for this filter.")
        else:
            c1,c2,c3,c4,c5 = st.columns(5)
            for col, sig, emoji, label in [
                (c1,"confirmed","✅","Confirmed"),
                (c2,"breakout","🔥","Breakout"),
                (c3,"near_52w","⚡","Near 52W"),
                (c4,"ema_cross","📡","EMA Cross"),
                (c5,"watching","👁","Watching"),
            ]:
                col.metric(f"{emoji} {label}", sum(1 for r in results if r["Signal"]==sig))

            st.markdown("---")
            label_map = {"confirmed":"✅ Confirmed","breakout":"🔥 Breakout",
                         "near_52w":"⚡ Near 52W","ema_cross":"📡 EMA Cross","watching":"👁 Watching"}
            rows = []
            for r in filtered:
                rs = r.get("RS Score")
                rows.append({
                    "Symbol"           : r["Symbol"],
                    "Signal"           : label_map.get(r["Signal"],r["Signal"]),
                    "RS Score"         : f"{rs:+.2f}" if rs is not None else "—",
                    "Price $"          : r["close"],
                    "EMA 220 $"        : r["ema220"],
                    "% above EMA"      : f"{r['pct_above_ema']:+.2f}%",
                    "52W High $ (locked)": r["w52_high"],
                    "% from 52W"       : f"{r['pct_from_52w']:+.2f}%",
                    "SL $"             : r["sl_level"],
                    "RSI"              : r["rsi"],
                    "Change %"         : f"{r['change_pct']:+.2f}%",
                    "EMA Cross Date"   : r.get("cross_date","—"),
                    "Days since cross" : r.get("days_since_cross","—"),
                })
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True, height=500)

            st.markdown("#### View chart for a signal stock")
            pick = st.selectbox("Select symbol", [r["Symbol"] for r in filtered])
            if pick:
                df_raw = fetch_data(pick, "2y")
                if df_raw is not None:
                    fig = build_chart(add_indicators(df_raw), pick, 180)
                    st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — MY POSITIONS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💼 My Positions":
    st.markdown("## My Nasdaq Positions")

    if "nasdaq_positions" not in st.session_state:
        st.session_state["nasdaq_positions"] = []

    with st.expander("➕ Add / Update Position", expanded=len(st.session_state["nasdaq_positions"])==0):
        c1,c2,c3,c4,c5 = st.columns([2,2,1,2,1])
        with c1: sym = st.text_input("Symbol", key="n_sym", placeholder="NVDA").upper().strip()
        with c2: ep  = st.number_input("Entry Price $", min_value=0.0, step=0.1, key="n_ep")
        with c3: sh  = st.number_input("Shares", min_value=1, step=1, key="n_sh")
        with c4: dt  = st.date_input("Entry Date", key="n_dt")
        with c5:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Add", type="primary", use_container_width=True, key="n_add"):
                if sym and ep > 0 and sh > 0:
                    existing = [p for p in st.session_state["nasdaq_positions"] if p["symbol"]!=sym]
                    existing.append({"symbol":sym,"entry_price":float(ep),
                                     "shares":int(sh),"entry_date":str(dt),
                                     "trailing_sl":round(ep*0.85,2)})
                    st.session_state["nasdaq_positions"] = existing
                    st.success(f"Added {sym}")
                    st.rerun()
                else:
                    st.error("Fill all fields.")

    positions = st.session_state["nasdaq_positions"]
    if not positions:
        st.info("No positions yet. Add your first trade above.")
    else:
        live = []
        with st.spinner("Fetching live prices..."):
            for pos in positions:
                df_raw = fetch_data(pos["symbol"])
                if df_raw is None: continue
                df  = add_indicators(df_raw)
                row = df.iloc[-1]
                c   = float(row["Close"]); e = float(row["EMA220"])
                ep  = pos["entry_price"]; sh = pos["shares"]
                sl  = pos["trailing_sl"]; pct = (c-ep)/ep*100
                nsl = round(max(e, c*0.85), 2)
                entry_dt = datetime.datetime.strptime(pos["entry_date"], "%Y-%m-%d")
                days = (datetime.datetime.now() - entry_dt).days
                live.append({**pos,"cmp":c,"ema220":round(e,2),
                             "pnl_pct":round(pct,2),"pnl_usd":round((c-ep)*sh,2),
                             "new_sl":nsl,"sl_updated":nsl>sl,"near_sl":c<sl*1.05,
                             "hit_40":pct>=40,"hit_100":pct>=100,
                             "target_40":round(ep*1.4,2),"target_100":round(ep*2,2),
                             "hold_days":days})

        # Alerts
        for p in live:
            if p["near_sl"]:   st.error(f"⚠️ {p['symbol']} — ${p['cmp']:.2f} near SL ${p['trailing_sl']:.2f}")
            if p["hit_40"]:    st.success(f"✅ {p['symbol']} — Up +{p['pnl_pct']:.1f}% · Consider booking 50% at ${p['target_40']:.2f}")
            if p["hit_100"]:   st.success(f"✅ {p['symbol']} — Up +{p['pnl_pct']:.1f}% · Consider booking next 25%")
            if p["sl_updated"]:st.info(f"↑ {p['symbol']} — Raise SL to ${p['new_sl']:.2f}")

        # Portfolio summary
        total_inv = sum(p["entry_price"]*p["shares"] for p in live)
        total_cur = sum(p["cmp"]*p["shares"] for p in live)
        total_pnl = total_cur - total_inv
        total_pct = total_pnl/total_inv*100 if total_inv > 0 else 0

        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("Invested",       f"${total_inv:,.0f}")
        c2.metric("Current Value",  f"${total_cur:,.0f}")
        c3.metric("Total P&L",      f"${total_pnl:+,.0f}", f"{total_pct:+.2f}%")
        c4.metric("Open Positions", f"{len(live)} / 8")
        c5.metric("Best Performer", max(live, key=lambda x:x["pnl_pct"])["symbol"] if live else "—",
                  f"{max(live, key=lambda x:x['pnl_pct'])['pnl_pct']:+.2f}%" if live else "")

        st.markdown("---")
        cols = st.columns(min(len(live), 3))
        for i, p in enumerate(live):
            with cols[i % 3]:
                bar = min(100, max(0,(p["cmp"]-p["trailing_sl"])/p["trailing_sl"]*500))
                bc  = "#f87171" if bar<20 else "#fbbf24" if bar<50 else "#34d399"
                cc  = "#f87171" if p["near_sl"] else "#34d399" if p["hit_40"] else "#1a3a2a"
                st.markdown(f"""
                <div style="background:#0f1a14;border:1px solid {cc};border-radius:10px;padding:14px;margin-bottom:10px">
                  <div style="display:flex;justify-content:space-between;margin-bottom:10px">
                    <div><div style="font-size:18px;font-weight:700">{p['symbol']}</div>
                    <div style="font-size:11px;color:#888">{p['entry_date']} · {p['hold_days']} days</div></div>
                    <div style="text-align:right">
                      <div style="font-size:20px;font-weight:700;color:{'#34d399' if p['pnl_pct']>=0 else '#f87171'}">{p['pnl_pct']:+.2f}%</div>
                      <div style="font-size:12px;color:{'#34d399' if p['pnl_usd']>=0 else '#f87171'}">${abs(p['pnl_usd']):,.0f}</div>
                    </div>
                  </div>
                  <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:13px">
                    <div><span style="color:#888;font-size:11px">CMP</span><br><b>${p['cmp']:,.2f}</b></div>
                    <div><span style="color:#888;font-size:11px">Entry</span><br><b>${p['entry_price']:,.2f}</b></div>
                    <div><span style="color:#888;font-size:11px">EMA 220</span><br><b>${p['ema220']:,.2f}</b></div>
                    <div><span style="color:#888;font-size:11px">Shares</span><br><b>{p['shares']}</b></div>
                    <div><span style="color:#888;font-size:11px">Trailing SL</span><br><b style="color:#f87171">${p['trailing_sl']:,.2f}</b></div>
                    <div><span style="color:#888;font-size:11px">Updated SL</span><br><b style="color:{'#34d399' if p['sl_updated'] else '#e0e0f0'}">${p['new_sl']:,.2f} {'↑' if p['sl_updated'] else ''}</b></div>
                    <div><span style="color:#888;font-size:11px">+40% Target</span><br><b style="color:{'#34d399' if p['hit_40'] else '#e0e0f0'}">${p['target_40']:,.2f} {'✓' if p['hit_40'] else ''}</b></div>
                    <div><span style="color:#888;font-size:11px">+100% Target</span><br><b style="color:{'#34d399' if p['hit_100'] else '#e0e0f0'}">${p['target_100']:,.2f} {'✓' if p['hit_100'] else ''}</b></div>
                  </div>
                  <div style="background:#0a0f0d;border-radius:3px;height:4px;margin-top:10px;overflow:hidden">
                    <div style="width:{bar}%;height:100%;background:{bc};border-radius:3px"></div>
                  </div>
                </div>""", unsafe_allow_html=True)
                bc1,bc2 = st.columns(2)
                with bc1:
                    if st.button("Update SL", key=f"nsl_{p['symbol']}"):
                        for pos in st.session_state["nasdaq_positions"]:
                            if pos["symbol"]==p["symbol"]: pos["trailing_sl"]=p["new_sl"]
                        st.success(f"SL updated to ${p['new_sl']:.2f}")
                        st.rerun()
                with bc2:
                    if st.button("Exit", key=f"nex_{p['symbol']}", type="secondary"):
                        st.session_state["nasdaq_positions"] = [
                            pos for pos in st.session_state["nasdaq_positions"]
                            if pos["symbol"]!=p["symbol"]]
                        st.rerun()

        st.markdown("---")
        pick = st.selectbox("View chart", [p["symbol"] for p in live])
        if pick:
            df_raw = fetch_data(pick,"2y")
            if df_raw is not None:
                df  = add_indicators(df_raw)
                pos = next(p for p in live if p["symbol"]==pick)
                fig = build_chart(df, pick, 180)
                fig.add_hline(y=pos["entry_price"], line_dash="dash",
                              line_color="#fbbf24", annotation_text="Entry",
                              annotation_font_color="#fbbf24", row=1, col=1)
                fig.add_hline(y=pos["trailing_sl"], line_dash="dash",
                              line_color="#f87171", annotation_text="SL",
                              annotation_font_color="#f87171", row=1, col=1)
                st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — QQQ BENCHMARK
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📈 QQQ Benchmark":
    st.markdown("## Market Benchmark")

    with st.spinner("Loading benchmark data..."):
        df_qqq  = fetch_data("QQQ",  "5y")   # Nasdaq 100 ETF
        df_spy  = fetch_data("SPY",  "5y")   # S&P 500 ETF
        df_iwm  = fetch_data("IWM",  "5y")   # Russell 2000

    idx_tab = st.radio("Select", ["QQQ (Nasdaq 100)", "SPY (S&P 500)", "Compare All"],
                       horizontal=True)

    def index_section(df_raw, label, currency="$"):
        if df_raw is None:
            st.error(f"Could not load {label} data.")
            return
        df   = add_indicators(df_raw)
        row  = df.iloc[-1]; prev = df.iloc[-2]
        cmp  = float(row["Close"])
        chg  = (cmp - float(prev["Close"])) / float(prev["Close"]) * 100
        def ret(n):
            return round((cmp / float(df["Close"].iloc[-n]) - 1)*100, 2) if len(df)>=n else None
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric(label,      f"{currency}{cmp:,.2f}", f"{chg:+.2f}%")
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
            rows.append({"Period":name,"Return":f"{r:+.2f}%" if r else "—",
                         "Direction":"📈" if r and r>0 else "📉" if r else "—"})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    if idx_tab == "QQQ (Nasdaq 100)":
        index_section(df_qqq, "QQQ — Nasdaq 100 ETF")
    elif idx_tab == "SPY (S&P 500)":
        index_section(df_spy, "SPY — S&P 500 ETF")
    else:
        st.markdown("### QQQ vs SPY vs IWM — Normalised (base = 100, last 1 year)")
        dfs = [("QQQ","#22d3ee",df_qqq), ("SPY","#34d399",df_spy), ("IWM","#fbbf24",df_iwm)]
        fig = go.Figure()
        for name, color, df_raw in dfs:
            if df_raw is None: continue
            d = df_raw["Close"].tail(252)
            n = d / float(d.iloc[0]) * 100
            fig.add_trace(go.Scatter(x=n.index, y=n.values, name=name,
                          line=dict(color=color, width=2)))
        fig.add_hline(y=100, line_dash="dot", line_color="#888", opacity=0.4)
        fig.update_layout(
            paper_bgcolor="#0a0f0d", plot_bgcolor="#0a0f0d",
            font=dict(color="#888"), height=400,
            legend=dict(bgcolor="#0f1a14", bordercolor="#1a3a2a"),
            margin=dict(l=10,r=10,t=20,b=10),
            yaxis=dict(gridcolor="#0f1a14", title="Indexed to 100"),
            xaxis=dict(gridcolor="#0f1a14"),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Returns comparison table
        rows = []
        for label, _, df_raw in dfs:
            if df_raw is None: continue
            c   = float(df_raw["Close"].iloc[-1])
            def r(n): return round((c/float(df_raw["Close"].iloc[-n])-1)*100,2) if len(df_raw)>=n else None
            rows.append({"Index":label,"1M":f"{r(21):+.2f}%" if r(21) else "—",
                         "3M":f"{r(63):+.2f}%" if r(63) else "—",
                         "6M":f"{r(126):+.2f}%" if r(126) else "—",
                         "1Y":f"{r(252):+.2f}%" if r(252) else "—",
                         "2Y":f"{r(504):+.2f}%" if r(504) else "—"})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — POSITION SIZER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🧮 Position Sizer":
    st.markdown("## 🧮 Position Size Calculator")
    st.markdown("1.5% risk rule — same as NSE strategy, applied to USD capital.")

    c1, c2 = st.columns(2)
    with c1:
        capital = st.number_input("Current Capital ($)", min_value=1000,
                                  max_value=10000000, value=10000, step=500)
    with c2:
        sym_input = st.text_input("Symbol (auto-fetches price & EMA 220)",
                                   placeholder="e.g. NVDA", value="").upper().strip()

    manual = st.toggle("Enter price manually", value=False)

    if manual or not sym_input:
        c1,c2 = st.columns(2)
        with c1: entry_price = st.number_input("Entry Price $", min_value=0.1, step=0.1, value=100.0)
        with c2: ema220_val  = st.number_input("EMA 220 $",     min_value=0.1, step=0.1, value=85.0)
    else:
        with st.spinner(f"Fetching {sym_input}..."):
            df_raw = fetch_data(sym_input)
        if df_raw is None:
            st.error(f"Could not fetch {sym_input}.")
            st.stop()
        df_ind    = add_indicators(df_raw)
        row_live  = df_ind.iloc[-1]; prev_live = df_ind.iloc[-2]
        cmp_live  = float(row_live["Close"])
        ema220_val= float(row_live["EMA220"])
        chg_live  = (cmp_live - float(prev_live["Close"])) / float(prev_live["Close"]) * 100
        st.success(f"✅ Live data for **{sym_input}**")
        q1,q2,q3,q4 = st.columns(4)
        q1.metric("Price",   f"${cmp_live:,.2f}", f"{chg_live:+.2f}%")
        q2.metric("EMA 220", f"${ema220_val:,.2f}")
        q3.metric("Open",    f"${float(row_live['Open']):,.2f}")
        q4.metric("RSI",     f"{float(row_live['RSI']):.1f}" if not pd.isna(row_live["RSI"]) else "—")
        entry_price = st.number_input("Expected Entry Price $",
                                       min_value=0.1, step=0.1,
                                       value=round(cmp_live, 2))

    st.markdown("---")
    sl_15      = entry_price * 0.85
    initial_sl = round(max(ema220_val, sl_15), 2)
    risk_amt   = capital * 0.015
    risk_per_sh= entry_price - initial_sl

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

    check_min = deploy >= 500   # $500 minimum for US stocks (vs ₹20k for NSE)
    deploy_pct= deploy / capital * 100

    st.markdown("### Result")
    if shares > 0 and check_min:
        st.success(f"✅ **BUY {shares} shares of {sym_input or 'stock'} at ${entry_price:,.2f} — Deploy ${deploy:,.0f}**")
    else:
        st.error(f"❌ Deploy ${deploy:,.0f} too small — skip this trade")
    if capped:
        st.warning(f"⚠️ Capped at 20% of capital. Original: {math.floor(risk_amt/risk_per_sh)} shares → capped to {shares}.")

    r1,r2,r3 = st.columns(3)
    with r1:
        st.markdown("**Stop Loss**")
        st.dataframe(pd.DataFrame({
            "Rule"  :["15% below entry","EMA 220","Initial SL (higher)"],
            "Value $":[f"${sl_15:,.2f}",f"${ema220_val:,.2f}",f"${initial_sl:,.2f}"],
            "Used?" :["✓" if sl_15>=ema220_val else "—","✓" if ema220_val>sl_15 else "—","✅"]
        }), hide_index=True, use_container_width=True)
    with r2:
        st.markdown("**Shares**")
        st.dataframe(pd.DataFrame({
            "Item" :["Capital","Risk 1.5%","Risk Amount","Risk/Share","Shares"],
            "Value":[f"${capital:,.0f}","1.5%",f"${risk_amt:,.0f}",
                     f"${risk_per_sh:,.2f}",f"{shares}"]
        }), hide_index=True, use_container_width=True)
    with r3:
        st.markdown("**Checks**")
        st.dataframe(pd.DataFrame({
            "Rule"    :["Min $500","Max 20% capital","Shares > 0"],
            "Required":[f"$500",f"${max_deploy:,.0f}","> 0"],
            "Actual"  :[f"${deploy:,.0f}",f"${deploy:,.0f}",str(shares)],
            "Status"  :["✅" if check_min else "❌","✅" if deploy<=max_deploy else "❌",
                        "✅" if shares>0 else "❌"]
        }), hide_index=True, use_container_width=True)

    st.markdown("---")
    st.markdown("#### Trade Summary")
    m1,m2,m3,m4,m5,m6 = st.columns(6)
    m1.metric("Shares",       f"{shares}")
    m2.metric("Deploy",       f"${deploy:,.0f}")
    m3.metric("% of Capital", f"{deploy_pct:.1f}%")
    m4.metric("Initial SL",   f"${initial_sl:,.2f}")
    m5.metric("Max Loss $",   f"${shares*risk_per_sh:,.0f}")
    m6.metric("Max Loss %",   "1.5%")

    st.markdown("#### Profit Targets")
    t1,t2,t3,t4 = st.columns(4)
    t1.metric("+20%",             f"${entry_price*1.20:,.2f}")
    t2.metric("+40% — sell 50%",  f"${entry_price*1.40:,.2f}",
              f"Receive ${math.floor(shares*0.5)*entry_price*1.40:,.0f}")
    t3.metric("+100% — sell 25%", f"${entry_price*2.00:,.2f}",
              f"Receive ${math.floor(shares*0.25)*entry_price*2.00:,.0f}")
    t4.metric("Hold last 25%",    f"{math.ceil(shares*0.25)} shares", "Until trailing SL")

    st.markdown("#### Trailing SL Schedule")
    trail_rows = []
    for mult in [1.05,1.10,1.20,1.30,1.40,1.60,1.80,2.00]:
        price    = entry_price * mult
        trail_sl = round(price * 0.85, 2)
        locked   = round((trail_sl - entry_price)/entry_price*100, 2)
        trail_rows.append({
            "If Price"       : f"${price:,.2f} ({(mult-1)*100:+.0f}%)",
            "Trailing SL"    : f"${trail_sl:,.2f}",
            "Locked-in Gain" : f"{locked:+.2f}%",
            "Status"         : "🔒 Profit locked!" if locked>0 else "📉 At risk"
        })
    st.dataframe(pd.DataFrame(trail_rows), hide_index=True, use_container_width=True)

    st.markdown("---")
    st.markdown("### Batch Calculator")
    batch = st.text_input("Symbols (comma separated)", placeholder="AAPL, NVDA, MSFT")
    if batch and st.button("Calculate All", type="primary"):
        syms = [s.strip().upper() for s in batch.split(",") if s.strip()][:8]
        rows = []; total_dep = 0
        with st.spinner("Fetching..."):
            for s in syms:
                df_b = fetch_data(s)
                if df_b is None:
                    rows.append({"Symbol":s,"Price":"—","EMA220":"—","SL":"—",
                                 "Shares":"—","Deploy":"—","% Cap":"—","Status":"❌"})
                    continue
                df_b   = add_indicators(df_b)
                rb     = df_b.iloc[-1]
                cb     = float(rb["Close"]); eb = float(rb["EMA220"])
                sl_b   = round(max(eb, cb*0.85), 2)
                rps_b  = cb - sl_b
                if rps_b <= 0:
                    rows.append({"Symbol":s,"Price":f"${cb:,.2f}","EMA220":f"${eb:,.2f}",
                                 "SL":f"${sl_b:,.2f}","Shares":"—","Deploy":"—","% Cap":"—",
                                 "Status":"❌ Below SL"}); continue
                sh_b   = math.floor((capital*0.015)/rps_b)
                dep_b  = sh_b * cb
                if dep_b > capital*0.20:
                    sh_b = math.floor(capital*0.20/cb); dep_b = sh_b*cb
                total_dep += dep_b
                rows.append({"Symbol":s,"Price $":f"${cb:,.2f}","EMA 220 $":f"${eb:,.2f}",
                             "SL $":f"${sl_b:,.2f}","Shares":sh_b,
                             "Deploy $":f"${dep_b:,.0f}","% Capital":f"{dep_b/capital*100:.1f}%",
                             "Status":"✅" if dep_b>=500 else "⚠️ Small"})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        b1,b2,b3 = st.columns(3)
        b1.metric("Total Deployed", f"${total_dep:,.0f}")
        b2.metric("% of Capital",   f"{total_dep/capital*100:.1f}%")
        b3.metric("Remaining Cash", f"${capital-total_dep:,.0f}")
