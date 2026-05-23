import streamlit as st
import requests

st.set_page_config(page_title="调试 GoldPrice.Today", layout="wide")

st.title("🔍 GoldPrice.Today API 调试")

# 尝试多个可能的接口地址
urls_to_test = [
    ("主接口 USD", "https://data-asg.goldprice.com/dbXRates/USD"),
    ("主接口 CNY", "https://data-asg.goldprice.com/dbXRates/CNY"),
    ("备用接口 USD", "https://data-asg.goldprice.com/dbXRates/USD/oz"),
    ("直接域名", "https://www.goldprice.today/api/latest"),
    ("旧版接口", "https://api.goldprice.today/v1/price/USD"),
]

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

for name, url in urls_to_test:
    st.subheader(f"测试: {name}")
    st.code(f"URL: {url}")
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        st.write(f"状态码: {resp.status_code}")
        st.write(f"响应长度: {len(resp.text)} 字符")
        
        if resp.status_code == 200:
            try:
                data = resp.json()
                st.json(data)
                
                # 尝试提取价格
                if 'items' in data and data['items']:
                    price = data['items'][0].get('xauPrice')
                    st.success(f"提取到价格: {price}")
                elif 'price' in data:
                    st.success(f"提取到价格: {data['price']}")
                else:
                    st.warning("未找到价格字段，请查看上方 JSON 结构")
            except:
                st.text(resp.text[:500])
        else:
            st.error(f"请求失败，状态码: {resp.status_code}")
    except Exception as e:
        st.error(f"请求异常: {e}")

st.markdown("---")
st.info("请把上面输出的结果截图或复制给我，我来调整接口地址和解析逻辑。")
