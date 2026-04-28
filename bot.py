import requests
import time
import os
import datetime
import threading

TOKEN = os.getenv("TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}/"

users = {}

stats = {"wins": 0, "losses": 0}
loss_streak = 0
cooldown_until = 0
risk_level = 1

# =========================
# الأزواج
# =========================
PAIRS = [
    "EURUSDT","GBPUSDT","AUDUSDT",
    "BTCUSDT","ETHUSDT","XRPUSDT"
]

# =========================
# إرسال رسالة
# =========================
def send_message(chat_id, text, keyboard=None):
    url = BASE_URL + "sendMessage"
    data = {"chat_id": chat_id, "text": text}
    if keyboard:
        data["reply_markup"] = keyboard
    requests.post(url, json=data)

# =========================
# القوائم
# =========================
def main_menu():
    return {
        "keyboard": [
            ["📊 إشارة", "💱 الأزواج"],
            ["⏱ المدة", "⚙️ الوضع"],
            ["🔥 ELITE", "🚀 PRO"],
            ["🤖 تلقائي", "📊 احصائيات"]
        ],
        "resize_keyboard": True
    }

def pairs_menu():
    return {
        "keyboard": [
            ["EURUSDT","GBPUSDT","AUDUSDT"],
            ["BTCUSDT","ETHUSDT","XRPUSDT"],
            ["⬅️ رجوع"]
        ],
        "resize_keyboard": True
    }

def time_menu():
    return {
        "keyboard": [
            ["1 دقيقة","2 دقيقة","3 دقيقة"],
            ["4 دقيقة","5 دقيقة"],
            ["⬅️ رجوع"]
        ],
        "resize_keyboard": True
    }

# =========================
# البيانات
# =========================
def get_prices(symbol):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=100"
        data = requests.get(url).json()
        return [float(c[4]) for c in data]
    except:
        return []

# =========================
# المؤشرات
# =========================
def ema(data, period):
    k = 2/(period+1)
    val = data[0]
    for p in data:
        val = p*k + val*(1-k)
    return val

def rsi(data, period=14):
    gains, losses = [], []
    for i in range(1, len(data)):
        diff = data[i] - data[i-1]
        if diff > 0:
            gains.append(diff)
        else:
            losses.append(abs(diff))
    avg_gain = sum(gains[-period:])/period if gains else 0.001
    avg_loss = sum(losses[-period:])/period if losses else 0.001
    rs = avg_gain / avg_loss
    return 100 - (100/(1+rs))

# =========================
# الذكاء
# =========================
def candle_confirmation(prices):
    if len(prices) < 3:
        return None
    if prices[-1] > prices[-2] > prices[-3]:
        return "BUY"
    if prices[-1] < prices[-2] < prices[-3]:
        return "SELL"
    return None

def market_filter(rsi_value):
    return not (45 < rsi_value < 55)

def entry_time():
    return 60 - int(time.time() % 60)

# =========================
# التحليل
# =========================
def pro_signal(pair):
    global risk_level

    prices = get_prices(pair)
    if len(prices) < 60:
        return None

    r = rsi(prices)
    ema_fast = ema(prices[-30:], 9)
    ema_slow = ema(prices[-30:], 21)
    candle = candle_confirmation(prices)

    strict = risk_level >= 2

    if not market_filter(r):
        return None

    if r < (35 if not strict else 30) and ema_fast > ema_slow and candle == "BUY":
        return "BUY ⬆️", 90 + risk_level

    if r > (65 if not strict else 70) and ema_fast < ema_slow and candle == "SELL":
        return "SELL ⬇️", 90 + risk_level

    return None

# =========================
# 🤖 التلقائي + تنبيه مسبق
# =========================
def auto_loop():
    last_signal_time = {}

    while True:
        for chat_id, user in users.items():

            if not user.get("auto"):
                continue

            if not user.get("time"):
                continue

            if time.time() < cooldown_until:
                continue

            now = time.time()
            if chat_id in last_signal_time and now - last_signal_time[chat_id] < 60:
                continue

            for pair in PAIRS:
                result = pro_signal(pair)
                if result:
                    direction, confidence = result

                    # 🔔 تنبيه قبل الصفقة
                    send_message(chat_id,f"""
🔔 تنبيه صفقة قادمة

💱 {pair}
📈 {direction}

⏳ بعد 60 ثانية سيتم الدخول
""")

                    time.sleep(60)

                    # 🚀 الصفقة
                    send_message(chat_id,f"""
🚀 دخول الصفقة الآن

💱 {pair}
📈 {direction}
🎯 {confidence}%

🔥 تلقائي
""")

                    last_signal_time[chat_id] = time.time()
                    break

        time.sleep(5)

# =========================
# التشغيل
# =========================
def run():
    global loss_streak, cooldown_until, risk_level

    offset = None

    while True:
        updates = requests.get(BASE_URL+"getUpdates", params={"timeout":100,"offset":offset}).json()

        for update in updates["result"]:
            offset = update["update_id"] + 1

            if "message" not in update:
                continue

            msg = update["message"]
            chat_id = msg["chat"]["id"]
            text = msg.get("text","")

            if chat_id not in users:
                users[chat_id] = {"pair":None,"time":None,"mode":"PRO","auto":False}

            user = users[chat_id]

            # ===== الأزرار =====

            if text == "/start":
                send_message(chat_id,"🔥 البوت جاهز",main_menu())

            elif text == "💱 الأزواج":
                send_message(chat_id,"اختر الزوج:",pairs_menu())

            elif text in PAIRS:
                user["pair"] = text
                user["auto"] = False
                send_message(chat_id,f"تم اختيار {text}")

            elif text == "⏱ المدة":
                send_message(chat_id,"اختر المدة:",time_menu())

            elif "دقيقة" in text:
                user["time"] = text.split()[0]
                send_message(chat_id,f"تم اختيار {user['time']} دقيقة")

            elif text == "🤖 تلقائي":
                user["auto"] = True
                send_message(chat_id,"🔥 تم تشغيل التلقائي")

            elif text == "📊 احصائيات":
                total = stats["wins"] + stats["losses"]
                rate = (stats["wins"]/total)*100 if total else 0
                send_message(chat_id,f"🎯 النجاح: {round(rate,2)}%")

            # ===== تعلم من الخسارة =====

            elif text == "❌ خسارة":
                stats["losses"] += 1
                loss_streak += 1
                risk_level = min(3, risk_level+1)

                if loss_streak >= 3:
                    cooldown_until = time.time() + 900
                    send_message(chat_id,"⛔ توقف 15 دقيقة")

            elif text == "✅ فوز":
                stats["wins"] += 1
                loss_streak = 0
                risk_level = 1

            # ===== الإشارة =====

            elif "إشارة" in text:

                if not user["pair"]:
                    send_message(chat_id,"اختر الزوج أولاً")
                    continue

                result = pro_signal(user["pair"])

                if not result:
                    send_message(chat_id,f"⏳ لا توجد صفقة\nانتظر {entry_time()} ثانية")
                    continue

                direction, confidence = result

                send_message(chat_id,f"""
📊 إشارة

💱 {user['pair']}
📈 {direction}
🎯 {confidence}%

⏱ الدخول بعد {entry_time()} ثانية
""")

        time.sleep(1)

# =========================
# تشغيل
# =========================
if __name__ == "__main__":
    threading.Thread(target=auto_loop).start()
    run()
