#足時間調整用
#DEPENDENCIES: [mod] time
import time
import datetime
#update sleepにintervalパラメータ追加。

class Atime:
	def __init__(self,interval=60,max_count=12):
		self.interval = interval
		self._start = 0
		self.count = 0
		self.max_count = max_count

	#開始時刻設定
	def start(self):
		self._start = time.time()
		#self.dtime = datetime.datetime.fromtimestamp(self._start)

	#規定時間-経過時間分待つ＆開始時刻リセット。
	def sleep(self,interval=None):
		end = time.time()
		delta = end - self._start 
		#待ち時間がマイナスになった場合、0になるよう工夫 time.sleepにマイナス渡すとエラーになるっぽい。
		interval = interval or self.interval
		wait_sec = max(interval - delta,0)
		time.sleep(wait_sec)
		self._update_count()
		#self._start = time.time()
		return delta
	
	def _update_count(self):
		self.count += 1
		if self.count >= self.max_count:
			self.count = 0
	

class DateChecker:
	#secs:60,300,900,3600,14400
	def __init__(self,secs):
		delta = datetime.timedelta(seconds=secs)
		now = datetime.datetime.now()
		if secs >= 14400:
			hr_sec = now.hour * 3600
			bef_hr = (hr_sec - (hr_sec % secs))/3600
			bef_obj = datetime.datetime(year=now.year,month=now.month,day=now.day,hour=int(bef_hr))
		else:
			min_sec = now.minute * 60
			bef_min = (min_sec - (min_sec % secs))/60
			bef_obj = datetime.datetime(year=now.year,month=now.month,day=now.day,hour=now.hour,minute=int(bef_min))
		self.next_time = bef_obj + delta
		self.delta = delta
	
	def check(self):
		ret = False
		now = datetime.datetime.now()
		if now >= self.next_time:
			self.next_time += self.delta
			ret = True
		return ret

		

if __name__ == "__main__":
	a = Atime(60)
	a.sleep2()

