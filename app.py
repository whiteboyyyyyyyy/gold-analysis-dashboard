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
st.sidebar.markdown("请选择你要与现货大盘进行比对的 **COMEX 期货主力月份**：")

contract_options = {
    "2026年06月主力 (GCM26)": "GCM26.CMX",
    "2026年08月远期 (GCQ26)": "GCQ26.CMX",
    "2026年12月远期 (GCZ26)": "GCZ26.CMX",
    "CME官方连续合约 (GC=F)": "GC=F"
}

selected_label = st.sidebar.selectbox("期货锚定合约", list(contract_options.keys()), index=0)
futures_ticker = contract_options[selected_label]

# 3. 极其强悍的单股下载与纯日期化清洗
def fetch_and_clean_single_ticker(ticker, start_date="2023-01-01"):
    try:
        df = yf.download(ticker, start=start_date)
        if df.empty:
            return pd.DataFrame()
            
        # 展平新版 yfinance 的 MultiIndex 列名
        if isinstance(df.columns, pd.MultiIndex):
            if ticker in df.columns.get_level_values(1):
                df.columns = df.columns.get_level_values(0)
            elif ticker in df.columns.get_level_values(0):
                df.columns = df.columns.get_level_values(1)
                
        # 🌟 核心修正：强制抹去时区，并将 DatetimeIndex 降维成纯粹的 'YYYY-MM-DD' 字符串型日期
        df.index = pd.to_datetime(df.index).tz_localize(None).strftime('%Y-%m-%d')
        # 去除可能重复的日期行（防止Yahoo周末数据污染）
        df = df[~df.index.duplicated(keep='last')]
        return df
    except Exception as e:
        return pd.DataFrame()

# 4. 弹性模糊时序拼接（解决周末对不齐的终极方案）
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
    
    # 🌟 核心改动：以期货的时间轴为主轴（Left Join）
    # 期货有交易的交易日，现货一定有。如果因为周末时区差了一天，现货没对上，后面用 ffill 强行拿最近一个价格填平
    final_df = f_df.join(s_df, how='left')
    
    # 强力向下填补因时区差造成的断层空值
    final_df['Spot_Close'] = final_df['Spot_Close'].ffill().bfill()
    final_df['Close'] = final_df['Close'].ffill().bfill()
    
    return final_df

try:
    with St.spinner("🚀 智驭高容错路由正在穿透 CME 与伦敦清算所..."):
        df = load_synchronized_data(futures_ticker)
    
    if not df.empty and len(df) >= 2:
        # 将字符串索引重新转回 DatetimeIndex 方便后续画图和计算变动率
        df.index = pd.to_datetime(df.index)
        df.sort_index(inplace=True)
        
        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
        df['Spot_Close'] = pd.to_numeric(df['Spot_Close'], errors='coerce')
        
        # 5. 指标寻址
        futures_latest = float(df['Close'].values[-1])
        spot_latest = float(df['Spot_Close'].values[-1])
        current_basis = futures_latest - spot_latest
        
        futures_prev = float(df['Close'].values[-2])
        futures_change = (futures_latest - futures_prev) / futures_prev * 100
        
        spot_prev = float(df['Spot_Close'].values[-2])
        spot_change = (spot_latest - spot_prev) / spot_prev * 100
        
        latest_date_str = df.index[-1].strftime('%Y-%m-%d')
        
        # 6. 渲染顶部核心数据面板
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                label=f"COMEX 期货收盘 ({futures_ticker})", 
                value=f"${futures_latest:,.2f}", 
                delta=f"{futures_change:+.2f}%"
            )
        with col2:
            st.metric(
                label="伦敦金现货基准 (XAU/USD)", 
                value=f"${spot_latest:,.2f}", 
                delta=f"{spot_change:+.2f}%"
            )
        with col3:
            st.metric(
                label="当前期现基差 (Basis / 升贴水)", 
                value=f"${current_basis:+.2f}",
                delta=f"交易日对齐节点: {latest_date_str}",
                delta_color="off"
            )
            
        st.markdown("---")
        
        # 7. 滚动风控矩阵计算
        df['Daily_Gain'] = df['Close'].pct_change(1)
        df['Weekly_Gain'] = df['Close'].pct_change(5)
        df['Monthly_Gain'] = df['Close'].pct_change(21)
        df['Quarterly_Gain'] = df['Close'].pct_change(63)
        df['Annual_Gain'] = df['Close'].pct_change(252)
        df['Year'] = df.index.year
        
        summary = df.groupby('Year').agg({
            'Daily_Gain': 'max',
            'Weekly_Gain': 'max',
            'Monthly_Gain': 'max',
            'Quarterly_Gain': 'max',
            'Annual_Gain': 'max'
        })
        
        summary_pct = (summary * 100).round(2)
        display_df = summary_pct.loc[summary_pct.index >= 2024].copy()
        
        for col in display_df.columns:
            display_df[col] = display_df[col].astype(str) + '%'
            
        display_df.columns = ['日最大涨幅', '周最大涨幅 (5日)', '月最大涨幅 (21日)', '季最大涨幅 (63日)', '年内累计最大涨幅']
        display_df.index.name = '年份/风控区间'
        
        st.subheader("📊 历史多周期极端波幅矩阵（压测与保证金风控基准）")
        st.table(display_df)
        
        # 8. 可视化期现走势
        st.subheader("📈 期现双轨收盘走势对比")
        chart_data = df.loc[df.index.year >= 2024, ['Close', 'Spot_Close']].copy()
        chart_data.columns = ['COMEX 期货价格', '伦敦金现货大盘']
        st.line_chart(chart_data)
        
        # 9. 历史明细流
        st.subheader("📋 交易日数据对齐明细")
        recent_history = df.tail(5).copy()
        recent_history['Basis'] = recent_history['Close'] - recent_history['Spot_Close']
        
        # 格式化
        recent_history['Close'] = recent_history['Close'].map('${:,.2f}'.format)
        recent_history['Spot_Close'] = recent_history['Spot_Close'].map('${:,.2f}'.format)
        recent_history['Basis'] = recent_history['Basis'].map('${:+.2f}'.format)
        recent_history['Volume'] = recent_history['Volume'].map('{:,.0f}'.format)
        recent_history.index = recent_history.index.strftime('%Y-%m-%d')
        
        st.dataframe(recent_history[['Close', 'Spot_Close', 'Basis', 'Volume']], use_container_width=True)
        
    else:
        st.error("⚠️ 现货或期货历史流未能成功合并，请检查网络或稍后重试。")
        
except Exception as e:
    st.error(f"🚨 运行异常: {e}")
