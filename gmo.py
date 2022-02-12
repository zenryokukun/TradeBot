from mod.exchange import Exchange
from pprint import pprint
import datetime
import time


def JST(stime):
    not_found = -1
    delta = datetime.timedelta(hours=9)
    if stime.find(".") == not_found:
        dtime = datetime.datetime.strptime(stime,'%Y-%m-%dT%H:%M:%SZ') 
    else:
        dtime = datetime.datetime.strptime(stime,'%Y-%m-%dT%H:%M:%S.%fZ')
    return dtime + delta

class _Ticker:
    def __init__(self,obj):
        self.ask = int(obj["ask"])
        self.bid = int(obj["bid"])
        self.price = int(obj["last"])
        self.jst_obj = JST(obj["timestamp"])
        
    @property
    def spread(self):
        return self.ask - self.bid

class _Positions:
    class _Position:
        def __init__(self,data):
            self.pid = data["positionId"]
            self.size = float(data["size"])
            self.price = int(data["price"])
            self.side = data["side"]
            self.profit = int(data["lossGain"])
            self.tstamp = data["timestamp"]
            self.jst_obj = JST(self.tstamp)
        
    def __init__(self,obj):
       self.pos = []
       for data in obj:
           self.pos.append(self._Position(data))
    
    #side:None,"BUY","SELL"
    def get_size(self,side=None):
        buys = 0.0
        sells = 0.0
        for p in self.pos:
            if p.side == "BUY":
                buys += float(p.size)
            elif p.side == "SELL":
                sells += float(p.size)

        if side == "BUY":
            return buys
        elif side == "SELL":
            return sells
        else:
            return buys + sells

    def total_prof(self,side=None):
        buy_prof = 0
        sell_prof = 0
        for p in self.pos:
            if p.side == "BUY":
                buy_prof += p.profit
            elif p.side == "SELL":
                sell_prof += p.profit

        if side == "BUY":
            return buy_prof
        elif side == "SELL":
            return sell_prof
        else:
            return buy_prof + sell_prof
    
    def latest_time(self):
        if len(self.pos) == 0:
            return None
        latest = max([p.jst_obj for p in self.pos])
        return latest

    
    def __len__(self):
        return len(self.pos)

class _Margin:
    def __init__(self,obj):
        self.valuation = int(obj["actualProfitLoss"])
        self.available = int(obj["availableAmount"])
        self.used = int(obj["margin"])
        self.profit = int(obj["profitLoss"])
        if "marginRatio" in obj:
            ratio = float(obj["marginRatio"]) / 100
        else:
            ratio = None
        self.ratio = ratio


class _Candle:
    def __init__(self,obj):
        self.open = int(obj["open"])
        self.high = int(obj["high"])
        self.low = int(obj["low"])
        self.close = int(obj["close"])
        self.volume = float(obj["volume"])
        self.open_time = datetime.datetime.fromtimestamp(int(obj["openTime"])/1000)

