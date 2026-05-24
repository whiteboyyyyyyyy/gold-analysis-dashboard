import streamlit as st
import pandas as pd
import os

# ========== 網頁配置 ==========
st.set_page_config(page_title="黃金歷史數據看板", layout="wide", page_icon="🥇")

st.title("🥇 黃金歷史數據看板")
st.caption("數據範圍：2020–2026 | COMEX 黃金期貨 + 倫敦金現貨 (XAU/USD)")

# ========== 讀取CSV函數 ==========
@st.cache_data
def load_csv(filepath):
    """讀取CSV，清理數字格式"""
    df = pd.read_csv(filepath)

    # 清理欄位名稱（去掉引號和空格）
    df.columns = [col.strip().strip('"') for col in df.columns]

    # 轉換日期
    df['日期'] = pd.to_datetime(df['日期'])

    # 把「收市」等數字欄位的逗號去掉，轉成float
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


# ========== 找最大漲跌幅 ==========
def find_max_gain_loss(df, label_col='日期'):
    """找出最大漲幅和最大跌幅"""
    gain_row = df.loc[df['升跌（%）'].idxmax()]
    loss_row = df.loc[df['升跌（%）'].idxmin()]
    return (
        gain_row['升跌（%）'], gain_row[label_col],
        loss_row['升跌（%）'], loss_row[label_col]
    )

# 現貨
s_d_gain, s_d_gain_date, s_d_loss, s_d_loss_date = find_max_gain_loss(spot_daily)
s_w_gain, s_w_gain_date, s_w_loss, s_w_loss_date = find_max_gain_loss(spot_weekly)
s_m_gain, s_m_gain_date, s_m_loss, s_m_loss_date = find_max_gain_loss(spot_monthly)

# 期貨
f_d_gain, f_d_gain_date, f_d_loss, f_d_loss_date = find_max_gain_loss(futures_daily)
f_w_gain, f_w_gain_date, f_w_loss, f_w_loss_date = find_max_gain_loss(futures_weekly)
f_m_gain, f_m_gain_date, f_m_loss, f_m_loss_date = find_max_gain_loss(futures_monthly)


# ========== 最新報價 ==========
spot_latest = spot_daily.iloc[-1]
futures_latest = futures_daily.iloc[-1]

# ========== 顯示最新報價用的輔助函數 ==========
def format_date(d):
    return d.strftime('%Y-%m-%d')

def show_latest_metrics(latest, label):
    """顯示最新報價的三個 metric"""
    col_date, col_close, col_change = st.columns(3)
    with col_date:
        st.metric(label=f"{label} 最新交易日", value=format_date(latest['日期']))
    with col_close:
        st.metric(label=f"{label} 收市價 (USD)", value=f"${latest['收市']:,.2f}")
    with col_change:
        st.metric(label=f"{label} 當日漲跌幅", value=f"{latest['升跌（%）']:+.2f}%")


# ========== 顯示最大漲跌幅用的輔助函數 ==========
def show_max_gain_loss(label, d_gain, d_gain_date, d_loss, d_loss_date,
                       w_gain, w_gain_date, w_loss, w_loss_date,
                       m_gain, m_gain_date, m_loss, m_loss_date):
    """顯示三週期最大漲跌幅"""
    st.subheader(f"📊 {label} — 三週期最大漲跌幅總覽（2020–2026）")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 日線")
        st.metric(
            label=f"▲ 最大單日漲幅 ({format_date(d_gain_date)})",
            value=f"+{d_gain:.2f}%"
        )
        st.metric(
            label=f"▼ 最大單日跌幅 ({format_date(d_loss_date)})",
            value=f"{d_loss:.2f}%"
        )

    with col2:
        st.markdown("### 週線")
        st.metric(
            label=f"▲ 最大單週漲幅 ({format_date(w_gain_date)})",
            value=f"+{w_gain:.2f}%"
        )
        st.metric(
            label=f"▼ 最大單週跌幅 ({format_date(w_loss_date)})",
            value=f"{w_loss:.2f}%"
        )

    with col3:
        st.markdown("### 月線")
        st.metric(
            label=f"▲ 最大單月漲幅 ({format_date(m_gain_date)})",
            value=f"+{m_gain:.2f}%"
        )
        st.metric(
            label=f"▼ 最大單月跌幅 ({format_date(m_loss_date)})",
            value=f"{m_loss:.2f}%"
        )


