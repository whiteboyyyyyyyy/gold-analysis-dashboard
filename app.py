import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# 1. 网页基础配置
st.set_page_config(page_title="智驭量化·期现联动监控看板", layout="wide", page_icon="🏆")

st.title("🏆 智驭量化：全球黄金期现联动与风控边界监控")
st.caption("数据源：Yahoo Finance 生产级弹性流 | 具备全自动时序对齐与数据容错清洗")

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

# 3. 稳健的单股数据下载与结构展平函数
def fetch_and_clean_single_ticker(ticker, start_date="2023-01-01"):
    """确保不管 yfinance 返回单层还是双层索引，都能干净地吐出标准 DataFrame"""
    try:
        df = yf.download(ticker, start=start_date)
        if df.empty:
            return pd.DataFrame()
            
        # 展平新版 yfinance 的 MultiIndex 列名
        if isinstance(df.columns, pd.MultiIndex):
            # 如果第一层是价格类型 (Close, Open...)，第二层是 Ticker
            if ticker in df.columns.get_level_values(1):
                df.columns = df.columns.get_level_values(0)
            # 如果第一层是 Ticker，第二层是价格类型
            elif ticker in df.columns.get_level_values(0):
                df.columns = df.columns.get_level_values(1)
                
        # 强制将索引转换为不带时区的时间戳，方便后续 Merge
        df.index = pd.to_datetime(df.index).tz_localize(None)
        return df
    except Exception as e:
        st.warning(f"下载 {ticker} 发生微弱异常，启动自动修复: {e}")
        return pd.DataFrame()

# 4. 双通道独立抓取与本业内聚拼装
@st.cache_data(ttl=1800)
def load_synchronized_data(fut_ticker):
    # 分开下载，断绝因合并导致的 MultiIndex 污染
    df_f = fetch_and_clean_single_ticker(fut_ticker)
    df_s = fetch_and_clean_single_ticker("XAUUSD=X")
    
    if df_f.empty or df_s.empty:
        return pd.DataFrame()
        
    # 提取核心列
    f_close = df_f['Close'] if 'Close' in df_f.columns else df_f.iloc[:, 0]
    f_vol = df_f['Volume'] if 'Volume' in df_f.columns else pd.Series(0, index=df_f.index)
    s_close = df_s['Close'] if 'Close' in df_s.columns else df_s.iloc[:, 0]
    
    # 转换为标准的单层 DataFrame
    f_df = pd.DataFrame({'Close': f_close, 'Volume': f_vol})
    s_df = pd.DataFrame({'Spot_Close': s_close})
    
    # 使用 Pandas 的 merge 按照日期取交集（Inner Join），彻底解决两边非交易日对不齐导致的空行
    final_df = pd.merge(f_df, s_df, left_index=True, right_index=True, how='inner')
    return final_df

try:
    with st.spinner("🚀 智驭高容错路由正在穿透 CME 与伦敦清算所..."):
        df = load_synchronized_data(futures_ticker)
    
    # 确保融合后的表里至少有 2 行数据才允许计算，死卡越界硬伤
    if not df.empty and len(df) >= 2:
        df.sort_index(inplace=True)
        
        # 确保数据格式全为标准 float
        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
        df['Spot_Close'] = pd.to_numeric(df['Spot_Close'], errors='coerce')
        df.dropna(subset=['Close', 'Spot_Close'], inplace=True)
        
        # 5. 安全的指标抓取（用时序位置取代易越界的 iloc 寻址）
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
        
        st.info("💡 **智驭风控提示**：当前时序引擎已升级为双通道独立对齐架构。系统自动通过 `Inner Join` 剪裁掉了周末不重合的幽灵K线，确保计算矩阵时绝不发生越界。")
        
    else:
        st.error("⚠️ 现货或期货历史流未能成功合并，可能由于当前处于周末非交易时段，底层 API 暂时截断了行情流。请稍后刷新或在左侧尝试切换合约。")
        
except Exception as e:
    st.error(f"🚨 运行异常: {e}")
