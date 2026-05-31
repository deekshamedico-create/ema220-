"""
220 EMA Breakout Strategy — Nasdaq 100 Live Dashboard
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
    .stApp { background-color: #0d0d14; color: #ffffff; }
    .stApp p, .stApp span, .stApp div, .stApp label { color: #ffffff; }
    div[data-testid="metric-container"] {
        background: #1e1e30; border: 1px solid #4a4a70;
        border-radius: 10px; padding: 12px;
    }
    div[data-testid="metric-container"] label { color: #ffffff !important; font-size: 13px !important; font-weight: 600 !important; }
    div[data-testid="metric-container"] [data-testid="metric-value"] { color: #ffffff !important; font-weight: 700 !important; font-size: 24px !important; }
    section[data-testid="stSidebar"] { background-color: #0f0f1e !important; }
    section[data-testid="stSidebar"] label { color: #ffffff !important; font-size: 14px !important; font-weight: 600 !important; }
    section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span { color: #ffffff !important; }
    div[data-testid="stInfo"]    { background: #0d1f33 !important; border-left: 4px solid #4488ff !important; color: #ffffff !important; }
    div[data-testid="stSuccess"] { background: #0a2018 !important; border-left: 4px solid #34d399 !important; color: #ffffff !important; }
    div[data-testid="stWarning"] { background: #281800 !important; border-left: 4px solid #fbbf24 !important; color: #ffffff !important; }
    div[data-testid="stError"]   { background: #280808 !important; border-left: 4px solid #f87171 !important; color: #ffffff !important; }
    div[data-testid="stInfo"] p, div[data-testid="stSuccess"] p, div[data-testid="stWarning"] p, div[data-testid="stError"] p { color: #ffffff !important; }
    .stButton button { background: #2a2a45 !important; color: #ffffff !important; border: 1px solid #6060c0 !important; font-weight: 700 !important; }
    .stButton button:hover { background: #3a3a60 !important; }
    .stTextInput input, .stNumberInput input { background: #1a1a2a !important; color: #ffffff !important; border: 1px solid #4a4a70 !important; }
    .stTextInput label, .stNumberInput label, .stDateInput label, .stSelectbox label, .stRadio label { color: #ffffff !important; font-weight: 700 !important; }
    .stDataFrame th { background: #1e1e30 !important; color: #ffffff !important; font-weight: 700 !important; }
    .stDataFrame td { color: #ffffff !important; }
    .streamlit-expanderHeader { color: #ffffff !important; font-weight: 700 !important; background: #1a1a2a !important; }
    .stTabs [data-baseweb="tab"] { color: #ccccee !important; font-weight: 700 !important; font-size: 14px !important; }
    .stTabs [aria-selected="true"] { color: #ffffff !important; border-bottom-color: #7c6af7 !important; }
    h1, h2, h3, h4, h5, h6 { color: #ffffff !important; }
    .stMarkdown p { color: #ffffff !important; }
</style>
""", unsafe_allow_html=True)

# ── Google Sheet Config ───────────────────────────────────────────────────────
SHEET_ID            = "1tT9NLUcpVqsVN7dFJ2O2v4I4lDwxZcHPAUStQff16OY"
NASDAQ_SHEET_ID     = "1_I2JEHn272zsVr_sWNmy_W0AmXROEFvtMppaCFS04rI"
NASDAQ_POS_URL      = f"https://docs.google.com/spreadsheets/d/{NASDAQ_SHEET_ID}/gviz/tq?tqx=out:csv&gid=0"
NASDAQ_CLOSED_URL   = f"https://docs.google.com/spreadsheets/d/{NASDAQ_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Sheet2"
SHEET_EDIT_URL      = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"
NASDAQ_SHEET_EDIT   = f"https://docs.google.com/spreadsheets/d/{NASDAQ_SHEET_ID}/edit"

# ── Constants ─────────────────────────────────────────────────────────────────
EMA_PERIOD = 220
os.makedirs("data_cache_nasdaq", exist_ok=True)

NASDAQ100 = list(dict.fromkeys([
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
    "CSGP","GFS","HON","KHC","LCID","LOGI","MAR","NDAQ","PCAR","PODD",
    "POOL","RIVN","SIRI","SWKS","TECH","TMUS","TXN","VRSN","WBA","ZBRA","ZM",
]))

# ── Market hours ──────────────────────────────────────────────────────────────
def get_market_status():
    now_et = datetime.datetime.utcnow() - datetime.timedelta(hours=4)
    is_weekend   = now_et.weekday() >= 5
    is_mkt_hours = datetime.time(9,30) <= now_et.time() <= datetime.time(16,0)
    is_post_close= now_et.time() > datetime.time(16,0)
    return now_et, is_weekend, is_mkt_hours, is_post_close

# ── Data fetch ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=86400)
def fetch_data(symbol, period="2y"):
    cache = f"data_cache_nasdaq/{symbol.replace('.','_').replace('^','_')}.csv"
    now_et, is_weekend, _, _ = get_market_status()
    today = now_et.date()
    market_close_utc = datetime.datetime.combine(today, datetime.time(20,0))
    if os.path.exists(cache):
        mtime    = datetime.datetime.utcfromtimestamp(os.path.getmtime(cache))
        cache_age= (datetime.datetime.utcnow() - mtime).total_seconds()
        if (mtime.date()==today and datetime.datetime.utcnow()>market_close_utc) or \
           (is_weekend and cache_age<172800):
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
    df["RSI"] = 100 - (100/(1 + g/l.replace(0, np.nan)))
    return df

def compute_rs_score(stock_df, bench_df):
    try:
        common = stock_df.index.intersection(bench_df.index)
        if len(common) < 126: return None
        s = stock_df["Close"].reindex(common)
        b = bench_df["Close"].reindex(common)
        s_now=float(s.iloc[-1]); b_now=float(b.iloc[-1])
        s63=(s_now/float(s.iloc[-63])-1); b63=(b_now/float(b.iloc[-63])-1)
        rs63 = s63/abs(b63) if b63!=0 else 0
        s126=(s_now/float(s.iloc[-126])-1); b126=(b_now/float(b.iloc[-126])-1)
        rs126 = s126/abs(b126) if b126!=0 else 0
        return round((rs63+rs126)/2, 2)
    except: return None

