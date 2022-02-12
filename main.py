'''updates
VER2.1(20211208):
・決済条件のバグ修正
-Trade.close_tradeを修正
問題：stdevが規定値を超えないと、LOSS_CUT以上の損失が出ていても決済しない
解決：LOSS_CUTは値動きに関係なしに損切。利確は一定の値動きに収まるまでしない。

VER2.1(20211204):
・全決済条件の変更
問題：stdev規定値越えで全決済をしていたが、価格変動が少ないレンジ相場で実行されると損失が増えてしまう。
対策：stdevが規定値を超えた場合でも、標準偏差の閾値を超えていない場合は全決済を行わない。
- SIGMA_THRESHOLD = 15000　を追加
- Trade.close_tradeを修正。stdev and sigma > SIGMA_THRESHOLD で全決済実行。
・メンテナンス復帰の復元処理を変更
問題：復帰後しばらく条件を満たしても新規取引が行われない（原因不明）
原因：復帰後のinit_dataが機能していない、もしくはループ内のrule=self.ruleが悪さ。
対策：loop内のメンテ突入時の処理の、self.rule = Rule()をコメントアウト。その後のinit_dataで止まっている間のデータは埋まる。
'''
from mod.tracker import Tracker
from mod.atime import DateChecker
from mod.stats.bollinger import Bollinger
#from mod.twitter2.tweet import tweet_with_story
from mod.twitter2.tweet import tweet
from mod.twitter2.tweet import tweet2 #成績ツイート
from mod.savereport import save_report
from gmo import GMO
import time
import datetime
import os
#version
BOT = {"NAME":"全力君FX","VER":"3.0"}
#leverage BTC
PAIR = "BTC_JPY"
#True when test mode
TEST = False
#trade "legs" in seconds
TRADE_INTERVAL_SEC = 300
#ATIMEのカウント周期
MAX_COUNT = 3600/TRADE_INTERVAL_SEC
#least amount of jpy to hold position
TRADE_THRESHOLD = 120000
#順張り切り替え偏差
REVERSE_THRESHOLD = 10000
#標準偏差の閾値
SIGMA_THRESHOLD = 15000
SPREAD_LIMIT = 3000
TRADE_AMOUNT = 0.01
PROF_RATIO = 0.007
LOSS_RATIO = 0.007
#max time to hold position
MAX_HOLD_TIME = datetime.timedelta(seconds=60*60*4)
#min time between trades
MIN_TRADE_SPAN = datetime.timedelta(seconds=0)

#開始時の残高
START_BALANCE = 300000

#価格推移ファイル名
TRANSIT_FILE = "log/transitlong.txt"
FEE_TIME = {
    "hourfrom":5,
    "hourto":6,
    "minutefrom":30,
    "minuteto":59
}
#APIでロウソク足チャート取得用
LEGS = {
    60:"1min",
    300:"5min",
    900:"15min",
    1800:"30min",
    3600:"1hour",
    14400:"4hour",
    86400:"1day"
}

TIME_IN_SEC = {
    "1m":60,
    "5m":300,
    "15m":900,
    "1h":3600,
    "2h":7200,
    "4h":14400,
    "1d":86400
}
DATECHECK_INTERVAL = TIME_IN_SEC["4h"]

def log_msg(string):
    now = datetime.datetime.now()
    now = now.strftime('%Y-%m-%d %H:%M:%S')
    print(now + '  ' + string)

def write_value(filename,value,price=None):
    '''グラフ用。valueは残高、priceはBTC価格を想定
    '''
    value = str(value)
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    base = os.path.dirname(__file__)
    path = os.path.join(base,filename)

    if not os.path.exists(path):
        open(path,'w').close()

    with open(path,mode="a") as f:
        value = str(value)
        price = str(price)
        rec = ",".join([now,value,price]) + "\n"
        f.write(rec)

