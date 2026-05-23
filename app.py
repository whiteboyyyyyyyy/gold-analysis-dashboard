import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# 1. 网页配置：设置为宽屏模式
st.set_page_config(page_title="全球金价历史波幅看板", layout="wide", page_icon="🏆")

st.title("🏆 全球黄金多周期历史涨幅与风控边界监控")
st.caption("数据源：Yahoo Finance 自动同步 | 覆盖 COMEX 期货 + 伦敦金现货 | 适合每日收盘盘点与团队/投资人共享")

# 2. 数据缓存机制：1小时内重复访问直接读内存，防止触发接口限频，完全免费

# ---- 国际期货：COMEX 黄金 ----
@st.cache_data(ttl=3600)
def load_futures_data():
    df = yf.download("GC=F", start="2023-01-01", end="2026-12-31")
    return df

# ---- 国际现货：伦敦金 ----
@st.cache_data(ttl=3600)
def load_spot_data():
    df = yf.download("XAUUSD=X", start="2023-01-01", end="2026-12-31")
    return df

try:
    with st.spinner("正在从国际交易所同步最新历史数据..."):
        futures_raw = load_futures_data()
        spot_raw = load_spot_data()

    if futures_raw.empty and spot_raw.empty:
        st.error("数据源返回空数据，请检查网络或稍后刷新重试。")
    else:
        # ---- 清洗期货数据 ----
        futures_df = futures_raw.copy()
        futures_df.index = pd.to_datetime(futures_df.index)

        # ---- 清洗现货数据 ----
        spot_df = spot_raw.copy()
        spot_df.index = pd.to_datetime(spot_df.index)

        # ---- 提取最新价与涨跌幅 ----
        # COMEX 期货
        futures_latest = float(futures_df['Close'].iloc[-1])
        futures_prev = float(futures_df['Close'].iloc[-2])
        futures_change = (futures_latest - futures_prev) / futures_prev * 100

        # 伦敦金现货
        spot_latest = float(spot_df['Close'].iloc[-1])
        spot_prev = float(spot_df['Close'].iloc[-2])
        spot_change = (spot_latest - spot_prev) / spot_prev * 100

        latest_date = futures_df.index[-1].strftime('%Y-%m-%d')

        # ========== 顶部核心指标卡片 ==========
        st.subheader("📌 实时报价概览")
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                label="COMEX 黄金期货 (主力合约 GC=F)",
                value=f"${futures_latest:,.2f}",
                delta=f"{futures_change:+.2f}% (当日)"
            )
        with col2:
            st.metric(
                label="伦敦金现货 (XAU/USD)",
                value=f"${spot_latest:,.2f}",
                delta=f"{spot_change:+.2f}% (当日)"
            )

        st.caption(f"数据最新同步交易日 (UTC): {latest_date}")
        st.markdown("---")

        # ========== 核心量化算法（基于 COMEX 期货） ==========
        futures_df['Daily_Gain'] = futures_df['Close'].pct_change(1)
        futures_df['Weekly_Gain'] = futures_df['Close'].pct_change(5)
        futures_df['Monthly_Gain'] = futures_df['Close'].pct_change(21)
        futures_df['Quarterly_Gain'] = futures_df['Close'].pct_change(63)
        futures_df['Annual_Gain'] = futures_df['Close'].pct_change(252)
        futures_df['Year'] = futures_df.index.year

        # ---- 过去1周最大日内涨幅 ----
        last_week_data = futures_df.tail(5)
        max_daily_in_week = last_week_data['Daily_Gain'].max()
        max_daily_in_week_str = f"{max_daily_in_week * 100:+.2f}%" if pd.notna(max_daily_in_week) else "N/A"

        # ---- 按年份分组，提取各周期最大涨幅 ----
        summary = futures_df.groupby('Year').agg({
            'Daily_Gain': 'max',
            'Weekly_Gain': 'max',
            'Monthly_Gain': 'max',
            'Quarterly_Gain': 'max',
            'Annual_Gain': 'max'
        })

        summary_pct = (summary * 100).round(2)
        display_df = summary_pct.loc[summary_pct.index >= 2024].copy()

        for col in display_df.columns:
            display_df[col] = display_df[col].astype(str) + '%'

        display_df.columns = [
            '日最大涨幅',
            '周最大涨幅 (5日滚动)',
            '月最大涨幅 (21日滚动)',
            '季最大涨幅 (63日滚动)',
            '年内累计最大涨幅'
        ]
        display_df.index.name = '年份/历史区间'

        # ========== 历史极端波幅矩阵 ==========
        st.subheader("📊 历史年份多周期最大涨幅统计矩阵 (风控基准 · 基于COMEX期货)")
        st.table(display_df)

        # ---- 过去1周最大日内涨幅高亮 ----
        st.metric(
            label="⚡ 过去1周 (最近5个交易日) 最大单日涨幅",
            value=max_daily_in_week_str
        )

        # ========== 辅助可视化：历史走势图 ==========
        st.subheader("📈 黄金价格历史走势图 (2024 - 2026)")

        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            st.markdown("**COMEX 黄金期货**")
            chart_futures = futures_df.loc[futures_df.index.year >= 2024, 'Close']
            st.line_chart(chart_futures)

        with col_chart2:
            st.markdown("**伦敦金现货**")
            chart_spot = spot_df.loc[spot_df.index.year >= 2024, 'Close']
            st.line_chart(chart_spot)

        st.info(
            "💡 系统提示：\n"
            "- 周/月/季度涨幅均采用量化滚动窗口（Rolling Window）算法，能完美捕获跨自然月、跨自然周的极端爆发性动量。\n"
            "- 历史涨幅矩阵基于 COMEX 期货主力合约计算，可作为风控回撤的量化基准参考。"
        )

except Exception as e:
    st.error(f"系统运行或计算异常: {e}")
