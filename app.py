import streamlit as st
import requests
import json
from datetime import datetime

st.set_page_config(page_title="AllTick 调试 v2", layout="wide")
st.title("🔍 AllTick API 调试 (正确接口)")

ALLTICK_TOKEN = "38aac33acb3ad3f84a2a7a2850a3344a-c-app"

end_unix = int(datetime(2024, 6, 30).timestamp())

# 测试1: 官方文档格式
st.subheader("测试1: 标准 query 格式")
query_data = {
    "trace": "test",
    "data": {
        "code": "XAUUSD",
        "kline_type": 8,
        "kline_timestamp_end": end_unix,
        "query_kline_num": 10,
        "adjust_type": 0
    }
}

url = "https://quote.alltick.co/quote-b-api/kline"
params = {
    "token": ALLTICK_TOKEN,
    "query": json.dumps(query_data)
}

st.write("**请求 URL:**", url)
st.write("**query 参数:**")
st.json(query_data)

try:
    resp = requests.get(url, params=params, timeout=15)
    st.write("**状态码:**", resp.status_code)
    
    if resp.status_code == 200:
        data = resp.json()
        st.write("**返回 code:**", data.get('code'))
        st.write("**返回 msg:**", data.get('msg'))
        st.json(data)
    else:
        st.text(resp.text[:500])
except Exception as e:
    st.error(f"异常: {e}")

# 测试2: 不同 kline_type
st.markdown("---")
st.subheader("测试2: 不同 kline_type 值")

for kt in [1, 2, 3, 4, 5, 6, 7, 8]:
    query_data2 = {
        "trace": "test",
        "data": {
            "code": "XAUUSD",
            "kline_type": kt,
            "kline_timestamp_end": end_unix,
            "query_kline_num": 5,
            "adjust_type": 0
        }
    }
    try:
        r = requests.get(url, params={"token": ALLTICK_TOKEN, "query": json.dumps(query_data2)}, timeout=10)
        if r.status_code == 200:
            d = r.json()
            code = d.get('code', 'N/A')
            msg = d.get('msg', '')
            klist = d.get('data', {}).get('kline_list', [])
            st.write(f"kline_type={kt}: code={code}, msg={msg}, K线数={len(klist)}")
        else:
            st.write(f"kline_type={kt}: HTTP {r.status_code}")
    except Exception as e:
        st.write(f"kline_type={kt}: 异常 {e}")

# 测试3: 试试 XAGUSD (白银)
st.markdown("---")
st.subheader("测试3: 换品种 XAGUSD")
query_data3 = {
    "trace": "test",
    "data": {
        "code": "XAGUSD",
        "kline_type": 8,
        "kline_timestamp_end": end_unix,
        "query_kline_num": 5,
        "adjust_type": 0
    }
}
try:
    r = requests.get(url, params={"token": ALLTICK_TOKEN, "query": json.dumps(query_data3)}, timeout=10)
    st.write("状态码:", r.status_code)
    if r.status_code == 200:
        st.json(r.json())
    else:
        st.text(r.text[:300])
except Exception as e:
    st.error(f"异常: {e}")
