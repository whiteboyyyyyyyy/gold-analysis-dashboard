import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

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

# 3. 弹性数据清洗函数（核心容错升级）
def clean_yfinance_df(df, target_col='Close'):
    """自动兼容新旧版 yfinance 的 MultiIndex 或 SingleIndex 列名"""
    if df.empty:
        return pd.Series(dtype='float64')
    
    # 如果是多级索引 (Ticker, Price_Type)，降级取第一层
    if isinstance(df.columns, pd.MultiIndex):
        # 寻找包含目标字段的列
        available_cols = df.columns.get_level_values(0)
        if target_col in available_cols:
            return df[target_col].iloc[:, 0] if df[target_col].ndim > 1 else df[target_col]
    else:
        if target_col in df.columns:
            return df[target_col]
            
    # 回退机制：如果找不到，强行取第一列
    return df.iloc[:, 0]

# 4. 双通道数据弹性抓取
@st.cache_data(ttl=1800) # 提高刷新率到半小时
def load_market_data(fut_ticker):
    # 为确保滚动计算（如年线252日）数据充足，从2023年开始拉取
    start_date = "2023-01-01" 
    
    try:
        # 同步一次性拉取，减少网络握手次数
        raw_data = yf.download([fut_ticker, "XAUUSD=X"], start=start_date)
        if raw_data.empty:
            return pd.DataFrame()
            
        # 弹性抽取期货收盘价与现货收盘价
        if isinstance(raw_data.columns, pd.MultiIndex):
            # 新版 yfinance 联合下载格式处理
            try:
                f_close = raw_data['Close'][fut_ticker]
                s_close = raw_data['Close']['XAUUSD=X']
                f_vol = raw_data['Volume'][fut_ticker]
            except KeyError:
                # 备用方案：如果多股下载索引格式异常，退回单股独立下载
                df_f = yf.download(fut_ticker, start=start_date)
                df_s = yf.download("XAUUSD=X", start=start_date)
                return combine_dfs(df_f, df_s)
        else:
            st.error("数据源格式异常")
            return pd.DataFrame()
            
        # 联立 DataFrame
        combined = pd.DataFrame({
            'Close': f_close,
            'Spot_Close': s_close,
            'Volume': f_vol
        })
        return combined
    except Exception as e:
        st.error(f"底层网络或接口异常: {e}")
        return pd.DataFrame()

def combine_dfs(df_f, df_s):
    """单股独立下载时的拼装路由"""
    f_c = clean_yfinance_df(df_f, 'Close')
    s_c = clean_yfinance_df(df_s, 'Close')
    f_v = clean_yfinance_df(df_f, 'Volume')
    
    combined = pd.DataFrame({'Close': f_c, 'Spot_Close': s_c, 'Volume': f_v})
    return combined

try:
    with st.spinner("🚀 智驭数据路由正在穿透 CME 与伦敦清算所..."):
        df = load_market_data(futures_ticker)
    
    if not df.empty:
        # 5. 弹性时序对齐与去噪
        df.index = pd.to_datetime(df.index)
        # 填充现货在期货非交易日（如特定国内假日前夕）产生的微小空缺（向前填充）
        df['Spot_Close'] = df['Spot_Close'].ffill()
        df['Close'] = df['Close'].ffill()
        
        # 剔除完全没有结算价值的极端非交易行
        df = df.dropna(subset=['Close', 'Spot_Close'])
        
        # 6. 核心量化指标实时计算
        futures_latest = float(df['Close'].iloc[-1])
        spot_latest = float(df['Spot_Close'].iloc[-1])
        current_basis = futures_latest - spot_latest
        
        futures_prev = float(df['Close'].iloc[-2]) if len(df) > 1 else futures_latest
        futures_change = (futures_latest - futures_prev) / futures_prev * 100 if futures_prev != 0 else 0
        
        spot_prev = float(df['Spot_Close'].iloc[-2]) if len(df) > 1 else spot_latest
        spot_change = (spot_latest - spot_prev) / spot_prev * 100 if spot_prev != 0 else 0
        
        latest_date_str = df.index[-1].strftime('%Y-%m-%d')
        
        # 7. 渲染顶部核心数据面板
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
                delta=f"更新节点: {latest_date_str}",
                delta_color="off"
            )
            
        st.markdown("---")
        
        # 8. 滚动风控矩阵计算（基于期货历史流）
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
        
        # 9. 可视化期现走势
        st.subheader("📈 期现双轨收盘走势对比")
        chart_data = df.loc[df.index.year >= 2024, ['Close', 'Spot_Close']].copy()
        chart_data.columns = ['COMEX 期货价格', '伦敦金现货大盘']
        st.line_chart(chart_data)
        
        # 10. 历史明细流
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
        st.error("⚠️ 警告：Yahoo Finance 服务器当前拒绝了联立请求。这通常是因为周末交易所停盘导致时序切片未生成。请在左侧侧边栏尝试切换至其他远期合约激活数据流。")
        
except Exception as e:
    st.error(f"🚨 系统运行异常: {e}")
