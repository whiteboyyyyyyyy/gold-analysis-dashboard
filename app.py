import streamlit as st
import pandas as pd
import os
import requests
from datetime import datetime, timedelta

# ========== 匯率設定 ==========
USD_CNY_RATE = 7.25  # 預設匯率（當API無法獲取時使用）
OUNCE_TO_GRAM = 31.1035

@st.cache_data(ttl=3600)
def get_current_usd_cny_rate():
    """獲取即時 USD/CNY 匯率"""
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            rate = data.get('rates', {}).get('CNY')
            if rate:
                return float(rate)
    except Exception:
        pass

    try:
        url = "https://api.frankfurter.app/latest?from=USD&to=CNY"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            rate = data.get('rates', {}).get('CNY')
            if rate:
                return float(rate)
    except Exception:
        pass

    return USD_CNY_RATE


@st.cache_data(ttl=86400)
def get_historical_rate(date_str):
    """
    獲取指定日期的 USD/CNY 匯率
    返回 (rate, source) 或 (None, None)
    source: 'historical' 或 'current'
    """
    try:
        url = f"https://api.frankfurter.app/{date_str}?from=USD&to=CNY"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            rate = data.get('rates', {}).get('CNY')
            if rate:
                return float(rate), "歷史匯率"
    except Exception:
        pass
    return None, None


def get_rate_for_date(d, current_rate):
    """
    獲取某個日期的匯率
    返回 (rate, source_label)
    """
    date_str = d.strftime('%Y-%m-%d')
    rate, source = get_historical_rate(date_str)
    if rate:
        return rate, source
    return current_rate, "即時匯率"


def cny_per_gram_to_usd_per_ounce(price_cny, rate):
    """人民幣/克 → 美元/盎司"""
    if rate == 0:
        return 0
    return (price_cny * OUNCE_TO_GRAM) / rate


# ========== 網頁配置 ==========
st.set_page_config(page_title="黃金歷史數據看板", layout="wide", page_icon="🥇")

st.title("🥇 黃金歷史數據看板")
st.caption(f"COMEX 黃金期貨 + 倫敦金現貨 (XAU/USD) + 上海金現貨 (Au99.99)")

# ========== 獲取即時匯率 ==========
current_rate = get_current_usd_cny_rate()
st.caption(f"💱 即時匯率: USD/CNY = {current_rate:.4f}（自動獲取，每小時更新 | 歷史換算優先使用當日歷史匯率，無歷史匯率時使用即時匯率）")

# ========== 讀取CSV函數 ==========
@st.cache_data
def load_csv(filepath):
    """讀取CSV，清理數字格式"""
    df = pd.read_csv(filepath)
    df.columns = [col.strip().strip('"') for col in df.columns]
    df['日期'] = pd.to_datetime(df['日期'])
    for col in ['收市', '開市', '高', '低']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '')
            df[col] = pd.to_numeric(df[col], errors='coerce')
    if '升跌（%）' in df.columns:
        df['升跌（%）'] = df['升跌（%）'].astype(str).str.replace('%', '')
        df['升跌（%）'] = pd.to_numeric(df['升跌（%）'], errors='coerce')
    df = df.sort_values('日期', ascending=False).reset_index(drop=True)
    return df

# ========== 載入數據 ==========
DATA_DIR = "data"

spot_daily = load_csv(os.path.join(DATA_DIR, "london_gold_daily.csv"))
spot_weekly = load_csv(os.path.join(DATA_DIR, "london_gold_weekly.csv"))
spot_monthly = load_csv(os.path.join(DATA_DIR, "london_gold_monthly.csv"))

futures_daily = load_csv(os.path.join(DATA_DIR, "comex_futures_daily.csv"))
futures_weekly = load_csv(os.path.join(DATA_DIR, "comex_futures_weekly.csv"))
futures_monthly = load_csv(os.path.join(DATA_DIR, "comex_futures_monthly.csv"))

sge_daily = load_csv(os.path.join(DATA_DIR, "sge_spot_daily.csv"))
sge_weekly = load_csv(os.path.join(DATA_DIR, "sge_spot_weekly.csv"))

