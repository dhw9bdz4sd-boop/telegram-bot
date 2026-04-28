import requests
import time
import os

TOKEN = os.getenv("TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}/"

users = {}

# =========================
# إرسال رسالة
# =========================
def send_message(chat_id, text, keyboard=None):
    url = BASE_URL + "sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": keyboard
    }
    requests.post(url, json=data)

# =========================
# الكيبورد
# =========================
def main_menu():
    return {
        "keyboard": [
            ["📊 إشارة", "💱 الأزواج"],
            ["⏱ المدة", "⚙️ الوضع"],
            ["🔥 ELITE", "🏦 SMC"]
        ],
        "resize_keyboard": True
    }

# =========================
# جلب الأسعار
# =========================
def get_prices(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=100"
    data = requests.get(url).json()
    return [float(c[4]) for c in data]

# =========================
# RSI
# =========================
def calculate_rsi(prices, period=14):
    gains, losses = [], []

    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        if diff >= 0:
            gains.append(diff)
        else:
            losses.append(abs(diff))

    avg_gain = sum(gains[-period:]) / period if gains else 0.0001
    avg_loss = sum(losses[-period:]) / period if losses else 0.0001

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# =========================
# EMA
# =========================
def ema(prices, period):
    k = 2 / (period + 1)
    ema_val = prices[0]

    for price in prices:
        ema_val = price * k + ema_val * (1 - k)

    return ema_val

# =========================
# تحليل احترافي
# =========================
def generate_signal(pair):
    try:
        prices = get_prices(pair)

        rsi = calculate_rsi(prices)
        ema_fast = ema(prices, 9)
        ema_slow = ema(prices, 21)
        last_price = prices[-1]

        # شروط BUY
        if rsi < 30 and ema_fast > ema_slow and last_price > ema_fast:
            return "BUY ⬆️ (Strong Trend + RSI)"

        # شروط SELL
        elif rsi > 70 and ema_fast < ema_slow and last_price < ema_fast:
            return "SELL ⬇️ (Strong Trend + RSI)"

        # فلترة السوق
        elif 40 < rsi < 60:
            return "❌ سوق ضعيف - لا تدخل"

        else:
            return "❌ إشارة غير واضحة"

    except Exception as e:
        return "⚠️ خطأ في البيانات"

# =========================
# تحديثات
# =========================
def get_updates(offset=None):
    url = BASE_URL + "getUpdates"
    params = {"timeout": 100, "offset": offset}
    return requests.get(url, params=params).json()

# =========================
# تشغيل
# =========================
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
                users[chat_id] = {
                    "pair": None,
                    "duration": None,
                    "mode": "ELITE"
                }

            user = users[chat_id]

            # START
            if text == "/start":
                send_message(chat_id, "🔥 البوت الاحترافي جاهز", main_menu())

            # الأزواج
            elif "الأزواج" in text:
                send_message(chat_id, "اختر:\nEURUSDT\nBTCUSDT\nGBPUSDT")

            elif text in ["EURUSDT", "BTCUSDT", "GBPUSDT"]:
                user["pair"] = text
                send_message(chat_id, f"تم اختيار {text}")

            # المدة
            elif "المدة" in text:
                send_message(chat_id, "اكتب 1 أو 5")

            elif text in ["1", "5"]:
                user["duration"] = text
                send_message(chat_id, f"تم اختيار {text} دقيقة")

            # الوضع
            elif "ELITE" in text:
                user["mode"] = "ELITE"
                send_message(chat_id, "🔥 ELITE مفعل")

            elif "SMC" in text:
                user["mode"] = "SMC"
                send_message(chat_id, "🏦 SMC مفعل")

            # الإشارة
            elif "إشارة" in text:
                if not user["pair"]:
                    send_message(chat_id, "❗ اختر الزوج")
                elif not user["duration"]:
                    send_message(chat_id, "❗ اختر المدة")
                else:
                    result = generate_signal(user["pair"])

                    send_message(chat_id, f"""
📊 إشارتك:

💱 الزوج: {user['pair']}
⏱ المدة: {user['duration']} دقيقة
⚙️ الوضع: {user['mode']}

📈 القرار:
{result}

💰 إدارة رأس المال:
- 2% فقط لكل صفقة
- لا تعوض الخسارة مباشرة

🔥 نظام احترافي
""")

# =========================
# تشغيل
# =========================
if __name__ == "__main__":
    run()
