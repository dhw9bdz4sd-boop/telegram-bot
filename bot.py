import requests
import time
import os
import threading

TOKEN = os.getenv("TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}/"

users = {}
stats = {"wins": 0, "losses": 0}
loss_streak = 0

PAIRS = ["EURUSDT","BTCUSDT","ETHUSDT","XRPUSDT"]

# =========================
# إرسال رسالة
# =========================
def send_message(chat_id, text, keyboard=None):
    try:
        url = BASE_URL + "sendMessage"
        data = {"chat_id": chat_id, "text": text}
        if keyboard:
            data["reply_markup"] = keyboard
        requests.post(url, json=data)
    except:
        pass

# =========================
# القوائم
# =========================
def main_menu():
    return {
        "keyboard": [
            ["📊 إشارة","🤖 تلقائي"],
            ["⏱ المدة","📊 احصائيات"]
        ],
        "resize_keyboard": True
    }

def time_menu():
    return {
        "keyboard": [
            ["1 دقيقة","2 دقيقة","3 دقيقة"],
            ["⬅️ رجوع"]
        ],
        "resize_keyboard": True
    }

# =========================
# بيانات السوق
# =========================
def get_prices(symbol):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=50"
        data = requests.get(url).json()
        return [float(c[4]) for c in data]
    except:
        return []

# =========================
# مؤشرات
# =========================
def ema(data, period):
    k = 2/(period+1)
    val = data[0]
    for p in data:
        val = p*k + val*(1-k)
    return val

def rsi(data, period=14):
    gains, losses = [], []
    for i in range(1,len(data)):
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
# 🔥 تحليل احترافي متوازن
# =========================
def balanced_signal(pair):
    global loss_streak

    prices = get_prices(pair)

    if len(prices) < 30:
        return "BUY ⬆️", 60

    r = rsi(prices)
    ema_fast = ema(prices[-20:], 9)
    ema_slow = ema(prices[-20:], 21)

    # إيقاف مؤقت عند الخسارة
    if loss_streak >= 3:
        return None

    # اتجاه
    if ema_fast > ema_slow:
        direction = "BUY ⬆️"
    else:
        direction = "SELL ⬇️"

    confidence = 65

    # تحسين الجودة
    if r < 40 or r > 60:
        confidence += 10

    if abs(ema_fast - ema_slow) > 0.05:
        confidence += 5

    return direction, confidence

# =========================
# وقت الدخول
# =========================
def entry_time():
    return 60 - int(time.time() % 60)

# =========================
# اختيار زوج
# =========================
def find_pair():
    return PAIRS[int(time.time()) % len(PAIRS)]

# =========================
# 🤖 التلقائي
# =========================
def auto_loop():
    last_sent = {}

    while True:
        for chat_id, user in users.items():

            if not user.get("auto"):
                continue

            now = time.time()
            if chat_id in last_sent and now - last_sent[chat_id] < 60:
                continue

            pair = find_pair()
            result = balanced_signal(pair)

            if not result:
                continue

            direction, confidence = result

            # 🔔 تنبيه
            send_message(chat_id,"⏳ صفقة بعد 60 ثانية...")

            time.sleep(60)

            send_message(chat_id,f"""
🤖 إشارة تلقائية

💱 {pair}
📈 {direction}
🎯 {confidence}%
""")

            last_sent[chat_id] = now

        time.sleep(5)

# =========================
# تشغيل
# =========================
def run():
    global loss_streak

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
                users[chat_id] = {"time":None,"auto":False}

            user = users[chat_id]

            if text == "/start":
                send_message(chat_id,"🔥 البوت الاحترافي جاهز",main_menu())

            elif text == "⏱ المدة":
                send_message(chat_id,"اختر:",time_menu())

            elif "دقيقة" in text:
                user["time"] = text
                send_message(chat_id,"تم اختيار المدة ✅",main_menu())

            elif text == "🤖 تلقائي":
                user["auto"] = True
                send_message(chat_id,"تم تشغيل التلقائي 🔥",main_menu())

            elif text == "📊 احصائيات":
                send_message(chat_id,f"""
📊 الأداء

✅ {stats['wins']}
❌ {stats['losses']}
""")

            elif text == "❌ خسارة":
                stats["losses"] += 1
                loss_streak += 1

            elif text == "✅ فوز":
                stats["wins"] += 1
                loss_streak = 0

            elif text == "⬅️ رجوع":
                send_message(chat_id,"رجوع",main_menu())

            elif text == "📊 إشارة":

                pair = find_pair()
                result = balanced_signal(pair)

                if not result:
                    send_message(chat_id,"⚠️ السوق غير واضح حالياً")
                    continue

                direction, confidence = result

                send_message(chat_id,f"""
📊 إشارة احترافية

💱 {pair}
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
