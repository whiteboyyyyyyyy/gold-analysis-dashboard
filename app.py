import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# 1. 网页配置：设置为宽屏模式
st.set_page_config(page_title="全球金价历史波幅看板", layout="wide", page_icon="🏆")

st.title("🏆 全球黄金多周期历史涨幅与风控边界监控")
st.caption("数据源：Yahoo Finance 自动同步 | 适合每日收盘盘点与团队/投资人共享")

# 2. 数据缓存机制：1小时内重复访问直接读内存，防止触发接口限频，完全免费
@st.cache_data(ttl=3600)
def load_gold_data():
    # 调取自2023年开始的数据，确保2024年初计算252日年滚动涨幅时有足够的历史窗口
    df = yf.download("GC=F", start="2023-01-01", end="2026-12-31")
    return df

try:
    with st.spinner("正在从国际交易所同步最新历史数据..."):
        raw_df = load_gold_data()
    
    if not raw_df.empty:
        # 清洗索引
        df = raw_df.copy()
        df.index = pd.to_datetime(df.index)
        
        # 3. 提取实时最新收盘状态
        latest_price = float(df['Close'].iloc[-1])
        prev_price = float(df['Close'].iloc[-2])
        daily_change = (latest_price - prev_price) / prev_price * 100
        latest_date = df.index[-1].strftime('%Y-%m-%d')
        
        # 顶部核心指标卡片
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                label="COMEX 黄金期货最新价 (主力合约)", 
                value=f"${latest_price:,.2f}", 
                delta=f"{daily_change:+.2f}% (当日)"
            )
        with col2:
            st.metric(label="数据最新同步交易日 (UTC)", value=latest_date)
            
        st.markdown("---")
        
        # 4. 核心量化算法：滚动计算多周期变动率
        # 交易日标准换算：1日/5日(周)/21日(月)/63日(季)/252日(年)
        df['Daily_Gain'] = df['Close'].pct_change(1)
        df['Weekly_Gain'] = df['Close'].pct_change(5)
        df['Monthly_Gain'] = df['Close'].pct_change(21)
        df['Quarterly_Gain'] = df['Close'].pct_change(63)
        df['Annual_Gain'] = df['Close'].pct_change(252)
        df['Year'] = df.index.year
        
        # 按年份分组，提取各个周期涨幅的最大绝对值
        summary = df.groupby('Year').agg({
            'Daily_Gain': 'max',
            'Weekly_Gain': 'max',
            'Monthly_Gain': 'max',
            'Quarterly_Gain': 'max',
            'Annual_Gain': 'max'
        })
        
        # 格式化清洗：转换为百分比并过滤掉2023过渡年
        summary_pct = (summary * 100).round(2)
        display_df = summary_pct.loc[summary_pct.index >= 2024].copy()
        
        # 改写表头使其具备极佳的可读性
        for col in display_df.columns:
            display_df[col] = display_df[col].astype(str) + '%'
            
        display_df.columns = [
            '日最大涨幅', 
            '周最大涨幅 (5日滚动)', 
            '月最大涨幅 (21日滚动)', 
            '季最大涨幅 (63日滚动)', 
            '年内累计最大涨幅'
        ]
        display_df.index.name = '年份/历史区间'
        
        # 5. 渲染历史极端波幅矩阵
        st.subheader("📊 历史年份多周期最大涨幅统计矩阵 (风控基准)")
        st.table(display_df)
        
        # 6. 辅助可视化：历史走势图
        st.subheader("📈 黄金期货价格历史走势图 (2024 - 2026)")
        chart_data = df.loc[df.index.year >= 2024, 'Close']
        st.line_chart(chart_data)
        
        st.info("💡 系统提示：周/月/季度涨幅均采用量化滚动窗口（Rolling Window）算法，能完美捕获跨自然月、跨自然周的极端爆发性动量。")
        
    else:
        st.error("数据源返回空数据，请检查网络或稍后刷新重试。")
except Exception as e:
    st.error(f"系统运行或计算异常: {e}")
