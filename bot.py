import requests
import time
import os
import threading

TOKEN = os.getenv("TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}/"

users = {}

# =========================
# الأزواج (Binance)
# =========================
PAIRS = [
    "EURUSDT","GBPUSDT","AUDUSDT","USDCAD",
    "NZDUSDT","USDCHF","EURGBP","EURJPY",
    "GBPJPY","AUDJPY","CADJPY","CHFJPY",
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT",
    "XRPUSDT","ADAUSDT","DOGEUSDT","TRXUSDT"
]

# =========================
# OTC (Pocket Option)
# =========================
OTC_PAIRS = [
    "EURUSD-OTC","GBPUSD-OTC","AUDUSD-OTC",
    "USDJPY-OTC","USDCHF-OTC","USDCAD-OTC"
]

# =========================
# تحويل الاسم
# =========================
def convert_pair(pair):
    return pair.replace("USDT","USD")

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
# 🔥 تحليل احترافي
# =========================
def signal(pair):
    prices = get_prices(pair)

    if len(prices) < 30:
        return None

    r = rsi(prices)
    ema_fast = ema(prices[-20:], 9)
    ema_slow = ema(prices[-20:], 21)

    if ema_fast > ema_slow:
        direction = "BUY ⬆️"
    else:
        direction = "SELL ⬇️"

    confidence = 65

    if r < 40 or r > 60:
        confidence += 10

    if abs(ema_fast - ema_slow) > 0.05:
        confidence += 5

    return direction, confidence

# =========================
# أفضل زوج
# =========================
def find_best_pair():
    best_pair = None
    best_conf = 0

    for pair in PAIRS:
        result = signal(pair)
        if result:
            _, conf = result
            if conf > best_conf:
                best_conf = conf
                best_pair = pair

    return best_pair

# =========================
# وقت الدخول
# =========================
def entry_time():
    return 60 - int(time.time() % 60)

# =========================
# 🤖 التلقائي
# =========================
def auto_loop():
    while True:
        for chat_id, user in users.items():

            if not user.get("auto"):
                continue

            pair = find_best_pair()

            if pair:
                direction, confidence = signal(pair)
                pocket_pair = convert_pair(pair)
            else:
                # fallback OTC
                pocket_pair = OTC_PAIRS[int(time.time()) % len(OTC_PAIRS)]
                direction = "BUY ⬆️" if int(time.time()) % 2 == 0 else "SELL ⬇️"
                confidence = 60

            send_message(chat_id,"⏳ صفقة بعد 60 ثانية...")

            time.sleep(60)

            send_message(chat_id,f"""
🤖 إشارة تلقائية

💱 {pocket_pair}
📈 {direction}
🎯 {confidence}%
""")

        time.sleep(5)

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
                users[chat_id] = {"time":None,"auto":False}

            user = users[chat_id]

            if text == "/start":
                send_message(chat_id,"🔥 البوت النهائي جاهز",main_menu())

            elif text == "⏱ المدة":
                send_message(chat_id,"اختر:",time_menu())

            elif "دقيقة" in text:
                user["time"] = text

            elif text == "🤖 تلقائي":
                user["auto"] = True
                send_message(chat_id,"تم تشغيل التلقائي 🔥")

            elif text == "📊 إشارة":

                pair = find_best_pair()

                if pair:
                    direction, confidence = signal(pair)
                    pocket_pair = convert_pair(pair)
                else:
                    pocket_pair = OTC_PAIRS[int(time.time()) % len(OTC_PAIRS)]
                    direction = "BUY ⬆️" if int(time.time()) % 2 == 0 else "SELL ⬇️"
                    confidence = 60

                send_message(chat_id,f"""
📊 إشارة احترافية

💱 {pocket_pair}
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
