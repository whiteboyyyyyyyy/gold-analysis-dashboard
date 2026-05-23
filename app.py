import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import json
from datetime import datetime

# ========== 配置 ==========
METAL_API_KEY = "6fbbb2d3ab2d4f0b34fa4f13970f0d8f"
ALLTICK_TOKEN = "38aac33acb3ad3f84a2a7a2850a3344a-c-app"

# ========== 网页配置 ==========
st.set_page_config(page_title="全球金价历史波幅看板", layout="wide", page_icon="🏆")

st.title("🏆 全球黄金多周期历史涨幅与风控边界监控")
st.caption("数据源：Yahoo Finance (期货) + MetalPriceAPI (现货) + AllTick (现货历史K线) | COMEX 期货 + 伦敦金现货 + 人民币金价")

# ========== 数据缓存 ==========

@st.cache_data(ttl=3600)
def load_futures_data():
    """COMEX 黄金期货 (Yahoo Finance)"""
    df = yf.download("GC=F", start="2023-01-01", end="2026-12-31")
    return df


@st.cache_data(ttl=300)
def load_spot_prices():
    """从 MetalPriceAPI 获取伦敦金现货价格，并换算人民币/克"""
    results = {}
    base_url = "https://api.metalpriceapi.com/v1/latest"

    try:
        params = {"api_key": METAL_API_KEY, "base": "USD", "currencies": "XAU"}
        resp = requests.get(base_url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success") and "rates" in data:
                xau_rate = data["rates"].get("XAU")
                if xau_rate and xau_rate > 0:
                    results['london'] = {
                        'price': 1 / xau_rate,
                        'currency': 'USD/oz'
                    }
    except Exception:
        pass

    if 'london' in results:
        try:
            params_cny = {"api_key": METAL_API_KEY, "base": "USD", "currencies": "CNY"}
            resp_cny = requests.get(base_url, params=params_cny, timeout=10)
            if resp_cny.status_code == 200:
                data_cny = resp_cny.json()
                if data_cny.get("success") and "rates" in data_cny:
                    usd_to_cny = data_cny["rates"].get("CNY")
                    if usd_to_cny:
                        results['shanghai'] = {
                            'price': (results['london']['price'] * usd_to_cny) / 31.1035,
                            'currency': 'CNY/g'
                        }
        except Exception:
            pass

    return results


@st.cache_data(ttl=3600)
def load_spot_history_alltick(symbol, start_date, end_date):
    """
    从 AllTick 获取现货历史日K线
    正确接口: https://quote.alltick.co/quote-b-api/kline
    参数封装在 query JSON 字符串中
    """
    # 将日期转为 Unix 时间戳（秒）
    end_unix = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp())
    
    # 查询1年大约250根日K线，加上缓冲取300根
    query_kline_num = 300
    
    # 构造 query 参数
    query_data = {
        "trace": "gold_dashboard",
        "data": {
            "code": symbol,
            "kline_type": 8,        # 8 = 日K线
            "kline_timestamp_end": end_unix,
            "query_kline_num": query_kline_num,
            "adjust_type": 0
        }
    }
    
    url = "https://quote.alltick.co/quote-b-api/kline"
    params = {
        "token": ALLTICK_TOKEN,
        "query": json.dumps(query_data)
    }
    
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('code') == 200:
                kline_list = data.get('data', {}).get('kline_list', [])
                if kline_list:
                    df = pd.DataFrame(kline_list)
                    # AllTick 返回: timestamp(秒), open, high, low, close, volume
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                    df.set_index('timestamp', inplace=True)
                    df.sort_index(inplace=True)
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

    s.name = 'close'
    s.index = pd.to_datetime(s.index)
    return s


