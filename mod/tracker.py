#足時間調整用
#DEPENDENCIES: [mod] time
import time
import datetime
#update sleepにintervalパラメータ追加。

'''時間tracker
基準時刻＋足（秒）から次時刻を計算し、datetime.datetime.now()との差分sleepさせる機能
sleep時、基準時刻　=　基準時刻＋足（秒）と更新し、次フレームに回せるようにする。
現在時刻が次回時刻を超えている場合、現在時刻から基準時刻と次回時刻を計算しなして対応する
基準時刻:self.base 足（秒）:self.secs
1時間を超える待ち時間には非対応。
'''
class Tracker:
	def __init__(self,secs=60):
		if secs > 3600:
			raise Exception("secs must be shorter than 1h")
		self.secs = secs
		self.base = datetime.datetime.fromtimestamp(self._get_base_sec())
		self.skip = datetime.timedelta(seconds=secs)

	#next_timeに達するまで待つ
	def wait(self):
		next_time = self.base + self.skip
		now = datetime.datetime.now()
		#現在時刻がnext_timeを超えている場合、現在時刻からnext_timeを計算しなおす。
		if now > next_time:
			_current = datetime.datetime.fromtimestamp(self._get_base_sec())
			next_time = _current + self.skip
		
		#次回時間と現在時刻の差分だけ待つ
		waitsec = (next_time - now).total_seconds()
		time.sleep(waitsec)
		#基準時間をnext_timeで更新
		self.base = next_time

	#基準時間を取得する。例：secs=60のとき、20:01:24なら20:01をutc timestampで返す
	# ret -> utc timestamp
	def _get_base_sec(self):
		now = time.time()
		rem = now % self.secs
		return now - rem
			
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
	t = Tracker(5)
	
	t.wait()


