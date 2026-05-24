import streamlit as st
import pandas as pd
import os

# ========== 匯率設定 ==========
USD_CNY_RATE = 7.25  # 可自行修改為即時匯率
OUNCE_TO_GRAM = 31.1035  # 1 盎司 = 31.1035 克

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
    """讀取CSV，清理數字格式"""
    df = pd.read_csv(filepath)

    # 清理欄位名稱（去掉引號和空格）
    df.columns = [col.strip().strip('"') for col in df.columns]

    # 轉換日期
    df['日期'] = pd.to_datetime(df['日期'])

    # 把數字欄位的逗號去掉，轉成float
    for col in ['收市', '開市', '高', '低']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '')
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # 把「升跌（%）」清理成float
    if '升跌（%）' in df.columns:
        df['升跌（%）'] = df['升跌（%）'].astype(str).str.replace('%', '')
        df['升跌（%）'] = pd.to_numeric(df['升跌（%）'], errors='coerce')

    # 按日期排序
    df = df.sort_values('日期').reset_index(drop=True)

    return df


# ========== 載入數據 ==========
DATA_DIR = "data"

# 倫敦金現貨
spot_daily = load_csv(os.path.join(DATA_DIR, "london_gold_daily.csv"))
spot_weekly = load_csv(os.path.join(DATA_DIR, "london_gold_weekly.csv"))
spot_monthly = load_csv(os.path.join(DATA_DIR, "london_gold_monthly.csv"))

# COMEX 期貨
futures_daily = load_csv(os.path.join(DATA_DIR, "comex_futures_daily.csv"))
futures_weekly = load_csv(os.path.join(DATA_DIR, "comex_futures_weekly.csv"))
futures_monthly = load_csv(os.path.join(DATA_DIR, "comex_futures_monthly.csv"))

# 上海金現貨
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

# 現貨
s_d_gain, s_d_gain_date, s_d_loss, s_d_loss_date = find_max_gain_loss(spot_daily)
s_w_gain, s_w_gain_date, s_w_loss, s_w_loss_date = find_max_gain_loss(spot_weekly)
s_m_gain, s_m_gain_date, s_m_loss, s_m_loss_date = find_max_gain_loss(spot_monthly)

# 期貨
f_d_gain, f_d_gain_date, f_d_loss, f_d_loss_date = find_max_gain_loss(futures_daily)
f_w_gain, f_w_gain_date, f_w_loss, f_w_loss_date = find_max_gain_loss(futures_weekly)
f_m_gain, f_m_gain_date, f_m_loss, f_m_loss_date = find_max_gain_loss(futures_monthly)

# 上海金
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


def show_latest_metrics_sge(latest):
    """顯示上海金最新報價（含換算）"""
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
    """顯示最大漲跌幅總覽"""
    st.subheader(f"📊 {label} — 最大漲跌幅總覽")
    cols = st.columns(len(periods))
    for i, (p_label, gain, gain_date, loss, loss_date) in enumerate(periods):
        with cols[i]:
            st.markdown(f"### {p_label}")
            st.metric(label=f"▲ 最大漲幅 ({format_date(gain_date)})", value=f"+{gain:.2f}%")
            st.metric(label=f"▼ 最大跌幅 ({format_date(loss_date)})", value=f"{loss:.2f}%")


def show_data_tabs(data_dict, label, currency="$"):
    """顯示數據分頁（國際金價用）"""
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
                use_container_width=True,
                hide_index=True,
                height=500
            )


def show_data_tabs_sge(data_dict):
    """顯示上海金數據分頁（含美元換算欄位）"""
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

            # 換算成 USD/盎司
            display['收市 (USD/盎司)'] = df['收市'].apply(lambda x: f"${cny_per_gram_to_usd_per_ounce(x):,.2f}")
            display['開市 (USD/盎司)'] = df['開市'].apply(lambda x: f"${cny_per_gram_to_usd_per_ounce(x):,.2f}")
            display['高 (USD/盎司)'] = df['高'].apply(lambda x: f"${cny_per_gram_to_usd_per_ounce(x):,.2f}")
            display['低 (USD/盎司)'] = df['低'].apply(lambda x: f"${cny_per_gram_to_usd_per_ounce(x):,.2f}")

            st.dataframe(
                display[[
                    '日期',
                    '收市 (CNY/克)', '收市 (USD/盎司)',
                    '開市 (CNY/克)', '開市 (USD/盎司)',
                    '高 (CNY/克)', '高 (USD/盎司)',
                    '低 (CNY/克)', '低 (USD/盎司)',
                    '升跌（%）'
                ]],
                use_container_width=True,
                hide_index=True,
                height=500
            )


