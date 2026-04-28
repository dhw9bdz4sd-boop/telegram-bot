import requests
import time
import os
import datetime

TOKEN = os.getenv("TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}/"

users = {}

stats = {"wins": 0, "losses": 0}
loss_streak = 0
trading_enabled = True
cooldown_until = 0
risk_level = 1  # نظام التعلم

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
            ["EURUSDT", "BTCUSDT"],
            ["GBPUSDT"],
            ["⬅️ رجوع"]
        ],
        "resize_keyboard": True
    }

def time_menu():
    return {
        "keyboard": [
            ["1 دقيقة", "5 دقائق"],
            ["⬅️ رجوع"]
        ],
        "resize_keyboard": True
    }

# =========================
# بيانات السوق
# =========================
def get_prices(symbol):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=100"
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
# إضافات
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
    if 45 < rsi_value < 55:
        return False
    return True

def entry_time():
    now = time.time()
    return 60 - int(now % 60)

def win_rate():
    total = stats["wins"] + stats["losses"]
    return round((stats["wins"]/total)*100,2) if total else 0

def trading_session():
    hour = datetime.datetime.utcnow().hour
    return 7 <= hour <= 17

# =========================
# تحليل ELITE
# =========================
def elite_signal(pair):
    prices = get_prices(pair)
    if len(prices) < 50:
        return None

    ema_fast = ema(prices[-30:], 9)
    ema_slow = ema(prices[-30:], 21)

    if ema_fast > ema_slow:
        return "BUY ⬆️", 75
    else:
        return "SELL ⬇️", 75

# =========================
# تحليل PRO (ذكي)
# =========================
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

    # فلترة أقوى حسب الخسارة
    strict = risk_level >= 2

    if not market_filter(r):
        return None

    if r < (35 if not strict else 30) and ema_fast > ema_slow and last > ema_fast and candle == "BUY":
        return "BUY ⬆️", 95

    if r > (65 if not strict else 70) and ema_fast < ema_slow and last < ema_fast and candle == "SELL":
        return "SELL ⬇️", 95

    return None

# =========================
# تشغيل
# =========================
def run():
    global loss_streak, trading_enabled, cooldown_until, risk_level

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
                users[chat_id] = {"pair":None,"time":None,"mode":"ELITE"}

            user = users[chat_id]

            if text == "/start":
                send_message(chat_id,"🔥 البوت الاحترافي جاهز",main_menu())

            elif text == "💱 الأزواج":
                send_message(chat_id,"اختر الزوج:",pairs_menu())

            elif text in ["EURUSDT","BTCUSDT","GBPUSDT"]:
                user["pair"] = text
                send_message(chat_id,f"تم اختيار {text}",main_menu())

            elif text == "⏱ المدة":
                send_message(chat_id,"اختر المدة:",time_menu())

            elif "1 دقيقة" in text:
                user["time"] = "1"
                send_message(chat_id,"تم اختيار 1 دقيقة",main_menu())

            elif "5 دقائق" in text:
                user["time"] = "5"
                send_message(chat_id,"تم اختيار 5 دقائق",main_menu())

            elif "PRO" in text:
                user["mode"] = "PRO"

            elif "ELITE" in text:
                user["mode"] = "ELITE"

            elif text == "✅ فوز":
                stats["wins"] += 1
                loss_streak = 0
                risk_level = 1

            elif text == "❌ خسارة":
                stats["losses"] += 1
                loss_streak += 1
                risk_level = min(3, risk_level + 1)

                if loss_streak >= 3:
                    cooldown_until = time.time() + 900
                    trading_enabled = False

            elif text == "📊 احصائيات":
                send_message(chat_id,f"""
📊 الأداء

✅ {stats['wins']}
❌ {stats['losses']}
🎯 {win_rate()}%
""")

            elif "إشارة" in text:

                if time.time() < cooldown_until:
                    remaining = int((cooldown_until-time.time())/60)
                    send_message(chat_id,f"⏳ متوقف {remaining} دقيقة")
                    continue

                if not trading_session():
                    send_message(chat_id,"⏰ السوق ضعيف")
                    continue

                start = time.time()

                result = pro_signal(user["pair"]) if user["mode"]=="PRO" else elite_signal(user["pair"])

                if not result:
                    send_message(chat_id,"⚠️ لا توجد صفقة")
                    continue

                direction, confidence = result
                wait = entry_time()
                analysis_time = round(time.time()-start,2)

                send_message(chat_id,f"""
📊 إشارة احترافية

💱 {user['pair']}
⏱ {user['time']} دقيقة
📈 {direction}
🎯 {confidence}%

⏱ ادخل بعد {wait} ثانية
⏳ التحليل: {analysis_time}s

📊 النجاح: {win_rate()}%
💡 مستوى المخاطرة: {risk_level}
""")

        time.sleep(1)

if __name__ == "__main__":
    run()
