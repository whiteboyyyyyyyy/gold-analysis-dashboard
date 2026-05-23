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
    """
    尝试多个 Yahoo Finance 伦敦金现货代码，按优先级依次尝试：
    XAUUSD=X  →  GOLD  →  IAUX  →  GLDA.L
    返回 (DataFrame, 使用的代码)
    """
    spot_symbols = [
        ("XAUUSD=X", "伦敦金现货"),
        ("GOLD", "伦敦金现货"),
        ("IAUX", "伦敦金现货"),
        ("GLDA.L", "伦敦金现货"),
    ]
    
    for symbol, label in spot_symbols:
        try:
            df = yf.download(symbol, start="2023-01-01", end="2026-12-31")
            if not df.empty and len(df) > 2:
                # 确认收盘价列有有效数据
                if isinstance(df.columns, pd.MultiIndex):
                    close_data = df.xs('Close', level=0, axis=1)
                else:
                    close_data = df['Close']
                if not close_data.empty and close_data.dropna().iloc[-1] > 0:
                    return df, symbol
        except Exception:
            continue
    
    return pd.DataFrame(), ""

# 3. 核心函数：从 DataFrame 中提取收盘价 Series
def get_close_series(raw_df):
    """提取收盘价 Series"""
    if raw_df.empty:
        return pd.Series(dtype=float, name='close')
    
    if isinstance(raw_df.columns, pd.MultiIndex):
        s = raw_df.xs('Close', level=0, axis=1)
        if isinstance(s, pd.DataFrame):
            s = s.iloc[:, 0]
    else:
        s = raw_df['Close']
    
    if isinstance(s, pd.DataFrame):
        s = s.squeeze(axis=1)
    
    s.name = 'close'
    s.index = pd.to_datetime(s.index)
    return s

try:
    with st.spinner("正在从国际交易所同步最新历史数据..."):
        futures_raw = load_futures_data()
        spot_raw, spot_symbol_used = load_spot_data()

    if futures_raw.empty:
        st.error("❌ COMEX 期货数据获取失败，请检查网络后刷新页面重试。")
        st.stop()

    # ---- 提取收盘价 Series ----
    futures_close = get_close_series(futures_raw)
    
    if futures_close.empty or len(futures_close) < 2:
        st.error("❌ COMEX 期货数据不足，无法计算。")
        st.stop()

    # ---- 现货数据处理 ----
    spot_available = False
    if not spot_raw.empty:
        spot_close = get_close_series(spot_raw)
        if not spot_close.empty and len(spot_close) >= 2:
            spot_available = True

    # ---- 获取期货最新价 ----
    futures_latest = float(futures_close.values[-1])
    futures_prev = float(futures_close.values[-2])
    futures_change = (futures_latest - futures_prev) / futures_prev * 100

    # ---- 获取现货最新价（如果有） ----
    if spot_available:
        spot_latest = float(spot_close.values[-1])
        spot_prev = float(spot_close.values[-2])
        spot_change = (spot_latest - spot_prev) / spot_prev * 100

    latest_date = futures_close.index[-1].strftime('%Y-%m-%d')

    # ========== 顶部实时报价卡片 ==========
    st.subheader("📌 实时报价概览")

    if spot_available and spot_latest != futures_latest:
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                label="COMEX 黄金期货 (GC=F)",
                value=f"${futures_latest:,.2f}",
                delta=f"{futures_change:+.2f}% (当日)"
            )
        with col2:
            st.metric(
                label=f"伦敦金现货 ({spot_symbol_used})",
                value=f"${spot_latest:,.2f}",
                delta=f"{spot_change:+.2f}% (当日)"
            )
    else:
        # 现货数据缺失，或与期货数据相同（回退到了GC=F）
        if spot_available and spot_latest == futures_latest:
            st.warning("⚠️ 伦敦金现货数据源暂不可用（Yahoo Finance限制），目前仅展示 COMEX 期货数据。")
        else:
            st.warning("⚠️ 伦敦金现货数据暂时无法获取，仅展示 COMEX 期货数据。")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            st.metric(
                label="COMEX 黄金期货 (GC=F)",
                value=f"${futures_latest:,.2f}",
                delta=f"{futures_change:+.2f}% (当日)"
            )
        with col2:
            st.metric(
                label="伦敦金现货 (暂不可用)",
                value="N/A",
                delta=None
            )

    st.caption(f"数据最新同步交易日 (UTC): {latest_date}")
    st.markdown("---")

    # ========== 核心量化算法（基于 COMEX 期货） ==========
    close = futures_close

    daily_gain = close.pct_change(1)
    weekly_gain = close.pct_change(5)
    monthly_gain = close.pct_change(21)
    quarterly_gain = close.pct_change(63)
    annual_gain = close.pct_change(252)

    year = close.index.year

    # ---- 过去1周最大日内涨幅 ----
    max_daily_in_week = daily_gain.tail(5).max()
    max_daily_in_week_str = f"{max_daily_in_week * 100:+.2f}%" if pd.notna(max_daily_in_week) else "N/A"

    # ---- 按年份分组 ----
    summary_data = {
        'daily_gain': daily_gain,
        'weekly_gain': weekly_gain,
        'monthly_gain': monthly_gain,
        'quarterly_gain': quarterly_gain,
        'annual_gain': annual_gain
    }
    summary_df = pd.DataFrame(summary_data, index=close.index)
    summary_df['year'] = year

    summary = summary_df.groupby('year').agg({
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

    if spot_available and spot_latest != futures_latest:
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            st.markdown("**COMEX 黄金期货**")
            chart_futures = close.loc[close.index.year >= 2024]
            st.line_chart(chart_futures)

        with col_chart2:
            st.markdown("**伦敦金现货**")
            chart_spot = spot_close.loc[spot_close.index.year >= 2024]
            st.line_chart(chart_spot)
    else:
        st.markdown("**COMEX 黄金期货**")
        chart_futures = close.loc[close.index.year >= 2024]
        st.line_chart(chart_futures)

    st.info(
        "💡 系统提示：\n"
        "- 周/月/季度涨幅均采用量化滚动窗口（Rolling Window）算法，能完美捕获跨自然月、跨自然周的极端爆发性动量。\n"
        "- 历史涨幅矩阵基于 COMEX 期货主力合约计算，可作为风控回撤的量化基准参考。\n"
        "- 伦敦金现货数据受 Yahoo Finance 接口限制，可能暂时不可用，系统会自动降级为仅展示期货数据。"
    )

except Exception as e:
    import traceback
    st.error(f"系统运行或计算异常: {e}")
    st.code(traceback.format_exc())
