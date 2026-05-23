import streamlit as st
import pandas as pd
import akshare as ak
from datetime import datetime

# 1. 网页配置
st.set_page_config(page_title="全球金价历史波幅看板", layout="wide", page_icon="🏆")

st.title("🏆 全球黄金多周期历史涨幅与风控边界监控")
st.caption("数据源：AkShare (东方财富底座) | 自动对齐国内行情终端行情流")

# 2. 数据缓存机制（外盘日线建议缓存1小时）
@st.cache_data(ttl=3600)
def load_gold_data_akshare():
    try:
        # 抓取 COMEX 黄金连续合约历史数据
        df = ak.futures_foreign_hist(symbol="GC")
        if not df.empty:
            # AkShare 返回列名通常为: date, open, high, low, close, volume
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            # 统一转换数值类型
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
            df.sort_index(inplace=True)
            # 大写重命名以兼容量化算法
            df.rename(columns={'open':'Open', 'high':'High', 'low':'Low', 'close':'Close', 'volume':'Volume'}, inplace=True)
            return df
    except Exception as e:
        st.error(f"AkShare 接口调用或网络异常: {e}")
    return pd.DataFrame()

try:
    with st.spinner("正在通过 AkShare 引擎清洗并同步国际行情..."):
        df = load_gold_data_akshare()
    
    if not df.empty:
        # 3. 提取最新收盘状态
        latest_price = float(df['Close'].iloc[-1])
        prev_price = float(df['Close'].iloc[-2])
        daily_change = (latest_price - prev_price) / prev_price * 100
        latest_date_str = df.index[-1].strftime('%Y-%m-%d')
        
        # 顶部核心指标卡片
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                label="COMEX 黄金期货最新价 (AkShare 同步)", 
                value=f"${latest_price:,.2f}", 
                delta=f"{daily_change:+.2f}% (当日涨跌)"
            )
        with col2:
            st.metric(label="当前数据锚定交易日", value=latest_date_str)
            
        st.markdown("---")
        
        # 4. 核心量化算法：滚动计算多周期变动率
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
        
        # 5. 渲染历史极端波幅矩阵
        st.subheader("📊 历史年份多周期最大涨幅统计矩阵 (风控基准)")
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
        
        # 7. 辅助可视化：历史走势图
        st.subheader("📈 黄金期货价格历史走势图")
        chart_data = df.loc[df.index.year >= 2024, 'Close']
        st.line_chart(chart_data)
        
        st.info("💡 **量化备注**：当前看板底座已切换至 AkShare 跨境期货数据流。东方财富的连续合约展期算法比原生新浪更贴合国内主流行情软件（如富途），能有效压制跨月基差产生的假跳空。")
        
    else:
        st.error("数据源返回空，可能触发了底层接口限流，请稍后重试。")
except Exception as e:
    st.error(f"系统运行或计算异常: {e}")
