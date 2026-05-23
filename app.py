import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(layout="wide")

# 侧边栏：这里只保留绝对有效的流
ticker = st.sidebar.selectbox("选择基准合约", ["GC=F", "GCQ26.CMX", "GCZ26.CMX"])

@st.cache_data(ttl=600)
def get_safe_data(f_ticker):
    # 分别抓取，不搞内联，防止被对方“误杀”
    df_f = yf.download(f_ticker, period="3mo")
    df_s = yf.download("XAUUSD=X", period="3mo")
    
    # 清洗：只取 Close
    for df in [df_f, df_s]:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
    
    # 格式化日期索引，确保能对齐
    df_f.index = pd.to_datetime(df_f.index).strftime('%Y-%m-%d')
    df_s.index = pd.to_datetime(df_s.index).strftime('%Y-%m-%d')
    
    # 暴力合并：以现货为主轴，期货没有的日期不删，而是留空
    df_final = pd.concat([df_f['Close'], df_s['Close']], axis=1)
    df_final.columns = ['Futures', 'Spot']
    
    # 填充缺失值：如果期货停盘，拿前一天的期货价补；现货同理
    df_final = df_final.ffill()
    return df_final

try:
    df = get_safe_data(ticker)
    
    st.write(f"当前分析合约: {ticker}")
    st.write("最近 5 天原始数据流:")
    st.table(df.tail(5))
    
    st.line_chart(df.tail(30))
    
    if df['Futures'].iloc[-1] == df['Futures'].iloc[-2]:
        st.warning("期货数据疑似静止（可能已停盘/交割），请以现货数据为准。")

except Exception as e:
    st.error(f"严重异常: {e}")