# ========== 顯示數據表用的輔助函數 ==========
def show_data_tabs(daily_df, weekly_df, monthly_df, label):
    """顯示日/週/月數據分頁"""
    st.subheader(f"📋 {label} — 完整歷史數據")

    tab1, tab2, tab3 = st.tabs(["📅 日線數據", "📅 週線數據", "📅 月線數據"])

    for tab, df, period_name in [
        (tab1, daily_df, "日線"),
        (tab2, weekly_df, "週線"),
        (tab3, monthly_df, "月線")
    ]:
        with tab:
            st.caption(f"{label} {period_name} — 共 {len(df)} 筆資料")
            display = df.copy()
            display['日期'] = display['日期'].dt.strftime('%Y-%m-%d')
            display['升跌（%）'] = display['升跌（%）'].apply(lambda x: f"{x:+.2f}%")
            display['收市'] = display['收市'].apply(lambda x: f"${x:,.2f}")
            display['開市'] = display['開市'].apply(lambda x: f"${x:,.2f}")
            display['高'] = display['高'].apply(lambda x: f"${x:,.2f}")
            display['低'] = display['低'].apply(lambda x: f"${x:,.2f}")
            st.dataframe(
                display[['日期', '收市', '開市', '高', '低', '升跌（%）']],
                use_container_width=True,
                hide_index=True,
                height=500
            )


# ========== 顯示走勢圖用的輔助函數 ==========
def show_charts(daily_df, weekly_df, monthly_df, label):
    """顯示三個週期的走勢圖"""
    st.subheader(f"📈 {label} — 收市價走勢圖")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**日線**")
        st.line_chart(daily_df.set_index('日期')['收市'])

    with col2:
        st.markdown("**週線**")
        st.line_chart(weekly_df.set_index('日期')['收市'])

    with col3:
        st.markdown("**月線**")
        st.line_chart(monthly_df.set_index('日期')['收市'])


# ========== 頁面佈局 ==========

# ---- 最新報價 ----
st.subheader("📌 最新報價")
show_latest_metrics(futures_latest, "COMEX 黃金期貨")
st.markdown("---")
show_latest_metrics(spot_latest, "倫敦金現貨")

st.markdown("---")

# ---- COMEX 期貨 最大漲跌幅 ----
show_max_gain_loss(
    "COMEX 黃金期貨",
    f_d_gain, f_d_gain_date, f_d_loss, f_d_loss_date,
    f_w_gain, f_w_gain_date, f_w_loss, f_w_loss_date,
    f_m_gain, f_m_gain_date, f_m_loss, f_m_loss_date
)

st.markdown("---")

# ---- 倫敦金現貨 最大漲跌幅 ----
show_max_gain_loss(
    "倫敦金現貨 (XAU/USD)",
    s_d_gain, s_d_gain_date, s_d_loss, s_d_loss_date,
    s_w_gain, s_w_gain_date, s_w_loss, s_w_loss_date,
    s_m_gain, s_m_gain_date, s_m_loss, s_m_loss_date
)

st.markdown("---")

# ---- COMEX 期貨 數據表 ----
show_data_tabs(futures_daily, futures_weekly, futures_monthly, "COMEX 黃金期貨")

st.markdown("---")

# ---- 倫敦金現貨 數據表 ----
show_data_tabs(spot_daily, spot_weekly, spot_monthly, "倫敦金現貨 (XAU/USD)")

st.markdown("---")

# ---- COMEX 期貨 走勢圖 ----
show_charts(futures_daily, futures_weekly, futures_monthly, "COMEX 黃金期貨")

st.markdown("---")

# ---- 倫敦金現貨 走勢圖 ----
show_charts(spot_daily, spot_weekly, spot_monthly, "倫敦金現貨 (XAU/USD)")