# ── Google Sheet functions ────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def read_nasdaq_positions():
    try:
        df = pd.read_csv(NASDAQ_POS_URL)
        df.columns = [c.strip().lower().replace(" ","_") for c in df.columns]
        positions = []
        for _, row in df.iterrows():
            sym = str(row.get("symbol","")).strip().upper()
            if not sym or sym in ("NAN","SYMBOL",""): continue
            # Handle both "entry_price" and "buy_price" column names
            ep_raw = row.get("entry_price", row.get("buy_price", row.get("buy price", 0)))
            sh_raw = row.get("shares", row.get("qty", row.get("quantity", 0)))
            sl_raw = row.get("trailing_sl", row.get("stoploss", row.get("sl", 0)))
            ep = float(str(ep_raw).replace(",","")) if ep_raw else 0
            sh = float(str(sh_raw).replace(",","")) if sh_raw else 0
            sl = float(str(sl_raw).replace(",","")) if sl_raw else 0
            if ep == 0 or sh == 0: continue
            positions.append({
                "symbol"      : sym,
                "entry_price" : ep,
                "shares"      : sh,   # keep as float to support fractional shares
                "entry_date"  : str(row.get("entry_date", row.get("date","2026-01-01"))).strip(),
                "trailing_sl" : sl,
            })
        return positions
    except Exception as e:
        st.warning(f"Could not read positions: {e}")
        return []

@st.cache_data(ttl=60)
def read_nasdaq_closed():
    NASDAQ_CLOSED_ID = "1_I2JEHn272zsVr_sWNmy_W0AmXROEFvtMppaCFS04rI"
    urls_to_try = [
        f"https://docs.google.com/spreadsheets/d/{NASDAQ_CLOSED_ID}/gviz/tq?tqx=out:csv&sheet=CLOSED",
        f"https://docs.google.com/spreadsheets/d/{NASDAQ_CLOSED_ID}/gviz/tq?tqx=out:csv&sheet=Closed",
        f"https://docs.google.com/spreadsheets/d/{NASDAQ_CLOSED_ID}/gviz/tq?tqx=out:csv&sheet=Sheet2",
        f"https://docs.google.com/spreadsheets/d/{NASDAQ_CLOSED_ID}/gviz/tq?tqx=out:csv&gid=1",
        f"https://docs.google.com/spreadsheets/d/{NASDAQ_CLOSED_ID}/pub?output=csv&sheet=Closed",
        f"https://docs.google.com/spreadsheets/d/{NASDAQ_CLOSED_ID}/pub?output=csv&sheet=CLOSED",
        f"https://docs.google.com/spreadsheets/d/{NASDAQ_CLOSED_ID}/pub?output=csv&gid=1",
    ]
    for url in urls_to_try:
        try:
            df = pd.read_csv(url)
            if df is None or df.empty: continue
            df.columns = [c.strip().lower().replace(" ","_") for c in df.columns]
            exit_col = next((c for c in df.columns if "exit" in c and "price" in c), None)
            if exit_col is None: continue
            trades = []
            for _, row in df.iterrows():
                sym = str(row.get("symbol","")).strip().upper()
                if not sym or sym in ("NAN","SYMBOL",""): continue
                ep_raw = row.get("entry_price", row.get("buy_price", row.get("buy_price",0)))
                xp_raw = row.get(exit_col, 0)
                sh_raw = row.get("shares", row.get("qty", 0))
                try:
                    ep = float(str(ep_raw).replace(",","").replace("$",""))
                    xp = float(str(xp_raw).replace(",","").replace("$",""))
                    sh = float(str(sh_raw).replace(",",""))
                except: continue
                if xp==0 or ep==0 or sh==0: continue
                pnl = round((xp-ep)*sh*0.995, 2)
                pct = round((xp-ep)/ep*100, 2) if ep>0 else 0
                xdt_raw = row.get("exit_date", row.get("date",""))
                try: xdt = pd.to_datetime(str(xdt_raw), dayfirst=True).strftime("%d/%m/%Y")
                except: xdt = str(xdt_raw)
                trades.append({"symbol":sym,"entry_price":ep,"exit_price":xp,"shares":sh,
                    "exit_date":xdt,"pnl_usd":pnl,"pnl_pct":pct,
                    "reason":str(row.get("reason", row.get("exit_reason","Manual Exit")))})
            if trades: return trades
        except: continue
    return []


def get_signal_state(df):
    if df is None or len(df) < EMA_PERIOD+5: return "none", {}
    row=df.iloc[-1]; prev=df.iloc[-2]
    c=float(row["Close"]); e=float(row["EMA220"])
    vol20=float(row["Vol20"]) if not pd.isna(row["Vol20"]) else 0
    rsi=float(row["RSI"]) if not pd.isna(row["RSI"]) else 50
    chg=(c-float(prev["Close"]))/float(prev["Close"])*100

    cross_idx=None; w52_fixed=None; cross_date=None
    for i in range(1, min(62, len(df)-2)):
        c1=float(df["Close"].iloc[-i]);  e1=float(df["EMA220"].iloc[-i])
        c0=float(df["Close"].iloc[-i-1]);e0=float(df["EMA220"].iloc[-i-1])
        if c1<=e1: break
        if c1>e1 and c0<=e0:
            cross_idx=i; cross_date=df.index[-i]
            cutoff=cross_date-pd.Timedelta(days=365)
            hist=df["Close"][(df.index>=cutoff)&(df.index<cross_date)]
            w52_fixed=float(hist.max()) if not hist.empty else float(df["Close"].iloc[:-i].max())
            break

    if cross_idx is None:
        return "none", {"close":round(c,2),"ema220":round(e,2),
            "w52_high":round(float(df["Close"].iloc[-252:].max()),2) if len(df)>=252 else 0,
            "pct_from_52w":0,"pct_above_ema":round((c-e)/e*100,2),
            "sl_level":round(max(e,c*0.85),2),"vol20":round(vol20),
            "rsi":round(rsi,1),"change_pct":round(chg,2),"above_ema":c>e}

    post_cross=df.iloc[-cross_idx:]
    stayed_above=all(float(post_cross["Close"].iloc[j])>float(post_cross["EMA220"].iloc[j])
                     for j in range(len(post_cross)))
    p52=(c-w52_fixed)/w52_fixed*100

    if not stayed_above:
        return "none", {"close":round(c,2),"ema220":round(e,2),"w52_high":round(w52_fixed,2),
            "pct_from_52w":round(p52,2),"pct_above_ema":round((c-e)/e*100,2),
            "sl_level":round(max(e,c*0.85),2),"vol20":round(vol20),
            "rsi":round(rsi,1),"change_pct":round(chg,2),"above_ema":c>e,
            "reset_reason":"Broke below EMA 220 after cross"}

    days_since_cross=cross_idx-1
    state="none"
    if days_since_cross<=1:
        state="ema_cross"
    elif c>w52_fixed:
        break_idx=None
        for j in range(len(post_cross)):
            if float(post_cross["Close"].iloc[j])>w52_fixed:
                break_idx=j; break
        days_since_break=(len(post_cross)-1-break_idx) if break_idx is not None else 0
        post_break=post_cross.iloc[break_idx:] if break_idx is not None else post_cross
        break_ok=all(float(post_break["Close"].iloc[j])>float(post_break["EMA220"].iloc[j])
                     for j in range(len(post_break)))
        state="confirmed" if days_since_break>=10 and break_ok else "breakout"
    elif p52>-3:
        state="near_52w"
    else:
        state="watching"

    break_idx2=None
    for j in range(len(post_cross)):
        if float(post_cross["Close"].iloc[j])>w52_fixed:
            break_idx2=j; break
    days_since_break2=(len(post_cross)-1-break_idx2) if break_idx2 is not None and c>w52_fixed else 0

    return state, {"close":round(c,2),"ema220":round(e,2),"w52_high":round(w52_fixed,2),
        "pct_from_52w":round(p52,2),"pct_above_ema":round((c-e)/e*100,2),
        "sl_level":round(max(e,c*0.85),2),"vol20":round(vol20),"rsi":round(rsi,1),
        "change_pct":round(chg,2),"above_ema":c>e,"days_since_cross":days_since_cross,
        "days_since_break":days_since_break2,"cross_date":str(cross_date.date()) if cross_date else "—"}

