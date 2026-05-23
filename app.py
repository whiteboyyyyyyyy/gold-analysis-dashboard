import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

st.set_page_config(page_title="全球金价历史波幅看板", layout="wide", page_icon="🏆")

st.title("🏆 全球黄金多周期历史涨幅与风控边界监控")

# ---- 直接下载看原始数据 ----
@st.cache_data(ttl=3600)
def load_raw_futures():
    return yf.download("GC=F", start="2023-01-01", end="2026-12-31")

@st.cache_data(ttl=3600)
def load_raw_spot():
    return yf.download("XAUUSD=X", start="2023-01-01", end="2026-12-31")

try:
    with st.spinner("正在同步数据..."):
        futures_df = load_raw_futures()
        spot_df = load_raw_spot()

    # ===== 调试：显示原始 DataFrame 信息 =====
    st.subheader("🔍 调试信息：COMEX 期货原始数据结构")
    st.write("**列索引类型：**", type(futures_df.columns))
    st.write("**列索引内容：**", futures_df.columns.tolist())
    st.write("**是否为 MultiIndex：**", isinstance(futures_df.columns, pd.MultiIndex))
    st.write("**前3行数据：**")
    st.dataframe(futures_df.head(3))

    st.subheader("🔍 调试信息：伦敦金现货原始数据结构")
    st.write("**列索引类型：**", type(spot_df.columns))
    st.write("**列索引内容：**", spot_df.columns.tolist())
    st.write("**是否为 MultiIndex：**", isinstance(spot_df.columns, pd.MultiIndex))
    st.write("**前3行数据：**")
    st.dataframe(spot_df.head(3))

except Exception as e:
    st.error(f"系统运行或计算异常: {e}")
