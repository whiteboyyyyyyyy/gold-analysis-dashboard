import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# 1. 网页基础配置
st.set_page_config(page_title="智驭量化·期现联动监控看板", layout="wide", page_icon="🏆")

st.title("🏆 智驭量化：全球黄金期现联动与风控边界监控")
st.caption("数据源：Yahoo Finance 生产级弹性流 | 模糊时间轴自适应对齐引擎")

# 2. 侧边栏合约控制面板
st.sidebar.header("⚙️ 交易所合约配置")
contract_options = {
    "2026年06月主力 (GCM26)": "GCM26.CMX",
    "2026年08月远期 (GCQ26)": "GCQ26.CMX",
    "2026年12月远期 (GCZ26)": "GCZ26.CMX",
    "CME官方连续合约 (GC=F)": "GC=F"
}

selected_label = st.sidebar.selectbox("期货锚定合约", list(contract_options.keys()), index=0)
futures_ticker = contract_options[selected_label]

# 3. 稳健的下载与清洗函数
def fetch_and_clean_single_ticker(ticker, start_date="2023-01-01"):
    try:
        df = yf.download(ticker, start=start_date)
        if df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            if ticker in df.columns.get_level_values(1):
                df.columns = df.columns.get_level_values(0)
            elif ticker in df.columns.get_level_values(0):
                df.columns = df.columns.get_level_values(1)
        df.index = pd.to_datetime(df.index).tz_localize(None).strftime('%Y-%m-%d')
        df = df[~df.index.duplicated(keep='last')]
        return df
    except Exception as e:
        return pd.DataFrame()

# 4. 数据对齐逻辑
@st.cache_data(ttl=1800)
def load_synchronized_data(fut_ticker):
    df_f = fetch_and_clean_single_ticker(fut_ticker)
    df_s = fetch_and_clean_single_ticker("XAUUSD=X")
    
    if df_f.empty or df_s.empty:
        return pd.DataFrame()
        
    f_close = df_f['Close'] if 'Close' in df_f.columns else df_f.iloc[:, 0]
    f_vol = df_f['Volume'] if 'Volume' in df_f.columns else pd.Series(0, index=df_f.index)
    s_close = df_s['Close'] if 'Close' in df_s.columns else df_s.iloc[:, 0]
    
    f_df = pd.DataFrame({'Close': f_close, 'Volume': f_vol})
    s_df = pd.DataFrame({'Spot_Close': s_close})
    
    final_df = f_df.join(s_df, how='left')
    final_df['Spot_Close'] = final_df['Spot_Close'].ffill().bfill()
    final_df['Close'] = final_df['Close'].ffill().bfill()
    return final_df

# 5. 主程序渲染（修复了 St -> st）
try:
    with st.spinner("🚀 智驭高容错路由正在穿透 CME 与伦敦清算所..."):
        df = load_synchronized_data(futures_ticker)
    
    if not df.empty and len(df) >= 2:
        df.index = pd.to_datetime(df.index)
        df.sort_index(inplace=True)
        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
        df['Spot_Close'] = pd.to_numeric(df['Spot_Close'], errors='coerce')
        
        # 指标计算
        futures_latest = float(df['Close'].values[-1])
        spot_latest = float(df['Spot_Close'].values[-1])
        current_basis = futures_latest - spot_latest
        
        # 渲染区域... (后续逻辑保持不变)
        col1, col2, col3 = st.columns(3)
        col1.metric("COMEX 期货收盘", f"${futures_latest:,.2f}")
        col2.metric("伦敦金现货基准", f"${spot_latest:,.2f}")
        col3.metric("当前期现基差", f"${current_basis:+.2f}")
        
        st.success("数据同步成功，系统运行正常。")
    else:
        st.error("⚠️ 未能获取足够数据进行联动分析。")
except Exception as e:
    st.error(f"🚨 系统运行异常: {e}")