# ========== 找最大漲跌幅 ==========
def find_max_gain_loss(df):
    """找出最大漲幅和最大跌幅"""
    gain_row = df.loc[df['升跌（%）'].idxmax()]
    loss_row = df.loc[df['升跌（%）'].idxmin()]
    return (
        gain_row['升跌（%）'], gain_row['日期'],
        loss_row['升跌（%）'], loss_row['日期']
    )

s_d_gain, s_d_gain_date, s_d_loss, s_d_loss_date = find_max_gain_loss(spot_daily)
s_w_gain, s_w_gain_date, s_w_loss, s_w_loss_date = find_max_gain_loss(spot_weekly)
s_m_gain, s_m_gain_date, s_m_loss, s_m_loss_date = find_max_gain_loss(spot_monthly)

f_d_gain, f_d_gain_date, f_d_loss, f_d_loss_date = find_max_gain_loss(futures_daily)
f_w_gain, f_w_gain_date, f_w_loss, f_w_loss_date = find_max_gain_loss(futures_weekly)
f_m_gain, f_m_gain_date, f_m_loss, f_m_loss_date = find_max_gain_loss(futures_monthly)

sge_d_gain, sge_d_gain_date, sge_d_loss, sge_d_loss_date = find_max_gain_loss(sge_daily)
sge_w_gain, sge_w_gain_date, sge_w_loss, sge_w_loss_date = find_max_gain_loss(sge_weekly)

# ========== 輔助函數 ==========
def format_date(d):
    return d.strftime('%Y-%m-%d')

def show_latest_metrics(latest, label, currency="$"):
    """顯示最新報價"""
    col_date, col_close, col_change = st.columns(3)
    with col_date:
        st.metric(label=f"{label} 最新交易日", value=format_date(latest['日期']))
    with col_close:
        st.metric(label=f"{label} 收市價", value=f"{currency}{latest['收市']:,.2f}")
    with col_change:
        st.metric(label=f"{label} 當日漲跌幅", value=f"{latest['升跌（%）']:+.2f}%")

def show_latest_metrics_sge(latest, rate):
    """顯示上海金最新報價（含換算）"""
    col_date, col_close_cny, col_close_usd, col_change = st.columns(4)
    usd_price = cny_per_gram_to_usd_per_ounce(latest['收市'], rate)
    with col_date:
        st.metric(label="上海金現貨 最新交易日", value=format_date(latest['日期']))
    with col_close_cny:
        st.metric(label="收市價 (CNY/克)", value=f"¥{latest['收市']:,.2f}")
    with col_close_usd:
        st.metric(label=f"換算 (USD/盎司) @ {rate:.4f}", value=f"${usd_price:,.2f}")
    with col_change:
        st.metric(label="當日漲跌幅", value=f"{latest['升跌（%）']:+.2f}%")

def show_max_gain_loss_section(label, periods):
    """顯示最大漲跌幅總覽"""
    st.subheader(f"📊 {label} — 最大漲跌幅總覽")
    cols = st.columns(len(periods))
    for i, (p_label, gain, gain_date, loss, loss_date) in enumerate(periods):
        with cols[i]:
            st.markdown(f"### {p_label}")
            st.metric(
                label=f"▲ 最大漲幅 ({format_date(gain_date)})",
                value=f"+{gain:.2f}%"
            )
            st.metric(
                label=f"▼ 最大跌幅 ({format_date(loss_date)})",
                value=f"{loss:.2f}%"
            )

def show_data_tabs(data_dict, label, currency="$", source=""):
    """顯示數據分頁（國際金價用）"""
    st.subheader(f"📋 {label} — 完整歷史數據")
    st.caption(f"📡 數據來源：{source}")
    tab_labels = list(data_dict.keys())
    tabs = st.tabs([f"📅 {t}" for t in tab_labels])
    for tab, (period_name, df) in zip(tabs, data_dict.items()):
        with tab:
            st.caption(f"{label} {period_name} — 共 {len(df)} 筆資料 | 數據來源：{source} | 由新至舊排列")
            display = df.copy()
            display['日期'] = display['日期'].dt.strftime('%Y-%m-%d')
            display['升跌（%）'] = display['升跌（%）'].apply(lambda x: f"{x:+.2f}%")
            display['收市'] = display['收市'].apply(lambda x: f"{currency}{x:,.2f}")
            display['開市'] = display['開市'].apply(lambda x: f"{currency}{x:,.2f}")
            display['高'] = display['高'].apply(lambda x: f"{currency}{x:,.2f}")
            display['低'] = display['低'].apply(lambda x: f"{currency}{x:,.2f}")
            st.dataframe(
                display[['日期', '收市', '開市', '高', '低', '升跌（%）']],
                use_container_width=True,
                hide_index=True,
                height=500
            )

