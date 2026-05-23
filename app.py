import streamlit as st
import yfinance as yf
import finnhub
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ========== 配置 ==========
FINNHUB_API_KEY = "d88ncv9r01qq4343sptgd88ncv9r01qq4343spu0"  # 你的 Finnhub API Key

st.set_page_config(page_title="全球金价历史波幅看板", layout="wide", page_icon="🏆")

st.title("🏆 全球黄金多周期历史涨幅与风控边界监控")
st.caption("数据源：Yahoo Finance (期货) + Finnhub (现货) | 覆盖 COMEX 期货 + 伦敦金现货 + 上海金 | 适合每日收盘盘点")

# ========== 1. Finnhub 客户端初始化 ==========
@st.cache_resource
def get_finnhub_client():
    return finnhub.Client(api_key=FINNHUB_API_KEY)

# ========== 2. 数据获取函数 ==========
@st.cache_data(ttl=3600)
def load_futures_data():
    """COMEX 黄金期货 (Yahoo Finance)"""
    df = yf.download("GC=F", start="2023-01-01", end="2026-12-31")
    return df

@st.cache_data(ttl=300)  # 5分钟缓存，现货价格变化快
def load_spot_prices():
    """
    从 Finnhub 获取实时现货报价：
    - 伦敦金现货 (XAU/USD)
    - 上海金现货 (以人民币计价的黄金)
    """
    client = get_finnhub_client()
    results = {}
    
    # 伦敦金现货
    try:
        london_quote = client.quote("XAUUSD")
        if london_quote and london_quote.get('c'):
            results['london'] = {
                'price': london_quote['c'],
                'prev_close': london_quote.get('pc', london_quote['c']),
                'high': london_quote.get('h'),
                'low': london_quote.get('l'),
                'change': london_quote.get('dp', 0)  # 涨跌幅百分比
            }
    except Exception:
        pass
    
    # 上海金现货 (使用 OANDA 的人民币计价黄金代码)
    try:
        shanghai_quote = client.quote("OANDA:XAU_CNY")
        if shanghai_quote and shanghai_quote.get('c'):
            results['shanghai'] = {
                'price': shanghai_quote['c'],
                'prev_close': shanghai_quote.get('pc', shanghai_quote['c']),
                'high': shanghai_quote.get('h'),
                'low': shanghai_quote.get('l'),
                'change': shanghai_quote.get('dp', 0)
            }
    except Exception:
        # 备用：尝试其他可能的上海金代码
        try:
            shanghai_quote = client.quote("XAU_CNY")
            if shanghai_quote and shanghai_quote.get('c'):
                results['shanghai'] = {
                    'price': shanghai_quote['c'],
                    'prev_close': shanghai_quote.get('pc', shanghai_quote['c']),
                    'high': shanghai_quote.get('h'),
                    'low': shanghai_quote.get('l'),
                    'change': shanghai_quote.get('dp', 0)
                }
        except Exception:
            pass
    
    return results

@st.cache_data(ttl=3600)
def load_spot_history(symbol, start_date, end_date):
    """
    从 Finnhub 获取现货历史K线数据 (用于走势图)
    symbol: 'XAUUSD' 或 'OANDA:XAU_CNY'
    """
    client = get_finnhub_client()
    try:
        # Finnhub 要求 Unix 时间戳
        start_unix = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp())
        end_unix = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp())
        
        candles = client.forex_candles(symbol, 'D', start_unix, end_unix)
        
        if candles and candles.get('s') == 'ok':
            df = pd.DataFrame({
                'close': candles['c'],
                'high': candles['h'],
                'low': candles['l'],
                'open': candles['o'],
            }, index=pd.to_datetime(candles['t'], unit='s'))
            return df
        else:
            return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# ========== 3. 辅助函数 ==========
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

# ========== 4. 主程序 ==========
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
                delta=f"{ldn['change']:+.2f}% (实时)" if ldn['change'] else None
            )
        else:
            st.metric(label="伦敦金现货 (XAU/USD)", value="N/A", delta=None)

    with col3:
        if 'shanghai' in spot_prices:
            sha = spot_prices['shanghai']
            st.metric(
                label="上海金现货 (人民币/克)",
                value=f"¥{sha['price']:,.2f}",
                delta=f"{sha['change']:+.2f}% (实时)" if sha['change'] else None
            )
        else:
            st.metric(label="上海金现货 (人民币/克)", value="N/A", delta=None)

    st.caption(f"数据同步时间 (UTC): {latest_date}")
    st.markdown("---")

    # ========== 历史波幅矩阵（基于 COMEX 期货） ==========
    close = futures_close
    daily_gain = close.pct_change(1)
    weekly_gain = close.pct_change(5)
    monthly_gain = close.pct_change(21)
    quarterly_gain = close.pct_change(63)
    annual_gain = close.pct_change(252)

    max_daily_in_week = daily_gain.tail(5).max()
    max_daily_in_week_str = f"{max_daily_in_week * 100:+.2f}%" if pd.notna(max_daily_in_week) else "N/A"

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

    st.subheader("📊 历史年份多周期最大涨幅统计矩阵 (风控基准 · 基于COMEX期货)")
    st.table(display_df)

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
        london_history = load_spot_history('XAUUSD', '2024-01-01', '2026-05-23')
        if not london_history.empty:
            st.line_chart(london_history['close'])
        else:
            st.info("伦敦金历史走势暂时无法加载")

    st.info(
        "💡 系统提示：\n"
        "- 周/月/季度涨幅均采用量化滚动窗口算法，捕获跨周期的极端动量。\n"
        "- 历史涨幅矩阵基于 COMEX 期货，作为风控回撤的量化基准。\n"
        "- 伦敦金现货和上海金现货由 Finnhub 提供实时报价。\n"
        "- 上海金现货以人民币/克计价，数据源为 OANDA。"
    )

except Exception as e:
    import traceback
    st.error(f"系统运行或计算异常: {e}")
    st.code(traceback.format_exc())
