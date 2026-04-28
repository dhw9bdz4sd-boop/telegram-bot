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
trading_enabled = True
cooldown_until = 0
risk_level = 1

# =========================
# الأزواج (20)
# =========================
PAIRS = [
    "EURUSDT","GBPUSDT","USDJPY","AUDUSD","USDCAD",
    "NZDUSD","EURJPY","GBPJPY","CHFJPY","EURAUD",
    "EURGBP","GBPCHF","AUDJPY","CADJPY","USDCHF",
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT"
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
            ["📊 احصائيات", "🔄 إعادة"]
        ],
        "resize_keyboard": True
    }

def pairs_menu():
    return {
        "keyboard": [
            ["EURUSDT","GBPUSDT","USDJPY"],
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
# إضافات ذكية
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

def win_rate():
    total = stats["wins"] + stats["losses"]
    return round((stats["wins"]/total)*100,2) if total else 0

def trading_session():
    hour = datetime.datetime.utcnow().hour
    return 7 <= hour <= 17

# =========================
# اختيار أفضل زوج
# =========================
def find_best_pair(mode):
    best_pair = None
    best_score = 0

    for pair in PAIRS:
        result = pro_signal(pair) if mode == "PRO" else elite_signal(pair)

        if result:
            _, confidence = result
            if confidence > best_score:
                best_score = confidence
                best_pair = pair

    return best_pair

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
    global risk_level

    prices = get_prices(pair)
    if len(prices) < 60:
        return None

    r = rsi(prices)
    ema_fast = ema(prices[-30:], 9)
    ema_slow = ema(prices[-30:], 21)
    last = prices[-1]
    candle = candle_confirmation(prices)

    strict = risk_level >= 2

    if not market_filter(r):
        return None

    if r < (35 if not strict else 30) and ema_fast > ema_slow and last > ema_fast and candle == "BUY":
        return "BUY ⬆️",95

    if r > (65 if not strict else 70) and ema_fast < ema_slow and last < ema_fast and candle == "SELL":
        return "SELL ⬇️",95

    return None

# =========================
# 🤖 الإشارات التلقائية
# =========================
def auto_signal_loop():
    last_sent = {}

    while True:
        for chat_id, user in users.items():

            if not user.get("auto"):
                continue

            if not user.get("time"):
                continue

            if time.time() < cooldown_until:
                continue

            if not trading_session():
                continue

            now = time.time()
            if chat_id in last_sent and now - last_sent[chat_id] < 60:
                continue

            best = find_best_pair(user["mode"])
            if not best:
                continue

            result = pro_signal(best) if user["mode"]=="PRO" else elite_signal(best)
            if not result:
                continue

            direction, confidence = result
            wait = entry_time()

            send_message(chat_id,f"""
🤖 إشارة تلقائية

💱 {best}
⏱ {user['time']} دقيقة
📈 {direction}
🎯 {confidence}%

⏱ ادخل بعد {wait} ثانية
🔥 تلقائي شغال
""")

            last_sent[chat_id] = now

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
                users[chat_id] = {"pair":None,"time":None,"mode":"ELITE","auto":False}

            user = users[chat_id]

            if text == "/start":
                send_message(chat_id,"🔥 البوت جاهز",main_menu())

            elif text == "💱 الأزواج":
                send_message(chat_id,"اختر الزوج:",pairs_menu())

            elif text == "🤖 تلقائي":
                user["auto"] = True
                send_message(chat_id,"تم تفعيل التلقائي")

            elif text in PAIRS:
                user["pair"] = text
                user["auto"] = False

            elif text == "⏱ المدة":
                send_message(chat_id,"اختر المدة:",time_menu())

            elif "دقيقة" in text:
                user["time"] = text.split()[0]

            elif text == "PRO":
                user["mode"] = "PRO"

            elif text == "ELITE":
                user["mode"] = "ELITE"

            elif text == "📊 احصائيات":
                send_message(chat_id,f"""
📊 الأداء
✅ {stats['wins']}
❌ {stats['losses']}
🎯 {win_rate()}%
""")

            elif "إشارة" in text:

                if time.time() < cooldown_until:
                    send_message(chat_id,"⏳ البوت متوقف مؤقت")
                    continue

                if user.get("auto"):
                    user["pair"] = find_best_pair(user["mode"])

                result = pro_signal(user["pair"]) if user["mode"]=="PRO" else elite_signal(user["pair"])

                if not result:
                    send_message(chat_id,"⚠️ لا توجد صفقة")
                    continue

                direction, confidence = result
                wait = entry_time()

                send_message(chat_id,f"""
📊 إشارة

💱 {user['pair']}
⏱ {user['time']} دقيقة
📈 {direction}
🎯 {confidence}%

⏱ ادخل بعد {wait} ثانية
""")

        time.sleep(1)

# =========================
# تشغيل
# =========================
if __name__ == "__main__":
    threading.Thread(target=auto_signal_loop).start()
    run()
