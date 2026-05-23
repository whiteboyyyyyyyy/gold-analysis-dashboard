import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# 1. 网页基础配置
st.set_page_config(page_title="智驭量化·期现联动监控看板", layout="wide", page_icon="🏆")

st.title("🏆 智驭量化：全球黄金期现联动与风控边界监控")
st.caption("数据源：Yahoo Finance | 自动联立 COMEX 期货单月合约与伦敦金现货 (XAU/USD)")

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

# 3. 双通道数据抓取与自适应清洗
@st.cache_data(ttl=3600)
def load_futures_data(ticker):
    try:
        df = yf.download(ticker, start="2024-01-01")
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception as e:
        st.error(f"期货数据抓取失败: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_spot_data():
    try:
        # XAUUSD=X 是 Yahoo 上的伦敦现货黄金标准代码
        df = yf.download("XAUUSD=X", start="2024-01-01")
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df[['Close']].rename(columns={'Close': 'Spot_Close'})
    except Exception as e:
        st.error(f"现货黄金数据抓取失败: {e}")
        return pd.DataFrame()

try:
    with st.spinner("正在同步全球期现市场收盘网络..."):
        df_futures = load_futures_data(futures_ticker)
        df_spot = load_spot_data()
        
    if not df_futures.empty and not df_spot.empty:
        # 统一时间流，进行时间轴对齐拼接
        df_futures.index = pd.to_datetime(df_futures.index)
        df_spot.index = pd.to_datetime(df_spot.index)
        
        # 内联拼接，确保每一行期现时间完全吻合
        df = df_futures.join(df_spot, how='inner')
        df = df[df['Volume'] > 0].dropna(subset=['Close', 'Spot_Close'])
        
        # 统一重命名核心列
        df.rename(columns={'open':'Open', 'high':'High', 'low':'Low', 'close':'Close', 'volume':'Volume'}, inplace=True)
        
        # 🌟 量化核心指标计算
        futures_latest = float(df['Close'].iloc[-1])
        spot_latest = float(df['Spot_Close'].iloc[-1])
        
        # 计算当前的绝对基差 (Basis = 期货 - 现货)
        current_basis = futures_latest - spot_latest
        
        # 计算期货当日涨跌幅
        futures_prev = float(df['Close'].iloc[-2])
        futures_change = (futures_latest - futures_prev) / futures_prev * 100
        
        # 计算现货当日涨跌幅
        spot_prev = float(df['Spot_Close'].iloc[-2])
        spot_change = (spot_latest - spot_prev) / spot_prev * 100
        
        latest_date_str = df.index[-1].strftime('%Y-%m-%d')
        
        # 4. 渲染顶部三大核心指标卡片
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                label=f"COMEX 期货价格 ({futures_ticker})", 
                value=f"${futures_latest:,.2f}", 
                delta=f"{futures_change:+.2f}%"
            )
        with col2:
            st.metric(
                label="伦敦金现货大盘 (XAU/USD)", 
                value=f"${spot_latest:,.2f}", 
                delta=f"{spot_change:+.2f}%"
            )
        with col3:
            # 基差如果是正数，代表远期升水 (Contango)
            st.metric(
                label="当前实时静态期现基差 (Basis)", 
                value=f"${current_basis:+.2f}",
                delta=f"锚定交易日: {latest_date_str}",
                delta_color="off"
            )
            
        st.markdown("---")
        
        # 5. 核心量化算法：滚动计算期货多周期变动率 (风控基准保持基于期货)
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
        display_df.index.name = '年份/历史区间'
        
        st.subheader("📊 期货历史年份多周期最大涨幅统计矩阵")
        st.table(display_df)
        
        # 6. 核心可视化：期现价格对比走势图
        st.subheader("📈 黄金期货 vs 伦敦金现货 历史收盘走势对比")
        chart_data = df.loc[df.index.year >= 2024, ['Close', 'Spot_Close']].copy()
        chart_data.columns = ['COMEX 期货价格', '伦敦金现货价格']
        st.line_chart(chart_data)
        
        # 7. 期现明细数据表
        st.subheader("📋 交易所期现联动最近 5 个交易日明细")
        recent_history = df.tail(5)[['Open', 'High', 'Low', 'Close', 'Spot_Close', 'Volume']].copy()
        recent_history['Basis'] = recent_history['Close'] - recent_history['Spot_Close']
        
        # 格式化输出
        recent_history['Open'] = recent_history['Open'].map('${:,.2f}'.format)
        recent_history['High'] = recent_history['High'].map('${:,.2f}'.format)
        recent_history['Low'] = recent_history['Low'].map('${:,.2f}'.format)
        recent_history['Close'] = recent_history['Close'].map('${:,.2f}'.format)
        recent_history['Spot_Close'] = recent_history['Spot_Close'].map('${:,.2f}'.format)
        recent_history['Basis'] = recent_history['Basis'].map('${:+.2f}'.format)
        recent_history['Volume'] = recent_history['Volume'].map('{:,.0f}'.format)
        recent_history.index = recent_history.index.strftime('%Y-%m-%d')
        
        # 调换一下列顺序，让期现放在一起好看
        recent_history = recent_history[['Open', 'High', 'Low', 'Close', 'Spot_Close', 'Basis', 'Volume']]
        st.dataframe(recent_history, use_container_width=True)
        
        st.info("💡 **智驭风控提示**：当前看板已全面接入期现双轨校验。当基差 (Basis) 异常拉大时，代表市场资金借贷成本高企或挤仓风险加剧，策略执行时需注意跨月展期滑点。")
        
    else:
        st.error("期现任意数据源返回空，请检查网络或稍后重试。")
except Exception as e:
    st.error(f"系统运行或计算异常: {e}")