def build_chart(df, symbol, show_days=180):
    df=df.tail(show_days).copy()
    fig=make_subplots(rows=3,cols=1,shared_xaxes=True,row_heights=[0.6,0.2,0.2],vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=df.index,open=df["Open"],high=df["High"],
        low=df["Low"],close=df["Close"],name="Price",
        increasing_fillcolor="#34d399",increasing_line_color="#34d399",
        decreasing_fillcolor="#f87171",decreasing_line_color="#f87171"),row=1,col=1)
    fig.add_trace(go.Scatter(x=df.index,y=df["EMA220"],name="EMA 220",line=dict(color="#22d3ee",width=2)),row=1,col=1)
    fig.add_trace(go.Scatter(x=df.index,y=df["EMA50"],name="EMA 50",line=dict(color="#fbbf24",width=1.2,dash="dash")),row=1,col=1)
    fig.add_trace(go.Scatter(x=df.index,y=df["EMA20"],name="EMA 20",line=dict(color="#a89cff",width=1,dash="dot")),row=1,col=1)
    colors=["#34d399" if c>=o else "#f87171" for c,o in zip(df["Close"],df["Open"])]
    fig.add_trace(go.Bar(x=df.index,y=df["Volume"],name="Volume",marker_color=colors,opacity=0.7),row=2,col=1)
    fig.add_trace(go.Scatter(x=df.index,y=df["Vol20"],name="Vol MA20",line=dict(color="#fbbf24",width=1.5)),row=2,col=1)
    fig.add_trace(go.Scatter(x=df.index,y=df["RSI"],name="RSI",line=dict(color="#a89cff",width=1.5)),row=3,col=1)
    fig.add_hline(y=70,line_dash="dot",line_color="#f87171",opacity=0.5,row=3,col=1)
    fig.add_hline(y=30,line_dash="dot",line_color="#34d399",opacity=0.5,row=3,col=1)
    fig.add_hline(y=50,line_dash="dot",line_color="#888",opacity=0.3,row=3,col=1)
    fig.update_layout(title=dict(text=f"{symbol} — Daily Chart",font=dict(size=16,color="#ffffff")),
        paper_bgcolor="#0d0d14",plot_bgcolor="#0d0d14",font=dict(color="#ffffff",size=12),
        xaxis_rangeslider_visible=False,
        legend=dict(bgcolor="#1e1e30",bordercolor="#4a4a70",borderwidth=1,font=dict(color="#ffffff",size=11)),
        height=650,margin=dict(l=10,r=10,t=50,b=10))
    for i in range(1,4):
        fig.update_xaxes(gridcolor="#1a1a2e",row=i,col=1)
        fig.update_yaxes(gridcolor="#1a1a2e",row=i,col=1)
    fig.update_yaxes(title_text="Price ($)",row=1,col=1)
    fig.update_yaxes(title_text="Volume",row=2,col=1)
    fig.update_yaxes(title_text="RSI",row=3,col=1,range=[0,100])
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
    now_et,is_weekend,is_mkt_hours,is_post_close = get_market_status()
    st.caption(f"ET: {now_et.strftime('%d %b %Y %H:%M')}")
    if is_weekend:    st.warning("Weekend — market closed")
    elif is_mkt_hours:st.info("Market open")
    else:             st.success("Market closed — best time to scan")
    st.caption(f"Universe: {len(NASDAQ100)} stocks · Benchmark: QQQ")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear(); st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — STOCK CHART
