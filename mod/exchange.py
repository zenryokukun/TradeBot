import requests
import configparser
import time
import datetime
import hmac
import hashlib
import json
import math
import os
from pprint import pprint


#symbol -> BTCは取引所、BTC_JPYはレバレッジ取引所
#robj -> response.json()
#price,size -> str....

#******************************************
#[public methods]
#status
#ticker
#kline 
#get_assets
#market
#buy
#limit
#stop
#******************************************

def search_key(di,key):
	if type(di) == dict:
		if key in di:
			return di["key"]
		else:
			for val in di.values():
				if type(val) == dict:
					return search_key(val,key)
	else:
		return None

class Exchange:

	URL_PRIVATE = 'https://api.coin.z.com/private'
	URL_PUBLIC = 'https://api.coin.z.com/public'
	
	def __init__(self):
		basepath = os.path.dirname(__file__)
		filepath = 'conf/config.ini'
		targetpath = os.path.join(basepath,filepath)
		
		conf = configparser.ConfigParser()
		conf.read(targetpath)

		self.api_key = conf['gmo']['api_key']
		self.api_secret = conf['gmo']["api_secret"]
		self.error_msg = ''

	#------------------------------------
	#authorization
	#------------------------------------

	#path -> disclude endpoints!
	def _getsign(self,path,reqbody=None,method='POST'):
		skey = self.api_secret
		nonce = str(int(time.time())) + '000'
		txt = nonce + method + path
		if reqbody:
			txt += json.dumps(reqbody)

		sign = hmac.new(skey.encode(),txt.encode(),
				hashlib.sha256).hexdigest()
		return nonce,sign
	
	def getheader(self,path,reqbody=None,method='POST'):
		akey = self.api_key
		nonce,sign = self._getsign(path,reqbody,method)
		ret = {
			"API-KEY":akey,
			"API-TIMESTAMP":nonce,
			"API-SIGN":sign
		}
		return ret
	
	#reqbody:[dict]params={}
	#認証後＆実行 private apiはこれを通して実行
	def auth(self,path,params=None,method="POST",fnName=None):
		if method == "POST":
			headers = self.getheader(path,params,method)
			data = json.dumps(params)
			#res = requests.post(self.URL_PRIVATE+path,headers=headers,data=data)
			res = self.exec(requests.post,self.URL_PRIVATE+path,headers=headers,data=data)
		elif method =="GET":
			#no params for signature when 'GET'
			headers = self.getheader(path=path,method=method)
			#res = requests.get(self.URL_PRIVATE+path,headers=headers,params=params)
			res = self.exec(requests.get,self.URL_PRIVATE+path,headers=headers,params=params)
		else:
		#POST GET以外はエラー DELETEはいまのところない
			self.log(f"auth:unknown method..->{method}")
			return None
		
		if res is None:
			return None
			
		robj = self.check_response(res,fnName=fnName)
		
		return robj
		
	#------------------------------------
	#checker and utility methods
	#------------------------------------
	
	def log(self,message):
		now=datetime.datetime.now()
		nowstr = now.strftime("%Y-%m-%d %H:%M:%S")
		print(nowstr + ' ' + message)

	#requests method実行
	#fn: requests method
	#args:url
	#kw:params,headers,data等想定
	def exec(self,fn,*args,**kw):
		res = None
		try:
			res = fn(*args,**kw)
		except requests.exceptions.ConnectionError as e:
			self.log("connection Error..")
		return res		

	#checks http status and api status
	# ret -> res.json() or None
	def check_response(self,res,fnName=None):
		if res is None:
			return None
		if self._res_http_check(res,fnName):
			#json to dict
			robj = res.json()
			if self._res_api_check(robj,fnName):
				return robj
		return None
	#http response status_code checker
	def _res_http_check(self,res,fnName=None):
		ret = False
		status = res.status_code
		if status != 200:
			self.log(f'[{fnName}] --http status:{status}')
			print(res.json())
		else:
			ret = True
		return ret
	
	#api status checker
	#res_http_check must be called beforehand.
	def _res_api_check(self,robj,fnName=None):
		ret = False
		if "status" in robj:
			if robj["status"] == 0:
				ret = True
				#エラーメッセージをリセット
				self.error_msg = ''
			else:
				self.log(f'[{fnName}] -- api status:{robj["status"]}')
				print(robj)
				#エラーメッセージをセット
				self.error_msg = robj
		else:
			self.log(f"[{fnName}]no such key in response ... -> 'status'")
			print(robj)
		return ret

	def extract_data(self,robj,key1,key2=None):
		ret = None
		if robj:
			if key1 in robj:
				if key2:
					if key2 in robj[key1]:
						ret = robj[key1][key2]
				else:
					ret = robj[key1]
		return ret

	#apiエラーメッセージ取得。httpエラーはとらないので注意
	#r-> {"message_code":str,"message_string":str}
	def api_error(self):
		if self.error_msg:
			return self.error_msg["messages"][0]
		return None
	
	def is_maintenance(self):
		if self.error_msg == '':
			return False
		else:
			err = self.api_error()
			if err:
				code = err["message_code"]
				print(f'err:{code}')
				#5201-定期メンテ　5202緊急メンテ
				if code in ["ERR-5201","ERR-5202"]:
					return True
			return False
	
	#------------------------------------
	#public api
	#------------------------------------
	
	#取引所status -> 'MAINTENANCE' 'PREOPEN' 'OPEN'
	#ret -> None or RES["data"]["status"]
	def status(self):
		path = '/v1/status'
		res = self.exec(requests.get,self.URL_PUBLIC+path)
		robj = self.check_response(res,"status")
		ret = self.extract_data(robj,key1="data",key2="status")
		return ret
		

	#BTC,ETH,BTC_JPY,ETH_JPY,....
	#ret -> None or RES["data"][0]
	def ticker(self,pair=None):
		path = '/v1/ticker'
		params = {}
		if pair:
			params["symbol"] = pair
		res = self.exec(requests.get,self.URL_PUBLIC + path,params=params)
		robj = self.check_response(res,"ticker")
		ret = self.extract_data(robj,key1="data")
		if ret:
			return ret[0]
		else:
			return None
	
	#candle stick
	#pair:BTC,ETH,BTC_JPY,...
	#interval:str 1min 5min 1hour 1day
	#after:str ~1h:YYYYMMDD  4h~:YYYY
	#ret -> None or RES["data"]
	def kline(self,pair,interval,after):
		path = '/v1/klines'
		params = {
			"symbol":pair,
			"interval":interval,
			"date":after
		}
		#res = requests.get(self.URL_PUBLIC + path,params=params)
		res = self.exec(requests.get,self.URL_PUBLIC + path,params=params)
		robj = self.check_response(res,"kline")
		ret = self.extract_data(robj,key1="data")
		return ret
	
	#------------------------------------
	#private api
	#------------------------------------
	def assets(self):
		path = '/v1/account/assets'
		robj = self.auth(path,method='GET',fnName="assets")
		return robj

	#args:["BTC","BTC_JPY"]	
	# ret -> {"BTC":0.05,"BTC_JPY":0.01,"JPY":5000000,..}	
	def get_assets(self,*args):
		ret = {}
		robj = self.assets()
		if robj is not None:
			for d in robj["data"]:
				sym = d["symbol"]
				if sym in args:
					ret[sym] = float(d["available"])
			return ret
		else:
			return None
	
	# ret -> None or RES["data"]
	def margin(self):
		path = '/v1/account/margin'
		robj = self.auth(path,method='GET',fnName="margin")
		ret = self.extract_data(robj,key1="data")
		return ret
	
	#side:"BUY","SELL"
	#execType:"MARKET" "LIMIT" "STOP"
	#-> int:orderID
	
	def order(self,pair,side,execType,size,price=None,losscutPrice=None,timeInForce=None,cancel=None):
		path = '/v1/order'
		params = {
			"symbol":pair,
			"pair":pair,
			"side":side,
			"executionType":execType,
			"size":str(size)
		}
		if price:
			params["price"] = str(price)
		if losscutPrice:
			params["losscutPrice"] = losscutPrice
		if timeInForce:
			params["timeInForce"] = timeInForce
		if cancel:
			params["cancelBefore"] = cancel
		
		robj = self.auth(path,params=params,fnName=execType)
		ret = self.extract_data(robj,key1="data")
		return ret
	
	def market(self,pair,side,size,**kw):
		robj = self.order(pair=pair,side=side,execType="MARKET",size=size,**kw)
		return robj

	def limit(self,pair,side,price,size,losscutPrice=None,**kw):
		robj = self.order(pair=pair,side=side,execType="LIMIT",
			size=size,price=price,losscutPrice=losscutPrice,**kw)
		return robj

	def stop(self,pair,side,price,size,losscutPrice=None,**kw):
		robj = self.order(pair=pair,side=side,execType="STOP",
			size=size,price=price,losscutPrice=losscutPrice,**kw)
		return robj
	
	#レバレッジのみ pairは"BTC_JPY" "ETH_JPY"
	def close_order(self,pair,side,execType,ID,size,price=None,timeInForce=None):
		path = '/v1/closeOrder'
		params = {
			"symbol":pair,
			"side":side,
			"executionType":execType,
			"settlePosition":[{
				"positionId":ID,
				"size":str(size)
			}]
		}
		
		if price:
			params["price"] = str(price)
		if timeInForce:
			params["timeInForce"] = timeInForce
		
		robj = self.auth(path,params=params,fnName="close_order")
		ret = self.extract_data(robj,key1="data")
		return ret
	
	def close_all(self,pair,side,execType,size,price=None,timeInForce=None):
		path ="/v1/closeBulkOrder"
		params = {
			"symbol":pair,
			"side":side,
			"executionType":execType,
			"size":str(size),
		}
		if price:
			params["price"] = price
		if timeInForce:
			params["timeInForce"] = timeInForce
		robj = self.auth(path,params=params,fnName="close_order")
		ret = self.extract_data(robj,key1="data")
		return ret
		

	#ids:list[str,str,...]
	def get_orders(self,ids):
		path = '/v1/orders'
		if type(ids) == list:
			orderid = ','.join(ids)
		elif type(ids) == int:
			orderid = ids
		else:
			return None
		params = {"orderId":orderid}
		robj = self.auth(path,params=params,method="GET",fnName="get_orders")
		ret = self.extract_data(robj,key1="data",key2="list")
		return ret

	def active_orders(self,pair,page=None,count=None):
		path = '/v1/activeOrders'
		params = {"symbol":pair}
		if page:
			params["page"] = page
		if count:
			params["count"] = count
		robj = self.auth(path,params=params,method="GET")
		ret = self.extract_data(robj,key1="data",key2="list")
		return ret

	def executions(self,orderid=None,exec_id=None):
		path = '/v1/executions'
		if orderid is None and exec_id is None:
			return None
		params = {}
		if orderid:
			params["orderId"] = orderid
		elif exec_id:
			params["executionId"] = exec_id
		robj = self.auth(path,params=params,method='GET')
		ret = self.extract_data(robj,key1="data",key2="list")
		return ret
	
	def latest_executions(self,pair,page=1,count=100):
		path = '/v1/latestExecutions'
		params = {
			"symbol":pair,
			"page":page,
			"count":count
		}
		robj = self.auth(path,params=params,method="GET")
		ret = self.extract_data(robj,key1="data",key2="list")
		
		return ret

	def cancel(self,orderid):
		path = '/v1/cancelOrder'
		params = {"orderid":orderid}
		robj = self.auth(path,params=params,fnName="cancel")
		ret = self.extract_data(robj,key1="status")
		return robj
	
	def positions(self,pair,page=1,count=100):
		path = '/v1/openPositions'
		params = {
			"symbol":pair,
			"page":page,
			"count":count
		}
		robj = self.auth(path,params,fnName="positions",method="GET")
		ret = self.extract_data(robj,key1="data",key2="list")
		return ret
	
	def position_summary(self):
		path = '/v1/positionSummary'
		robj = self.auth(path,method='GET',fnName="position_summary")
		ret = self.extract_data(robj,key1="data",key2="list")
		return ret

