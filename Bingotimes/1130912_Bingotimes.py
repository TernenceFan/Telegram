import requests
import json

# 登入成功後的 sessionGuid 和其他必要資料
web_session_guid = "bf3fb7be-110b-45fd-9f47-f964b9bb8fd1"  # 這裡你需要確認這個是否正確
session_guid = "bdd0b497-625f-408e-8f48-993ee7feb1c3"  # 這裡需要從登入回應中獲取

# 設定要撈取的資料
fetch_url = "http://118.163.190.55:5000/api/reports/deposit-withdraw"
fetch_data = {
    "webSessionGuid": web_session_guid,
    "httpRequestSerial": 97,
    "dateFromUtc": "",
    "dateToUtc": "",
    "shiftNumberFrom": 24091202,
    "shiftNumberTo": 24091202,
    "egmIdFrom": -1,
    "egmIdTo": -1,
    "cashflowPkFrom": -1,
    "cashflowPkTo": -1,
    "cashflowCauses": [],
    "sakuraFilter": 1,
    "memberId": "",
    "uplineId": "",
    "shouldGroupMember": False,
    "shouldShowTotalsOnly": False,
    "isMobilePlayOnly": False,
    "pageNumberFromOne": 1,
    "sortOnIndex": -1,
    "isSortOnDescending": False,
    "sessionGuid": session_guid
}

# 設定 headers
headers = {
    "Accept": "application/json",
    "Accept-Language": "zh-TW,zh-Hant;q=0.9",
    "Content-Type": "application/json; charset=utf-8",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15"
}

# 發送資料請求
response = requests.post(fetch_url, headers=headers, json=fetch_data)

# 檢查回應狀態
if response.status_code == 200:
    result = response.json()
    # 將資料寫入文字檔案
    with open("result_data.txt", "w", encoding="utf-8") as file:
        json.dump(result, file, indent=4, ensure_ascii=False)
    print("資料已成功寫入 result_data.txt 檔案中")
else:
    print(f"Failed to fetch data. Status code: {response.status_code}")
    print(response.text)  # 顯示伺服器回應的內容