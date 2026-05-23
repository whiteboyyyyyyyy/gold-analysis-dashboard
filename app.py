import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# 1. 页面配置
st.set_page_config(page_title="智驭·现货黄金监控", layout="wide", page_icon="💰")
st.title("💰 伦敦金现货 (XAU/USD) 深度监控看板")
st.caption("实时拉取全球流动性基准 | 基于 ATR 的风控边界计算")

# 2. 现货数据加载引擎
@st.cache_data(ttl=600)
def load_spot_gold():
    # 抓取过去 1 年的现货数据，确保指标计算的样本量充足
    df = yf.download("XAUUSD=X", period="1y")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # 基础清洗
    df = df.dropna()
    
    # 计算量化指标
    # ATR (Average True Range) 用于计算风控边界
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    df['ATR'] = ranges.max(axis=1).rolling(14).mean()
    
    # 计算涨跌幅
    df['Pct_Change'] = df['Close'].pct_change() * 100
    return df

try:
    df = load_spot_gold()
    
    # 3. 实时状态监控
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("最新成交价", f"${latest['Close']:,.2f}", f"{latest['Pct_Change']:+.2f}%")
    col2.metric("日内振幅边界 (ATR)", f"${latest['ATR']:,.2f}")
    col3.metric("市场强度评分", "稳健" if latest['Close'] > df['Close'].rolling(20).mean().iloc[-1] else "震荡")
    
    st.markdown("---")
    
    # 4. 数据展示
    tab1, tab2 = st.tabs(["走势曲线", "原始数据明细"])
    
    with tab1:
        st.line_chart(df[['Close']])
        
    with tab2:
        st.dataframe(df.tail(10).style.format("${:.2f}"))

except Exception as e:
    st.error(f"现货数据服务异常: {e}")
