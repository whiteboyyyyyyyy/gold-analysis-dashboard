import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import json
from datetime import datetime

# ========== 配置 ==========
ALLTICK_TOKEN = "38aac33acb3ad3f84a2a7a2850a3344a-c-app"

# ========== 网页配置 ==========
st.set_page_config(page_title="全球金价历史波幅看板", layout="wide", page_icon="🏆")

st.title("🏆 全球黄金多周期历史涨幅与风控边界监控")
st.caption("数据源：Yahoo Finance (期货) + AllTick (现货历史K线) | COMEX 期货 + 伦敦金现货 | 适合每日收盘复盘")

# ========== 数据缓存 ==========

@st.cache_data(ttl=3600)
def load_futures_data():
    """COMEX 黄金期货 (Yahoo Finance)"""
    df = yf.download("GC=F", start="2023-01-01", end="2026-12-31")
    return df


@st.cache_data(ttl=3600)
def load_spot_history_alltick():
    """从 AllTick 获取伦敦金现货近1年历史日K线"""
    end_unix = int(datetime.now().timestamp())

    query_data = {
        "trace": "gold_dashboard",
        "data": {
            "code": "GOLD",
            "kline_type": 8,
            "kline_timestamp_end": end_unix,
            "query_kline_num": 260,
            "adjust_type": 0
        }
    }

    url = "https://quote.alltick.co/quote-b-api/kline"
    params = {"token": ALLTICK_TOKEN, "query": json.dumps(query_data)}

    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('msg') == 'ok':
                kline_list = data.get('data', {}).get('kline_list', [])
                if kline_list:
                    df = pd.DataFrame(kline_list)
                    df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='s')
                    df.set_index('timestamp', inplace=True)
                    df.sort_index(inplace=True)
                    for col in ['open_price', 'close_price', 'high_price', 'low_price']:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                    df.rename(columns={
                        'open_price': 'open',
                        'close_price': 'close',
                        'high_price': 'high',
                        'low_price': 'low',
                    }, inplace=True)
                    return df
    except Exception:
        pass

    return pd.DataFrame()


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

    s = pd.to_numeric(s, errors='coerce')
    s.name = 'close'
    s.index = pd.to_datetime(s.index)
    return s


def compute_wave_matrix(price_series, label=""):
    """计算多周期最大涨幅矩阵"""
    close = price_series.dropna().astype(float)
    if len(close) < 5:
        return pd.DataFrame(), "N/A"

    daily_gain = close.pct_change(1)
    weekly_gain = close.pct_change(5)
    monthly_gain = close.pct_change(21)
    quarterly_gain = close.pct_change(63)
    annual_gain = close.pct_change(252) if len(close) >= 252 else pd.Series(index=close.index, dtype=float)

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

    max_daily_in_week = daily_gain.tail(5).max()
    max_daily_str = f"{max_daily_in_week * 100:+.2f}%" if pd.notna(max_daily_in_week) else "N/A"

    return display_df, max_daily_str


# ========== 主程序 ==========
try:
    with st.spinner("正在同步全球金价数据..."):
        futures_raw = load_futures_data()
        spot_history = load_spot_history_alltick()

    if futures_raw.empty:
        st.error("❌ COMEX 期货数据获取失败，请刷新重试。")
        st.stop()

    # ---- 期货数据 ----
    futures_close = get_close_series(futures_raw)

    if futures_close.empty or len(futures_close) < 2:
        st.error("❌ COMEX 期货数据不足。")
        st.stop()

    futures_latest = float(futures_close.values[-1])
    futures_prev = float(futures_close.values[-2])
    futures_change = (futures_latest - futures_prev) / futures_prev * 100
    latest_date = futures_close.index[-1].strftime('%Y-%m-%d')

    # ---- 现货历史数据 ----
    spot_has_history = False
    spot_close = None
    spot_latest = None
    spot_prev = None
    spot_change = None

    if not spot_history.empty and 'close' in spot_history.columns:
        spot_close = spot_history['close'].dropna().astype(float)
        if len(spot_close) >= 5:
            spot_has_history = True
            spot_latest = float(spot_close.values[-1])
            spot_prev = float(spot_close.values[-2])
            spot_change = (spot_latest - spot_prev) / spot_prev * 100

    # ========== 实时报价卡片 ==========
    st.subheader("📌 全球黄金最新报价")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            label="COMEX 黄金期货 (GC=F)",
            value=f"${futures_latest:,.2f}",
            delta=f"{futures_change:+.2f}% (最新交易日)"
        )

    with col2:
        if spot_has_history:
            st.metric(
                label="伦敦金现货 (XAU/USD)",
                value=f"${spot_latest:,.2f}",
                delta=f"{spot_change:+.2f}% (最新交易日)"
            )
        else:
            st.metric(label="伦敦金现货 (XAU/USD)", value="加载中...")

    st.caption(f"数据同步至 (UTC): {latest_date} | 期货: Yahoo Finance | 现货历史K线: AllTick")
    st.markdown("---")

    # ========== 表1：COMEX 期货 ==========
    st.subheader("📊 表1：COMEX 黄金期货 — 历史多周期最大涨幅矩阵 (2024-2026)")
    futures_matrix, futures_week_max = compute_wave_matrix(futures_close)
    if not futures_matrix.empty:
        st.table(futures_matrix)
        st.metric(label="⚡ COMEX 期货 · 过去1周最大单日涨幅", value=futures_week_max)
    else:
        st.warning("数据不足")

    st.markdown("---")

    # ========== 表2：伦敦金现货 ==========
    st.subheader("📊 表2：伦敦金现货 (XAU/USD) — 历史多周期最大涨幅矩阵 (近1年)")
    if spot_has_history:
        spot_matrix, spot_week_max = compute_wave_matrix(spot_close)
        if not spot_matrix.empty:
            st.table(spot_matrix)
            st.metric(label="⚡ 伦敦金现货 · 过去1周最大单日涨幅", value=spot_week_max)
        else:
            st.warning("现货历史数据不足")
    else:
        st.warning("⚠️ AllTick 数据加载中，请稍后刷新。")

    st.markdown("---")

    # ========== 走势图 ==========
    st.subheader("📈 黄金价格历史走势图 (2024 - 2026)")

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown("**COMEX 黄金期货**")
        st.line_chart(futures_close.loc[futures_close.index.year >= 2024])

    with col_chart2:
        st.markdown("**伦敦金现货 (近1年)**")
        if spot_has_history:
            st.line_chart(spot_close)
        else:
            st.info("💡 等待数据加载")
            st.line_chart(futures_close.loc[futures_close.index.year >= 2024])

    st.info(
        "💡 使用说明：\n"
        "- 表1 基于 COMEX 期货主力合约，数据覆盖 2024-2026，适合中长期风控回测。\n"
        "- 表2 基于伦敦金现货近1年日K线，适合近期波动率参考。\n"
        "- 上海金（人民币/克）涨跌幅与国际金价完全同步，可直接复用表2的百分比数据。\n"
        "- 所有涨幅均采用量化滚动窗口算法，捕获跨周期的极端动量。"
    )

except Exception as e:
    import traceback
    st.error(f"系统异常: {e}")
    st.code(traceback.format_exc())
