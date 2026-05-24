import streamlit as st
import pandas as pd
import os

# ========== 匯率設定 ==========
USD_CNY_RATE = 7.25
OUNCE_TO_GRAM = 31.1035

def cny_per_gram_to_usd_per_ounce(price_cny):
    """人民幣/克 → 美元/盎司"""
    return (price_cny * OUNCE_TO_GRAM) / USD_CNY_RATE

# ========== 網頁配置 ==========
st.set_page_config(page_title="黃金歷史數據看板", layout="wide", page_icon="🥇")

st.title("🥇 黃金歷史數據看板")
st.caption(f"COMEX 黃金期貨 + 倫敦金現貨 (XAU/USD) + 上海金現貨 (Au99.99) | 匯率: USD/CNY = {USD_CNY_RATE}")

# ========== 讀取CSV函數 ==========
@st.cache_data
def load_csv(filepath):
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
    df = df.sort_values('日期').reset_index(drop=True)
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
    gain_row = df.loc[df['升跌（%）'].idxmax()]
    loss_row = df.loc[df['升跌（%）'].idxmin()]
    return (gain_row['升跌（%）'], gain_row['日期'], loss_row['升跌（%）'], loss_row['日期'])

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
    col_date, col_close, col_change = st.columns(3)
    with col_date:
        st.metric(label=f"{label} 最新交易日", value=format_date(latest['日期']))
    with col_close:
        st.metric(label=f"{label} 收市價", value=f"{currency}{latest['收市']:,.2f}")
    with col_change:
        st.metric(label=f"{label} 當日漲跌幅", value=f"{latest['升跌（%）']:+.2f}%")

def show_latest_metrics_sge(latest):
    col_date, col_close_cny, col_close_usd, col_change = st.columns(4)
    usd_price = cny_per_gram_to_usd_per_ounce(latest['收市'])
    with col_date:
        st.metric(label="上海金現貨 最新交易日", value=format_date(latest['日期']))
    with col_close_cny:
        st.metric(label="收市價 (CNY/克)", value=f"¥{latest['收市']:,.2f}")
    with col_close_usd:
        st.metric(label="換算 (USD/盎司)", value=f"${usd_price:,.2f}")
    with col_change:
        st.metric(label="當日漲跌幅", value=f"{latest['升跌（%）']:+.2f}%")

def show_max_gain_loss_section(label, periods):
    st.subheader(f"📊 {label} — 最大漲跌幅總覽")
    cols = st.columns(len(periods))
    for i, (p_label, gain, gain_date, loss, loss_date) in enumerate(periods):
        with cols[i]:
            st.markdown(f"### {p_label}")
            st.metric(label=f"▲ 最大漲幅 ({format_date(gain_date)})", value=f"+{gain:.2f}%")
            st.metric(label=f"▼ 最大跌幅 ({format_date(loss_date)})", value=f"{loss:.2f}%")

def show_data_tabs(data_dict, label, currency="$"):
    st.subheader(f"📋 {label} — 完整歷史數據")
    tab_labels = list(data_dict.keys())
    tabs = st.tabs([f"📅 {t}" for t in tab_labels])
    for tab, (period_name, df) in zip(tabs, data_dict.items()):
        with tab:
            st.caption(f"{label} {period_name} — 共 {len(df)} 筆資料")
            display = df.copy()
            display['日期'] = display['日期'].dt.strftime('%Y-%m-%d')
            display['升跌（%）'] = display['升跌（%）'].apply(lambda x: f"{x:+.2f}%")
            display['收市'] = display['收市'].apply(lambda x: f"{currency}{x:,.2f}")
            display['開市'] = display['開市'].apply(lambda x: f"{currency}{x:,.2f}")
            display['高'] = display['高'].apply(lambda x: f"{currency}{x:,.2f}")
            display['低'] = display['低'].apply(lambda x: f"{currency}{x:,.2f}")
            st.dataframe(
                display[['日期', '收市', '開市', '高', '低', '升跌（%）']],
                use_container_width=True, hide_index=True, height=500
            )

