
import pandas as pd
import matplotlib.pyplot as plt

# extrema API
# search:
#	param:[x:list,y:list,df:dataframe,ratio:float]
#	ret[(list,list)]
# show:
#	param:[times:list,prices:list,peaks;list,bottoms:list]
#	ret:[None]


_NOT_FOUND = -1
_RATIO = 0.025
_CNT = 0

def show(times,prices,peaks,bottoms,save=False):
	fig = plt.figure()
	ax = fig.add_subplot(111)

	#価格と時間
	ax.plot(times,prices)
	
	#山と時間
	ptime = peaks["dtime"]
	pprice = peaks["price"]

	#谷と時間
	btime = bottoms["dtime"]
	bprice = bottoms["price"]

	#test start
	#for val in pprice:
	#	ax.plot(times,[val for i in range(len(times))],color="grey")
	for val in bprice:
		ax.plot(times,[val for i in range(len(times))],color="purple")
	#test end


	ax.scatter(ptime,pprice,color="red")
	ax.scatter(btime,bprice,color="green")
	
	#x軸調整
	fig.autofmt_xdate()
	#グリッド表示
	plt.grid(True)
	if save:
		global _CNT
		_CNT += 1
		plt.savefig("extrema"+str(_CNT))
	else:
		plt.show()

def _testargs(x,y,df):
	msg = ''
	try:
		if df is None:
			if x is None:
				if y is None:
					msg="ArgumentError:pass x and y or df"
				else:
					msg="ArgumentError:pass both x and y"
				raise Exception(msg)
			else:
				if y is None:
					msg = "ArgumentError:pass both x and y"
					raise Exception(msg)
		else:
			if x is not None or y is not None:
				msg = "ArgumentError:do not pass x or y when passing df"
				raise Exception(msg)
	except Exception as e:
		print(e)

def _testargs_type(x,y,df):
	msg = ''
	try:
		if df is not None:
			if type(df) != pd.core.frame.DataFrame:
				msg = "ArgumentTypeError:df must be pandas DataFrame not " + str(type(df))
				raise Exception(msg)
		else:
			if type(x) != list:
				msg = "ArgumentTypeError: x must be list not " + str(type(x))
				raise Exception(msg)
			if type(y) != list:
				msg = "ArgumentTypeError: y must be list not " + str(type(y))
				raise Exception(msg)
	except Exception as e:
		print(e)

def _convert_args(x,y,df):
	if df is None:
		if type(x) == pd.core.series.Series:
			x = list(x)
		if type(y) == pd.core.series.Series:
			y = list(y)
	return x,y,df

def _fix_args(x,y,df):
	if df is not None:
		x = list(df.iloc[:,0])
		y = list(df.iloc[:,1])
	return x,y

def _testargs_len(x,y):
	try:
		if len(x) != len(y):
			msg = "ArgumentError:axis x and y must be same length"
			raise Exception(msg)
	except Exception as e:
		print(e)

def _check(x,y,df):
	_testargs(x,y,df)
	x,y,df = _convert_args(x,y,df)
	_testargs_type(x,y,df)
	x,y = _fix_args(x,y,df)
	_testargs_len(x,y)
	return x,y

def _is_extremus(extremus,current,ascend):
	ret = False
	if ascend:
		if current > extremus:
			ret = True
	else:
		if current < extremus:
			ret = True
	return ret

def _is_fixed(extremus,current,threshold,ascend):
	ret = False
	if ascend:
		if current < extremus - threshold:
			ret = True
	else:
		if current > extremus + threshold:
			ret = True
	return ret

def _update_extrema(x,y,index,peaks,bottoms,ascend):
	price = y[index]
	dtime = x[index]
	targ = peaks if ascend else bottoms
	targ["dtime"].append(dtime)
	targ["price"].append(price)

def _extrema(y,start,threshold,ascend):
	step = 0
	extremus = 0
	data = y[start:]

	for i,val in enumerate(data):
		if i==0:
		#初回は初期化のみ
			extremus = val
			step = i
		else:
			if _is_extremus(extremus,val,ascend):
				extremus = val
				step = i
			else:
				if _is_fixed(extremus,val,threshold,ascend):
					return step

	#not found
	return _NOT_FOUND

def search(x=None,y=None,df=None,ratio=_RATIO):
	x,y = _check(x,y,df)
	threshold = int(sum(y)/len(y) * ratio)
	index = 0
	ascend = True
	maxima = {"dtime":[],"price":[]}
	minima = {"dtime":[],"price":[]}
	
	while index < len(x):
		step = _extrema(y,index,threshold,ascend)
		if step != _NOT_FOUND:
			index += step
			_update_extrema(x,y,index,maxima,minima,ascend)
		else:
			break
		ascend = not ascend
	#show(x,y,maxima,minima)
	return maxima,minima
		


if __name__ == "__main__":
	file_data = pd.read_csv("out.csv")
	df = file_data.drop(axis=1,columns=['OpenPrice','HighPrice','LowPrice','Volume','QuoteVolume'])
	df["CloseTime"] = pd.to_datetime(df["CloseTime"],format='%Y-%m-%d %H:%M:%S')
	
	prices = list(df["ClosePrice"])
	times = list(df["CloseTime"])

	#maxima,minima = search(x=df["CloseTime"],y=df["ClosePrice"])
	#search(df=df)

	maxima,minima = search(times,prices,ratio=0.015)
	show(times,prices,maxima,minima,save=True)



