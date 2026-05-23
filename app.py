import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# 1. 网页基础配置
st.set_page_config(page_title="智驭量化·全球金价风控监控", layout="wide", page_icon="🏆")

st.title("🏆 智驭量化：全球黄金多周期历史涨幅与风控边界监控")
st.caption("数据源：Yahoo Finance 机构单月历史流 | 彻底解决连续合约展期溢价误差")

# 2. 🌟 核心破局点：侧边栏合约控制面板
st.sidebar.header("⚙️ 交易所合约配置")
st.sidebar.markdown("由于全球商品期货存在**远期升水（Contango）**，连续合约（GC=F）自动展期会导致数据失真。请选择你当前看盘终端（如富途）正在交易的主力月份：")

# 映射国人看盘习惯的合约月份
contract_options = {
    "2026年06月主力 (GCM26)": "GCM26.CMX",
    "2026年08月远期 (GCQ26)": "GCQ26.CMX",
    "2026年12月远期 (GCZ26)": "GCZ26.CMX",
    "CME官方连续合约 (存在展期跳空)": "GC=F"
}

selected_label = st.sidebar.selectbox("当前锚定主力合约", list(contract_options.keys()), index=0)
target_ticker = contract_options[selected_label]

st.sidebar.info(f"📡 当前系统底层已强制锁死代码：`{target_ticker}`，拒绝无意义的跨月基差干扰。")

# 3. 数据缓存机制（1小时刷新历史流）
@st.cache_data(ttl=3600)
def load_gold_data(ticker):
    try:
        # 调取指定的独立交割月份合约
        df = yf.download(ticker, start="2024-01-01", end="2026-12-31")
        return df
    except Exception as e:
        st.error(f"从交易所拉取单月合约数据失败: {e}")
        return pd.DataFrame()

try:
    with st.spinner(f"正在同步 {target_ticker} 交易所原始清洗数据..."):
        raw_df = load_gold_data(target_ticker)
    
    if not raw_df.empty:
        df = raw_df.copy()
        
        # 清洗 MultiIndex 列名（yfinance 新版标准清洗）
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df.index = pd.to_datetime(df.index)
        
        # 剔除无成交量的异常交易日
        df = df[df['Volume'] > 0].dropna(subset=['Close'])
        
        # 4. 提取最新价格状态
        latest_price = float(df['Close'].iloc[-1])
        prev_price = float(df['Close'].iloc[-2])
        daily_change = (latest_price - prev_price) / prev_price * 100
        latest_date_str = df.index[-1].strftime('%Y-%m-%d')
        
        # 顶部核心指标卡片
        col1, col2 = st.columns(2)
        with col2:
            st.metric(label="数据源锚定交易日 (美东时间)", value=latest_date_str)
        with col1:
            st.metric(
                label=f"COMEX 黄金期货最新价 ({target_ticker})", 
                value=f"${latest_price:,.2f}", 
                delta=f"{daily_change:+.2f}% (单月合约当日实际涨跌)"
            )
            
        st.markdown("---")
        
        # 5. 核心量化算法：滚动计算多周期变动率
        df['Daily_Gain'] = df['Close'].pct_change(1)
        df['Weekly_Gain'] = df['Close'].pct_change(5)
        df['Monthly_Gain'] = df['Close'].pct_change(21)
        df['Quarterly_Gain'] = df['Close'].pct_change(63)
        df['Annual_Gain'] = df['Close'].pct_change(252)
        df['Year'] = df.index.year
        
        # 计算历史区间最大波幅矩阵
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
        
        # 渲染历史极端波幅矩阵
        st.subheader("📊 该合约特定交割期多周期最大涨幅统计 (风控基准)")
        st.table(display_df)
        
        # 6. 输出最近 5 个交易日的明细数据流
        st.subheader("📋 交易所最近 5 个交易日行情明细 (核对校验)")
        recent_history = df.tail(5)[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        recent_history['Open'] = recent_history['Open'].map('${:,.2f}'.format)
        recent_history['High'] = recent_history['High'].map('${:,.2f}'.format)
        recent_history['Low'] = recent_history['Low'].map('${:,.2f}'.format)
        recent_history['Close'] = recent_history['Close'].map('${:,.2f}'.format)
        recent_history['Volume'] = recent_history['Volume'].map('{:,.0f}'.format)
        recent_history.index = recent_history.index.strftime('%Y-%m-%d')
        st.dataframe(recent_history, use_container_width=True)
        
        # 7. 历史走势图
        st.subheader("📈 目标合约历史走势图")
        chart_data = df.loc[df.index.year >= 2024, 'Close']
        st.line_chart(chart_data)
        
    else:
        st.error("数据源返回空，请检查交易日或稍后重试。")
except Exception as e:
    st.error(f"系统运行或计算异常: {e}")
