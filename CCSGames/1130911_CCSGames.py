import os
import requests
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import calendar
from datetime import datetime, timezone
import schedule
import threading

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = "7512844838:AAFQvbE7EtUxmPbVX82ETV0zkOxjilE0hn0"

# 設置每天早上 8:00 發送 /grand 資料
def schedule_grand_report():
    schedule.every().day.at("08:00").do(send_grand_report)

    # 執行 schedule
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分鐘檢查一次任務

# 使用 threading 來運行定時任務
def start_scheduler():
    scheduler_thread = threading.Thread(target=schedule_grand_report)
    scheduler_thread.daemon = True
    scheduler_thread.start()

# 將 /Date(毫秒數)/ 轉換為可讀日期格式
def convert_timestamp(ms_string):
    timestamp = int(ms_string.strip("/Date()/")) / 1000
    dt_object = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return dt_object.strftime('%Y-%m-%d %H:%M:%S')

# 格式化總數值和Bingo數值的函數
def format_total_value(total_value):
    return "{:,.2f}".format(total_value)

def format_bingo_value(bingo_value):
    return "{:,.2f}".format(bingo_value / 100)

# 初始化瀏覽器
def init_browser():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # 無頭模式
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    browser = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return browser

# Login and get cookies
def login_and_get_cookies():
    browser = init_browser()
    login_url = "https://mgt2.ccsgames.com/Account/Login?ReturnUrl=%2F"
    
    try:
        # Navigate to the login page
        browser.get(login_url)

        # Explicit wait
        wait = WebDriverWait(browser, 10)
        
        # Wait for the username and password fields on the login page
        username_field = wait.until(EC.presence_of_element_located((By.NAME, 'UserName')))
        password_field = wait.until(EC.presence_of_element_located((By.NAME, 'Password')))
        login_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[type="submit"]')))

        # Simulate login
        username_field.send_keys("mingwade")
        password_field.send_keys("Open888")
        login_button.click()

        # Wait for the page to redirect
        time.sleep(5)

        # Fetch cookies
        cookies = browser.get_cookies()
        session = requests.Session()
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'])

        logging.info("Cookies obtained successfully")
        return session

    except Exception as e:
        logging.error(f"Login failed, error: {str(e)}")
        return None
    
    finally:
        browser.quit()

# Fetch WinLoseReport data
def fetch_winlose_report(session, start_date, end_date, local_server_id):
    url = "https://mgt2.ccsgames.com/WinLoseReport/List"
    headers = {
        "Accept": "*/*",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest"
    }
    payload = {
        "sort": "",
        "page": 1,
        "pageSize": 500,
        "group": "",
        "aggregate": "_TotalBet-sum~_TotalWin-sum~_CouponBet-sum~_Winlose-sum~WinJP-sum~_TotalWinlose-sum~MachineTotalIn-sum~MachineTotalOut-sum~Profit-sum",
        "filter": "",
        "agentId": "196",  # Ensure this is the correct agentId
        "LocalServerId": local_server_id,
        "StartDateTime": start_date,
        "StartTime": "00:00:00",
        "EndDateTime": end_date,
        "EndTime": "23:59:59",
        "query": "true"
    }
    
    response = session.post(url, data=payload, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"WinLose Report request failed, status code: {response.status_code}")
        return None
            
# Fetch WinLoseReport summary data
def fetch_winlose_summary(session):
    url = "https://mgt2.ccsgames.com/WinLoseReport/GetSummary"
    headers = {
        "Accept": "*/*",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
        "X-Requested-With": "XMLHttpRequest"
    }
    payload = {
        "sort": "",
        "group": "",
        "filter": ""
    }
    
    response = session.post(url, data=payload, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"WinLose Summary request failed, status code: {response.status_code}")
        return None

# 格式化數字的函數
def format_number_chinese_style(number):
    number = float(number) / 100
    formatted = f"{number:,.2f}"
    return formatted