def is_fee_time(now=None):
    '''持ち越し手数料回避用'''
    now = now or datetime.datetime.now()
    hr = now.hour
    mi = now.minute
    ret = False
    if hr >= FEE_TIME["hourfrom"] and hr < FEE_TIME["hourto"]:
        if mi >= FEE_TIME["minutefrom"] and mi <= FEE_TIME["minuteto"]:
            ret = True
    return ret

#result:[dict] {"BUY":{"trades":int,"profit":int,"wins":0},"SELL":{...same},TOTAL:{...same},valuation:int}
def send_tweet(result,side=None):
    '''ツイート用関数'''
    nowstr = datetime.datetime.now().strftime("%m月%d日%H時")
    nowstr += "の物語"    
    valuation = result["valuation"]
    trades = result["TOTAL"]["trades"]
    wins = result["TOTAL"]["wins"]
    prof = result["TOTAL"]["profit"]
    keys = ["評価額 ","取引回数","勝利数 ","確定損益"]
    values = [valuation,trades,wins,prof]

    if side:
        keys.append("全力判定")
        values.append(side)

    tweet(nowstr,keys=keys,values=values,bot=BOT)

def report(after=None,ext=".png"):
    '''成績ツイート用関数'''
    opath = "./res/rpt"
    if after is None:
        now = datetime.datetime.now()
        delta = datetime.timedelta(days=7)
        after = now - delta
    
    save_report(TRANSIT_FILE,opath)
    msg = f'💰{after.year}年{after.month}月{after.day}日{after.hour}時以降の成績💰\n'
    imgfile = opath + ext
    tweet2(msg,img=imgfile,bot=BOT)
    

class Rule(Bollinger):

    def __init__(self):
        super().__init__()

    def update(self,price):
        super().update(price)
    
    
    def is_range(self,ratio):
        if len(self.prices) < self.interval:
            return True
        prices = self.prices[:self.interval]
        max_p = max(prices)
        min_p = min(prices)
        diff = max_p - min_p
        thresh = min_p * ratio
        ret = diff < thresh
        #print(f'diff:{diff} th:{thresh}')
        #print(ret)
        return ret
    
    def stdev_check(self):
        '''starndardizeが2以上もしくは-2以下かチェックする
        !20211215　BUY SELLを逆転させた。
        Returns:
            None | "BUY" | "SELL]:
                None when simgas[0] < SIGMA_THRESHOLD
                "SELL" when dev >= 2
                "BUY" when dev <= -2
                None otherwise
        '''
        #sigma = self.sigmas[0]
        #if sigma < SIGMA_THRESHOLD: return None
        
        dev = self.standardize()
        if dev <= -2: return "BUY"
        if dev >= 2: return "SELL"
        return None
    
    def velocity_check(self,index=0):
        '''20211216追加
        stdev_checkから外だし
        threshold以上の値動きがある時True。ないときFalse
        '''
        return self.sigmas[index] > SIGMA_THRESHOLD

    #side:"BUY"|"SELL"
    #ratio:float
    def is_safe(self,side,ratio,current=None):
        prices = self.prices
        current = current or prices[0]
        itv = self.interval

        #価格が埋まり切っていない場合はTrue判定
        if len(prices) < itv:
            return True
        #sideが取得出来ていない場合はTrue判定
        if side is None:
            return True

        avg = sum(prices[:itv])/itv
        #print(f'avg:{avg}')
        
        if side == "BUY":
            #現在値が閾値未満ならFalse
            thresh = avg * (1 - ratio)
            if current < thresh:
                return False
        elif side == "SELL":
            #現在値が閾値を超えるならFalse
            thresh = avg * (1 + ratio)
            if current > thresh:
                return False
            
        return True
    
    def is_over_ndist(self,position,val=2, pos=0):
        under = False if position.side == "BUY" else True
        return super().is_over_ndist(val=val, pos=pos, under=under)
    
    def prof_close_check(self,position,ratio):
        #取引方向に2σ超えている場合False(利確しない)
        #isover = self.is_over_ndist(position)
        #if isover:
        #    return False

        price = self.prices[0]
        open_price = position.price
        side = position.side
        magni = (1+ratio) if side == "BUY" else (1-ratio)
        ret = price > open_price * magni if side == "BUY" else price < open_price * magni
        #print(f'prof check:{ret}')
        return ret

    def loss_close_check(self,position,ratio):
        price = self.prices[0]
        open_price = position.price
        side = position.side
        magni = (1-ratio) if side == "BUY" else (1+ratio)
        ret = price < open_price * magni if side == "BUY" else price > open_price * magni
        return ret

    @property
    def max_len_reached(self):
        return len(self.prices) == self.max_length

