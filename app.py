import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime

# ========== 配置 ==========
METAL_API_KEY = "6fbbb2d3ab2d4f0b34fa4f13970f0d8f"
ALLTICK_TOKEN = "38aac33acb3ad3f84a2a7a2850a3344a-c-app"

# ========== 网页配置 ==========
st.set_page_config(page_title="全球金价历史波幅看板", layout="wide", page_icon="🏆")

st.title("🏆 全球黄金多周期历史涨幅与风控边界监控")
st.caption("数据源：Yahoo Finance (期货) + MetalPriceAPI (现货) + AllTick (现货历史K线) | COMEX 期货 + 伦敦金现货 + 人民币金价 | 适合每日收盘盘点")

# ========== 数据缓存 ==========

@st.cache_data(ttl=3600)
def load_futures_data():
    """COMEX 黄金期货 (Yahoo Finance)"""
    df = yf.download("GC=F", start="2023-01-01", end="2026-12-31")
    return df


@st.cache_data(ttl=300)
def load_spot_prices():
    """
    从 MetalPriceAPI 获取伦敦金现货价格 (美元/盎司)
    并通过 USD/CNY 汇率换算为人民币/克
    """
    results = {}
    base_url = "https://api.metalpriceapi.com/v1/latest"

    # ---- 伦敦金现货 (XAU/USD) ----
    try:
        params = {
            "api_key": METAL_API_KEY,
            "base": "USD",
            "currencies": "XAU"
        }
        resp = requests.get(base_url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success") and "rates" in data:
                xau_rate = data["rates"].get("XAU")
                if xau_rate and xau_rate > 0:
                    price_usd_per_ounce = 1 / xau_rate
                    results['london'] = {
                        'price': price_usd_per_ounce,
                        'currency': 'USD/oz'
                    }
    except Exception:
        pass

    # ---- USD/CNY 汇率 ----
    if 'london' in results:
        try:
            params_cny = {
                "api_key": METAL_API_KEY,
                "base": "USD",
                "currencies": "CNY"
            }
            resp_cny = requests.get(base_url, params=params_cny, timeout=10)
            if resp_cny.status_code == 200:
                data_cny = resp_cny.json()
                if data_cny.get("success") and "rates" in data_cny:
                    usd_to_cny = data_cny["rates"].get("CNY")
                    if usd_to_cny:
                        price_cny_per_gram = (results['london']['price'] * usd_to_cny) / 31.1035
                        results['shanghai'] = {
                            'price': price_cny_per_gram,
                            'currency': 'CNY/g'
                        }
        except Exception:
            pass

    return results


@st.cache_data(ttl=3600)
def load_spot_history(symbol, start_date, end_date):
    """
    从 AllTick 获取现货历史日K线数据
    symbol: 'XAUUSD' 伦敦金现货
    """
    url = "https://quote.alltick.io/quote-gold-api/history"
    params = {
        "token": ALLTICK_TOKEN,
        "code": symbol,
        "start_time": start_date,
        "end_time": end_date,
        "kline_type": 5  # 5 = 日K线
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            kline_list = data.get('data', {}).get('kline_list', [])
            if kline_list:
                df = pd.DataFrame(kline_list)
                # AllTick 返回的时间戳字段可能是 'timestamp' 或 'kline_time'
                time_col = 'timestamp' if 'timestamp' in df.columns else 'kline_time'
                df[time_col] = pd.to_datetime(df[time_col])
                df.set_index(time_col, inplace=True)
                # 确保有 close 列
                if 'close' not in df.columns:
                    # 备选字段名
                    close_col = [c for c in df.columns if 'close' in c.lower()]
                    if close_col:
                        df.rename(columns={close_col[0]: 'close'}, inplace=True)
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
    """
    输入一个收盘价 Series，返回多周期最大涨幅矩阵 DataFrame
    """
    close = price_series.dropna()
    if len(close) < 252:
        return pd.DataFrame()

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

    # 过去1周最大日内涨幅
    max_daily_in_week = daily_gain.tail(5).max()
    max_daily_str = f"{max_daily_in_week * 100:+.2f}%" if pd.notna(max_daily_in_week) else "N/A"

    return display_df, max_daily_str


# ========== 主程序 ==========
try:
    with st.spinner("正在同步全球金价数据..."):
        futures_raw = load_futures_data()
        spot_prices = load_spot_prices()
        spot_history = load_spot_history("XAUUSD", "2023-01-01", "2026-05-23")

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

    # ---- 现货历史数据处理 ----
    spot_has_history = False
    if not spot_history.empty and 'close' in spot_history.columns:
        spot_close = spot_history['close'].dropna()
        if len(spot_close) >= 252:
            spot_has_history = True
            spot_latest = float(spot_close.values[-1])
        else:
            # 数据不够一年，只用实时价
            spot_latest = spot_prices.get('london', {}).get('price', None)
    else:
        spot_latest = spot_prices.get('london', {}).get('price', None)

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
                label="上海金参考价 (CNY/克)",
                value=f"¥{sha['price']:,.2f}",
                delta="实时换算"
            )
        else:
            st.metric(label="上海金参考价 (CNY/克)", value="N/A")

    st.caption(f"期货数据同步交易日 (UTC): {latest_date} | 现货实时: MetalPriceAPI | 现货历史K线: AllTick")
    st.markdown("---")

    # ========== 历史波幅矩阵 ==========

    # ---- 表1：COMEX 黄金期货 ----
    st.subheader("📊 表1：COMEX 黄金期货 — 历史多周期最大涨幅矩阵")
    futures_matrix, futures_week_max = compute_wave_matrix(futures_close)
    if not futures_matrix.empty:
        st.table(futures_matrix)
        st.metric(
            label="⚡ COMEX 期货 · 过去1周最大单日涨幅",
            value=futures_week_max
        )
    else:
        st.warning("COMEX 期货历史数据不足，无法生成矩阵")

    st.markdown("---")

    # ---- 表2：伦敦金现货 ----
    st.subheader("📊 表2：伦敦金现货 (XAU/USD) — 历史多周期最大涨幅矩阵")
    if spot_has_history:
        spot_matrix, spot_week_max = compute_wave_matrix(spot_close)
        if not spot_matrix.empty:
            st.table(spot_matrix)
            st.metric(
                label="⚡ 伦敦金现货 · 过去1周最大单日涨幅",
                value=spot_week_max
            )
        else:
            st.warning("伦敦金现货历史数据不足，无法生成独立矩阵")
    else:
        st.info("💡 伦敦金现货历史K线暂不可用，其波动规律与COMEX期货高度同步，请参考表1数据。")

    st.markdown("---")

    # ---- 表3：上海金参考价 ----
    st.subheader("📊 表3：上海金参考价 (CNY/克) — 历史多周期最大涨幅矩阵")
    st.info("💡 上海金价格由国际金价 × USD/CNY汇率换算得出，日内涨跌幅规律与国际金价一致。请参考伦敦金现货矩阵（表2），涨跌幅百分比可直接通用。")

    st.markdown("---")

    # ========== 辅助可视化 ==========
    st.subheader("📈 黄金价格历史走势图 (2024 - 2026)")

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown("**COMEX 黄金期货**")
        chart_futures = futures_close.loc[futures_close.index.year >= 2024]
        st.line_chart(chart_futures)

    with col_chart2:
        st.markdown("**伦敦金现货**")
        if spot_has_history:
            chart_spot = spot_close.loc[spot_close.index.year >= 2024]
            st.line_chart(chart_spot)
        else:
            st.info("💡 现货历史走势与期货高度同步，可参考左图")
            st.line_chart(chart_futures.loc[futures_close.index.year >= 2024])

    st.info(
        "💡 系统提示：\n"
        "- 周/月/季度涨幅均采用量化滚动窗口（Rolling Window）算法，捕获跨周期的极端动量。\n"
        "- COMEX期货矩阵基于 Yahoo Finance 真实期货数据计算。\n"
        "- 伦敦金现货矩阵基于 AllTick 历史日K线数据计算。\n"
        "- 上海金参考价通过国际金价 × USD/CNY汇率 ÷ 31.1035 实时换算，涨跌幅与国际金价一致。\n"
        "- 三个品种的日内涨跌幅高度联动，矩阵数据可互相参考验证。"
    )

except Exception as e:
    import traceback
    st.error(f"系统运行或计算异常: {e}")
    st.code(traceback.format_exc())
