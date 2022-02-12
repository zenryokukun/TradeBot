import math
from .mva import MVA

'''updates
20211114
 [std] prices = self.prices[:self.interval]
 pricesがself.intervalより長い場合でも計算が合うように修正
[__init__]
 interval,max_lengthと別々の値が設定出来るよう修正

'''

class Bollinger(MVA):
	def __init__(self,interval=20,max_length=None):
		max_length = max_length or interval
		super().__init__(interval=interval,max_length=max_length)
		#self.max_length = interval
		self.sigmas = []

	def update(self,price):
		super().update(price)
		#if len(self.prices) == self.max_length:
		if len(self.mva) > 0:	
			self.std()

	#standard deviation
	def std(self):
		prices = self.prices[:self.interval]
		mva = self.mva[0]
		diff_sum = 0
		for price in prices:
			squared_diff = (price - mva) ** 2
			diff_sum += squared_diff
		#分散
		variance = diff_sum/len(prices)
		#標準偏差
		deviation = math.sqrt(variance)

		self.sigmas.insert(0,deviation)
		if len(self.sigmas) > self.max_length:
			self.sigmas.pop()

	#normal distribution
	#val:[int]σ1～α3
	#pos:[int]何足目か
	def ndist(self,val,pos=0):
		ret = None
		#まだ１つもデータがたまっていなければ何もしない
		if val > len(self.mva):
			return ret

		if val >= 1 and val <=3:
			dev = self.sigmas[pos]
			mva = self.mva[pos]
			ret = {
				"pos":mva + dev * val,
				"neg":mva - dev * val
			}

		return ret
	
	#val:[int]σ1～α3
	#pos:[int]何足目か
	#under:[bool] True→ -nシグマ未満か　False→ +nシグマ超えか
	def is_over_ndist(self,val=2,pos=0,under=False):
		#配列の長さよりindex(pos)が大きい場合は戻る
		if len(self.prices) <= pos:
			return None
		#current price
		price = self.prices[pos]
		sig = self.ndist(val,pos)
		if sig:
			if under:
				ret = price <= sig["neg"]
			else:
				ret = price >= sig["pos"]
			return ret
		return None
	
	def standardize(self,pos=0):
		if len(self.prices) == 0 or \
				len(self.mva) == 0 or \
				len(self.sigmas) == 0:
			return None
		val = self.prices[pos]
		mva = self.mva[pos]
		dev = self.sigmas[pos]
		return (val-mva)/dev

	
if __name__ == "__main__":
	'''
	mva = MVA(interval = 7)

	p = [7,5,9,8,3,5,12,5,6]
	p.reverse()
	for v in p:
		mva.update(v)


	print(mva.mva)
	''' 
	bol  = Bollinger(6)
	vals = [1,2,3,4,5,6,80,92,64,72,45,59]
	for val in vals:
		bol.update(val)
		v = bol.standardize()
		print(f'std{v}')

	print(bol.std())
	print(bol.mva[0])
	print(bol.sigmas[0])
	print(bol.ndist(1,0))
	print(bol.ndist(2,0))
	print(bol.ndist(3,0))

	val = bol.standardize()	
	print(f'st:{val}')
