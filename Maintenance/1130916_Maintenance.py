import asyncio
import json
import logging
import os
from datetime import datetime, time
from typing import List, Dict, Any

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import NetworkError

# Constants
FAULT_RECORDS_FILE = 'fault_records.json'
REPAIRED_RECORDS_FILE = 'repaired_records.json'
RETRY_TIME = 5
CHAT_ID = ""  # Replace with your actual group chat ID

# Initialize logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class FaultManagementSystem:
    def __init__(self):
        self.fault_records: List[Dict[str, Any]] = self.load_records(FAULT_RECORDS_FILE)
        self.repaired_records: List[Dict[str, Any]] = self.load_records(REPAIRED_RECORDS_FILE)

    @staticmethod
    def load_records(filename: str) -> List[Dict[str, Any]]:
        if os.path.exists(filename):
            with open(filename, 'r') as file:
                return json.load(file)
        return []

    def save_records(self):
        self.save_to_file(FAULT_RECORDS_FILE, self.fault_records)
        self.save_to_file(REPAIRED_RECORDS_FILE, self.repaired_records)

    @staticmethod
    def save_to_file(filename: str, data: List[Dict[str, Any]]):
        with open(filename, 'w') as file:
            json.dump(data, file, indent=4)

    def add_fault(self, fault_data: Dict[str, Any]):
        self.fault_records.append(fault_data)
        self.save_records()

    def remove_fault(self, store: str, machine_number: str) -> bool:
        for record in self.fault_records:
            if record["store"] == store and record["machine_number"] == machine_number:
                self.fault_records.remove(record)
                self.save_records()
                return True
        return False

    def mark_as_repaired(self, store: str, machine_number: str, repair_info: Dict[str, str]) -> bool:
        for record in self.fault_records:
            if record["store"] == store and record["machine_number"] == machine_number:
                record.update(repair_info)
                self.fault_records.remove(record)
                self.repaired_records.append(record)
                self.save_records()
                return True
        return False

fault_system = FaultManagementSystem()

async def send_daily_report(context: ContextTypes.DEFAULT_TYPE) -> None:
    response = "故障紀錄:\n"
    if not fault_system.fault_records:
        response += "目前沒有任何故障紀錄。"
    else:
        for record in fault_system.fault_records:
            response += (
                f"\n故障日期：{record.get('date', '未知日期')}\n"
                f"故障時間：{record.get('time', '未知時間')}\n"
                f"店家：{record.get('store', '未知店家')}\n"
                f"機台編號：{record.get('machine_number', '未知機台編號')}\n"
                f"故障概述：{record.get('reason', '未知故障原因')}\n"
            )
    
    await context.bot.send_message(chat_id=CHAT_ID, text=response)

async def record_fault(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("請使用正確的格式: /F 店家 機台編號(雙位數字) 故障原因")
        return

    store, machine_number, *reason_parts = args
    reason = ' '.join(reason_parts)

    if not (machine_number.isdigit() and len(machine_number) == 2):
        await update.message.reply_text("機台編號必須為雙位數字，例如01、99。請重新輸入。")
        return

    timestamp = datetime.now()
    fault_record = {
        "date": timestamp.strftime("%Y年%m月%d日"),
        "time": timestamp.strftime("%H:%M"),
        "store": store,
        "machine_number": machine_number,
        "reason": reason
    }

    fault_system.add_fault(fault_record)

    response_text = (
        f"故障日期：{fault_record['date']}\n"
        f"故障時間：{fault_record['time']}\n"
        f"店家：{store}\n"
        f"機台編號：{machine_number}\n"
        f"故障概述：{reason}"
    )

    await update.message.reply_text(f"已紀錄以下資訊：\n{response_text}")

async def list_faults(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not fault_system.fault_records:
        await update.message.reply_text("目前沒有任何故障紀錄。")
        return

    response = "故障紀錄:\n"
    for record in fault_system.fault_records:
        response += (
            f"\n故障日期：{record.get('date', '未知日期')}\n"
            f"故障時間：{record.get('time', '未知時間')}\n"
            f"店家：{record.get('store', '未知店家')}\n"
            f"機台編號：{record.get('machine_number', '未知機台編號')}\n"
            f"故障概述：{record.get('reason', '未知故障原因')}\n"
        )

    await update.message.reply_text(response)

async def delete_fault(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("請使用正確的格式: /D 店家 機台編號(雙位數字)")
        return

    store = args[0]
    machine_number = args[1]

    if fault_system.remove_fault(store, machine_number):
        await update.message.reply_text(f"已刪除 {store} 號店, {machine_number} 號機台的故障紀錄。")
    else:
        await update.message.reply_text("找不到該故障紀錄。")

# ... [其他函數的實現，如 mark_repair, mark_shipping, list_repaired, delete_fault, help_command] ...

def main():
    application = Application.builder().token("7512844838:AAFQvbE7EtUxmPbVX82ETV0zkOxjilE0hn0").build()

    application.add_handler(CommandHandler("F", record_fault))
    application.add_handler(CommandHandler("L", list_faults))
    application.add_handler(CommandHandler("D", delete_fault))
    application.add_handler(CommandHandler("oks", mark_shipping))
    application.add_handler(CommandHandler("okr", mark_repair))
    application.add_handler(CommandHandler("okl", list_repaired))
    application.add_handler(CommandHandler("HELPB", help_command))

    job_queue = application.job_queue
    job_queue.run_daily(send_daily_report, time(hour=9, minute=0, second=0))

    async def run_bot():
        while True:
            try:
                await application.initialize()
                await application.start()
                await application.updater.start_polling()
                logger.info("Bot is running...")
                await application.updater.stop()
            except NetworkError as e:
                logger.error(f"Network error occurred: {e}")
                logger.info(f"Retrying in {RETRY_TIME} seconds...")
                await asyncio.sleep(RETRY_TIME)
            finally:
                await application.stop()

    asyncio.run(run_bot())

if __name__ == '__main__':
    main()