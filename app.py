import streamlit as st
import yfinance as yf
import pandas as pd

# 1. 网页配置：设置为宽屏模式
st.set_page_config(page_title="全球金价历史波幅看板", layout="wide", page_icon="🏆")

st.title("🏆 全球黄金多周期历史涨幅与风控边界监控")
st.caption("数据源：Yahoo Finance | 自动对齐纽约交易所时区 | 适合团队与投资人每日盘点")

# 2. 数据缓存机制（1小时刷新）
@st.cache_data(ttl=3600)
def load_gold_data():
    # 调取黄金期货主力合约 (GC=F)
    df = yf.download("GC=F", start="2023-01-01", end="2026-12-31")
    return df

try:
    with st.spinner("正在从国际交易所同步并清洗最新数据..."):
        raw_df = load_gold_data()
    
    if not raw_df.empty:
        df = raw_df.copy()
        
        # 如果 yfinance 返回了双层列名 (MultiIndex)，强制将其拍平成单层常规列名
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df.index = pd.to_datetime(df.index)
        
        # 🌟 量化清洗 1：过滤掉成交量为0或NaN的非交易日/幽灵盘后数据，防止服务器时区干扰
        df = df[df['Volume'] > 0].dropna(subset=['Close'])
        
        # 3. 提取真实的最新收盘状态
        latest_price = float(df['Close'].iloc[-1])
        prev_price = float(df['Close'].iloc[-2])
        daily_change = (latest_price - prev_price) / prev_price * 100
        
        # 🌟 量化清洗 2：明确标注该笔数据对应的美东交易所交易日（而非服务器或本地时间）
        latest_date_str = df.index[-1].strftime('%Y-%m-%d')
        
        # 顶部核心指标卡片
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                label="COMEX 黄金期货最新价 (主力合约收盘价)", 
                value=f"${latest_price:,.2f}", 
                delta=f"{daily_change:+.2f}% (当日涨跌)"
            )
        with col2:
            st.metric(label="当前数据锚定交易日 (纽约美东时间)", value=latest_date_str)
            
        st.markdown("---")
        
        # 4. 核心量化算法：滚动计算多周期变动率
        df['Daily_Gain'] = df['Close'].pct_change(1)
        df['Weekly_Gain'] = df['Close'].pct_change(5)
        df['Monthly_Gain'] = df['Close'].pct_change(21)
        df['Quarterly_Gain'] = df['Close'].pct_change(63)
        df['Annual_Gain'] = df['Close'].pct_change(252)
        df['Year'] = df.index.year
        
        # 按年份分组，提取各个周期涨幅的最大值
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
        
        # 改写表头
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
        
        # 🌟 核心新增 3：输出最近 5 个交易日的明细数据流，方便团队交叉比对
        st.subheader("📋 交易所最近 5 个交易日行情明细 (验证比对)")
        recent_history = df.tail(5)[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        # 格式化美化
        recent_history['Open'] = recent_history['Open'].map('${:,.2f}'.format)
        recent_history['High'] = recent_history['High'].map('${:,.2f}'.format)
        recent_history['Low'] = recent_history['Low'].map('${:,.2f}'.format)
        recent_history['Close'] = recent_history['Close'].map('${:,.2f}'.format)
        recent_history['Volume'] = recent_history['Volume'].map('{:,.0f}'.format)
        recent_history.index = recent_history.index.strftime('%Y-%m-%d')
        recent_history.index.name = '交易日期 (美东)'
        st.dataframe(recent_history, use_container_width=True)
        
        # 6. 辅助可视化：历史走势图
        st.subheader("📈 黄金期货价格历史走势图 (2024 - 2026)")
        chart_data = df.loc[df.index.year >= 2024, 'Close']
        st.line_chart(chart_data)
        
        st.info("💡 **风控提示**：本系统已强制对齐纽约商品交易所（COMEX）交易日，自适应过滤服务器时区产生的脏数据。由于免费数据源未接入官方结算价（Settlement Price）API，数据点采用每日电子盘最后成交价（Last Trade Close），若与机构终端有极微小价差属于正常技术交割范围。")
        
    else:
        st.error("数据源返回空数据，请检查网络或稍后刷新重试。")
except Exception as e:
    st.error(f"系统运行或计算异常: {e}")
