import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="调试 AllTick", layout="wide")
st.title("🔍 AllTick API 调试")

ALLTICK_TOKEN = "38aac33acb3ad3f84a2a7a2850a3344a-c-app"

# 测试1: 直接看原始返回
url = "https://quote.alltick.io/quote-gold-api/history"
params = {
    "token": ALLTICK_TOKEN,
    "code": "XAUUSD",
    "start_time": "2024-01-01",
    "end_time": "2024-01-31",
    "kline_type": 5
}

st.subheader("请求参数")
st.json(params)

try:
    resp = requests.get(url, params=params, timeout=15)
    st.subheader(f"状态码: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        st.subheader("完整返回结构")
        st.json(data)
        
        # 看有哪些键
        st.subheader("顶层键")
        st.write(list(data.keys()))
        
        if 'data' in data:
            st.subheader("data 层的键")
            st.write(list(data['data'].keys()) if isinstance(data['data'], dict) else type(data['data']))
    else:
        st.error(f"请求失败: {resp.status_code}")
        st.text(resp.text[:1000])
        
except Exception as e:
    st.error(f"异常: {e}")

# 测试2: 试试不同 kline_type
st.markdown("---")
st.subheader("测试不同 kline_type")

for kt in [1, 3, 5, 7]:
    params2 = {
        "token": ALLTICK_TOKEN,
        "code": "XAUUSD",
        "start_time": "2024-06-01",
        "end_time": "2024-06-05",
        "kline_type": kt
    }
    try:
        r = requests.get(url, params=params2, timeout=10)
        if r.status_code == 200:
            d = r.json()
            kline_count = len(d.get('data', {}).get('kline_list', [])) if d.get('data') else 0
            st.write(f"kline_type={kt}: 状态码={r.status_code}, K线数量={kline_count}")
        else:
            st.write(f"kline_type={kt}: 状态码={r.status_code}")
    except Exception as e:
        st.write(f"kline_type={kt}: 异常 {e}")
