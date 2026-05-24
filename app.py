import streamlit as st
import pandas as pd
import os

# ========== 網頁配置 ==========
st.set_page_config(page_title="倫敦金現貨歷史數據看板", layout="wide", page_icon="🥇")

st.title("🥇 倫敦金現貨 (XAU/USD) 歷史數據看板")
st.caption("數據範圍：2020–2026 | 資料來源：歷史CSV數據")

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

daily_df = load_csv(os.path.join(DATA_DIR, "london_gold_daily.csv"))
weekly_df = load_csv(os.path.join(DATA_DIR, "london_gold_weekly.csv"))
monthly_df = load_csv(os.path.join(DATA_DIR, "london_gold_monthly.csv"))


# ========== 找最大漲跌幅 ==========
def find_max_gain_loss(df):
    """找出最大漲幅和最大跌幅"""
    gain_row = df.loc[df['升跌（%）'].idxmax()]
    loss_row = df.loc[df['升跌（%）'].idxmin()]
    return (
        gain_row['升跌（%）'], gain_row['日期'],
        loss_row['升跌（%）'], loss_row['日期']
    )

daily_max_gain, daily_gain_date, daily_max_loss, daily_loss_date = find_max_gain_loss(daily_df)
weekly_max_gain, weekly_gain_date, weekly_max_loss, weekly_loss_date = find_max_gain_loss(weekly_df)
monthly_max_gain, monthly_gain_date, monthly_max_loss, monthly_loss_date = find_max_gain_loss(monthly_df)


# ========== 最新報價 ==========
latest = daily_df.iloc[-1]
latest_date = latest['日期'].strftime('%Y-%m-%d')
latest_close = latest['收市']
latest_change = latest['升跌（%）']


# ========== 頂部：最新報價 ==========
st.subheader("📌 最新報價")

col_date, col_close, col_change = st.columns(3)
with col_date:
    st.metric(label="最新交易日", value=latest_date)
with col_close:
    st.metric(label="倫敦金現貨收市價 (USD)", value=f"${latest_close:,.2f}")
with col_change:
    st.metric(label="當日漲跌幅", value=f"{latest_change:+.2f}%")

st.markdown("---")


# ========== 頂部：三週期最大漲跌幅總覽 ==========
st.subheader("📊 三週期最大漲跌幅總覽（2020–2026）")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 日線")
    st.metric(
        label=f"▲ 最大單日漲幅 ({daily_gain_date.strftime('%Y-%m-%d')})",
        value=f"+{daily_max_gain:.2f}%"
    )
    st.metric(
        label=f"▼ 最大單日跌幅 ({daily_loss_date.strftime('%Y-%m-%d')})",
        value=f"{daily_max_loss:.2f}%"
    )

with col2:
    st.markdown("### 週線")
    st.metric(
        label=f"▲ 最大單週漲幅 ({weekly_gain_date.strftime('%Y-%m-%d')})",
        value=f"+{weekly_max_gain:.2f}%"
    )
    st.metric(
        label=f"▼ 最大單週跌幅 ({weekly_loss_date.strftime('%Y-%m-%d')})",
        value=f"{weekly_max_loss:.2f}%"
    )

with col3:
    st.markdown("### 月線")
    st.metric(
        label=f"▲ 最大單月漲幅 ({monthly_gain_date.strftime('%Y-%m-%d')})",
        value=f"+{monthly_max_gain:.2f}%"
    )
    st.metric(
        label=f"▼ 最大單月跌幅 ({monthly_loss_date.strftime('%Y-%m-%d')})",
        value=f"{monthly_max_loss:.2f}%"
    )

st.markdown("---")


# ========== 完整數據表（三個分頁） ==========
st.subheader("📋 完整歷史數據")

tab1, tab2, tab3 = st.tabs(["📅 日線數據", "📅 週線數據", "📅 月線數據"])

with tab1:
    st.caption(f"共 {len(daily_df)} 筆資料")
    display_daily = daily_df.copy()
    display_daily['日期'] = display_daily['日期'].dt.strftime('%Y-%m-%d')
    display_daily['升跌（%）'] = display_daily['升跌（%）'].apply(lambda x: f"{x:+.2f}%")
    display_daily['收市'] = display_daily['收市'].apply(lambda x: f"${x:,.2f}")
    display_daily['開市'] = display_daily['開市'].apply(lambda x: f"${x:,.2f}")
    display_daily['高'] = display_daily['高'].apply(lambda x: f"${x:,.2f}")
    display_daily['低'] = display_daily['低'].apply(lambda x: f"${x:,.2f}")
    st.dataframe(
        display_daily[['日期', '收市', '開市', '高', '低', '升跌（%）']],
        use_container_width=True,
        hide_index=True,
        height=500
    )

with tab2:
    st.caption(f"共 {len(weekly_df)} 筆資料")
    display_weekly = weekly_df.copy()
    display_weekly['日期'] = display_weekly['日期'].dt.strftime('%Y-%m-%d')
    display_weekly['升跌（%）'] = display_weekly['升跌（%）'].apply(lambda x: f"{x:+.2f}%")
    display_weekly['收市'] = display_weekly['收市'].apply(lambda x: f"${x:,.2f}")
    display_weekly['開市'] = display_weekly['開市'].apply(lambda x: f"${x:,.2f}")
    display_weekly['高'] = display_weekly['高'].apply(lambda x: f"${x:,.2f}")
    display_weekly['低'] = display_weekly['低'].apply(lambda x: f"${x:,.2f}")
    st.dataframe(
        display_weekly[['日期', '收市', '開市', '高', '低', '升跌（%）']],
        use_container_width=True,
        hide_index=True,
        height=500
    )

with tab3:
    st.caption(f"共 {len(monthly_df)} 筆資料")
    display_monthly = monthly_df.copy()
    display_monthly['日期'] = display_monthly['日期'].dt.strftime('%Y-%m-%d')
    display_monthly['升跌（%）'] = display_monthly['升跌（%）'].apply(lambda x: f"{x:+.2f}%")
    display_monthly['收市'] = display_monthly['收市'].apply(lambda x: f"${x:,.2f}")
    display_monthly['開市'] = display_monthly['開市'].apply(lambda x: f"${x:,.2f}")
    display_monthly['高'] = display_monthly['高'].apply(lambda x: f"${x:,.2f}")
    display_monthly['低'] = display_monthly['低'].apply(lambda x: f"${x:,.2f}")
    st.dataframe(
        display_monthly[['日期', '收市', '開市', '高', '低', '升跌（%）']],
        use_container_width=True,
        hide_index=True,
        height=500
    )

st.markdown("---")


# ========== 走勢圖 ==========
st.subheader("📈 收市價走勢圖")

chart_col1, chart_col2, chart_col3 = st.columns(3)

with chart_col1:
    st.markdown("**日線**")
    st.line_chart(daily_df.set_index('日期')['收市'])

with chart_col2:
    st.markdown("**週線**")
    st.line_chart(weekly_df.set_index('日期')['收市'])

with chart_col3:
    st.markdown("**月線**")
    st.line_chart(monthly_df.set_index('日期')['收市'])