class GMO(Exchange):
  
    def __init__(self,pair=None):
        super().__init__()
        self.pair = pair
    
    def margin(self):
        robj = super().margin()
        if robj:
            return _Margin(robj)
        else:
            return None

    def ticker(self):
        robj = super().ticker(self.pair)
        if robj:
            return _Ticker(robj)
        else:
            return None
    
    def positions(self):
        robj = super().positions(self.pair)
        if robj:
            return _Positions(robj)
        else:
            return None
    
    #afterobj:after befobj:before
    #afterobj <= result < befobj
    def summary_after(self,afterobj=None,befobj=None):
        if afterobj is None:
            now = datetime.datetime.now()
            afterobj = datetime.datetime(year=now.year,month=now.month,day=now.day,hour=6)
        execs = []
        count=1
        while True:
            _execs = self.latest_executions(self.pair,count)
            #time.sleep(0.3)
            if _execs is None:
                break
            else:
                execs += _execs
            oldest =JST(_execs[-1]["timestamp"])
            if oldest >= afterobj:
                count += 1
            else:
                break
        #filter
        ret = []
        for exec in execs:
            jst = JST(exec["timestamp"])
            if jst >= afterobj:
                if befobj:
                    if jst < befobj:
                        ret.append(exec)
                else:
                    ret.append(exec)

        if len(ret) > 0:
            return self.summary(ret)
        else:
            return None

        #return execs

    def summary(self,execs=None):
        if execs is None:
            execs = self.latest_executions(self.pair)
 
        if execs:
            ret = {
                "BUY":{ "trades":0,"profit":0,"wins":0},
                "SELL":{"trades":0,"profit":0,"wins":0},
                "TOTAL":{"trades":0,"profit":0,"wins":0}
            }
            for exec in execs:
                if exec["settleType"] == "CLOSE":
                    if exec["side"] == "BUY":
                        #決済時のポジションのsideが表示される
                        #だからBUYの時ret["SELL"]に設定
                        lossGain = int(exec["lossGain"])
                        ret["SELL"]["profit"] += lossGain
                        ret["SELL"]["trades"] += 1
                        if lossGain > 0:
                            ret["SELL"]["wins"] +=1

                    elif exec["side"] == "SELL":
                        #決済時のポジションのsideが表示される
                        #だからSELLの時close_buyssに設定
                        lossGain = int(exec["lossGain"])
                        ret["BUY"]["profit"] += lossGain
                        ret["BUY"]["trades"] += 1
                        if lossGain > 0:
                            ret["BUY"]["wins"] += 1
            
            ret["TOTAL"]["trades"] = ret["BUY"]["trades"] + ret["SELL"]["trades"]
            ret["TOTAL"]["profit"] = ret["BUY"]["profit"] + ret["SELL"]["profit"]
            ret["TOTAL"]["wins"] = ret["BUY"]["wins"] + ret["SELL"]["wins"]

            return ret

        return None

    #本日もしくはdobjの日付から過去recs分取得  
    def get_candles(self,recs,trade_secs,dobj=None):
        itv = self._secs_to_interval(trade_secs)
        if trade_secs >= 14400:
            robj= self._candles_yyyy(itv,dobj)
        else:
            robj = self._candles_yyyymmdd(itv,recs,dobj)
        if robj:
            ret = []
            for obj in robj[-recs:]:
                #ret.insert(0,_Candle(obj))
                ret.append(_Candle(obj))
            return ret
        else:
            return None
        #candles = self.kline(self.pair)
    
    #recsでfilterしないで全権取得。余分もあるはずなので取得元でfilterすること
    def get_candles_all(self,recs,trade_secs,dobj=None):
        itv = self._secs_to_interval(trade_secs)
        if trade_secs >= 14400:
            robj= self._candles_yyyy(itv,dobj)
        else:
            robj = self._candles_yyyymmdd(itv,recs,dobj)
        if robj:
            ret = []
            for obj in robj:
                #ret.insert(0,_Candle(obj))
                ret.append(_Candle(obj))
            return ret
        else:
            return None
    
    #Y:datetime.datetime
    def _candles_yyyy(self,itv,Y=None):
        if Y:
            Y = datetime.datetime.strftime(Y,"%Y")
        else:
            Y = datetime.datetime.now().strftime("%Y")
        return self.kline(self.pair,itv,Y)

    #ymd_obj:datetime.datetime
    def _candles_yyyymmdd(self,itv,recs,ymd_obj=None):
        if ymd_obj:
            ymd_str = ymd_obj.strftime("%Y%m%d")
        else:
            ymd_obj = datetime.datetime.now()
            
            '''kline -> 6:00～5:00を取得してくる。0～23時ではない。
            6時のデータが取得出来るのは7時になってから。
            そのため10/2の0～6時台は10/1のデータとして取得する'''
            if ymd_obj.hour >= 0 and ymd_obj.hour <= 6:
                ymd_obj = ymd_obj - datetime.timedelta(days=1)
                print(f'yesterday:{ymd_obj}')
            ymd_str = ymd_obj.strftime("%Y%m%d")
            
        ret = self.kline(self.pair,itv,ymd_str)
        if ret is None:
            return None
        '''ここまで来たら、klineは１個以上あることが保障される'''
        while len(ret) < recs:
            ymd_obj = ymd_obj - datetime.timedelta(days=1)
            ymd_str = ymd_obj.strftime("%Y%m%d")
            prevdata = self.kline(self.pair,itv,ymd_str)
            if prevdata is None:
                break
            ret = prevdata + ret
        return ret

    def _secs_to_interval(self,secs):
        if secs == 60:
            return "1min"
        elif secs == 300:
            return "5min"
        elif secs == 900:
            return "15min"
        elif secs == 3600:
            return "1hour"
        elif secs == 14400:
            return "4hour"
        elif secs == 86400:
            return "1day"



if __name__ == "__main__":
    gmo = GMO("BTC_JPY")
    '''
    base = datetime.datetime(2021,10,22)
    candles = gmo.get_candles(30,3600,base)
    print(candles[0].open_time)
    print(candles[len(candles)-1].open_time)
    '''
    candles = gmo.get_candles(20,3600)
    print(len(candles))
    print(candles[0].open_time)
    print(candles[len(candles)-1].open_time)
    
    '''
    c = gmo.kline("BTC_JPY","1min","20211012")
    import json
    with open("./candles.json",mode="w") as f:
        json.dump(c,f)
    '''
    '''
    after = datetime.datetime(2021,10,9,6)
    bef = datetime.datetime(2021,10,10,6)
    r = gmo.summary_after(after,bef)
    print(r)
    '''
    '''
    r = gmo.get_candles(21,300)
    print(len(r))
    c = r[0]
    print(c.open_time)
    print(c.high)
    print(c.low)
    print(c.close)
    print(c.open)
    '''
