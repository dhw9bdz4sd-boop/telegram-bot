import os, requests, time, json
from datetime import datetime

TOKEN = os.getenv("TOKEN")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}/"

chat_id=None

pairs={"EURUSD":"EURUSDT","GBPUSD":"GBPUSDT","USDJPY":"USDUSDT"}
selected_pair="EURUSDT"
selected_name="EURUSD"

mode="ELITE"
trade_mode="MANUAL"
duration=1

balance=100
risk=0.02
loss_streak=0
cooldown=False

def send(text,keyboard=None):
    requests.post(BASE_URL+"sendMessage",json={
        "chat_id":chat_id,
        "text":text,
        "reply_markup":keyboard
    })

def updates(offset=None):
    return requests.get(BASE_URL+"getUpdates",params={"offset":offset}).json()

def menu():
    return {"keyboard":[
        ["📊 إشارة","💱 الأزواج"],
        ["⏱ المدة","🎛 الوضع"],
        ["🔥 ELITE","🏦 SMC"]
    ],"resize_keyboard":True}

def get_prices(symbol):
    data=requests.get(f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=50").json()
    return [float(c[4]) for c in data]

def ema(p):
    e=p[0]; k=2/(20+1)
    for x in p: e=x*k+e*(1-k)
    return e

def rsi(p):
    g,l=[],[]
    for i in range(1,len(p)):
        d=p[i]-p[i-1]
        if d>=0:g.append(d)
        else:l.append(abs(d))
    ag=sum(g[-14:])/14 if g else 0.001
    al=sum(l[-14:])/14 if l else 0.001
    return 100-(100/(1+ag/al))

def elite(sym):
    p=get_prices(sym)
    if rsi(p)<25 and p[-1]>ema(p): return "BUY",p[-1]
    if rsi(p)>75 and p[-1]<ema(p): return "SELL",p[-1]
    return None

def smc(sym):
    p=get_prices(sym)
    h=max(p[-10:]); l=min(p[-10:])
    if p[-1]<l: return "BUY",p[-1]
    if p[-1]>h: return "SELL",p[-1]
    return None

def lot():
    r=risk if loss_streak<2 else 0.01
    return round(balance*r,2)

def entry_signal(direction):
    send(f"🚨 إشارة {direction} بعد 10 ثواني")
    time.sleep(10)
    send(f"🔥 ادخل الآن\n{selected_name} {direction}\n💰 {lot()}$\n⏱ {duration} دقيقة")

def run():
    global chat_id,mode,selected_pair,selected_name
    global trade_mode,duration,loss_streak,cooldown

    offset=None

    while True:
        data=updates(offset)

        for u in data.get("result",[]):
            offset=u["update_id"]+1
            msg=u.get("message")
            if not msg: continue

            chat_id=msg["chat"]["id"]
            text=msg.get("text","")

            if text=="/start":
                send("🔥 جاهز",menu())

            elif text=="💱 الأزواج":
                send("اختر:",{"keyboard":[["EURUSD","GBPUSD"],["USDJPY"]],"resize_keyboard":True})

            elif text in pairs:
                selected_pair=pairs[text]
                selected_name=text
                send(f"تم {text}",menu())

            elif text=="⏱ المدة":
                send("اختر:",{"keyboard":[["1","3","5"]],"resize_keyboard":True})

            elif text in ["1","3","5"]:
                duration=int(text)
                send(f"تم {duration} دقيقة",menu())

            elif text=="🎛 الوضع":
                send("اختر:",{"keyboard":[["MANUAL","AUTO"]],"resize_keyboard":True})

            elif text in ["MANUAL","AUTO"]:
                trade_mode=text
                send(f"تم {text}",menu())

            elif text=="📊 إشارة":
                if cooldown:
                    send("⛔ توقف")
                    continue

                result=smc(selected_pair) if mode=="SMC" else elite(selected_pair)

                if result:
                    d,_=result
                    entry_signal(d)
                else:
                    send("❌ لا يوجد")

            elif text=="🔥 ELITE":
                mode="ELITE"
                send("تم ELITE")

            elif text=="🏦 SMC":
                mode="SMC"
                send("تم SMC")

            elif text=="loss":
                loss_streak+=1
                if loss_streak>=3:
                    cooldown=True

            elif text=="win":
                loss_streak=0

            elif text=="resume":
                cooldown=False
                loss_streak=0
                send("رجعنا")

        time.sleep(1)

run()