# ============================================================
# 頁面佈局
# ============================================================

# ============================================================
# 第一部分：最新報價
# ============================================================
st.header("📌 最新報價")

st.markdown("### COMEX 黃金期貨")
futures_latest = futures_daily.iloc[-1]
show_latest_metrics(futures_latest, "COMEX 黃金期貨", "$")

st.markdown("---")

st.markdown("### 倫敦金現貨 (XAU/USD)")
spot_latest = spot_daily.iloc[-1]
show_latest_metrics(spot_latest, "倫敦金現貨", "$")

st.markdown("---")

st.markdown("### 上海金現貨 (Au99.99)")
sge_latest = sge_daily.iloc[-1]
show_latest_metrics_sge(sge_latest)

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
    "COMEX 黃金期貨", "$"
)

st.markdown("---")

show_data_tabs(
    {"日線": spot_daily, "週線": spot_weekly, "月線": spot_monthly},
    "倫敦金現貨 (XAU/USD)", "$"
)

st.markdown("---")

# 上海金（含美元換算）
show_data_tabs_sge(
    {"日線": sge_daily, "週線": sge_weekly}
)

st.markdown("---")

# ============================================================
# 第四部分：走勢圖
# ============================================================
st.header("📈 收市價走勢圖")

# ---- 國際金價：COMEX 期貨 vs 倫敦金現貨（合併圖） ----
st.subheader("COMEX 黃金期貨 vs 倫敦金現貨 (XAU/USD)")

compare_col1, compare_col2, compare_col3 = st.columns(3)

with compare_col1:
    st.markdown("**日線對比**")
    daily_compare = pd.DataFrame({
        'COMEX 期貨': futures_daily.set_index('日期')['收市'],
        '倫敦金現貨': spot_daily.set_index('日期')['收市']
    }).dropna()
    st.line_chart(daily_compare, color=["#FF6B35", "#004E89"])

with compare_col2:
    st.markdown("**週線對比**")
    weekly_compare = pd.DataFrame({
        'COMEX 期貨': futures_weekly.set_index('日期')['收市'],
        '倫敦金現貨': spot_weekly.set_index('日期')['收市']
    }).dropna()
    st.line_chart(weekly_compare, color=["#FF6B35", "#004E89"])

with compare_col3:
    st.markdown("**月線對比**")
    monthly_compare = pd.DataFrame({
        'COMEX 期貨': futures_monthly.set_index('日期')['收市'],
        '倫敦金現貨': spot_monthly.set_index('日期')['收市']
    }).dropna()
    st.line_chart(monthly_compare, color=["#FF6B35", "#004E89"])

st.markdown("---")

# ---- 上海金現貨（獨立圖，含 USD 換算線） ----
st.subheader("上海金現貨 (Au99.99) — 換算為 USD/盎司 對比國際金價")

sge_col1, sge_col2 = st.columns(2)

with sge_col1:
    st.markdown("**日線**")
    sge_daily_chart = pd.DataFrame({
        '上海金 (USD/盎司)': sge_daily.set_index('日期')['收市'].apply(cny_per_gram_to_usd_per_ounce),
        '倫敦金現貨 (USD/盎司)': spot_daily.set_index('日期')['收市']
    }).dropna()
    st.line_chart(sge_daily_chart, color=["#E63946", "#004E89"])

with sge_col2:
    st.markdown("**週線**")
    sge_weekly_chart = pd.DataFrame({
        '上海金 (USD/盎司)': sge_weekly.set_index('日期')['收市'].apply(cny_per_gram_to_usd_per_ounce),
        '倫敦金現貨 (USD/盎司)': spot_weekly.set_index('日期')['收市']
    }).dropna()
    st.line_chart(sge_weekly_chart, color=["#E63946", "#004E89"])
