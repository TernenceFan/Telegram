from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import pandas as pd
from datetime import datetime, timedelta
import time

def main():
    # 設置 Selenium WebDriver 及其選項
    options = Options()
    options.add_argument("--headless")  # 隱藏瀏覽器視窗
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")

    # 使用 ChromeDriver
    driver = webdriver.Chrome(service=Service("/Users/ternencevan/Library/Mobile Documents/com~apple~CloudDocs/python/myenv/bin/chromedriver"), options=options)

    try:
        # 打開目標網站進行登入
        driver.get("http://118.163.190.55:5000/index.html")

        # 找到登入的輸入框並輸入帳號與密碼
        member_id_input = driver.find_element(By.NAME, "memberId")  # 根據表單的 name 屬性選擇輸入框
        password_input = driver.find_element(By.NAME, "password")
        
        member_id_input.send_keys("11")
        password_input.send_keys("3132888")
        password_input.send_keys(Keys.RETURN)  # 模擬按下回車鍵進行登入

        time.sleep(3)  # 等待登入頁面加載

        # 登入成功後，導航到特定頁面以獲取數據
        driver.get("http://118.163.190.55:5000/api/reports/deposit-withdraw")

        # 獲取數據
        page_source = driver.page_source

        # 解析和處理數據 (您可以根據具體的網頁結構進行處理)
        # 這裡我們假設數據是以某種表格形式呈現的
        rows = driver.find_elements(By.TAG_NAME, "tr")
        data = []

        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if cells:
                time_utc = cells[0].text
                time_local = (datetime.strptime(time_utc, '%Y-%m-%dT%H:%M:%SZ') + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S') if time_utc else ""
                
                row_data = {
                    '時間': time_local,
                    '班次': cells[1].text,
                    '機檯': cells[2].text,
                    '帳號': cells[3].text,
                    '上層代理': cells[4].text,
                    '鈔入': cells[5].text,
                    '單機開點': cells[6].text,
                    '機檯總餘點': cells[7].text,
                    '會員餘點': cells[8].text,
                    '積點轉表底': cells[9].text
                }
                data.append(row_data)

        # 使用 pandas 將資料轉換為 DataFrame
        df = pd.DataFrame(data)

        # 儲存為 Excel 檔案
        df.to_excel("result_data_selenium.xlsx", index=False)
        print("資料已成功轉換為 Excel 檔案 result_data_selenium.xlsx")

    finally:
        # 結束會話並關閉瀏覽器
        driver.quit()

if __name__ == "__main__":
    main()