if __name__ == "__main__":
	#__init__ test
	gmo = Exchange()
	can = gmo.kline("BTC_JPY","1hour","20211025")
	func = lambda d : str(datetime.datetime.fromtimestamp(int(d)/1000))
	times = [func(c["openTime"]) for c in can]
	print(times)
	'''
	kl = gmo.kline("BTC_JPY","1min","20211012")
	kl += gmo.kline("BTC_JPY","1min","20211013")
	print(len(kl))
	with open("candles.json","w") as f:
		json.dump(kl,f,indent=2)
	'''
	#-------------------
	
	#extract_data test
	'''
	test = {
		"data":{
			"list":[
				{"a":1},
				{"a":2},
				{"a":3}
			]
		}
	}
	print(gmo.extract_data(test,"data"))
	'''
	#-------------------
	#status test
	#status = gmo.status()
	#print(status)
	
	#assets test
	#res = gmo.assets()
	#pprint(res)

	#-------------------
	#get_assets test
	#res = gmo.get_assets("JPY","BTC","btc")
	#print(res)
	
	#-------------------
	#margin test
	#res = gmo.margin()
	#print(res)

	#-------------------
	#get_orders test
	#res = gmo.get_orders("123,456")
	#print(res)

	#-------------------
	#active_orders test
	#res = gmo.active_orders("BTC")
	#print(res)

	#-------------------
	#execution test
	#res = gmo.executions(orderid="123",exec_id="456")
	#print(res)
	
	#position tet
	#res = gmo.positions("BTC_JPY")
	#print(res)
	
	#close order test
	#ret = gmo.close_order("BTC_JPY","BUY","MARKET",1,"0.1")
	#print(ret)
	#-------------------
	#ticker test
	#res = gmo.ticker("BTC,ETC") #this won't work..
	#print(res)
	#res = gmo.ticker("BTC_JPY")
	#print(res)

	#-------------------
	#order test
	#orderid = gmo.order("BTC","BUY","MARKET","0.01")
	#print(orderid)
	
	#-------------------
	#market test
	#orderid = gmo.market("BTC","BUY",size=0.02)
	#print(orderid)

	#limit test
	#orderid = gmo.limit("BTC_JPY","SELL","5500000","0.01")
	#print(orderid)

	#stop test
	#orderid = gmo.limit("BTC_JPY","SELL","5500000","0.01")
	#print(orderid)

	#order test
	#robj = gmo.cancel(5)
	#print(robj)

	#latest_executions test
	#r = gmo.latest_executions("BTC_JPY")
	#pprint(r)
	'''kline test	
	res = gmo.kline("BTC",'5min','20210920')
	jdata = {"openTime":[],"close":[]}
	for d in res:
		ot = int(d["openTime"])/1000
		cp = int(d["close"])
		dobj = datetime.datetime.utcfromtimestamp(ot)
		jst = dobj + datetime.timedelta(hours=9)
		jst = jst.strftime('%Y-%m-%d %H:%M:%S')
		jdata["openTime"].append(jst)
		jdata["close"].append(cp)

	pprint(jdata)	
	'''

	'''ticker test
	while True:
		b = gmo.ticker("BTC")["data"][0]["last"]
		bj = gmo.ticker("BTC_JPY")["data"][0]["last"]
		print(b,bj)
		time.sleep(5)
	'''