def show_data_tabs_sge(data_dict):
    st.subheader("📋 上海金現貨 (Au99.99) — 完整歷史數據")
    tab_labels = list(data_dict.keys())
    tabs = st.tabs([f"📅 {t}" for t in tab_labels])
    for tab, (period_name, df) in zip(tabs, data_dict.items()):
        with tab:
            st.caption(f"上海金現貨 {period_name} — 共 {len(df)} 筆資料 | 換算匯率: USD/CNY = {USD_CNY_RATE}")
            display = df.copy()
            display['日期'] = display['日期'].dt.strftime('%Y-%m-%d')
            display['升跌（%）'] = display['升跌（%）'].apply(lambda x: f"{x:+.2f}%")
            display['收市 (CNY/克)'] = display['收市'].apply(lambda x: f"¥{x:,.2f}")
            display['開市 (CNY/克)'] = display['開市'].apply(lambda x: f"¥{x:,.2f}")
            display['高 (CNY/克)'] = display['高'].apply(lambda x: f"¥{x:,.2f}")
            display['低 (CNY/克)'] = display['低'].apply(lambda x: f"¥{x:,.2f}")
            display['收市 (USD/盎司)'] = df['收市'].apply(lambda x: f"${cny_per_gram_to_usd_per_ounce(x):,.2f}")
            display['開市 (USD/盎司)'] = df['開市'].apply(lambda x: f"${cny_per_gram_to_usd_per_ounce(x):,.2f}")
            display['高 (USD/盎司)'] = df['高'].apply(lambda x: f"${cny_per_gram_to_usd_per_ounce(x):,.2f}")
            display['低 (USD/盎司)'] = df['低'].apply(lambda x: f"${cny_per_gram_to_usd_per_ounce(x):,.2f}")
            st.dataframe(
                display[['日期', '收市 (CNY/克)', '收市 (USD/盎司)', '開市 (CNY/克)', '開市 (USD/盎司)', '高 (CNY/克)', '高 (USD/盎司)', '低 (CNY/克)', '低 (USD/盎司)', '升跌（%）']],
                use_container_width=True, hide_index=True, height=500
            )

def merge_chart_data(df1, df2, label1, label2):
    """
    安全合併兩個 DataFrame 的收市價，保留各自日期，用 outer join
    """
    s1 = df1.set_index('日期')['收市']
    s2 = df2.set_index('日期')['收市']
    result = pd.DataFrame({label1: s1, label2: s2}).sort_index()
    # 不過濾掉 NaN，各自畫各自的線段
    return result


# ============================================================
# 頁面佈局
# ============================================================

# ============================================================
# 第一部分：最新報價
# ============================================================
st.header("📌 最新報價")

st.markdown("### COMEX 黃金期貨")
show_latest_metrics(futures_daily.iloc[-1], "COMEX 黃金期貨", "$")

st.markdown("---")

st.markdown("### 倫敦金現貨 (XAU/USD)")
show_latest_metrics(spot_daily.iloc[-1], "倫敦金現貨", "$")

st.markdown("---")

st.markdown("### 上海金現貨 (Au99.99)")
show_latest_metrics_sge(sge_daily.iloc[-1])

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

show_data_tabs({"日線": futures_daily, "週線": futures_weekly, "月線": futures_monthly}, "COMEX 黃金期貨", "$")
st.markdown("---")

show_data_tabs({"日線": spot_daily, "週線": spot_weekly, "月線": spot_monthly}, "倫敦金現貨 (XAU/USD)", "$")
st.markdown("---")

show_data_tabs_sge({"日線": sge_daily, "週線": sge_weekly})
st.markdown("---")

# ============================================================
# 第四部分：走勢圖
# ============================================================
st.header("📈 收市價走勢圖")

