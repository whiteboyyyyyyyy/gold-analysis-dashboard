import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="週線調試", layout="wide")
st.title("🔍 週線日期格式調試")

@st.cache_data
def load_csv(filepath):
    df = pd.read_csv(filepath)
    df.columns = [col.strip().strip('"') for col in df.columns]
    df['日期'] = pd.to_datetime(df['日期'])
    return df

DATA_DIR = "data"

spot_weekly = load_csv(os.path.join(DATA_DIR, "london_gold_weekly.csv"))
sge_weekly = load_csv(os.path.join(DATA_DIR, "sge_spot_weekly.csv"))

st.subheader("倫敦金週線")
st.write(f"筆數: {len(spot_weekly)}")
st.write("日期範圍:", spot_weekly['日期'].min(), "~", spot_weekly['日期'].max())
st.write("前5筆日期:", spot_weekly['日期'].head().tolist())
st.write("後5筆日期:", spot_weekly['日期'].tail().tolist())

st.subheader("上海金週線")
st.write(f"筆數: {len(sge_weekly)}")
st.write("日期範圍:", sge_weekly['日期'].min(), "~", sge_weekly['日期'].max())
st.write("前5筆日期:", sge_weekly['日期'].head().tolist())
st.write("後5筆日期:", sge_weekly['日期'].tail().tolist())

# 檢查交集
s1 = spot_weekly.set_index('日期')['收市']
s2 = sge_weekly.set_index('日期')['收市']
common = s1.index.intersection(s2.index)
st.subheader(f"共同日期數: {len(common)}")
if len(common) > 0:
    st.write("共同日期:", common.tolist())
else:
    st.error("沒有共同日期！")
    st.write("倫敦金日期範例:", s1.index[:5].tolist())
    st.write("上海金日期範例:", s2.index[:5].tolist())