class Trade:


    def __init__(self):
        self.gmo = GMO(PAIR)
        self.rule = Rule()
        #全決済フラグ
        self.all_closed = False
    
    def init_data(self,trade_sec,sleep=True):
        if trade_sec >= TIME_IN_SEC["1m"]:
            last_time = self._init_data(trade_sec)
            sleep_time = self._first_sleep_time(last_time,trade_sec)
            if sleep:
                time.sleep(sleep_time)

    #ret => [datetimeo]last time
    def _init_data(self,trade_sec=60):
        #ボリバンのσを埋めるため２倍
        recs = self.rule.max_length * 2
        candles = self.gmo.get_candles(recs,trade_sec)
        if candles is None:
            #candles未取得の時は前回時間を計算して返す。。。
            log_msg("candles are None!")
            now = time.time()
            rem = now % trade_sec
            return datetime.datetime.fromtimestamp(now -rem)
        for candle in candles:
            price = candle.close
            self.rule.update(price)
        return candle.open_time

    #last_time:[datetime]
    #trade_interval:[int]secoonds
    def _first_sleep_time(self,last_time,trade_sec):
        delta = datetime.timedelta(seconds=trade_sec)
        next_time = last_time + delta
        now = datetime.datetime.now()
        sleep_time = (next_time-now).total_seconds()
        sleep_time = max(sleep_time,0)
        return sleep_time
    
    #maintenance後復帰処理
    def wait_til_open(self,tis):
         log_msg("gonna sleep for 1h...market is not open.")
         time.sleep(TIME_IN_SEC["1h"])
        
    
    def loop(self,tis=300,max_count=12):
        gmo = self.gmo
        #rule = self.rule
        tracker = Tracker(tis)
        datechecker = DateChecker(DATECHECK_INTERVAL)
        
        while True:
            #メンテ復帰後、新規取引出来るようにこっちに移動。
            #_init_dataでself.ruleに対して更新が行われるため、ruleに対しては行われない。。
            rule = self.rule
            ticker = gmo.ticker()
            #check tweet time
            if datechecker.check():
                log_msg(f'next_time:{datechecker.next_time}')
                result = self.get_result()
                if result:
                    _pr = ticker.price if ticker else 0
                    write_value(TRANSIT_FILE,result["valuation"],_pr)
                    send_tweet(result)
            
            #tickerが取得できた場合のみ、売買判定を行う
            if ticker:
                rule.update(ticker.price)
                if is_fee_time():
                #手数料時間内なら全決済
                    if not self.all_closed:
                        #全決済フラグがOFFなら全決済
                        self.close_all_positions()
                        #フラグも立てておく。次フレームで実行されないように。
                        self.all_closed = True
                else:
                #手数料時間外なら取引
                    #全決済フラグをOFFに戻す
                    if self.all_closed:
                        self.all_closed = False
                    
                    self.open_trade()
                    self.close_trade()
                #ticker取れなかったときはsleepさせたくないので、ここに入れる。
                #手数料時間中でも同じ感覚でsleep。価格は更新しておきたいため。
                tracker.wait()

            #tickerの取得ができなかった場合、marketが空いているかチェックする。
            elif self.is_not_open() or gmo.is_maintenance():
                #sleep後の復帰処理...
                #self.ruleに対して行う。ruleだとself.ruleとの参照が切れ、init_dataの対象にならん。
                #self.rule = Rule()
                #成績ツイート
                report()
                self.wait_til_open(tis)
                #restarting...
                self.init_data(tis,sleep=True)

    
    def open_trade(self):
        '''checks whether to make a open trade
        Returns None
        '''
        margin = self.gmo.margin()
        if margin:
            action = self.rule.stdev_check()
            #open判定
            if action:
                if self.rule.velocity_check():
                    #余力あり
                    if margin.available >= TRADE_THRESHOLD:
                        self.market_open(action)
                    #余力なし
                    else:
                        log_msg("not enough money to trade!")
                else:
                    sig = self.rule.sigmas[0]
                    log_msg(f"open_trade stopped...sigma:{sig}")
   
    def close_trade(self):
        '''closeの条件を整理
        1.全決済：actionが"BUY"か"SELL"かつsigma閾値超えで逆ポジ全決済。
                 actionがNoneならしない。
        2.利確：PROF_RATIOを超えている。ただし、ポジションがactionと同じ方向の時は利確しない。
        3.損切：LOSS_RATIOが超えている
    
        '''
        action = self.rule.stdev_check()
        #sigma = self.rule.sigmas[0]
        positions = self.gmo.positions()

        if positions is None: return None
        #1.全決済
        #20211215修正 sigmaをstdev_checkに盛り込んだため
        #if action and sigma > SIGMA_THRESHOLD:
        if action:
            if self.rule.velocity_check():
                self.market_close_one_side(action,positions)
            else:
                sig = self.rule.sigmas[0]
                log_msg(f"close_all_trade stopped...sigma:{sig}")

        #2と3
        for p in positions.pos:

            close = False
            msg = ""
            #2 利確ラインを超えている
            if self.rule.prof_close_check(p,PROF_RATIO):
                #2 acitionとポジションが同じ向きでない場合、利確
                if p.side != action:
                    close = True
                    msg = f'{p.pid} {p.side} profit closing!'
            #3　損切ラインを超えていたら損切
            elif self.rule.loss_close_check(p,LOSS_RATIO):
                close = True
                msg = f'{p.pid} {p.side} loss closing...'

            if close:
                self.market_close(p)
                log_msg(msg)
        
    def market_open(self,side):
        '''executes openbuy or opensell. This must be called after `open_trade` function.
        side(str):"BUY" | "SELL"
        ''' 
        if side is None: return None
        buy = True if side == "BUY" else False
        #ポジション有り時は直近取引からMIN_TRADE_SPAN以上経過していること
        positions = self.gmo.positions()
        if positions:
            latest = positions.latest_time()
            if latest:
                if latest + MIN_TRADE_SPAN > datetime.datetime.now():
                    return None
            else:
                #ポジション無し。何もせず取引に進みましょう。
                pass
        if buy:
            self.gmo.market(self.gmo.pair,"BUY",TRADE_AMOUNT)
            log_msg(f"open buy! sigma:{self.rule.sigmas[0]}")
        else:
            self.gmo.market(self.gmo.pair,"SELL",TRADE_AMOUNT)
            log_msg(f"open sell! sigma:{self.rule.sigmas[0]}")
    
    def market_close(self,position):
        '''単一のポジションをクローズする関数'''
        p = position
        if p.side == "BUY":
            side = "SELL"
        elif p.side == "SELL":
            side = "BUY"
        else:
            side = None
        if side:
            log_msg(f"close {side}")
            self.gmo.close_order(self.gmo.pair,side,"MARKET",p.pid,p.size)

    def market_close_one_side(self,side,positions=None):
        '''sideに応じて片方のポジションを全決済する
        side(str):"BUY"|"SELL"
        '''
        if side is None: return None
        closebuy = False
        closesell = False
        if side == "BUY":
            #stdevが2以上→売りポジ全解消
            closesell = True
        elif side == "SELL":
            #stdevが-2以下→買いポジ全解消
            closebuy = True
        else:
            return None
        #片方全決済
        if closesell or closebuy:     
            self.close_all_positions(closebuy,closesell,positions)
                    
    def close_all_positions(self,closebuy=True,closesell=True,positions=None):
        '''全ポジション決済。closebuy,closesellで片方のポジションを全決済。デフォルトは両向き全決済
        closebuy(boolean)[opt]
        closesell(boolean)[opt]
        '''
        positions = positions or self.gmo.positions()
        if positions:
            log_msg(f"closing pos! closebuy:{closebuy} closesell:{closesell}")
            bsize = positions.get_size("BUY")
            ssize = positions.get_size("SELL")

            if bsize > 0.0 and closebuy:
                #反対決済なのでSELLで決済
                self.gmo.close_all(self.gmo.pair,"SELL","MARKET",bsize)
            if ssize > 0.0 and closesell:
                #反対決済なのでBUY
                self.gmo.close_all(self.gmo.pair,"BUY","MARKET",ssize)

    def get_result(self):
        now = datetime.datetime.now()
        afterobj = None
        #0AM以上、6AM未満の時は1n日マイナス
        #6AM～翌6AMを集計対象にするため
        if now.hour >= 0 and now.hour < 6:
            delta = datetime.timedelta(days=1)
            yesterday = now - delta
            afterobj = datetime.datetime(
                year=yesterday.year,month=yesterday.month,
                day=yesterday.day,hour=6)
    
        
        margin = self.gmo.margin()
        summary = self.gmo.summary_after(afterobj=afterobj)
       
        #api　6/sec 上限対策
        time.sleep(1)

        #template return dict
        ret =  {
            "BUY":{ "trades":0,"profit":0,"wins":0},
            "SELL":{"trades":0,"profit":0,"wins":0},
            "TOTAL":{"trades":0,"profit":0,"wins":0},
            "valuation":0
        }
        if margin and summary:
            #両方ある場合は以下のとおり
            summary["valuation"] = margin.valuation
            ret = summary
        elif margin and not summary:
            #summaryが取れない場合（朝とか、、、）,評価額のみ設定
            ret["valuation"] = margin.valuation
        else:
            #どちらにも合致しない場合はtemplateのまま返す
            pass
        return ret
        '''
        if ret and margin:
            ret["valuation"] = margin.valuation
            return ret
        else:
            ret =  {
                "BUY":{ "trades":0,"profit":0,"wins":0},
                "SELL":{"trades":0,"profit":0,"wins":0},
                "TOTAL":{"trades":0,"profit":0,"wins":0},
                "valuation":0
            }
            return ret
        '''
    def is_not_open(self):
        ret = self.gmo.status()
        if ret:
            if ret != "OPEN":
                return True
        return False

    def _test_open_trade(self):
        print("open trade")
        ret = self.rule.open_check()

    def _test_close_trade(self):
        pass
        #print("test close!")
    
    def override(self):
        self.open_trade = self._test_close_trade
        self.close_trade = self._test_close_trade

def main():
    trade = Trade()
    if not TEST:
        trade.init_data(TRADE_INTERVAL_SEC,sleep=True)
        #sleeptime = trade.first_sleep_time(last,TRADE_INTERVAL_SEC)
    else:
        #trade.override()
        #trade.open_trade = _test_open_trade
        #trade.close_trade = _test_close_trade
        'leave me as it is...'
    trade.loop(TRADE_INTERVAL_SEC,MAX_COUNT)

if __name__ =="__main__":
    main()

    #r = latest_extremus(3600,30,0.005)
    '''
    t = Trade()
    result = t.get_result()
    print(result)
    write_value(TRANSIT_FILE,result["valuation"])
    '''
    
    
    #---------------------------------
    #test
    '''
    res = {
        "valuation":300000,
        "TOTAL":{"trades":50,"wins":40,"profit":5000}
    }
    send_tweet(res)
    '''
    '''
    write_value(TRANSIT_FILE,5000)
    write_value(TRANSIT_FILE,5000)
    t = Trade()
    res = t.get_result()
    send_tweet(res)
    '''