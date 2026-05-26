import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="週線調試", layout="wide")
st.title("🔍 週線日期調試")

@st.cache_data
def load_csv(filepath):
    df = pd.read_csv(filepath)
    df.columns = [col.strip().strip('"') for col in df.columns]
    df['日期'] = pd.to_datetime(df['日期'])
    return df

DATA_DIR = "data"

spot_weekly = load_csv(os.path.join(DATA_DIR, "london_gold_weekly.csv"))
futures_weekly = load_csv(os.path.join(DATA_DIR, "comex_futures_weekly.csv"))
sge_weekly = load_csv(os.path.join(DATA_DIR, "sge_spot_weekly.csv"))
sge_td_weekly = load_csv(os.path.join(DATA_DIR, "sge_td_weekly.csv"))

for name, df in [("倫敦金現貨週線", spot_weekly), ("COMEX期貨週線", futures_weekly), ("上海金現貨週線", sge_weekly), ("Au(T+D)週線", sge_td_weekly)]:
    st.subheader(name)
    st.write(f"筆數: {len(df)}")
    st.write(f"日期範圍: {df['日期'].min()} ~ {df['日期'].max()}")
    st.write(f"日期類型: {df['日期'].dtype}")
    st.write(f"前5個日期: {df['日期'].head().tolist()}")
    st.write(f"後5個日期: {df['日期'].tail().tolist()}")

st.subheader("交集測試")
for name1, df1 in [("上海金現貨", sge_weekly), ("Au(T+D)", sge_td_weekly)]:
    for name2, df2 in [("倫敦金現貨", spot_weekly), ("COMEX期貨", futures_weekly)]:
        s1 = df1.set_index('日期')['收市']
        s2 = df2.set_index('日期')['收市']
        common = s1.index.intersection(s2.index)
        st.write(f"{name1} vs {name2}: 共同日期數 = {len(common)}")
        if len(common) > 0:
            st.write(f"  範例: {common[:3].tolist()}")
