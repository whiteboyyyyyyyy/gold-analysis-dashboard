import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# 1. 网页配置
st.set_page_config(page_title="全球金价历史波幅看板", layout="wide", page_icon="🏆")

st.title("🏆 全球黄金多周期历史涨幅与风控边界监控")
st.caption("数据源：Yahoo Finance 自动同步 | 覆盖 COMEX 期货 + 伦敦金现货 | 适合每日收盘盘点与团队/投资人共享")

# 2. 数据缓存
@st.cache_data(ttl=3600)
def load_futures_data():
    df = yf.download("GC=F", start="2023-01-01", end="2026-12-31")
    return df

@st.cache_data(ttl=3600)
def load_spot_data():
    df = yf.download("XAUUSD=X", start="2023-01-01", end="2026-12-31")
    return df

# 3. 数据清洗函数：处理 MultiIndex 列
def extract_column(df, field_name):
    """
    从 MultiIndex 列中提取指定字段的 Series。
    field_name 例如: 'Close', 'High', 'Low', 'Open', 'Volume'
    """
    if isinstance(df.columns, pd.MultiIndex):
        # 列结构: [('Close', 'GC=F'), ('High', 'GC=F'), ...]
        # 直接取第一层的 field_name
        return df.xs(field_name, level=0, axis=1)
    else:
        # 兼容单层列的情况
        return df[field_name]

try:
    with st.spinner("正在从国际交易所同步最新历史数据..."):
        futures_raw = load_futures_data()
        spot_raw = load_spot_data()

    if futures_raw.empty and spot_raw.empty:
        st.error("数据源返回空数据，请检查网络或稍后刷新重试。")
    else:
        # ---- 提取关键字段 ----
        futures_close = extract_column(futures_raw, 'Close')
        spot_close = extract_column(spot_raw, 'Close')

        # ---- 获取最新价 ----
        futures_latest = float(futures_close.iloc[-1])
        futures_prev = float(futures_close.iloc[-2])
        futures_change = (futures_latest - futures_prev) / futures_prev * 100

        spot_latest = float(spot_close.iloc[-1])
        spot_prev = float(spot_close.iloc[-2])
        spot_change = (spot_latest - spot_prev) / spot_prev * 100

        latest_date = futures_close.index[-1].strftime('%Y-%m-%d')

        # ========== 顶部实时报价卡片 ==========
        st.subheader("📌 实时报价概览")
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                label="COMEX 黄金期货 (GC=F)",
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
        # 构建分析专用 DataFrame
        analysis_df = pd.DataFrame(index=futures_close.index)
        analysis_df['close'] = futures_close

        analysis_df['daily_gain'] = analysis_df['close'].pct_change(1)
        analysis_df['weekly_gain'] = analysis_df['close'].pct_change(5)
        analysis_df['monthly_gain'] = analysis_df['close'].pct_change(21)
        analysis_df['quarterly_gain'] = analysis_df['close'].pct_change(63)
        analysis_df['annual_gain'] = analysis_df['close'].pct_change(252)
        analysis_df['year'] = analysis_df.index.year

        # ---- 过去1周最大日内涨幅 ----
        last_week_data = analysis_df.tail(5)
        max_daily_in_week = last_week_data['daily_gain'].max()
        max_daily_in_week_str = f"{max_daily_in_week * 100:+.2f}%" if pd.notna(max_daily_in_week) else "N/A"

        # ---- 按年份分组，提取各周期最大涨幅 ----
        summary = analysis_df.groupby('year').agg({
            'daily_gain': 'max',
            'weekly_gain': 'max',
            'monthly_gain': 'max',
            'quarterly_gain': 'max',
            'annual_gain': 'max'
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

        # ========== 辅助可视化 ==========
        st.subheader("📈 黄金价格历史走势图 (2024 - 2026)")

        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            st.markdown("**COMEX 黄金期货**")
            chart_futures = analysis_df.loc[analysis_df.index.year >= 2024, 'close']
            st.line_chart(chart_futures)

        with col_chart2:
            st.markdown("**伦敦金现货**")
            chart_spot = spot_close.loc[spot_close.index.year >= 2024]
            st.line_chart(chart_spot)

        st.info(
            "💡 系统提示：\n"
            "- 周/月/季度涨幅均采用量化滚动窗口（Rolling Window）算法，能完美捕获跨自然月、跨自然周的极端爆发性动量。\n"
            "- 历史涨幅矩阵基于 COMEX 期货主力合约计算，可作为风控回撤的量化基准参考。"
        )

except Exception as e:
    st.error(f"系统运行或计算异常: {e}")
