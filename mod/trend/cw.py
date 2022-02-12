import requests
import datetime

'''
get candlestick useing crypto api
[public] crypto(int,int,dateobj,dateobj) -> [['CloseTime', 'OpenPrice', 'HighPrice', 'LowPrice', 'ClosePrice','Volume', 'QuoteVolume'],[...]]
[public] crypto_dict(int,int,dateobj,dateobj) -> [{"closetime":str,"open":int,"high":int,"low":int,"close":int,"volume":float,"quote":float}]
[public】crypto_close(int,int,dateobj,dateoobj) ->[close,close]
'''

#timestamp to jst string
def ts_jst_str(ts):
	jstobj = datetime.datetime.fromtimestamp(ts)
	jststr = jstobj.strftime("%Y-%m-%d %H:%M:%S")
	return jststr

#periods:[int] in seconds
#after,before:[datetime.datetime]
#max_recs:[int] max recs to retrieve
def crypto(periods,max_recs,before=None,after=None):
	url = 'https://api.cryptowat.ch/markets/bitflyer/btcjpy/ohlc'
	before = before or datetime.datetime.now(datetime.timezone.utc)
	after = after or before - datetime.timedelta(seconds=periods * max_recs)
	#api data columns
	# ['CloseTime', 'OpenPrice', 'HighPrice', 'LowPrice', 'ClosePrice','Volume', 'QuoteVolume']
	res = requests.get(url,params = {
		"periods":periods,
		"before":int(before.timestamp()),
		"after":int(after.timestamp())
	})

	if res.status_code == 200:
		resp = res.json()
		if "result" in resp:
			result = resp["result"]
			periods = str(periods)
			if periods in result:
				ret = result[periods]
				return ret
	else:
		print(f"{datetime.datetime.now()}: crypto api error")

	return None

#closepriceだけを取得
def crypto_close(periods,max_recs,before=None,after=None):
	datas = crypto(periods,max_recs,before,after)
	if datas:
		return [data[4] for data in datas]

def vel(periods,max_recs,before=None,after=None):
	datas = crypto_dict(periods,max_recs,before,after)
	highs = [data["high"] for data in datas]
	lows = [data["low"] for data in datas]
	times = [data["closetime"] for data in datas]
	for h,l,t in zip(highs,lows,times):
		diff = h-l
		_vel = diff/l
		print(t,_vel)

#dict型で全項目取得
def crypto_dict(periods,max_recs,before=None,after=None):
	datas = crypto(periods,max_recs,before,after)
	if datas:
		ret = []
		#"closetime":str,"open":int,"high":int,"low":int,"close":int,"volume":float,"quote":float
		for data in datas:
			di = {
				"closetime":ts_jst_str(data[0]),
				"open":data[1],
				"high":data[2],
				"low":data[3],
				"close":data[4],
				"volume":data[5],
				"quote":data[6]
			}
			ret.append(di)
		return ret
	return None

if __name__ == "__main__":
	datas = vel(60*60*24,5)
	print(datas)
	