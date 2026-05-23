import streamlit as st
import requests
import json

st.set_page_config(page_title="AllTick 实时报价调试", layout="wide")
st.title("🔍 AllTick 实时报价接口调试")

ALLTICK_TOKEN = "38aac33acb3ad3f84a2a7a2850a3344a-c-app"
url = "https://quote.alltick.co/quote-b-api/quote"

# 测试1: XAUUSD
st.subheader("测试1: XAUUSD")
query1 = {"trace": "test", "data": {"code": "XAUUSD"}}
try:
    resp = requests.get(url, params={"token": ALLTICK_TOKEN, "query": json.dumps(query1)}, timeout=10)
    st.write("状态码:", resp.status_code)
    if resp.status_code == 200:
        st.json(resp.json())
    else:
        st.text(resp.text[:500])
except Exception as e:
    st.error(f"异常: {e}")

# 测试2: GOLD
st.subheader("测试2: GOLD")
query2 = {"trace": "test", "data": {"code": "GOLD"}}
try:
    resp = requests.get(url, params={"token": ALLTICK_TOKEN, "query": json.dumps(query2)}, timeout=10)
    st.write("状态码:", resp.status_code)
    if resp.status_code == 200:
        st.json(resp.json())
    else:
        st.text(resp.text[:500])
except Exception as e:
    st.error(f"异常: {e}")

# 测试3: USDCNY
st.subheader("测试3: USDCNY")
query3 = {"trace": "test", "data": {"code": "USDCNY"}}
try:
    resp = requests.get(url, params={"token": ALLTICK_TOKEN, "query": json.dumps(query3)}, timeout=10)
    st.write("状态码:", resp.status_code)
    if resp.status_code == 200:
        st.json(resp.json())
    else:
        st.text(resp.text[:500])
except Exception as e:
    st.error(f"异常: {e}")
