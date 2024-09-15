from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, JobQueue
from datetime import datetime, time
from telegram.error import NetworkError
import json
import os
import logging
import time as time_module

# 初始化故障記錄的字典
fault_records = []
repaired_records = []
RETRY_TIME = 5

# 如果已有記錄，則載入
if os.path.exists('fault_records.json'):
    with open('fault_records.json', 'r') as file:
        fault_records = json.load(file)

if os.path.exists('repaired_records.json'):
    with open('repaired_records.json', 'r') as file:
        repaired_records = json.load(file)

def schedule_jobs(application: Application):
    job_queue = application.job_queue  # 确保 JobQueue 存在
    # 使用datetime.time而不是time
    job_queue.run_daily(send_daily_report, time(hour=9, minute=0, second=0))

def save_records():
    with open('fault_records.json', 'w') as file:
        json.dump(fault_records, file, indent=4)
    with open('repaired_records.json', 'w') as file:
        json.dump(repaired_records, file, indent=4)

async def send_daily_report(context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = "<YOUR_GROUP_CHAT_ID>"  # 替换为您的群组聊天 ID
    response = "故障紀錄:\n"

    if not fault_records:
        response += "目前沒有任何故障紀錄。"
    else:
        for record in fault_records:
            date = record.get("date", "未知日期")
            time_str = record.get("time", "未知時間")
            store = record.get("store", "未知店家")
            machine_number = record.get("machine_number", "未知機台編號")
            reason = record.get("reason", "未知故障原因")
            response += (
                f"\n故障日期：{date}\n"
                f"故障時間：{time_str}\n"
                f"店家：{store}\n"
                f"機台編號：{machine_number}\n"
                f"故障概述：{reason}\n"
            )
    
    await context.bot.send_message(chat_id=chat_id, text=response)

async def record_fault(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("請使用正確的格式: /F 店家 機台編號(雙位數字) 故障原因")
        return

    store = args[0]
    machine_number = args[1]

    # 檢查機台編號是否為雙位數字
    if not (machine_number.isdigit() and len(machine_number) == 2):
        await update.message.reply_text("機台編號必須為雙位數字，例如01、99。請重新輸入。")
        return

    reason = ' '.join(args[2:])
    timestamp = datetime.now()

    date_str = timestamp.strftime("%Y年%m月%d日")
    time_str = timestamp.strftime("%H:%M")

    # 使用字典來保存每一筆記錄
    fault_record = {
        "date": date_str,
        "time": time_str,
        "store": store,
        "machine_number": machine_number,
        "reason": reason
    }

    # 將新記錄添加到故障記錄列表中
    fault_records.append(fault_record)

    save_records()

    response_text = (
        f"故障日期：{date_str}\n"
        f"故障時間：{time_str}\n"
        f"店家：{store}\n"
        f"機台編號：{machine_number}\n"
        f"故障概述：{reason}"
    )

    await update.message.reply_text(f"已紀錄以下資訊：\n{response_text}")

async def list_faults(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not fault_records:
        await update.message.reply_text("目前沒有任何故障紀錄。")
        return

    response = "故障紀錄:\n"
    for record in fault_records:
        date = record.get("date", "未知日期")
        time = record.get("time", "未知時間")
        store = record.get("store", "未知店家")
        machine_number = record.get("machine_number", "未知機台編號")
        reason = record.get("reason", "未知故障原因")

        response += (
            f"\n故障日期：{date}\n"
            f"故障時間：{time}\n"
            f"店家：{store}\n"
            f"機台編號：{machine_number}\n"
            f"故障概述：{reason}\n"
        )

    await update.message.reply_text(response)

# 標記故障為已修復的指令
async def mark_repair(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("請使用正確的格式: /okr 店家 機台編號(雙位數字)")
        return

    store = args[0]
    machine_number = args[1]
    timestamp = datetime.now()

    date_str = timestamp.strftime("%Y年%m月%d日")
    time_str = timestamp.strftime("%H:%M")

    # 在 fault_records 列表中查找对应的记录
    record_to_repair = None
    for record in fault_records:
        if record["store"] == store and record["machine_number"] == machine_number:
            record_to_repair = record
            break

    if record_to_repair:
        # 添加維修到場的日期和時間到記錄中
        record_to_repair["repair_date"] = date_str
        record_to_repair["repair_time"] = time_str
        
        # 从故障列表中移除并添加到已修复列表中
        fault_records.remove(record_to_repair)
        repaired_records.append(record_to_repair)
        save_records()
        await update.message.reply_text(f"店家： {store} 機台編號： {machine_number} 的故障，維修時間為 {date_str} {time_str}。")
    else:
        await update.message.reply_text("找不到該故障紀錄。")

# 標記故障為已寄送維修的指令
async def mark_shipping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if len(args) != 3:
        await update.message.reply_text("請使用正確的格式: /oks 店家 機台編號(雙位數字) 貨運單號碼")
        return

    store = args[0]
    machine_number = args[1]
    tracking_number = args[2]

    # 在 fault_records 列表中查找对应的记录
    record_to_repair = None
    for record in fault_records:
        if record["store"] == store and record["machine_number"] == machine_number:
            record_to_repair = record
            break

    if record_to_repair:
        # 添加貨運單號碼到記錄中
        record_to_repair["tracking_number"] = tracking_number
        
        # 从故障列表中移除并添加到已修复列表中
        fault_records.remove(record_to_repair)
        repaired_records.append(record_to_repair)
        save_records()
        await update.message.reply_text(f"店家： {store} 機台編號： {machine_number} 的故障已安排寄貨，貨運單號為 {tracking_number} 預計隔天送到，如延遲請依單號查詢。")
    else:
        await update.message.reply_text("找不到該故障紀錄。")

async def list_repaired(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not repaired_records:
        await update.message.reply_text("目前沒有已修復的故障紀錄。")
        return

    response = "已修復的故障紀錄:\n"
    for record in repaired_records:
        date = record.get("date", "未知日期")
        time = record.get("time", "未知時間")
        store = record.get("store", "未知店家")
        machine_number = record.get("machine_number", "未知機台編號")
        reason = record.get("reason", "未知故障原因")
        tracking_number = record.get("tracking_number", "無貨運單號")
        repair_date = record.get("repair_date", "無維修日期")
        repair_time = record.get("repair_time", "無維修時間")

        response += (
            f"\n故障日期：{date}\n"
            f"故障時間：{time}\n"
            f"店家：{store}\n"
            f"機台編號：{machine_number}\n"
            f"故障概述：{reason}\n"
            f"貨運單號：{tracking_number}\n"
            f"維修日期：{repair_date}\n"
            f"維修時間：{repair_time}\n"
        )

    await update.message.reply_text(response)

async def delete_fault(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("請使用正確的格式: /D 店家 機台編號(雙位數字)")
        return

    store = args[0]
    machine_number = args[1]

    # 在 fault_records 列表中查找对应的记录
    record_to_delete = None
    for record in fault_records:
        if record["store"] == store and record["machine_number"] == machine_number:
            record_to_delete = record
            break

    if record_to_delete:
        # 从故障列表中删除记录
        fault_records.remove(record_to_delete)
        save_records()
        await update.message.reply_text(f"已刪除 {store} 號店, {machine_number} 號機台的故障紀錄。")
    else:
        await update.message.reply_text("找不到該故障紀錄。")

# 顯示幫助指令
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "/F 店家 機台編號(雙位數字) 故障原因 - 紀錄機台故障\n"
        "/L - 列出所有故障紀錄\n"
        "/D 店家 機台編號(雙位數字) - 刪除指定的故障紀錄\n"
        "/oks 店家 機台編號(雙位數字) 貨運單號碼 - 標記故障為已發貨\n"
        "/okr 店家 機台編號(雙位數字) - 標記故障為已修復\n"
        "/okl - 列出所有已修復的故障紀錄\n"
        "/HELPB - 顯示這個幫助訊息"
    )
    await update.message.reply_text(help_text)

def main():
    application = Application.builder().token("7512844838:AAFQvbE7EtUxmPbVX82ETV0zkOxjilE0hn0").build()

    application.add_handler(CommandHandler("F", record_fault))
    application.add_handler(CommandHandler("L", list_faults))
    application.add_handler(CommandHandler("D", delete_fault))
    application.add_handler(CommandHandler("oks", mark_shipping))
    application.add_handler(CommandHandler("okr", mark_repair))
    application.add_handler(CommandHandler("okl", list_repaired))
    application.add_handler(CommandHandler("HELPB", help_command))

    # 调用定时任务函数
    schedule_jobs(application)

    while True:
        try:
            print("Bot is running...")
            application.run_polling()
        except NetworkError as e:
            logging.error(f"Network error occurred: {e}")
            print(f"Network error occurred: {e}. Retrying in {RETRY_TIME} seconds...")
            time.sleep(RETRY_TIME)

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    main()