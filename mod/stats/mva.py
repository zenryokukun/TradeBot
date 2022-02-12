class MVA:
	def __init__(self,interval=7,max_length=7):
		self.prices = []
		self.mva = []
		self.interval = interval
		self.max_length = max_length

	def update(self,current):
		
		self.prices.insert(0,current)
		itv = self.interval
		ml = self.max_length

		if len(self.prices) >= itv:
			mva = sum(self.prices[:itv]) / itv
			self.mva.insert(0,mva)

		if len(self.prices) > ml:
			self.prices.pop()

		if len(self.mva) > ml:
			self.mva.pop()
