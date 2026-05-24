import streamlit as st
import pandas as pd
import os

# ========== 網頁配置 ==========
st.set_page_config(page_title="黃金歷史數據看板", layout="wide", page_icon="🥇")

st.title("🥇 黃金歷史數據看板")
st.caption("COMEX 黃金期貨 + 倫敦金現貨 (XAU/USD) + 上海金現貨 (Au99.99)")

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


def show_max_gain_loss_section(label, periods):
    """
    顯示三週期最大漲跌幅
    periods = [(label, gain, gain_date, loss, loss_date), ...]
    """
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


def show_data_tabs(data_dict, label, currency="$"):
    """顯示數據分頁
    data_dict = {"日線": df, "週線": df, "月線": df}
    """
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


def show_charts(data_dict, label):
    """顯示走勢圖"""
    st.subheader(f"📈 {label} — 收市價走勢圖")

    cols = st.columns(len(data_dict))

    for i, (period_name, df) in enumerate(data_dict.items()):
        with cols[i]:
            st.markdown(f"**{period_name}**")
            st.line_chart(df.set_index('日期')['收市'])


# ========== 頁面佈局 ==========

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
show_latest_metrics(sge_latest, "上海金現貨", "¥")

st.markdown("---")

# ============================================================
# 第二部分：最大漲跌幅總覽
# ============================================================
st.header("📊 最大漲跌幅總覽")

# COMEX 期貨
show_max_gain_loss_section("COMEX 黃金期貨", [
    ("日線", f_d_gain, f_d_gain_date, f_d_loss, f_d_loss_date),
    ("週線", f_w_gain, f_w_gain_date, f_w_loss, f_w_loss_date),
    ("月線", f_m_gain, f_m_gain_date, f_m_loss, f_m_loss_date),
])

st.markdown("---")

# 倫敦金現貨
show_max_gain_loss_section("倫敦金現貨 (XAU/USD)", [
    ("日線", s_d_gain, s_d_gain_date, s_d_loss, s_d_loss_date),
    ("週線", s_w_gain, s_w_gain_date, s_w_loss, s_w_loss_date),
    ("月線", s_m_gain, s_m_gain_date, s_m_loss, s_m_loss_date),
])

st.markdown("---")

# 上海金現貨
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

show_data_tabs(
    {"日線": sge_daily, "週線": sge_weekly},
    "上海金現貨 (Au99.99)", "¥"
)

st.markdown("---")

# ============================================================
# 第四部分：走勢圖
# ============================================================
st.header("📈 收市價走勢圖")

show_charts(
    {"日線": futures_daily, "週線": futures_weekly, "月線": futures_monthly},
    "COMEX 黃金期貨"
)

st.markdown("---")

show_charts(
    {"日線": spot_daily, "週線": spot_weekly, "月線": spot_monthly},
    "倫敦金現貨 (XAU/USD)"
)

st.markdown("---")

show_charts(
    {"日線": sge_daily, "週線": sge_weekly},
    "上海金現貨 (Au99.99)"
)
