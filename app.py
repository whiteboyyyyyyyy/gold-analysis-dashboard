import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime

# ========== 网页配置 ==========
st.set_page_config(page_title="全球金价历史波幅看板", layout="wide", page_icon="🏆")

st.title("🏆 全球黄金多周期历史涨幅与风控边界监控")
st.caption("数据源：Yahoo Finance (期货) + GoldPrice.Today (现货) | COMEX 期货 + 伦敦金现货 + 人民币金价 | 适合每日收盘盘点")

# ========== 数据缓存 ==========
@st.cache_data(ttl=3600)
def load_futures_data():
    """COMEX 黄金期货 (Yahoo Finance)"""
    df = yf.download("GC=F", start="2023-01-01", end="2026-12-31")
    return df

@st.cache_data(ttl=300)
def load_spot_prices():
    """
    从 GoldPrice.Today 获取现货价格
    完全免费，无需 API Key
    """
    results = {}

    headers = {"User-Agent": "Mozilla/5.0"}

    # 伦敦金现货 (美元/盎司)
    try:
        resp = requests.get("https://data-asg.goldprice.com/dbXRates/USD", headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get('items', [])
            if items:
                price = items[0].get('xauPrice', 0)
                if price:
                    results['london'] = {
                        'price': float(price),
                        'currency': 'USD/oz'
                    }
    except Exception:
        pass

    # 人民币金价 (人民币/克)
    try:
        resp = requests.get("https://data-asg.goldprice.com/dbXRates/CNY", headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get('items', [])
            if items:
                price = items[0].get('xauPrice', 0)
                if price:
                    results['shanghai'] = {
                        'price': float(price),
                        'currency': 'CNY/g'
                    }
    except Exception:
        pass

    return results

# ========== 辅助函数 ==========
def get_close_series(raw_df):
    """从 yfinance DataFrame 提取收盘价 Series"""
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

# ========== 主程序 ==========
try:
    with st.spinner("正在同步全球金价数据..."):
        futures_raw = load_futures_data()
        spot_prices = load_spot_prices()

    if futures_raw.empty:
        st.error("❌ COMEX 期货数据获取失败，请检查网络后刷新页面重试。")
        st.stop()

    # ---- 期货数据处理 ----
    futures_close = get_close_series(futures_raw)

    if futures_close.empty or len(futures_close) < 2:
        st.error("❌ COMEX 期货数据不足，无法计算。")
        st.stop()

    futures_latest = float(futures_close.values[-1])
    futures_prev = float(futures_close.values[-2])
    futures_change = (futures_latest - futures_prev) / futures_prev * 100
    latest_date = futures_close.index[-1].strftime('%Y-%m-%d')

    # ========== 顶部实时报价卡片 ==========
    st.subheader("📌 全球黄金实时报价")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="COMEX 黄金期货 (GC=F)",
            value=f"${futures_latest:,.2f}",
            delta=f"{futures_change:+.2f}% (当日)"
        )

    with col2:
        if 'london' in spot_prices:
            ldn = spot_prices['london']
            st.metric(
                label="伦敦金现货 (XAU/USD)",
                value=f"${ldn['price']:,.2f}",
                delta="实时"
            )
        else:
            st.metric(label="伦敦金现货 (XAU/USD)", value="N/A")

    with col3:
        if 'shanghai' in spot_prices:
            sha = spot_prices['shanghai']
            st.metric(
                label="人民币金价 (CNY/克)",
                value=f"¥{sha['price']:,.2f}",
                delta="实时"
            )
        else:
            st.metric(label="人民币金价 (CNY/克)", value="N/A")

    st.caption(f"期货数据同步交易日 (UTC): {latest_date} | 现货数据源: GoldPrice.Today (每5分钟更新)")
    st.markdown("---")

    # ========== 历史波幅矩阵（基于 COMEX 期货） ==========
    close = futures_close
    daily_gain = close.pct_change(1)
    weekly_gain = close.pct_change(5)
    monthly_gain = close.pct_change(21)
    quarterly_gain = close.pct_change(63)
    annual_gain = close.pct_change(252)

    # 过去1周最大日内涨幅
    max_daily_in_week = daily_gain.tail(5).max()
    max_daily_in_week_str = f"{max_daily_in_week * 100:+.2f}%" if pd.notna(max_daily_in_week) else "N/A"

    # 按年份分组
    year = close.index.year
    summary_df = pd.DataFrame({
        'daily_gain': daily_gain,
        'weekly_gain': weekly_gain,
        'monthly_gain': monthly_gain,
        'quarterly_gain': quarterly_gain,
        'annual_gain': annual_gain,
        'year': year
    })

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

    # 过去1周最大日内涨幅高亮
    st.metric(
        label="⚡ 过去1周 (最近5个交易日) 最大单日涨幅",
        value=max_daily_in_week_str
    )

    # ========== 辅助可视化 ==========
    st.subheader("📈 黄金价格历史走势图 (2024 - 2026)")

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown("**COMEX 黄金期货**")
        chart_futures = close.loc[close.index.year >= 2024]
        st.line_chart(chart_futures)

    with col_chart2:
        st.markdown("**伦敦金现货**")
        # 从 GoldPrice.Today 拿不到历史数据，用期货走势作参考
        st.info("💡 现货历史走势与期货高度同步，可参考左图期货走势")
        chart_futures_copy = close.loc[close.index.year >= 2024]
        st.line_chart(chart_futures_copy)

    st.info(
        "💡 系统提示：\n"
        "- 周/月/季度涨幅均采用量化滚动窗口（Rolling Window）算法，捕获跨周期的极端动量。\n"
        "- 历史涨幅矩阵基于 COMEX 期货主力合约，作为风控回撤的量化基准。\n"
        "- 伦敦金现货与人民币金价由 GoldPrice.Today 免费提供，每5分钟更新一次。\n"
        "- 现货与期货价格高度联动，日内涨跌幅规律一致，矩阵数据可通用。"
    )

except Exception as e:
    import traceback
    st.error(f"系统运行或计算异常: {e}")
    st.code(traceback.format_exc())
