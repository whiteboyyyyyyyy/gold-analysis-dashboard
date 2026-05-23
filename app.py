import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="智驭·现货黄金看板", layout="wide")
st.title("💰 伦敦金现货 (XAU/USD) 稳健监控看板")

@st.cache_data(ttl=600)
def get_spot_gold():
    # 强制获取最近 30 天，保证数据覆盖周末
    df = yf.download("XAUUSD=X", period="1mo")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

try:
    df = get_spot_gold()
    
    # 🚨 核心修复：永远不要假设数据存在，先检查长度
    if df is not None and len(df) > 0:
        # 使用 tail(1) 获取最新数据，它处理空值比 iloc[-1] 更稳健
        latest = df.tail(1).iloc[0] 
        
        st.metric("最新成交价", f"${latest['Close']:,.2f}")
        
        st.subheader("历史走势")
        st.line_chart(df['Close'])
        
        st.subheader("最近 5 个交易日数据")
        st.dataframe(df.tail(5).style.format("${:.2f}"))
    else:
        st.error("数据源返回为空，请检查网络连接或 API 限制。")
        
except Exception as e:
    st.error(f"发生错误: {e}")
