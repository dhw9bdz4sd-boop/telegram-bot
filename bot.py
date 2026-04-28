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
            ["🧠 ذكي", "📊 احصائيات"]
        ],
        "resize_keyboard": True
    }

def pairs_menu():
    return {
        "keyboard": [
            ["EURUSDT","GBPUSDT","AUDUSDT"],
            ["BTCUSDT","ETHUSDT","XRPUSDT"],
            ["🤖 تلقائي"],
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
# ذكاء إضافي
# =========================
def candle_confirmation(prices):
    if len(prices) < 3:
        return None
    if prices[-1] > prices[-2] > prices[-3]:
        return "BUY"
    if prices[-1] < prices[-2] < prices[-3]:
        return "SELL"
    return None

def entry_time():
    return 60 - int(time.time() % 60)

# =========================
# تقييم الصفقة
# =========================
def strength(conf):
    if conf >= 95:
        return "🔥 خارقة"
    elif conf >= 85:
        return "🟢 قوية"
    elif conf >= 75:
        return "🟡 متوسطة"
    else:
        return "🔴 ضعيفة"

# =========================
# التحليل
# =========================
def elite_signal(pair):
    prices = get_prices(pair)
    if len(prices) < 50:
        return None

    ema_fast = ema(prices[-30:], 9)
    ema_slow = ema(prices[-30:], 21)

    return ("BUY ⬆️",75) if ema_fast > ema_slow else ("SELL ⬇️",75)

def pro_signal(pair):
    prices = get_prices(pair)
    if len(prices) < 60:
        return None

    r = rsi(prices)
    ema_fast = ema(prices[-30:], 9)
    ema_slow = ema(prices[-30:], 21)
    candle = candle_confirmation(prices)

    if r < 35 and ema_fast > ema_slow and candle == "BUY":
        return "BUY ⬆️",95

    if r > 65 and ema_fast < ema_slow and candle == "SELL":
        return "SELL ⬇️",95

    return None

# =========================
# الوضع الذكي
# =========================
def smart_signal(pair):
    prices = get_prices(pair)
    if len(prices) < 60:
        return None

    r = rsi(prices)

    if r < 40 or r > 60:
        return pro_signal(pair)
    else:
        return elite_signal(pair)

# =========================
# التشغيل
# =========================
def run():
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
                users[chat_id] = {"pair":None,"time":None,"mode":"ELITE","auto":False}

            user = users[chat_id]

            if text == "/start":
                send_message(chat_id,"🔥 البوت المطور جاهز",main_menu())

            elif text == "💱 الأزواج":
                send_message(chat_id,"اختر الزوج:",pairs_menu())

            elif text in PAIRS:
                user["pair"] = text
                send_message(chat_id,f"تم اختيار {text}")

            elif text == "⏱ المدة":
                send_message(chat_id,"اختر المدة:",time_menu())

            elif "دقيقة" in text:
                user["time"] = text.split()[0]
                send_message(chat_id,f"تم اختيار {user['time']} دقيقة")

            elif text == "🔥 ELITE":
                user["mode"] = "ELITE"
                send_message(chat_id,"تم تفعيل ELITE")

            elif text == "🚀 PRO":
                user["mode"] = "PRO"
                send_message(chat_id,"تم تفعيل PRO")

            elif text == "🧠 ذكي":
                user["mode"] = "SMART"
                send_message(chat_id,"🧠 الوضع الذكي مفعل")

            elif text == "📊 احصائيات":
                total = stats["wins"] + stats["losses"]
                rate = (stats["wins"]/total)*100 if total else 0
                send_message(chat_id,f"🎯 نسبة النجاح: {round(rate,2)}%")

            elif "إشارة" in text:

                if not user["pair"]:
                    send_message(chat_id,"اختر زوج أولاً")
                    continue

                if not user["time"]:
                    send_message(chat_id,"اختر مدة أولاً")
                    continue

                start = time.time()

                if user["mode"] == "SMART":
                    result = smart_signal(user["pair"])
                elif user["mode"] == "PRO":
                    result = pro_signal(user["pair"])
                else:
                    result = elite_signal(user["pair"])

                if not result:
                    wait = entry_time()
                    send_message(chat_id,f"⏳ لا توجد صفقة\n⏱ انتظر {wait} ثانية")
                    continue

                direction, conf = result
                wait = entry_time()
                analysis = round(time.time()-start,2)

                send_message(chat_id,f"""
📊 إشارة احترافية

💱 {user['pair']}
⏱ {user['time']} دقيقة
📈 {direction}

🎯 {conf}%
📊 {strength(conf)}

⏱ الدخول بعد {wait} ثانية
⏳ التحليل: {analysis}s
""")

        time.sleep(1)

# =========================
# تشغيل
# =========================
if __name__ == "__main__":
    run()