def compute_wave_matrix(price_series):
    """输入收盘价 Series，返回多周期最大涨幅矩阵"""
    close = price_series.dropna()
    if len(close) < 252:
        return pd.DataFrame(), "N/A"

    daily_gain = close.pct_change(1)
    weekly_gain = close.pct_change(5)
    monthly_gain = close.pct_change(21)
    quarterly_gain = close.pct_change(63)
    annual_gain = close.pct_change(252)

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
        spot_prices = load_spot_prices()
        spot_history = load_spot_history_alltick("XAUUSD", "2023-01-01", "2026-05-23")

    if futures_raw.empty:
        st.error("❌ COMEX 期货数据获取失败，请刷新重试。")
        st.stop()

    futures_close = get_close_series(futures_raw)

    if futures_close.empty or len(futures_close) < 2:
        st.error("❌ COMEX 期货数据不足。")
        st.stop()

    futures_latest = float(futures_close.values[-1])
    futures_prev = float(futures_close.values[-2])
    futures_change = (futures_latest - futures_prev) / futures_prev * 100
    latest_date = futures_close.index[-1].strftime('%Y-%m-%d')

    # 现货历史数据处理
    spot_has_history = False
    if not spot_history.empty and 'close' in spot_history.columns:
        spot_close = spot_history['close'].dropna()
        if len(spot_close) >= 252:
            spot_has_history = True

    # ========== 顶部实时报价 ==========
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
            st.metric(
                label="伦敦金现货 (XAU/USD)",
                value=f"${spot_prices['london']['price']:,.2f}",
                delta="实时"
            )
        else:
            st.metric(label="伦敦金现货 (XAU/USD)", value="N/A")

    with col3:
        if 'shanghai' in spot_prices:
            st.metric(
                label="上海金参考价 (CNY/克)",
                value=f"¥{spot_prices['shanghai']['price']:,.2f}",
                delta="实时换算"
            )
        else:
            st.metric(label="上海金参考价 (CNY/克)", value="N/A")

    st.caption(f"期货数据同步交易日 (UTC): {latest_date} | 现货实时: MetalPriceAPI | 现货历史K线: AllTick")
    st.markdown("---")

    # ========== 表1：COMEX 期货 ==========
    st.subheader("📊 表1：COMEX 黄金期货 — 历史多周期最大涨幅矩阵")
    futures_matrix, futures_week_max = compute_wave_matrix(futures_close)
    if not futures_matrix.empty:
        st.table(futures_matrix)
        st.metric(label="⚡ COMEX 期货 · 过去1周最大单日涨幅", value=futures_week_max)
    else:
        st.warning("数据不足")

    st.markdown("---")

    # ========== 表2：伦敦金现货 ==========
    st.subheader("📊 表2：伦敦金现货 (XAU/USD) — 历史多周期最大涨幅矩阵")
    if spot_has_history:
        spot_matrix, spot_week_max = compute_wave_matrix(spot_close)
        if not spot_matrix.empty:
            st.table(spot_matrix)
            st.metric(label="⚡ 伦敦金现货 · 过去1周最大单日涨幅", value=spot_week_max)
        else:
            st.warning("现货历史数据不足")
    else:
        st.warning("⚠️ AllTick 历史K线获取失败，请检查Token权限或网络。伦敦金现货涨跌幅规律与COMEX期货一致，可暂用表1数据参考。")

    st.markdown("---")

    # ========== 表3：上海金 ==========
    st.subheader("📊 表3：上海金参考价 (CNY/克) — 历史多周期最大涨幅矩阵")
    st.info("💡 上海金价格 = 国际金价 × USD/CNY汇率 ÷ 31.1035。日内涨跌幅百分比与国际金价完全一致，请直接参考表2伦敦金现货的涨跌幅数据。")

    st.markdown("---")

    # ========== 走势图 ==========
    st.subheader("📈 黄金价格历史走势图 (2024 - 2026)")

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown("**COMEX 黄金期货**")
        st.line_chart(futures_close.loc[futures_close.index.year >= 2024])

    with col_chart2:
        st.markdown("**伦敦金现货**")
        if spot_has_history:
            st.line_chart(spot_close.loc[spot_close.index.year >= 2024])
        else:
            st.info("💡 现货走势与期货高度同步，参考左图")
            st.line_chart(futures_close.loc[futures_close.index.year >= 2024])

    st.info(
        "💡 系统提示：\n"
        "- 所有涨幅均采用滚动窗口算法，捕获跨周期极端动量。\n"
        "- COMEX期货矩阵基于 Yahoo Finance 真实数据。\n"
        "- 伦敦金现货矩阵基于 AllTick 历史日K线数据。\n"
        "- 上海金涨跌幅与国际金价一致，直接复用现货矩阵。"
    )

except Exception as e:
    import traceback
    st.error(f"系统异常: {e}")
    st.code(traceback.format_exc())
