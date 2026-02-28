import os
import requests
from bs4 import BeautifulSoup

# --- 1. 設定區 (請務必填寫正確的 Email) ---
USER_AGENT = "Shin Chung Shao (scshao@infodoc.com.tw)" # SEC 規定必須包含姓名與 Email
GEMINI_API_KEY = "AIzaSyAlGu21J7-HqcGR7X5ePmj3uPt3kkzpS1s"
IBM_CIK = "0000051143" # IBM 的唯一識別碼

# 初始化 Gemini
# genai.configure(api_key=GEMINI_API_KEY)
#model = genai.GenerativeModel('gemini-1.5-flash-latest')
# model = genai.GenerativeModel('gemini-2.0-flash')
#model = genai.GenerativeModel('gemini-1.5-pro')
#model = genai.GenerativeModel('gemini-1.5-pro-latest')

# --- 2. 直接從 SEC API 抓取最新 10-K ---
def get_ibm_latest_10k():
    print("正在透過 SEC 官方 API 搜尋 IBM 最新報表...")
    headers = {'User-Agent': USER_AGENT}
    
    # 步驟 A: 取得 IBM 的所有報表清單
    # SEC 提供 JSON 格式的索引資料
    url = f"https://data.sec.gov/submissions/CIK{IBM_CIK}.json"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        raise Exception(f"無法存取 SEC 資料，狀態碼: {response.status_code}。請檢查 Email 格式。")
    
    data = response.json()
    filings = data['filings']['recent']
    
    # 步驟 B: 尋找最近的一個 '10-K'
    target_index = -1
    for i, form in enumerate(filings['form']):
        if form == '10-K':
            target_index = i
            break
            
    if target_index == -1:
        raise Exception("找不到 IBM 的 10-K 報表。")

    acc_num = filings['accessionNumber'][target_index].replace('-', '')
    doc_name = filings['primaryDocument'][target_index]
    
    # 步驟 C: 建立檔案下載連結
    # 格式: https://www.sec.gov/Archives/edgar/data/{CIK}/{AccNum}/{DocName}
    file_url = f"https://www.sec.gov/Archives/edgar/data/{IBM_CIK.strip('0')}/{acc_num}/{doc_name}"
    
    print(f"正在下載報表文件: {file_url}")
    file_response = requests.get(file_url, headers=headers)
    return file_response.text

# --- 3. 清理 HTML 並分析 ---
def analyze_data(raw_html):
    print("正在解析內容並交給 Gemini 分析...")
    soup = BeautifulSoup(raw_html, 'html.parser')
    
    # 移除干擾元素
    for s in soup(['script', 'style']):
        s.decompose()
        
    clean_text = soup.get_text(separator=' ', strip=True)
    
    # 傳給 Gemini (取前 500,000 字元)
    # prompt = f"""
    # 你是一位專業的證券分析師。請根據以下 IBM 10-K 報表內容，產出一份給投資人的摘要：
    # 1. 營收與獲利：去年表現如何？
    # 2. 業務重點：雲端與 AI 業務的成長數據。
    # 3. 自由現金流：數據為何？是否足以支付股利？
    # 4. 潛在風險：管理層最擔心的三個問題。
    
    # 報表內容：
    # {clean_text[:500000]}
    # """
    
    # response = model.generate_content(prompt)
    return clean_text # response.text

# --- 4. 執行 ---
if __name__ == "__main__":
    try:
        html_content = get_ibm_latest_10k()
        result = analyze_data(html_content)
        print("\n" + "="*50)
        print("📊 IBM 最新年報 AI 分析報告")
        print("="*50 + "\n")
        print(result)
    except Exception as e:
        print(f"❌ 錯誤: {e}")