def show_data_tabs_sge(data_dict, current_rate):
    """顯示上海金數據分頁（含美元換算欄位，使用當日歷史匯率）"""
    st.subheader("📋 上海金現貨 (Au99.99) — 完整歷史數據")
    st.caption("📡 數據來源：上海黃金交易所")
    tab_labels = list(data_dict.keys())
    tabs = st.tabs([f"📅 {t}" for t in tab_labels])
    for tab, (period_name, df) in zip(tabs, data_dict.items()):
        with tab:
            st.caption(f"上海金現貨 {period_name} — 共 {len(df)} 筆資料 | 數據來源：上海黃金交易所 | 換算優先使用當日歷史匯率 | 由新至舊排列")

            # 計算每一筆的匯率和來源
            rates_info = df['日期'].apply(lambda d: get_rate_for_date(d, current_rate))
            df['換算匯率'] = rates_info.apply(lambda x: x[0])
            df['匯率來源'] = rates_info.apply(lambda x: x[1])

            display = df.copy()
            display['日期'] = display['日期'].dt.strftime('%Y-%m-%d')
            display['升跌（%）'] = display['升跌（%）'].apply(lambda x: f"{x:+.2f}%")
            display['收市 (CNY/克)'] = display['收市'].apply(lambda x: f"¥{x:,.2f}")
            display['開市 (CNY/克)'] = display['開市'].apply(lambda x: f"¥{x:,.2f}")
            display['高 (CNY/克)'] = display['高'].apply(lambda x: f"¥{x:,.2f}")
            display['低 (CNY/克)'] = display['低'].apply(lambda x: f"¥{x:,.2f}")

            # 用對應匯率換算
            display['收市 (USD/盎司)'] = display.apply(
                lambda row: f"${cny_per_gram_to_usd_per_ounce(row['收市'], row['換算匯率']):,.2f}", axis=1
            )
            display['開市 (USD/盎司)'] = display.apply(
                lambda row: f"${cny_per_gram_to_usd_per_ounce(row['開市'], row['換算匯率']):,.2f}", axis=1
            )
            display['高 (USD/盎司)'] = display.apply(
                lambda row: f"${cny_per_gram_to_usd_per_ounce(row['高'], row['換算匯率']):,.2f}", axis=1
            )
            display['低 (USD/盎司)'] = display.apply(
                lambda row: f"${cny_per_gram_to_usd_per_ounce(row['低'], row['換算匯率']):,.2f}", axis=1
            )
            display['換算匯率'] = display['換算匯率'].apply(lambda x: f"{x:.4f}")
            display['匯率來源'] = display['匯率來源'].apply(lambda x: f"{'🔵' if x == '歷史匯率' else '🟡'} {x}")

            st.dataframe(
                display[[
                    '日期',
                    '收市 (CNY/克)', '收市 (USD/盎司)',
                    '開市 (CNY/克)', '開市 (USD/盎司)',
                    '高 (CNY/克)', '高 (USD/盎司)',
                    '低 (CNY/克)', '低 (USD/盎司)',
                    '升跌（%）',
                    '換算匯率', '匯率來源'
                ]],
                use_container_width=True,
                hide_index=True,
                height=500
            )

            # 統計使用了多少歷史匯率 vs 即時匯率
            historical_count = display['匯率來源'].str.contains('歷史匯率').sum()
            fallback_count = len(display) - historical_count
            st.caption(f"🔵 歷史匯率: {historical_count} 筆 | 🟡 即時匯率備用: {fallback_count} 筆")


def get_common_dates(df1, df2):
    """只取兩個 DataFrame 都有的日期，返回兩個 Series"""
    s1 = df1.set_index('日期')['收市']
    s2 = df2.set_index('日期')['收市']
    common = s1.index.intersection(s2.index)
    return s1.loc[common], s2.loc[common]

