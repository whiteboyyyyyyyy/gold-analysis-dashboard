import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="智驭量化调试台", layout="wide")
st.title("🏆 智驭量化数据流调试器")

# 侧边栏：强制合约选择
contract_ticker = st.sidebar.selectbox("选择合约", ["GCM26.CMX", "GC=F", "GCQ26.CMX"], index=0)

# 调试函数：直接打印原始数据形态
def fetch_raw(ticker):
    df = yf.download(ticker, period="1mo") # 只抓最近一个月，避免日期过滤太苛刻
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

try:
    with st.spinner("正在拉取原始数据..."):
        df_f = fetch_raw(contract_ticker)
        df_s = fetch_raw("XAUUSD=X")
        
        st.write("期货数据头 3 行:", df_f.head(3))
        st.write("现货数据头 3 行:", df_s.head(3))
        
        # 强制将索引转换为标准日期格式
        df_f.index = pd.to_datetime(df_f.index).strftime('%Y-%m-%d')
        df_s.index = pd.to_datetime(df_s.index).strftime('%Y-%m-%d')
        
        # 合并
        df_combined = pd.DataFrame({'Futures': df_f['Close'], 'Spot': df_s['Close']})
        df_combined = df_combined.dropna()
        
        st.write("合并后的数据（行数）:", len(df_combined))
        
        if len(df_combined) >= 1:
            st.success("数据获取成功！")
            st.line_chart(df_combined)
        else:
            st.error("数据仍然无法对齐。请检查是否因为合约过期（如GCM26已经进入交割期导致代码失效）。")
            
except Exception as e:
    st.error(f"捕获到异常: {e}")