# ══════════════════════════════════════════════════════════════════════════════
if page == "📊 Stock Chart":
    st.markdown("## Stock Chart & Analysis")
    c1,c2,c3 = st.columns([2,1,1])
    with c1: symbol = st.text_input("Nasdaq Symbol",value="AAPL",placeholder="e.g. NVDA, MSFT").upper().strip()
    with c2: period = st.selectbox("Period",["6mo","1y","2y","5y"],index=2)
    with c3: show_days = st.selectbox("Chart view",[60,90,180,365,730],index=2,format_func=lambda x:f"Last {x} days")

    if symbol:
        with st.spinner(f"Loading {symbol}..."):
            df_raw = fetch_data(symbol, period)
        if df_raw is None or df_raw.empty:
            st.error(f"Could not load data for {symbol}.")
        else:
            df=add_indicators(df_raw); state,info=get_signal_state(df)
            row=df.iloc[-1]; cmp=float(row["Close"]); chg=info.get("change_pct",0)
            m1,m2,m3,m4,m5,m6 = st.columns(6)
            m1.metric("Price",      f"${cmp:,.2f}",            f"{chg:+.2f}%")
            m2.metric("EMA 220",    f"${info['ema220']:,.2f}",  f"{info['pct_above_ema']:+.2f}%")
            m3.metric("52W High",   f"${info['w52_high']:,.2f}",f"{info['pct_from_52w']:+.2f}%")
            m4.metric("RSI (14)",   f"{info['rsi']}")
            m5.metric("SL Level",   f"${info['sl_level']:,.2f}")
            m6.metric("Vol 20d avg",f"{info['vol20']/1e6:.1f}M")
            state_map = {
                "confirmed":("✅ CONFIRMED — 10+ days above 52W high. Trade ready!","success"),
                "breakout" :("🔥 BREAKOUT — Just crossed 52W high. Confirmation window.","success"),
                "near_52w" :("⚡ NEAR 52W HIGH — Within 3% of locked 52W high","warning"),
                "ema_cross":("📡 FRESH EMA CROSS — 52W high locked","info"),
                "watching" :("👁 WATCHING — Above EMA 220, awaiting 52W break","info"),
                "none"     :("— No active signal",None),
            }
            label,kind = state_map.get(state,("—",None))
            if kind=="success": st.success(label)
            elif kind=="warning": st.warning(label)
            elif kind=="info": st.info(label)
            st.plotly_chart(build_chart(df,symbol,show_days), use_container_width=True)
            col1,col2 = st.columns(2)
            with col1:
                st.dataframe(pd.DataFrame({
                    "Level":["Price","EMA 220","EMA 50","52W High (locked)","SL Level"],
                    "Value $":[f"${cmp:,.2f}",f"${info['ema220']:,.2f}",
                               f"${float(row['EMA50']):,.2f}",f"${info['w52_high']:,.2f}",f"${info['sl_level']:,.2f}"],
                    "% from CMP":["—",f"{info['pct_above_ema']:+.2f}%",
                                  f"{(cmp/float(row['EMA50'])-1)*100:+.2f}%",
                                  f"{info['pct_from_52w']:+.2f}%",f"{(cmp/info['sl_level']-1)*100:+.2f}%"],
                }),hide_index=True,use_container_width=True)
            with col2:
                st.dataframe(pd.DataFrame({
                    "Target":["+40% (sell 50%)","+100% (sell 25%)","+200%"],
                    "Price $":[f"${cmp*1.40:,.2f}",f"${cmp*2.00:,.2f}",f"${cmp*3.00:,.2f}"],
                }),hide_index=True,use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — SIGNAL SCANNER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔍 Signal Scanner":
    st.markdown("## Signal Scanner — Nasdaq 100")
    now_et,is_weekend,is_mkt_hours,is_post_close = get_market_status()
    if is_weekend:     st.warning("Weekend — US markets closed. Run Monday–Friday after 4 PM ET.")
    elif is_mkt_hours: st.warning(f"Market open ({now_et.strftime('%H:%M')} ET). Scan after 4 PM ET.")
    elif is_post_close:st.success(f"Market closed ({now_et.strftime('%H:%M')} ET). Best time to scan!")

    filt = st.pills("Filter",["All","✅ Confirmed","🔥 Breakout","⚡ Near 52W High","📡 EMA Cross","👁 Watching"],default="All")

    last_scan_time=st.session_state.get("nasdaq_scan_time","")
    scan_locked=False
    if last_scan_time and not is_weekend and is_post_close:
        try:
            scan_dt=datetime.datetime.strptime(last_scan_time,"%d %b %Y %H:%M ET")
            if scan_dt.date()==now_et.date(): scan_locked=True
        except: pass

    scan_label="🔍 Run Full Scan"
    if is_weekend: scan_label="🔍 Run Full Scan (weekend — use with caution)"
    if scan_locked: scan_label="🔒 Re-scan (today locked)"

    if st.button(scan_label,type="primary",use_container_width=True):
        bench_df_raw=fetch_data("QQQ","2y")
        results=[]; pb=st.progress(0,text="Scanning Nasdaq 100..."); total=len(NASDAQ100)
        for i,ticker in enumerate(NASDAQ100):
            pb.progress((i+1)/total,text=f"Scanning {ticker}... ({i+1}/{total})")
            df_raw=fetch_data(ticker,"2y")
            if df_raw is None or len(df_raw)<225: continue
            df=add_indicators(df_raw); state,info=get_signal_state(df)
            if state=="none" or info.get("vol20",0)<500000 or info.get("close",0)<5: continue
            rs=compute_rs_score(df_raw,bench_df_raw) if bench_df_raw is not None else None
            results.append({"Symbol":ticker,"Signal":state,"RS Score":rs,**info})
        results.sort(key=lambda x:(
            {"confirmed":0,"breakout":1,"near_52w":2,"ema_cross":3,"watching":4}.get(x["Signal"],5),
            -(x["RS Score"] or 0)))
        pb.empty()
        st.session_state["nasdaq_scan_results"]=results
        st.session_state["nasdaq_scan_time"]=now_et.strftime("%d %b %Y %H:%M ET")
        st.session_state["nasdaq_scan_status"]="weekend" if is_weekend else "market_hours" if is_mkt_hours else "post_close"

    if "nasdaq_scan_results" in st.session_state:
        results=st.session_state["nasdaq_scan_results"]
        st.caption(f"Last scan: {st.session_state.get('nasdaq_scan_time','')} · {len(NASDAQ100)} stocks · {len(results)} signals")
        label_map={"confirmed":"✅ Confirmed","breakout":"🔥 Breakout",
                   "near_52w":"⚡ Near 52W","ema_cross":"📡 EMA Cross","watching":"👁 Watching"}
        state_map2={"All":None,"✅ Confirmed":"confirmed","🔥 Breakout":"breakout",
                    "⚡ Near 52W High":"near_52w","📡 EMA Cross":"ema_cross","👁 Watching":"watching"}
        sel=state_map2.get(filt)
        filtered=[r for r in results if sel is None or r["Signal"]==sel]

        c1,c2,c3,c4,c5=st.columns(5)
        for col,sig,emoji,lbl in [(c1,"confirmed","✅","Confirmed"),(c2,"breakout","🔥","Breakout"),
            (c3,"near_52w","⚡","Near 52W"),(c4,"ema_cross","📡","EMA Cross"),(c5,"watching","👁","Watching")]:
            col.metric(f"{emoji} {lbl}",sum(1 for r in results if r["Signal"]==sig))

        st.markdown("---")
        rows=[]
        for r in filtered:
            rs=r.get("RS Score")
            rows.append({"Symbol":r["Symbol"],"Signal":label_map.get(r["Signal"],r["Signal"]),
                "RS Score":f"{rs:+.2f}" if rs is not None else "—",
                "Price $":r["close"],"EMA 220 $":r["ema220"],
                "% above EMA":f"{r['pct_above_ema']:+.2f}%",
                "52W High $":r["w52_high"],"% from 52W":f"{r['pct_from_52w']:+.2f}%",
                "SL $":r["sl_level"],"RSI":r["rsi"],"Change %":f"{r['change_pct']:+.2f}%",
                "Days above 52W":r.get("days_since_break","—")})
        st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True,height=500)

        st.markdown("#### View chart")
        pick=st.selectbox("Select symbol",[r["Symbol"] for r in filtered])
        if pick:
            df_raw=fetch_data(pick,"2y")
            if df_raw is not None:
                st.plotly_chart(build_chart(add_indicators(df_raw),pick,180),use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — MY POSITIONS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💼 My Positions":
    st.markdown("## My Nasdaq Portfolio")

    positions = read_nasdaq_positions()
    closed    = read_nasdaq_closed()

    st.markdown(f'Data source: [Open Google Sheet]({NASDAQ_SHEET_EDIT})')
    if st.button("🔄 Reload from Sheet"):
        st.cache_data.clear(); st.rerun()

    if not positions:
        st.info("No positions found. Sheet needs: Symbol | BUY PRICE | Shares")
    else:
        # Fetch live prices
        live = []
        with st.spinner("Fetching live prices..."):
            for pos in positions:
                sym = pos.get("symbol","").upper()
                df_raw = fetch_data(sym)
                if df_raw is None: continue
                df  = add_indicators(df_raw)
                row = df.iloc[-1]; prev = df.iloc[-2]
                cmp = float(row["Close"]); ema = float(row["EMA220"])
                ep  = float(pos.get("entry_price", cmp))
                sh  = float(pos.get("shares", 0))
                sl  = float(pos.get("trailing_sl", 0)) or round(max(ema, cmp*0.85), 2)
                pct = (cmp - ep) / ep * 100
                chg = (cmp - float(prev["Close"])) / float(prev["Close"]) * 100
                nsl = round(max(ema, cmp*0.85), 2)
                live.append({
                    "symbol"       : sym,
                    "entry_price"  : ep,
                    "shares"       : sh,
                    "cmp"          : round(cmp, 2),
                    "ema220"       : round(ema, 2),
                    "pnl_pct"      : round(pct, 2),
                    "pnl_usd"      : round((cmp - ep) * sh, 2),
                    "change_pct"   : round(chg, 2),
                    "day_pnl"      : round(chg/100 * cmp * sh, 2),
                    "trailing_sl"  : round(sl, 2),
                    "new_sl"       : nsl,
                    "sl_updated"   : nsl > sl,
                    "near_sl"      : cmp < sl * 1.05,
                    "curr_val"     : round(cmp * sh, 2),
                    "invested"     : round(ep * sh, 2),
                    "hit_40"       : pct >= 40,
                    "hit_100"      : pct >= 100,
                    "target_40"    : round(ep * 1.4, 2),
                    "target_100"   : round(ep * 2.0, 2),
                })
        st.session_state["_nasdaq_live_cache"] = live

        if not live:
            st.error("Could not fetch prices.")
        else:
            total_inv = sum(p["invested"]  for p in live)
            total_cur = sum(p["curr_val"]  for p in live)
            total_pnl = total_cur - total_inv
            total_pct = total_pnl / total_inv * 100 if total_inv > 0 else 0
            day_pnl   = sum(p["day_pnl"]   for p in live)

            # ── Summary metrics ──
            s1,s2,s3,s4 = st.columns(4)
            s1.metric("Total Invested",   f"${total_inv:,.0f}")
            s2.metric("Current Value",    f"${total_cur:,.0f}")
            s3.metric("Total P&L",        f"${total_pnl:+,.0f}", f"{total_pct:+.2f}%")
            s4.metric("Today P&L",        f"${day_pnl:+,.0f}")

            st.markdown("---")

            # ── Zerodha-style holdings list ──
            st.markdown("#### Holdings")
            html = ['<div style="background:#1a1a2e;border:1px solid #4a4a70;border-radius:12px;overflow:hidden;margin-bottom:16px">']
            for i, p in enumerate(sorted(live, key=lambda x: x["pnl_pct"], reverse=True)):
                pnl_c  = "#4dffb0" if p["pnl_pct"] >= 0 else "#ff7070"
                chg_c  = "#4dffb0" if p["change_pct"] >= 0 else "#ff7070"
                border = "border-bottom:1px solid #4a4a70;" if i < len(live)-1 else ""
                html.append(
                    f'<div style="padding:14px 18px;{border}">'
                    f'<div style="display:flex;justify-content:space-between;margin-bottom:3px">'
                    f'<span style="font-size:12px;color:#ffffff">{p["shares"]} shares &middot; Avg ${p["entry_price"]:,.2f}</span>'
                    f'<span style="font-size:13px;font-weight:700;color:{pnl_c}">{p["pnl_pct"]:+.2f}%</span>'
                    f'</div>'
                    f'<div style="display:flex;justify-content:space-between;margin-bottom:3px">'
                    f'<span style="font-size:18px;font-weight:700;color:#ffffff">{p["symbol"]}</span>'
                    f'<span style="font-size:18px;font-weight:700;color:{pnl_c}">${p["pnl_usd"]:+,.2f}</span>'
                    f'</div>'
                    f'<div style="display:flex;justify-content:space-between">'
                    f'<span style="font-size:12px;color:#ffffff">Invested ${p["invested"]:,.0f} &middot; SL <span style="color:#ff7070">${p["trailing_sl"]:,.2f}</span></span>'
                    f'<span style="font-size:12px;color:#ffffff">LTP ${p["cmp"]:,.2f} <span style="color:{chg_c}">({p["change_pct"]:+.2f}%)</span></span>'
                    f'</div>'
                    f'</div>'
                )
            html.append('</div>')
            st.markdown("".join(html), unsafe_allow_html=True)

            # Day P&L footer
            day_c = "#4dffb0" if day_pnl >= 0 else "#ff7070"
            st.markdown(
                f'<div style="background:#1a1a2e;border:1px solid #4a4a70;border-radius:8px;'
                f'padding:12px 18px;display:flex;justify-content:space-between">'
                f'<span style="color:#ffffff;font-size:14px">Day P&L</span>'
                f'<span style="color:{day_c};font-size:14px;font-weight:700">${day_pnl:+,.2f}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

            st.markdown("---")

            # ── Full holdings table ──
            st.markdown("#### Portfolio Table")
            rows = []
            for p in sorted(live, key=lambda x: x["curr_val"], reverse=True):
                alloc = p["curr_val"] / total_cur * 100 if total_cur > 0 else 0
                rows.append({
                    "Symbol"       : p["symbol"],
                    "Shares"       : round(p["shares"], 4),
                    "Avg Buy $"    : f"${p['entry_price']:,.2f}",
                    "LTP $"        : f"${p['cmp']:,.2f}",
                    "Invested $"   : f"${p['invested']:,.0f}",
                    "Value $"      : f"${p['curr_val']:,.0f}",
                    "P&L $"        : f"${p['pnl_usd']:+,.2f}",
                    "P&L %"        : f"{p['pnl_pct']:+.2f}%",
                    "Allocation %"  : f"{alloc:.1f}%",
                    "Day %"        : f"{p['change_pct']:+.2f}%",
                    "SL $"         : f"${p['trailing_sl']:,.2f}",
                    "Updated SL $" : f"${p['new_sl']:,.2f}" + (" ↑" if p["sl_updated"] else ""),
                })
            st.dataframe(rows, hide_index=True, use_container_width=True)

            st.markdown("---")

            # ── Charts ──
            cc1, cc2 = st.columns(2)
            with cc1:
                st.markdown("#### % Allocation")
                fig_pie = go.Figure(data=[go.Pie(
                    labels=[p["symbol"] for p in live],
                    values=[round(p["curr_val"], 0) for p in live],
                    hole=0.5, textinfo="label+percent",
                    marker=dict(colors=["#7c6af7","#34d399","#f87171","#fbbf24","#22d3ee",
                                        "#a89cff","#6ee7b7","#fca5a5","#60efff","#ff9f7f",
                                        "#b8ff87","#ffd6e0","#c3adff","#87ceeb","#ffb347",
                                        "#98ff98","#dda0dd","#f0e68c"]),
                )])
                fig_pie.update_layout(
                    paper_bgcolor="#0d0d14", plot_bgcolor="#0d0d14",
                    font=dict(color="#ffffff"), showlegend=False, height=350,
                    margin=dict(l=10,r=10,t=10,b=10),
                    annotations=[dict(text=f"${total_cur:,.0f}", x=0.5, y=0.5,
                        font_size=13, font_color="#ffffff", showarrow=False)])
                st.plotly_chart(fig_pie, use_container_width=True)

            with cc2:
                st.markdown("#### P&L by Stock")
                sorted_live = sorted(live, key=lambda x: x["pnl_usd"], reverse=True)
                pnl_vals = [p["pnl_usd"] for p in sorted_live]
                fig_bar = go.Figure(data=[go.Bar(
                    x=[p["symbol"] for p in sorted_live], y=pnl_vals,
                    marker_color=["#34d399" if v >= 0 else "#f87171" for v in pnl_vals],
                    text=[f"${v:+,.0f}" for v in pnl_vals],
                    textposition="outside",
                )])
                fig_bar.update_layout(
                    paper_bgcolor="#0d0d14", plot_bgcolor="#0d0d14",
                    font=dict(color="#ffffff"), height=350, showlegend=False,
                    margin=dict(l=10,r=10,t=10,b=10),
                    xaxis=dict(gridcolor="#1a1a2e"),
                    yaxis=dict(gridcolor="#1a1a2e", title="P&L ($)"))
                fig_bar.add_hline(y=0, line_color="#888", line_dash="dot")
                st.plotly_chart(fig_bar, use_container_width=True)

            st.markdown("---")

            # ── SL alerts ──
            sl_alerts = [p for p in live if p["sl_updated"] or p["near_sl"] or p["hit_40"]]
            if sl_alerts:
                st.markdown("#### Action Alerts")
                for p in sl_alerts:
                    if p["near_sl"]:    st.error(f"⚠️ {p['symbol']} near SL ${p['trailing_sl']} — monitor closely!")
                    if p["hit_40"]:     st.success(f"✅ {p['symbol']} +{p['pnl_pct']:.1f}% — consider booking 50%")
                    if p["sl_updated"]: st.info(f"↑ {p['symbol']} — raise SL from ${p['trailing_sl']} to ${p['new_sl']} in sheet")

            # ── Realised P&L ──
            st.markdown("---")
            _live_data = st.session_state.get("_nasdaq_live_cache", [])
            _total_inv = sum(p["invested"] for p in _live_data) if _live_data else 0
            _unreal    = sum(p["pnl_usd"]  for p in _live_data) if _live_data else 0
            _real      = sum(t["pnl_usd"]  for t in closed)     if closed     else 0

            st.markdown("### P&L Summary")
            ps1, ps2, ps3 = st.columns(3)
            ps1.metric("Unrealised P&L", f"${_unreal:+,.2f}",
                f"{_unreal/_total_inv*100:+.2f}%" if _total_inv > 0 else "")
            ps2.metric("Realised P&L",   f"${_real:+,.2f}",
                f"{len(closed)} trades" if closed else "No closed trades")
            ps3.metric("Combined P&L",   f"${_unreal+_real:+,.2f}")

            if closed:
                st.markdown("#### Closed Trades")
                wins   = [t for t in closed if t["pnl_usd"] > 0]
                losses = [t for t in closed if t["pnl_usd"] <= 0]
                wr     = len(wins)/len(closed)*100 if closed else 0
                rc1,rc2,rc3,rc4 = st.columns(4)
                rc1.metric("Total Trades", len(closed))
                rc2.metric("Win Rate",     f"{wr:.0f}%")
                rc3.metric("Total Won",    f"${sum(t['pnl_usd'] for t in wins):+,.2f}")
                rc4.metric("Total Lost",   f"${sum(t['pnl_usd'] for t in losses):+,.2f}")
                trows = [{"Symbol":t["symbol"],"Entry $":t["entry_price"],"Exit $":t["exit_price"],
                    "Shares":t["shares"],"P&L $":f"${t['pnl_usd']:+,.2f}","P&L %":f"{t['pnl_pct']:+.2f}%",
                    "Reason":t["reason"]} for t in reversed(closed)]
                st.dataframe(trows, hide_index=True, use_container_width=True)
            else:
                st.info("No closed trades yet. Add exits to your Google Sheet Sheet2 tab.")


elif page == "📈 QQQ Benchmark":
    st.markdown("## Market Benchmark")
    with st.spinner("Loading benchmark data..."):
        df_qqq=fetch_data("QQQ","5y"); df_spy=fetch_data("SPY","5y"); df_iwm=fetch_data("IWM","5y")

    idx_tab=st.radio("Select",["QQQ (Nasdaq 100)","SPY (S&P 500)","Compare All"],horizontal=True)

    def index_section(df_raw, label):
        if df_raw is None: st.error(f"Could not load {label}."); return
        df=add_indicators(df_raw); row=df.iloc[-1]; prev=df.iloc[-2]
        cmp=float(row["Close"]); chg=(cmp-float(prev["Close"]))/float(prev["Close"])*100
        def ret(n): return round((cmp/float(df["Close"].iloc[-n])-1)*100,2) if len(df)>=n else None
        c1,c2,c3,c4,c5=st.columns(5)
        c1.metric(label,f"${cmp:,.2f}",f"{chg:+.2f}%")
        c2.metric("1 Month", f"{ret(21):+.2f}%" if ret(21) else "—")
        c3.metric("3 Months",f"{ret(63):+.2f}%" if ret(63) else "—")
        c4.metric("6 Months",f"{ret(126):+.2f}%" if ret(126) else "—")
        c5.metric("1 Year",  f"{ret(252):+.2f}%" if ret(252) else "—")
        st.plotly_chart(build_chart(df,label,365),use_container_width=True)

    if idx_tab=="QQQ (Nasdaq 100)": index_section(df_qqq,"QQQ — Nasdaq 100 ETF")
    elif idx_tab=="SPY (S&P 500)":  index_section(df_spy,"SPY — S&P 500 ETF")
    else:
        st.markdown("### QQQ vs SPY vs IWM — Normalised (last 1 year)")
        fig=go.Figure()
        for name,color,df_raw in [("QQQ","#22d3ee",df_qqq),("SPY","#34d399",df_spy),("IWM","#fbbf24",df_iwm)]:
            if df_raw is None: continue
            d=df_raw["Close"].tail(252); n=d/float(d.iloc[0])*100
            fig.add_trace(go.Scatter(x=n.index,y=n.values,name=name,line=dict(color=color,width=2)))
        fig.add_hline(y=100,line_dash="dot",line_color="#888",opacity=0.4)
        fig.update_layout(paper_bgcolor="#0d0d14",plot_bgcolor="#0d0d14",font=dict(color="#ffffff"),
            height=400,legend=dict(bgcolor="#1e1e30",bordercolor="#4a4a70"),
            margin=dict(l=10,r=10,t=20,b=10),
            yaxis=dict(gridcolor="#1a1a2e",title="Indexed to 100"),xaxis=dict(gridcolor="#1a1a2e"))
        st.plotly_chart(fig,use_container_width=True)
        rows=[]
        for label,_,df_raw in [("QQQ",None,df_qqq),("SPY",None,df_spy),("IWM",None,df_iwm)]:
            if df_raw is None: continue
            c=float(df_raw["Close"].iloc[-1])
            def r(n): return round((c/float(df_raw["Close"].iloc[-n])-1)*100,2) if len(df_raw)>=n else None
            rows.append({"Index":label,"1M":f"{r(21):+.2f}%" if r(21) else "—",
                "3M":f"{r(63):+.2f}%" if r(63) else "—","6M":f"{r(126):+.2f}%" if r(126) else "—",
                "1Y":f"{r(252):+.2f}%" if r(252) else "—","2Y":f"{r(504):+.2f}%" if r(504) else "—"})
        st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — POSITION SIZER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🧮 Position Sizer":
    st.markdown("## Position Size Calculator")
    st.markdown("1% risk rule · 15% SL · USD capital")

    c1,c2=st.columns(2)
    with c1: capital=st.number_input("Capital ($)",min_value=1000,max_value=10000000,value=10000,step=500)
    with c2: sym_input=st.text_input("Symbol (auto-fetches price & EMA 220)",placeholder="e.g. NVDA").upper().strip()

    manual=st.toggle("Enter price manually",value=False)

    if manual or not sym_input:
        c1,c2=st.columns(2)
        with c1: entry_price=st.number_input("Entry Price $",min_value=0.1,step=0.1,value=100.0)
        with c2: ema220_val =st.number_input("EMA 220 $",    min_value=0.1,step=0.1,value=85.0)
    else:
        with st.spinner(f"Fetching {sym_input}..."):
            df_raw=fetch_data(sym_input)
        if df_raw is None: st.error(f"Could not fetch {sym_input}."); st.stop()
        df_ind=add_indicators(df_raw); row_live=df_ind.iloc[-1]; prev_live=df_ind.iloc[-2]
        cmp_live=float(row_live["Close"]); ema220_val=float(row_live["EMA220"])
        chg_live=(cmp_live-float(prev_live["Close"]))/float(prev_live["Close"])*100
        st.success(f"Live data for {sym_input}")
        q1,q2,q3,q4=st.columns(4)
        q1.metric("Price",  f"${cmp_live:,.2f}",f"{chg_live:+.2f}%")
        q2.metric("EMA 220",f"${ema220_val:,.2f}")
        q3.metric("RSI",    f"{float(row_live['RSI']):.1f}" if not pd.isna(row_live["RSI"]) else "—")
        q4.metric("Vol 20d",f"{float(row_live['Vol20'])/1e6:.1f}M" if not pd.isna(row_live["Vol20"]) else "—")
        entry_price=st.number_input("Expected Entry Price $",min_value=0.1,step=0.1,value=round(cmp_live,2))

    st.markdown("---")
    sl_15pct  =entry_price*0.85
    initial_sl=round(max(ema220_val,sl_15pct),2)
    risk_amt  =capital*0.01          # 1% risk
    risk_per_sh=entry_price-initial_sl

    if risk_per_sh<=0:
        st.error("Entry price is at or below SL — invalid setup."); st.stop()

    shares=math.floor(risk_amt/risk_per_sh)
    deploy=shares*entry_price
    max_deploy=capital*0.20
    capped=False
    if deploy>max_deploy:
        shares=math.floor(max_deploy/entry_price); deploy=shares*entry_price; capped=True

    check_min=deploy>=500
    deploy_pct=deploy/capital*100

    st.markdown("### Result")
    if shares>0 and check_min:
        st.success(f"BUY {shares} shares of {sym_input or 'stock'} at ${entry_price:,.2f} — Deploy ${deploy:,.0f}")
    else:
        st.error(f"Deploy ${deploy:,.0f} too small — skip this trade")
    if capped: st.warning(f"Capped at 20% of capital.")

    r1,r2,r3=st.columns(3)
    with r1:
        st.markdown("**Stop Loss**")
        st.dataframe(pd.DataFrame({
            "Rule":["15% below entry","EMA 220","Initial SL (higher)"],
            "Value $":[f"${sl_15pct:,.2f}",f"${ema220_val:,.2f}",f"${initial_sl:,.2f}"],
            "Used?":["✓" if sl_15pct>=ema220_val else "—","✓" if ema220_val>sl_15pct else "—","✅"]
        }),hide_index=True,use_container_width=True)
    with r2:
        st.markdown("**Shares**")
        st.dataframe(pd.DataFrame({
            "Item":["Capital","Risk 1%","Risk Amount","Risk/Share","Shares"],
            "Value":[f"${capital:,.0f}","1%",f"${risk_amt:,.0f}",f"${risk_per_sh:,.2f}",f"{shares}"]
        }),hide_index=True,use_container_width=True)
    with r3:
        st.markdown("**Checks**")
        st.dataframe(pd.DataFrame({
            "Rule":["Min $500","Max 20% capital","Shares > 0"],
            "Required":[f"$500",f"${max_deploy:,.0f}","> 0"],
            "Actual":[f"${deploy:,.0f}",f"${deploy:,.0f}",str(shares)],
            "Status":["✅" if check_min else "❌","✅" if deploy<=max_deploy else "❌","✅" if shares>0 else "❌"]
        }),hide_index=True,use_container_width=True)

    st.markdown("---")
    m1,m2,m3,m4,m5,m6=st.columns(6)
    m1.metric("Shares",       f"{shares}")
    m2.metric("Deploy",       f"${deploy:,.0f}")
    m3.metric("% of Capital", f"{deploy_pct:.1f}%")
    m4.metric("Initial SL",   f"${initial_sl:,.2f}")
    m5.metric("Max Loss $",   f"${shares*risk_per_sh:,.0f}")
    m6.metric("Max Loss %",   "1%")

    st.markdown("#### Profit Targets")
    t1,t2,t3,t4=st.columns(4)
    t1.metric("+20%",            f"${entry_price*1.20:,.2f}")
    t2.metric("+40% — sell 50%", f"${entry_price*1.40:,.2f}",f"Receive ${math.floor(shares*0.5)*entry_price*1.40:,.0f}")
    t3.metric("+100% — sell 25%",f"${entry_price*2.00:,.2f}",f"Receive ${math.floor(shares*0.25)*entry_price*2.00:,.0f}")
    t4.metric("Hold last 25%",   f"{math.ceil(shares*0.25)} shares","Until trailing SL")

    st.markdown("#### Trailing SL Schedule")
    trail_rows=[]
    for mult in [1.05,1.10,1.20,1.30,1.40,1.60,1.80,2.00]:
        price=entry_price*mult; trail_sl=round(price*0.85,2)
        locked=round((trail_sl-entry_price)/entry_price*100,2)
        trail_rows.append({"If Price":f"${price:,.2f} ({(mult-1)*100:+.0f}%)",
            "Trailing SL":f"${trail_sl:,.2f}","Locked-in Gain":f"{locked:+.2f}%",
            "Status":"Profit locked!" if locked>0 else "At risk"})
    st.dataframe(pd.DataFrame(trail_rows),hide_index=True,use_container_width=True)

    st.markdown("---")
    st.markdown("### Batch Calculator")
    batch=st.text_input("Symbols (comma separated)",placeholder="AAPL, NVDA, MSFT")
    if batch and st.button("Calculate All",type="primary"):
        syms=[s.strip().upper() for s in batch.split(",") if s.strip()][:8]
        rows=[]; total_dep=0
        with st.spinner("Fetching..."):
            for s in syms:
                df_b=fetch_data(s)
                if df_b is None:
                    rows.append({"Symbol":s,"Status":"❌ No data"}); continue
                df_b=add_indicators(df_b); rb=df_b.iloc[-1]
                cb=float(rb["Close"]); eb=float(rb["EMA220"])
                sl_b=round(max(eb,cb*0.85),2); rps_b=cb-sl_b
                if rps_b<=0:
                    rows.append({"Symbol":s,"Price $":f"${cb:,.2f}","Status":"❌ Below SL"}); continue
                sh_b=math.floor((capital*0.01)/rps_b); dep_b=sh_b*cb
                if dep_b>capital*0.20: sh_b=math.floor(capital*0.20/cb); dep_b=sh_b*cb
                total_dep+=dep_b
                rows.append({"Symbol":s,"Price $":f"${cb:,.2f}","EMA 220 $":f"${eb:,.2f}",
                    "SL $":f"${sl_b:,.2f}","Shares":sh_b,"Deploy $":f"${dep_b:,.0f}",
                    "% Cap":f"{dep_b/capital*100:.1f}%","Status":"✅" if dep_b>=500 else "⚠️ Small"})
        st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
        b1,b2,b3=st.columns(3)
        b1.metric("Total Deployed",f"${total_dep:,.0f}")
        b2.metric("% of Capital",  f"{total_dep/capital*100:.1f}%")
        b3.metric("Remaining Cash",f"${capital-total_dep:,.0f}")