def get_common_dates_by_series(s1, s2):
    """只取兩個 Series 都有的日期"""
    common = s1.index.intersection(s2.index)
    return s1.loc[common], s2.loc[common]

def align_weekly_to_sunday(df):
    """把週線日期對齊到週日"""
    df = df.copy()
    df['日期'] = df['日期'].apply(lambda d: d + pd.Timedelta(days=(6 - d.weekday())))
    return df

def get_common_weekly(sge_w, spot_w):
    """上海金週線對齊週日後，跟倫敦金週線找交集"""
    sge_aligned = align_weekly_to_sunday(sge_w)
    s1 = sge_aligned.set_index('日期')['收市']
    s2 = spot_w.set_index('日期')['收市']
    common = s1.index.intersection(s2.index)
    return s1.loc[common], s2.loc[common]


# ============================================================
# 頁面佈局
# ============================================================

# ============================================================
# 第一部分：最新報價 + 交易時段
# ============================================================
st.header("📌 最新報價")

# COMEX 期貨 + 交易時段
col_futures, col_futures_session = st.columns([3, 1])
with col_futures:
    st.markdown("### COMEX 黃金期貨")
    show_latest_metrics(futures_daily.iloc[0], "COMEX 黃金期貨", "$")
with col_futures_session:
    st.markdown("### 🕐 交易時段")
    st.markdown("""
    **COMEX 黃金期貨 (GC)**  
    夏令：週一 06:00 – 週六 05:00  
    冬令：週一 07:00 – 週六 06:00  
    每日休市 1 小時
    """)

st.markdown("---")

# 倫敦金現貨 + 交易時段
col_spot, col_spot_session = st.columns([3, 1])
with col_spot:
    st.markdown("### 倫敦金現貨 (XAU/USD)")
    show_latest_metrics(spot_daily.iloc[0], "倫敦金現貨", "$")
with col_spot_session:
    st.markdown("### 🕐 交易時段")
    st.markdown("""
    **倫敦金現貨 (XAU/USD)**  
    夏令：週一 06:00 – 週六 05:00  
    冬令：週一 07:00 – 週六 06:00  
    每日休市 1 小時
    """)

st.markdown("---")

# 上海金現貨 + 交易時段
col_sge, col_sge_session = st.columns([3, 1])
with col_sge:
    st.markdown("### 上海金現貨 (Au99.99)")
    show_latest_metrics_sge(sge_daily.iloc[0], current_rate)
with col_sge_session:
    st.markdown("### 🕐 交易時段")
    st.markdown("""
    **上海金現貨 (Au99.99)**  
    早盤：09:00 – 11:30  
    午盤：13:30 – 15:30  
    夜盤：20:00 – 02:30
    """)

st.markdown("---")

# ============================================================
# 第二部分：最大漲跌幅總覽
# ============================================================
st.header("📊 最大漲跌幅總覽")

show_max_gain_loss_section("COMEX 黃金期貨", [
    ("日線", f_d_gain, f_d_gain_date, f_d_loss, f_d_loss_date),
    ("週線", f_w_gain, f_w_gain_date, f_w_loss, f_w_loss_date),
    ("月線", f_m_gain, f_m_gain_date, f_m_loss, f_m_loss_date),
])

st.markdown("---")

show_max_gain_loss_section("倫敦金現貨 (XAU/USD)", [
    ("日線", s_d_gain, s_d_gain_date, s_d_loss, s_d_loss_date),
    ("週線", s_w_gain, s_w_gain_date, s_w_loss, s_w_loss_date),
    ("月線", s_m_gain, s_m_gain_date, s_m_loss, s_m_loss_date),
])

st.markdown("---")

show_max_gain_loss_section("上海金現貨 (Au99.99)", [
    ("日線", sge_d_gain, sge_d_gain_date, sge_d_loss, sge_d_loss_date),
    ("週線", sge_w_gain, sge_w_gain_date, sge_w_loss, sge_w_loss_date),
])

st.markdown("---")

# ============================================================
# 第三部分：完整歷史數據
# ============================================================
st.header("📋 完整歷史數據")

show_data_tabs(
    {"日線": futures_daily, "週線": futures_weekly, "月線": futures_monthly},
    "COMEX 黃金期貨", "$", "Investing.com"
)

st.markdown("---")

