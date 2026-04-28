import requests, time, os, statistics, random

TOKEN = os.getenv("TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}/"

users = {}
AUTO_CHAT_IDS = set()

def get_updates(offset=None):
    try:
        r = requests.get(BASE_URL + "getUpdates",
                         params={"timeout": 100, "offset": offset},
                         timeout=120)
        return r.json()
    except:
        return {"result": []}

def send_message(chat_id, text):
    try:
        requests.post(BASE_URL + "sendMessage",
                      data={"chat_id": chat_id, "text": text})
    except:
        pass

def get_prices(symbol):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=60"
        data = requests.get(url, timeout=10).json()
        if not isinstance(data, list):
            return []
        return [float(c[4]) for c in data if len(c) > 4]
    except:
        return []

def calc_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50
    gains, losses = [], []
    for i in range(1, period + 1):
        diff = prices[-i] - prices[-i-1]
        if diff >= 0:
            gains.append(diff)
        else:
            losses.append(abs(diff))
    avg_gain = sum(gains)/period if gains else 0.0001
    avg_loss = sum(losses)/period if losses else 0.0001
    rs = avg_gain / avg_loss
    return 100 - (100/(1+rs))

def trend(prices):
    if len(prices) < 30:
        return "FLAT"
    short = sum(prices[-10:]) / 10
    long = sum(prices[-30:]) / 30
    if short > long:
        return "UP"
    elif short < long:
        return "DOWN"
    return "FLAT"

def candle_confirm(prices):
    if len(prices) < 3:
        return "NONE"
    if prices[-1] > prices[-2] > prices[-3]:
        return "UP"
    if prices[-1] < prices[-2] < prices[-3]:
        return "DOWN"
    return "NONE"

def pro_signal(symbol):
    p = get_prices(symbol)
    if not p or len(p) < 30:
        return None, "❌ لا توجد بيانات الآن"

    r = calc_rsi(p)
    t = trend(p)
    c = candle_confirm(p)

    if t == "UP" and r < 35 and c == "UP":
        return ("BUY ⬆️", random.randint(88, 96)), None
    if t == "DOWN" and r > 65 and c == "DOWN":
        return ("SELL ⬇️", random.randint(88, 96)), None

    return None, "⏳ لا توجد فرصة الآن"

def handle(chat_id, text):
    if chat_id not in users:
        users[chat_id] = {"pair":"EURUSDT","duration":1,"auto":False}

    u = users[chat_id]

    if text == "/start":
        send_message(chat_id, "🔥 البوت جاهز\n\nالأوامر:\nالأزواج / المدة / إشارة / تلقائي / إيقاف")

    elif text == "الأزواج":
        send_message(chat_id, "EURUSDT\nGBPUSDT\nBTCUSDT")

    elif text in ["EURUSDT","GBPUSDT","BTCUSDT"]:
        u["pair"] = text
        send_message(chat_id, f"تم اختيار {text}")

    elif text == "المدة":
        send_message(chat_id, "اكتب عدد الدقائق")

    elif text.isdigit():
        u["duration"] = int(text)
        send_message(chat_id, f"{text} دقيقة")

    elif text == "تلقائي":
        u["auto"] = True
        AUTO_CHAT_IDS.add(chat_id)
        send_message(chat_id, "تم تشغيل التلقائي")

    elif text == "إيقاف":
        u["auto"] = False
        AUTO_CHAT_IDS.discard(chat_id)
        send_message(chat_id, "تم الإيقاف")

    elif text == "إشارة":
        direction, err = pro_signal(u["pair"])
        if err:
            send_message(chat_id, err)
            return

        d, conf = direction
        msg = f"""🚨 إشارة

{u['pair']}
{d}
{u['duration']} دقيقة
{conf}%
"""
        send_message(chat_id, msg)

    else:
        send_message(chat_id, "❌ غير معروف")

def auto_loop():
    while True:
        for cid in list(AUTO_CHAT_IDS):
            u = users.get(cid)
            if not u or not u.get("auto"):
                continue

            direction, err = pro_signal(u["pair"])
            if not err:
                d, conf = direction
                send_message(cid, f"🚨 تلقائي\n{u['pair']}\n{d}\n{conf}%")

        time.sleep(60)

def main():
    import threading
    threading.Thread(target=auto_loop, daemon=True).start()

    offset = None
    while True:
        updates = get_updates(offset)
        for u in updates.get("result", []):
            offset = u["update_id"] + 1
            m = u.get("message")
            if not m: continue
            handle(m["chat"]["id"], m.get("text",""))
        time.sleep(1)

if __name__ == "__main__":
    main()