# ---- COMEX vs 倫敦金 ----
st.subheader("COMEX 黃金期貨 vs 倫敦金現貨 (XAU/USD)")
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("**日線對比**")
    st.line_chart(merge_chart_data(futures_daily, spot_daily, 'COMEX 期貨', '倫敦金現貨'), color=["#FF6B35", "#004E89"])
with c2:
    st.markdown("**週線對比**")
    st.line_chart(merge_chart_data(futures_weekly, spot_weekly, 'COMEX 期貨', '倫敦金現貨'), color=["#FF6B35", "#004E89"])
with c3:
    st.markdown("**月線對比**")
    st.line_chart(merge_chart_data(futures_monthly, spot_monthly, 'COMEX 期貨', '倫敦金現貨'), color=["#FF6B35", "#004E89"])

st.markdown("---")

# ---- 上海金(換算USD) vs 倫敦金 ----
st.subheader("上海金現貨 (換算 USD/盎司) vs 倫敦金現貨")
# 建立上海金 USD 換算 Series
sge_daily_usd = sge_daily.copy()
sge_daily_usd['收市_USD'] = sge_daily_usd['收市'].apply(cny_per_gram_to_usd_per_ounce)
sge_weekly_usd = sge_weekly.copy()
sge_weekly_usd['收市_USD'] = sge_weekly_usd['收市'].apply(cny_per_gram_to_usd_per_ounce)

d1, d2 = st.columns(2)
with d1:
    st.markdown("**日線對比**")
    # 合併
    daily_sge_vs_spot = pd.DataFrame({
        '上海金 (USD/盎司)': sge_daily_usd.set_index('日期')['收市_USD'],
        '倫敦金現貨 (USD/盎司)': spot_daily.set_index('日期')['收市']
    }).sort_index()
    st.line_chart(daily_sge_vs_spot, color=["#E63946", "#004E89"])

with d2:
    st.markdown("**週線對比**")
    weekly_sge_vs_spot = pd.DataFrame({
        '上海金 (USD/盎司)': sge_weekly_usd.set_index('日期')['收市_USD'],
        '倫敦金現貨 (USD/盎司)': spot_weekly.set_index('日期')['收市']
    }).sort_index()
    st.line_chart(weekly_sge_vs_spot, color=["#E63946", "#004E89"])

st.markdown("---")

# ============================================================
# 第五部分：交易時段（香港時間）
# ============================================================
st.header("🕐 交易時段（香港時間）")

col_a, col_b, col_c = st.columns(3)

with col_a:
    st.markdown("### 倫敦金現貨 (XAU/USD)")
    st.markdown("""
    | 時段 | 香港時間 |
    |:---|:---|
    | 夏令時間 | 星期一 06:00 – 星期六 05:00 [citation:5][citation:10] |
    | 冬令時間 | 星期一 07:00 – 星期六 06:00 [citation:5][citation:10] |
    | 每日休市 | 05:00–06:00（夏令）或 06:00–07:00（冬令）[citation:8] |
    """)

with col_b:
    st.markdown("### COMEX 黃金期貨 (GC)")
    st.markdown("""
    | 時段 | 香港時間 |
    |:---|:---|
    | 夏令時間 | 星期一 06:00 – 星期六 05:00 [citation:3][citation:6] |
    | 冬令時間 | 星期一 07:00 – 星期六 06:00 [citation:3][citation:6] |
    | 每日休市 | 05:00–06:00（夏令）或 06:00–07:00（冬令）[citation:6] |
    """)

with col_c:
    st.markdown("### 上海金現貨 (Au99.99)")
    st.markdown("""
    | 時段 | 香港時間 |
    |:---|:---|
    | 早盤 | 09:00 – 11:30 [citation:1] |
    | 午盤 | 13:30 – 15:30 [citation:1] |
    | 夜盤 | 20:00 – 02:30（翌日凌晨）[citation:1] |
    """)
