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
    "EURUSDT","GBPUSDT","USDJPY","AUDUSD","USDCAD",
    "NZDUSD","EURJPY","GBPJPY","CHFJPY","EURAUD",
    "EURGBP","GBPCHF","AUDJPY","CADJPY","USDCHF",
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT"
]

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
            ["📊 إشارة", "💱 الأزواج"],
            ["⏱ المدة", "⚙️ الوضع"],
            ["🤖 تلقائي"],
            ["📊 احصائيات"]
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
# تحسين الإشارات 🔥
# =========================
def vip_signal(pair):
    global loss_streak

    prices = get_prices(pair)
    if len(prices) < 50:
        return None

    r = rsi(prices)
    ema_fast = ema(prices[-30:], 9)
    ema_slow = ema(prices[-30:], 21)

    # وقف فقط لو خسائر كثيرة
    if loss_streak >= 3:
        return None

    # BUY
    if r < 40 and ema_fast > ema_slow:
        return "BUY ⬆️", 80

    # SELL
    if r > 60 and ema_fast < ema_slow:
        return "SELL ⬇️", 80

    return None

# =========================
# وقت الدخول
# =========================
def entry_time():
    return 60 - int(time.time() % 60)

# =========================
# احصائيات
# =========================
def win_rate():
    total = stats["wins"] + stats["losses"]
    return round((stats["wins"]/total)*100,2) if total else 0

# =========================
# أفضل زوج
# =========================
def find_best_pair():
    for pair in PAIRS:
        result = vip_signal(pair)
        if result:
            return pair
    return None

# =========================
# إشارات تلقائية 🔥
# =========================
def auto_signal_loop():
    last_sent = {}

    while True:
        for chat_id, user in users.items():

            if not user.get("auto"):
                continue

            if not user.get("time"):
                continue

            now = time.time()

            if chat_id in last_sent and now - last_sent[chat_id] < 60:
                continue

            pair = find_best_pair()
            if not pair:
                continue

            result = vip_signal(pair)
            if not result:
                continue

            direction, confidence = result

            # 🔥 تنبيه قبل الصفقة
            send_message(chat_id, "⏳ بعد 60 ثانية صفقة قادمة... استعد")

            time.sleep(60)

            send_message(chat_id, f"""
🤖 إشارة تلقائية

💱 {pair}
⏱ {user['time']} دقيقة
📈 {direction}
🎯 {confidence}%
""")

            last_sent[chat_id] = now

        time.sleep(5)

# =========================
# التشغيل
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
                users[chat_id] = {"pair":None,"time":None,"auto":False}

            user = users[chat_id]

            # START
            if text == "/start":
                send_message(chat_id,"🔥 البوت جاهز",main_menu())

            # الأزواج
            elif text == "💱 الأزواج":
                send_message(chat_id,"اختر الزوج:",pairs_menu())

            elif text in PAIRS:
                user["pair"] = text
                user["auto"] = False
                send_message(chat_id,f"✅ تم اختيار {text}",main_menu())

            # تلقائي
            elif text == "🤖 تلقائي":
                user["auto"] = True
                send_message(chat_id,"🤖 تم تفعيل التلقائي",main_menu())

            # المدة
            elif text == "⏱ المدة":
                send_message(chat_id,"اختر المدة:",time_menu())

            elif "دقيقة" in text:
                user["time"] = text.split()[0]
                send_message(chat_id,f"⏱ تم اختيار {user['time']} دقيقة",main_menu())

            # رجوع
            elif text == "⬅️ رجوع":
                send_message(chat_id,"رجعت",main_menu())

            # احصائيات
            elif text == "📊 احصائيات":
                send_message(chat_id,f"""
📊 الأداء

✅ {stats['wins']}
❌ {stats['losses']}
🎯 {win_rate()}%
""")

            # إشارات
            elif "إشارة" in text:

                if not user["pair"] and not user.get("auto"):
                    send_message(chat_id,"❗ اختر الزوج")
                    continue

                if not user["time"]:
                    send_message(chat_id,"❗ اختر المدة")
                    continue

                if user.get("auto"):
                    user["pair"] = find_best_pair()

                result = vip_signal(user["pair"])

                if not result:
                    wait = entry_time()
                    send_message(chat_id,f"⏳ لا توجد صفقة\n⏱ انتظر {wait} ثانية")
                    continue

                direction, confidence = result

                send_message(chat_id,f"""
📊 إشارة

💱 {user['pair']}
⏱ {user['time']} دقيقة
📈 {direction}
🎯 {confidence}%

⏱ الدخول بعد {entry_time()} ثانية
""")

        time.sleep(1)

# =========================
# تشغيل
# =========================
if __name__ == "__main__":
    threading.Thread(target=auto_signal_loop).start()
    run()