show_data_tabs(
    {"日線": spot_daily, "週線": spot_weekly, "月線": spot_monthly},
    "倫敦金現貨 (XAU/USD)", "$", "Investing.com"
)

st.markdown("---")

show_data_tabs_sge({"日線": sge_daily, "週線": sge_weekly}, current_rate)

st.markdown("---")

# ============================================================
# 第四部分：走勢圖
# ============================================================
st.header("📈 收市價走勢圖（只顯示共同交易日的數據）")

# ---- COMEX vs 倫敦金 ----
st.subheader("COMEX 黃金期貨 vs 倫敦金現貨 (XAU/USD)")

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("**日線對比**")
    s1, s2 = get_common_dates(futures_daily, spot_daily)
    chart = pd.DataFrame({'COMEX 期貨': s1, '倫敦金現貨': s2}).sort_index()
    st.line_chart(chart, color=["#FF6B35", "#004E89"])

with c2:
    st.markdown("**週線對比**")
    s1, s2 = get_common_dates(futures_weekly, spot_weekly)
    chart = pd.DataFrame({'COMEX 期貨': s1, '倫敦金現貨': s2}).sort_index()
    st.line_chart(chart, color=["#FF6B35", "#004E89"])

with c3:
    st.markdown("**月線對比**")
    s1, s2 = get_common_dates(futures_monthly, spot_monthly)
    chart = pd.DataFrame({'COMEX 期貨': s1, '倫敦金現貨': s2}).sort_index()
    st.line_chart(chart, color=["#FF6B35", "#004E89"])

st.markdown("---")

# ---- 上海金 vs 倫敦金 ----
st.subheader("上海金現貨 (使用當日歷史匯率換算 USD/盎司) vs 倫敦金現貨")

sge_daily_with_rate = sge_daily.copy()
sge_daily_rates = sge_daily_with_rate['日期'].apply(lambda d: get_rate_for_date(d, current_rate))
sge_daily_with_rate['rate'] = sge_daily_rates.apply(lambda x: x[0])
sge_daily_with_rate['rate_source'] = sge_daily_rates.apply(lambda x: x[1])
sge_daily_with_rate['收市_USD'] = sge_daily_with_rate.apply(
    lambda row: cny_per_gram_to_usd_per_ounce(row['收市'], row['rate']), axis=1
)

spot_daily_s = spot_daily.set_index('日期')['收市']

d1, d2 = st.columns(2)

with d1:
    st.markdown("**日線對比**")
    sge_daily_usd_series = sge_daily_with_rate.set_index('日期')['收市_USD']
    s1, s2 = get_common_dates_by_series(sge_daily_usd_series, spot_daily_s)
    # 統計匯率來源
    common_dates = s1.index
    rate_sources = sge_daily_with_rate.set_index('日期').loc[common_dates, 'rate_source']
    hist_count = (rate_sources == '歷史匯率').sum()
    curr_count = (rate_sources == '即時匯率').sum()
    st.caption(f"換算匯率: 🔵 歷史匯率 {hist_count} 日 | 🟡 即時匯率 {curr_count} 日")
    chart = pd.DataFrame({'上海金 (USD/盎司)': s1, '倫敦金現貨': s2}).sort_index()
    st.line_chart(chart, color=["#E63946", "#004E89"])

with d2:
    st.markdown("**週線對比**")
    s1, s2 = get_common_weekly(sge_weekly, spot_weekly)
    s1_usd_list = []
    s1_rate_sources = []
    for idx, val in s1.items():
        rate, source = get_rate_for_date(idx, current_rate)
        s1_usd_list.append(cny_per_gram_to_usd_per_ounce(val, rate))
        s1_rate_sources.append(source)
    s1_usd = pd.Series(s1_usd_list, index=s1.index)
    hist_count = sum(1 for s in s1_rate_sources if s == '歷史匯率')
    curr_count = len(s1_rate_sources) - hist_count
    st.caption(f"換算匯率: 🔵 歷史匯率 {hist_count} 週 | 🟡 即時匯率 {curr_count} 週")
    chart = pd.DataFrame({'上海金 (USD/盎司)': s1_usd, '倫敦金現貨': s2}).sort_index()
    st.line_chart(chart, color=["#E63946", "#004E89"])