# 獲取 API 數據
def get_jp_values():
    url = "https://jp-service.ccsgames.com/get_jp_values"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            logging.error(f"API request failed, status code: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"API request error: {e}")
        return None

# 發送 /grand 當月數據給指定用戶的函數
def send_grand_report():
    TARGET_CHAT_ID = "YOUR_CHAT_ID_HERE"  # 替換成您指定用戶或群組的 chat_id
    year = datetime.now().year
    month = datetime.now().month

    # 獲取 cookies 並查詢數據
    session = login_and_get_cookies()
    if session:
        data = fetch_list_data(session, month)
        if data:
            total_grand = None
            if "AggregateResults" in data and data["AggregateResults"]:
                total_grand = format_total_value(data["AggregateResults"][0]["FormattedValue"])
            grand_data = [item for item in data['Data'] if item['JPName'] == 'Grand']
            if grand_data:
                messages = []
                messages.append(f"*** GRAND for {year}-{month:02d} ***")
                for item in grand_data:
                    readable_date = convert_timestamp(item['DateTime'])
                    formatted_bingo = format_bingo_value(item['BingoValue'])
                    message = (f"Server ldx: {item['DisplayName']}\n"
                               f"Machine ID: {item['MachineID']}\n"
                               f"Bingo: {formatted_bingo}\n"
                               f"Date: {readable_date}")
                    messages.append(message)
                
                if total_grand:
                    messages.append(f"\n*** Total GRAND for {year}-{month:02d} ***")
                    messages.append(f"Total ： {total_grand}")

                # 發送資料給指定用戶
                application.bot.send_message(chat_id=TARGET_CHAT_ID, text="\n\n".join(messages))

# 分析數據並發送消息
async def jackpot(update: Update, context):
    data = get_jp_values()
    if data:
        message = (
            f"*** Jackpot King's Report ***\n"
            f"GRAND: {format_number_chinese_style(data['DV5'])}\n"
            f"MEGA: {format_number_chinese_style(data['DV1'])}\n"
            f"MAJOR: {format_number_chinese_style(data['DV2'])}\n"
            f"MINOR: {format_number_chinese_style(data['DV3'])}\n"
            f"MINI: {format_number_chinese_style(data['DV4'])}\n"
        )
        await update.message.reply_text(message)
    else:
        await update.message.reply_text("Unable to retrieve Jackpot data, please try again later.")

# Format the report data based on Telegram command
def format_report(data):
    try:
        # Use f-string and close any unnecessary indentation
        today_alone_report = (
            f"*** Monthly Store Report ***\n"
            f"Name : {data['NickName']}\n"
            f"Total Bet : {data['_TotalBet']:,.2f}\n"
            f"Coupon Bet : {data['_CouponBet']:,.2f}\n"
            f"Total Win : {data['_TotalWin']:,.2f}\n"
            f"RTP : {data['_RTP']}\n"
            f"Win/Lose : {data['_Winlose']:,.2f}\n"
            f"Win JP : {data['WinJP']:,.2f}\n"
            f"RTP (JP) : {data['_RTPIncludeJP']}\n"
            f"Total Win/Lose : {data['_TotalWinlose']:,.2f}\n"
            f"Total In : {data['MachineTotalIn']:,}\n"
            f"Total Out : {data['MachineTotalOut']:,}\n"
            f"Profit (K-L-H) : {data['Profit']:,}\n"
        )
        return today_alone_report
    except Exception as e:
        logging.error(f"Error formatting Today Alone Report data: {str(e)}")
        return f"Error formatting data: {str(e)}"

def format_summary(summary_data):
    try:
        if 'Data' in summary_data and len(summary_data['Data']) > 0:
            summary = summary_data['Data'][0]
            # Adjust multi-line string to remove unnecessary indentation
            today_all_report = (
                f"*** Monthly All Report ***\n"
                f"Total Bet : {summary['TotalBet']:,.2f}\n"
                f"Coupon Bet : {summary['CouponBet']:,.2f}\n"
                f"Total Win : {summary['TotalWin']:,.2f}\n"
                f"RTP : {summary['RTP']:.2f}%\n"
                f"Win/Lose : {summary['Winlose']:,.2f}\n"
                f"Win JP : {summary['WinJP']:,.2f}\n"
                f"RTP (JP) : {summary['RTPIncludeJP']:.2f}%\n"
                f"Total Win/Lose : {summary['TotalWinlose']:,.2f}\n"
                f"Total In : {summary['TotalMachineIn']:,}\n"
                f"Total Out : {summary['TotalMachineOut']:,}\n"
                f"Profit (K-L-H) : {summary['TotalProfit']:,}\n"
            )
            return today_all_report
        else:
            return "Error: Unable to fetch summary data."
    except Exception as e:
        logging.error(f"Error formatting Today All Report data: {str(e)}")
        return f"Error formatting data: {str(e)}"
    
# Telegram command handler for reports
async def fetch_report(update: Update, context, local_server_id):
    if len(context.args) not in [1, 2]:  # Allow 1 or 2 arguments
        await update.message.reply_text("Please enter the correct year and month format. For example, use /store_code 2023 09 to fetch data for September 2023, or use /store_code 09 to fetch data for the current year.")
        return

    # Immediately reply "Fetching data, please wait..."
    await update.message.reply_text("Fetching data, please wait...")

    # If only the month is provided, use the current year by default
    if len(context.args) == 1:
        year = str(2024)  # Or use the current year: year = str(time.localtime().tm_year)
        month = context.args[0]
    else:
        year = context.args[0]
        month = context.args[1]

    # Keep year and month as strings until length check, then convert to integers
    if len(month) == 2 and month.isdigit() and len(year) == 4 and year.isdigit():
        year = int(year)
        month = int(month)
        try:
            days_in_month = calendar.monthrange(year, month)[1]  # 動態計算該月的天數
            start_date = f"{year}/{month:02d}/01"
            end_date = f"{year}/{month:02d}/{days_in_month}"

            # Login and get cookies
            session = login_and_get_cookies()
            if not session:
                await update.message.reply_text("Login failed, unable to fetch data.")
                return

            # Fetch WinLose Report
            data = fetch_winlose_report(session, start_date, end_date, local_server_id)
            if data and 'Data' in data and len(data['Data']) > 0:
                report = format_report(data['Data'][0])
                await update.message.reply_text(report)
            else:
                logging.error(f"WinLose Report data fetch failed or format incorrect: {data}")
                await update.message.reply_text("Data fetch failed, please try again later.")

            # Fetch Summary Report
            summary_data = fetch_winlose_summary(session)
            if summary_data and 'Data' in summary_data and len(summary_data['Data']) > 0:
                summary_report = format_summary(summary_data)
                await update.message.reply_text(summary_report)
            else:
                logging.error(f"Summary Report data fetch failed or format incorrect: {summary_data}")
                await update.message.reply_text("Summary data fetch failed, please try again later.")

        except Exception as e:
            logging.error(f"Error occurred while processing request: {str(e)}")
            await update.message.reply_text("An error occurred while processing the request, please try again later.")
    else:
        await update.message.reply_text("Invalid year or month format. Please enter a four-digit year and two-digit month, e.g., 2023 09.")

# 定义 fetch_list_data 函数
def fetch_list_data(session, month):
    list_url = "https://mgt2.ccsgames.com/JackpotRecord/List"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Accept': '*/*',
        'Accept-Language': 'zh-TW,zh-Hant;q=0.9',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15',
        'Referer': 'https://mgt2.ccsgames.com/JackpotRecord',
        'X-Requested-With': 'XMLHttpRequest',
    }
    start_date = f"2024/{month}/01"
    end_date = f"2024/{month}/{30 if month != '02' else '28'}"
    payload = {
        'sort': '',
        'page': 1,
        'pageSize': 70,
        'group': '',
        'aggregate': '_BingoValue-sum',
        'filter': '',
        'agentId': '196',
        'LocalServerId': '',
        'JPLevel': '5',
        'StartDateTime': start_date,
        'StartTime': '00:00:00',
        'EndDateTime': end_date,
        'EndTime': '23:59:59',
        'query': 'true'
    }
    
    response = session.post(list_url, headers=headers, data=payload)
    if response.status_code == 200:
        try:
            data = response.json()
            logging.info("成功獲取 List 數據！")
            return data
        except Exception as e:
            logging.error(f"解析 List 數據失敗: {str(e)}")
            return None
    else:
        logging.error(f"無法獲取 List 數據，狀態碼: {response.status_code}")
        return None

# GRAND 指令的處理器
async def grand_command(update: Update, context):
    if context.args:
        if len(context.args) == 1:
            year = str(datetime.now().year)  # 當前年份
            month = context.args[0]
        elif len(context.args) == 2:
            year = context.args[0]
            month = context.args[1]
        else:
            await update.message.reply_text("請輸入正確的年份和月份格式，如 /grand 09 或 /grand 2023 09")
            return

        if len(month) == 2 and month.isdigit():  # 確保月份為兩位數字
            logging.info(f"收到 /GRAND {year} {month} 指令，開始獲取數據...")
            await update.message.reply_text(f"Fetching data for {year}-{month}, please wait...")

            # 計算該月的天數
            year = int(year)
            month = int(month)
            days_in_month = calendar.monthrange(year, month)[1]  # 動態計算該月的天數
            start_date = f"{year}/{month:02d}/01"
            end_date = f"{year}/{month:02d}/{days_in_month}"

            session = login_and_get_cookies()
            if session:
                data = fetch_list_data(session, month)

                if data:
                    total_grand = None
                    if "AggregateResults" in data and data["AggregateResults"]:
                        total_grand = format_total_value(data["AggregateResults"][0]["FormattedValue"])
                    grand_data = [item for item in data['Data'] if item['JPName'] == 'Grand']
                    if grand_data:
                        messages = []
                        messages.append(f"*** GRAND for {year}-{month:02d} ***")
                        for item in grand_data:
                            readable_date = convert_timestamp(item['DateTime'])
                            formatted_bingo = format_bingo_value(item['BingoValue'])
                            message = (f"Server ldx: {item['DisplayName']}\n"
                                       f"Machine ID: {item['MachineID']}\n"
                                       f"Bingo: {formatted_bingo}\n"
                                       f"Date: {readable_date}")
                            messages.append(message)
                        if total_grand:
                            messages.append(f"\n*** Total GRAND for {year}-{month:02d} ***")
                            messages.append(f"Total ： {total_grand}")
                        await update.message.reply_text("\n\n".join(messages))
                    else:
                        await update.message.reply_text("No data found for this month.")
                else:
                    await update.message.reply_text("Failed to retrieve data, please try again later.")
            else:
                await update.message.reply_text("Login failed, unable to retrieve data.")
        else:
            await update.message.reply_text("Please enter the correct month format, for example, /GRAND 09")
    else:
        await update.message.reply_text("Please provide the month, such as /GRAND 09 to retrieve data for September.")

# Main program
def main():
    from telegram.ext import Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # 啟動定時任務
    start_scheduler()

    # Add command handlers, using different LocalServerID based on the command
    application.add_handler(CommandHandler("2198", lambda update, context: fetch_report(update, context, "700006040004")))
    application.add_handler(CommandHandler("3136", lambda update, context: fetch_report(update, context, "700006040002")))
    application.add_handler(CommandHandler("260", lambda update, context: fetch_report(update, context, "700006040006")))
    application.add_handler(CommandHandler("3132", lambda update, context: fetch_report(update, context, "700006040007")))
    application.add_handler(CommandHandler("26", lambda update, context: fetch_report(update, context, "700006040008")))
    application.add_handler(CommandHandler("3135", lambda update, context: fetch_report(update, context, "700006040010")))
    application.add_handler(CommandHandler("266", lambda update, context: fetch_report(update, context, "700006040014")))
    application.add_handler(CommandHandler("369", lambda update, context: fetch_report(update, context, "700006040132")))
    application.add_handler(CommandHandler("363", lambda update, context: fetch_report(update, context, "700006040276")))

    # Add jackpot command handler
    application.add_handler(CommandHandler("jackpot", jackpot))

    # Add grand command handler
    application.add_handler(CommandHandler("grand", grand_command))

    application.run_polling()

if __name__ == '__main__':
    main()
