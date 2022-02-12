import pandas as pd
import matplotlib.pyplot as plt
import datetime

'''description
after以降の残高推移の画像のパスを保存。tweet用
afterを省略した場合は現時刻から1週間前を起点。
ifilepath:[str]　ファイル名込みパス
ofilepath:[str] ファイル名込みパス。拡張子はいれないこと
after:[datetime.datetime]
'''
def save_report(ifilepath,ofilepath,after=None):
    
    sfname = "report"

    if after is None:
        after = datetime.datetime.now() - datetime.timedelta(days=7)
    df = pd.read_csv(ifilepath,names=["date","balance","price"])
    df["ndate"] = pd.to_datetime(df["date"])
    
    x = []
    y = []
    y2 = []
    
    for i,row in df.iterrows():
        if row["ndate"] >= after:
            x.append(row["ndate"])
            y.append(row["balance"])
            y2.append(row["price"])
    
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax2 = ax.twinx()
    l1 = ax.plot(x,y,label="balance")
    l2 = ax2.plot(x,y2,label="BTC",color="red")
    ax.set_xlabel("time")
    ax.set_ylabel("balance(JPY)")
    ax2.set_ylabel("BTC")
    fig.autofmt_xdate()
    plt.grid(True)
    lines = l1 + l2
    labels = [l.get_label() for l in lines]
    lgd = plt.legend(lines,labels,loc=1)
    frame = lgd.get_frame()
    frame.set_color("turquoise")
     
    

    plt.savefig(ofilepath)
    return 

if __name__ == "__main__":
    d = datetime.datetime(2021,10,31,8)
    i = "./log/transitlong.txt"
    o = "./report"
    save_report(i,o,d)
