import streamlit as st
import requests
import json
from datetime import datetime

st.set_page_config(page_title="AllTick GOLD 调试", layout="wide")
st.title("🔍 AllTick GOLD 代码测试")

ALLTICK_TOKEN = "38aac33acb3ad3f84a2a7a2850a3344a-c-app"

end_unix = int(datetime(2024, 6, 30).timestamp())

query_data = {
    "trace": "test",
    "data": {
        "code": "GOLD",
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

try:
    resp = requests.get(url, params=params, timeout=15)
    st.write("状态码:", resp.status_code)
    if resp.status_code == 200:
        data = resp.json()
        st.write("code:", data.get('code'))
        st.write("msg:", data.get('msg'))
        kline_list = data.get('data', {}).get('kline_list', [])
        st.write(f"K线数量: {len(kline_list)}")
        if kline_list:
            st.json(kline_list[:3])
        else:
            st.json(data)
    else:
        st.text(resp.text[:500])
except Exception as e:
    st.error(f"异常: {e}")
