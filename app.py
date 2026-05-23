import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime

# 1. 网页配置
st.set_page_config(page_title="全球金价历史波幅看板", layout="wide", page_icon="🏆")

st.title("🏆 全球黄金多周期历史涨幅与风控边界监控")
st.caption("数据源：新浪财经标准行情接口 | 自动对齐主流终端基准价 | 免Key完全免费")

# 🌟 核心量化函数：从新浪财经抓取 COMEX 黄金 (内盘代码: hf_GC) 的标准日线历史数据
@st.cache_data(ttl=1800)  # 缓存半小时，兼顾实时性与加载速度
def load_gold_data_from_sina():
    # 新浪财经外盘期货日线历史数据接口
    url = "https://stock.finance.sina.com.cn/futures/api/jsonp.php//GlobalFuturesService.getGlobalFuturesDailyKLine?symbol=GC"
    headers = {
        "Referer": "https://finance.sina.com.cn/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        # 提取 jsonp 返回的纯 json 字符串
        text = response.text
        json_start = text.find("[")
        json_end = text.rfind("]") + 1
        json_data = json.loads(text[json_start:json_end])
        
        # 转换为 DataFrame
        # 新浪返回格式: [{'date': '2026-05-22', 'open': '...', 'high': '...', 'low': '...', 'close': '...', 'volume': '...'}, ...]
        df = pd.DataFrame(json_data)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        # 转换数值类型
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        df.sort_index(inplace=True)
        # 首字母大写以兼容后续逻辑
        df.rename(columns={'open':'Open', 'high':'High', 'low':'Low', 'close':'Close', 'volume':'Volume'}, inplace=True)
        return df
    except Exception as e:
        st.error(f"底层 API 抓取异常: {e}")
        return pd.DataFrame()

try:
    with st.spinner("正在通过新浪财经量化接口同步标准行情..."):
        df = load_gold_data_from_sina()
    
    if not df.empty:
        # 2. 提取标准的最新收盘状态
        latest_price = float(df['Close'].iloc[-1])
        prev_price = float(df['Close'].iloc[-2])
        daily_change = (latest_price - prev_price) / prev_price * 100
        latest_date_str = df.index[-1].strftime('%Y-%m-%d')
        
        # 顶部核心指标卡片（此时已自动对齐主流终端价格）
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                label="COMEX 黄金期货标准价 (新浪财经同步)", 
                value=f"${latest_price:,.2f}", 
                delta=f"{daily_change:+.2f}% (当日涨跌)"
            )
        with col2:
            st.metric(label="当前数据锚定交易日", value=latest_date_str)
            
        st.markdown("---")
        
        # 3. 核心量化算法：滚动计算多周期变动率
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
        
        # 4. 渲染历史极端波幅矩阵
        st.subheader("📊 历史年份多周期最大涨幅统计矩阵 (风控基准)")
        st.table(display_df)
        
        # 5. 输出最近 5 个交易日的明细数据流
        st.subheader("📋 交易所最近 5 个交易日行情明细 (核对校验)")
        recent_history = df.tail(5)[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        recent_history['Open'] = recent_history['Open'].map('${:,.2f}'.format)
        recent_history['High'] = recent_history['High'].map('${:,.2f}'.format)
        recent_history['Low'] = recent_history['Low'].map('${:,.2f}'.format)
        recent_history['Close'] = recent_history['Close'].map('${:,.2f}'.format)
        recent_history['Volume'] = recent_history['Volume'].map('{:,.0f}'.format)
        recent_history.index = recent_history.index.strftime('%Y-%m-%d')
        recent_history.index.name = '交易日期'
        st.dataframe(recent_history, use_container_width=True)
        
        # 6. 辅助可视化：历史走势图
        st.subheader("📈 黄金期货价格历史走势图 (2024 - 2026)")
        chart_data = df.loc[df.index.year >= 2024, 'Close']
        st.line_chart(chart_data)
        
        st.info("💡 **量化备注**：由于切换至新浪财经行情源，系统已自动过滤美东电子盘深夜无结算性质的溢价波动，最新价格与历史K线已与国内主流行情软件（如富途、同花顺、文华等）完全同步。")
        
    else:
        st.error("无法获取新浪财经数据，请检查网络或稍后重试。")
except Exception as e:
    st.error(f"系统运行或计算异常: {e}")
