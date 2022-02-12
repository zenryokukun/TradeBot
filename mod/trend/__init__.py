from .cw import crypto_dict
from .extrema import search
from .extrema import show

def times_and_prices(periods,max_recs,before=None,after=None):
	datas = crypto_dict(periods,max_recs,before,after)
	if datas:
		times = [data["closetime"] for data in datas]
		prices = [data["close"] for data in datas]
		return times,prices
	return None,None
#params:periods:int,max_recs:int,ratio:float
#=> maxima:[int],minima:[int]
def local_datas(times,prices,ratio):
	return search(x=times,y=prices,ratio=ratio)


def latest(maxima,minima):
	max_len = len(maxima["dtime"]) 
	min_len = len(minima["dtime"])
	maxi_date = None
	mini_date  = None
	which = None
	ret = None

	if max_len !=0:
		maxi_date = maxima["dtime"][-1]
	if min_len !=0:
		mini_date  = minima["dtime"][-1]
	
	if maxi_date is None and mini_date is None:
		return None
	
	if maxi_date and mini_date  is None:
		which = "maxi"
	if maxi_date is None and mini_date :
		which = "mini"
	
	if maxi_date and mini_date :
		if maxi_date > mini_date :
			which = "maxi" 
		else:
			which = "mini"

	if which == "maxi":
		ret = {
			"time":maxi_date,
			"price":maxima["price"][-1],
			"is_maxi":True
		} 

	elif which == "mini":
		ret = {
			"time":mini_date,
			"price":minima["price"][-1],
			"is_maxi":False
		}
	
	return ret

#seconds:秒　recs:足の数 ratio:山谷を作る値動きの比率
#crypto apiから取得
def latest_extremus(seconds:int,recs:int,ratio:float):
	times,prices =  times_and_prices(seconds,recs)
	if times is None or prices is None:
		return None

	maxi,mini = local_datas(times,prices,ratio)
	ret =  latest(maxi,mini)
	return ret
	
#パラメータのデータから取得
def latest_extremus_udata(times,prices,ratio,before=None,after=None):
	if times is None and prices is None:
		return None
	maxi,mini = local_datas(times,prices,ratio)
	ret =  latest(maxi,mini)
	return ret

#testing purpose only
#get data from crypto
def test(secs=3600,recs=20,ratio=0.005,before=None,after=None):
	times,prices = times_and_prices(secs,recs,before,after)
	maxi,mini = local_datas(times,prices,ratio)
	ret = latest(maxi,mini)
	print(ret)
	show(times,prices,maxi,mini)

def test_udata(times,prices,ratio,before=None,after=None):
	maxi,mini = local_datas(times,prices,ratio)
	ret = latest(maxi,mini)
	print(ret)
	show(times,prices,maxi,mini)


if __name__ == "__main__":
	
	times,prices = times_and_prices(60*60,20)
	maxi,mini = local_datas(times,prices,0.005)
	ret = latest(maxi,mini)
	print(ret)
	show(times,prices,maxi,mini)
	#ret = latest_extremus(60*60,30,0.005)
	#print(ret)

	
	