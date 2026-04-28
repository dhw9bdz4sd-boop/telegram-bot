import requests
import os

TOKEN = os.getenv("TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}/"

users = {}

# إرسال رسالة
def send_message(chat_id, text, keyboard=None):
    url = BASE_URL + "sendMessage"
    data = {"chat_id": chat_id, "text": text}
    if keyboard:
        data["reply_markup"] = keyboard
    requests.post(url, json=data)

# القائمة الرئيسية
def main_menu():
    return {
        "keyboard": [
            ["📊 إشارة", "💱 الأزواج"],
            ["⏱ المدة", "⚙️ الوضع"],
            ["🔥 ELITE", "🏦 SMC"]
        ],
        "resize_keyboard": True
    }

# أزرار الأزواج
def pairs_menu():
    return {
        "keyboard": [
            ["EURUSDT", "BTCUSDT"],
            ["GBPUSDT"],
            ["⬅️ رجوع"]
        ],
        "resize_keyboard": True
    }

# أزرار المدة
def time_menu():
    return {
        "keyboard": [
            ["1 دقيقة", "5 دقائق"],
            ["⬅️ رجوع"]
        ],
        "resize_keyboard": True
    }

# تحليل (مبسط حالياً)
def generate_signal():
    import random
    return random.choice(["BUY ⬆️", "SELL ⬇️"])

# التحديثات
def get_updates(offset=None):
    url = BASE_URL + "getUpdates"
    params = {"timeout": 100, "offset": offset}
    return requests.get(url, params=params).json()

# تشغيل
def run():
    offset = None

    while True:
        updates = get_updates(offset)

        for update in updates["result"]:
            offset = update["update_id"] + 1

            if "message" not in update:
                continue

            msg = update["message"]
            chat_id = msg["chat"]["id"]
            text = msg.get("text", "")

            if chat_id not in users:
                users[chat_id] = {"pair": None, "time": None}

            user = users[chat_id]

            # START
            if text == "/start":
                send_message(chat_id, "🔥 البوت جاهز", main_menu())

            # الأزواج
            elif text == "💱 الأزواج":
                send_message(chat_id, "اختر الزوج:", pairs_menu())

            elif text in ["EURUSDT", "BTCUSDT", "GBPUSDT"]:
                user["pair"] = text
                send_message(chat_id, f"✅ تم اختيار {text}", main_menu())

            # المدة
            elif text == "⏱ المدة":
                send_message(chat_id, "اختر المدة:", time_menu())

            elif "1 دقيقة" in text:
                user["time"] = "1"
                send_message(chat_id, "✅ تم اختيار 1 دقيقة", main_menu())

            elif "5 دقائق" in text:
                user["time"] = "5"
                send_message(chat_id, "✅ تم اختيار 5 دقائق", main_menu())

            # رجوع
            elif "رجوع" in text:
                send_message(chat_id, "رجعنا للقائمة", main_menu())

            # إشارة 🔥
            elif "إشارة" in text:
                if not user["pair"]:
                    send_message(chat_id, "❗ اختر الزوج أولاً")
                elif not user["time"]:
                    send_message(chat_id, "❗ اختر المدة أولاً")
                else:
                    signal = generate_signal()
                    send_message(chat_id, f"""
📊 الإشارة:

💱 {user['pair']}
⏱ {user['time']} دقيقة

📈 {signal}
🔥 موفق
""")

# تشغيل
if __name__ == "__main__":
    run()
