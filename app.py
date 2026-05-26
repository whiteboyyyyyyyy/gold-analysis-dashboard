import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="日期格式檢查", layout="wide")

@st.cache_data
def load_csv(filepath):
    df = pd.read_csv(filepath)
    df.columns = [col.strip().strip('"') for col in df.columns]
    df['日期'] = pd.to_datetime(df['日期'])
    return df

DATA_DIR = "data"

spot_weekly = load_csv(os.path.join(DATA_DIR, "london_gold_weekly.csv"))
sge_weekly = load_csv(os.path.join(DATA_DIR, "sge_spot_weekly.csv"))

st.subheader("倫敦金現貨週線 CSV 原始內容（前5行）")
with open(os.path.join(DATA_DIR, "london_gold_weekly.csv"), "r") as f:
    for i, line in enumerate(f):
        if i < 5:
            st.text(line.strip())

st.subheader("上海金現貨週線 CSV 原始內容（前5行）")
with open(os.path.join(DATA_DIR, "sge_spot_weekly.csv"), "r") as f:
    for i, line in enumerate(f):
        if i < 5:
            st.text(line.strip())

st.subheader("倫敦金現貨週線 日期")
st.write("類型:", spot_weekly['日期'].dtype)
st.write("前5個:", spot_weekly['日期'].head().tolist())

st.subheader("上海金現貨週線 日期")
st.write("類型:", sge_weekly['日期'].dtype)
st.write("前5個:", sge_weekly['日期'].head().tolist())

# 手動比較日期字串
spot_dates = set(spot_weekly['日期'].dt.strftime('%Y-%m-%d').tolist())
sge_dates = set(sge_weekly['日期'].dt.strftime('%Y-%m-%d').tolist())

st.subheader("日期字串交集")
st.write("倫敦金週線日期數:", len(spot_dates))
st.write("上海金週線日期數:", len(sge_dates))
common = spot_dates & sge_dates
st.write("交集數量:", len(common))
if common:
    st.write("交集:", sorted(common))
else:
    st.write("倫敦金日期範例:", sorted(list(spot_dates))[:5])
    st.write("上海金日期範例:", sorted(list(sge_dates))[:5])
