import json
import os
import random
from requests_oauthlib import OAuth1Session
from .story import get_story
#######################################
#[公開関数]
#tweet　のみ
#######################################

_TAGS = "#プログラミング初心者 #btc #bitcoin #自作EA"
BOT = {"NAME":"全力君FX","VER":"1.4"}
URL =  "https://api.twitter.com/1.1/statuses/update.json"
URL_IMAGE = "https://upload.twitter.com/1.1/media/upload.json"
KEY_FILE_NAME = 'keys.json'
MSG_FILE_NAME = 'msg.json'

#ret -> CK,CS,AT,AS
def _get_keys():
	here = os.path.dirname(__file__)
	path = os.path.join(here,KEY_FILE_NAME)
	with open(path,'r') as jf:
		_keys = json.load(jf)
	CK = _keys["API_KEY"]
	CS = _keys["API_SCRET"]
	AT = _keys["ACCESS_TOKEN"]
	AS = _keys["AT_SECRET"]
	return CK,CS,AT,AS


def _get_messages():
	ret = ''
	here = os.path.dirname(__file__)
	path = os.path.join(here,MSG_FILE_NAME)
	with open(path,mode="r",encoding="utf-8") as jf:
		data = json.load(jf)
		#messages = data["value1"]
		length = len(data)
		i = random.randrange(length)
		ret = data[i]
	return ret	

def _slice_tweet(msg):
	cnt = 0
	index = 0
	for ch in msg:
		if ch.isascii():
			cnt += 1
		else:
			cnt += 2
		
		if cnt > 280:
			return index
		index += 1
	return index

def _img_tweet(req,img_path):
	fullpath = os.path.join(os.path.dirname(__file__),img_path)
	param = {
		"media":open(fullpath,'rb'),
		"media_category":"tweet_image"
	}

	res = req.post(URL_IMAGE,files=param)
	if res.status_code == 200:
		res = res.json()
		media_id = res["media_id"]
		return media_id
	else:
		print(f"tweetImage api error:{res.status_code}")
		res = res.json()
		print(res)
		return None

#keys,values:[list]
#bot:{"NAME":str,"VER":str}
def tweet(*args,keys=None,values=None,bot=None):
	'''通常ツイート。画像ありも対応'''
	#param check
	if keys is None or values is None:
		return None
	#init var
	msg = ""
	media_id = None
	CK,CS,AT,AS = _get_keys()
	req = OAuth1Session(CK,CS,AT,AS)
	#body以外のメッセージ連携されたメッセージ
	for arg in args:
		msg += arg + "\n"
	#version
	if bot:
		msg += "[" + bot["NAME"] + "]" + bot["VER"] + "\n"
	#key value部分　keyを[]で囲う
	for k,v in zip(keys,values):
		msg += "[" + k + "]" + str(v) + "\n"

	#random message
	automsg = _get_messages()
	msg += automsg["msg"] + "\n"
	#adding tags..
	msg += _TAGS + "\n"
	#tweeting image first
	if automsg["img"] != "":
		media_id = _img_tweet(req,automsg["img"])
	#tweet text
	index = _slice_tweet(msg)
	msg = msg[:index]
	params = {"status":msg}

	if media_id:
		params["media_ids"] = media_id
		
	res = req.post(URL,params=params)

	if res.status_code != 200:
		print(f"tweetText api error:{res.status_code}")
		res = res.json()
		print(res)

def tweet2(*args,img=None,bot=None):
	'''画像ファイルをパラメータで受け取れる。成績ツイートで使ってる'''
	CK,CS,AT,AS = _get_keys()
	req = OAuth1Session(CK,CS,AT,AS)
	media_id = None
	param = {
		"media":open(img,'rb'),
		"media_category":"tweet_image"
	}

	res = req.post(URL_IMAGE,files=param)
	if res.status_code == 200:
		res = res.json()
		media_id = res["media_id"]
		#return media_id
	else:
		print(f"tweetImage api error:{res.status_code}")
		res = res.json()
		print(res)
		return None
	
	msg = ""
	if bot:
		msg += "[" + bot["NAME"] + "]" + bot["VER"] + "\n"
	for arg in args:
		msg += arg + "\n"
	msg += _TAGS + "\n"
	index = _slice_tweet(msg)
	msg = msg[:index]

	params = {"status":msg,"media_ids":media_id}

	res = req.post(URL,params=params)

	if res.status_code != 200:
		print(f"tweet2 api error:{res.status_code}")
		res = res.json()
		print(res)

def tweet_with_story(*args,keys=None,values=None,bot=None,img=None):
	'''物語ツイート用'''
	msg = ""
	media_id = None
	CK,CS,AT,AS = _get_keys()
	req = OAuth1Session(CK,CS,AT,AS)
	#body以外のメッセージ連携されたメッセージ
	for arg in args:
		msg += arg + "\n"
	#version
	if bot:
		msg += "[" + bot["NAME"] + "]" + bot["VER"] + "\n"
	#key value部分　keyを[]で囲う
	for k,v in zip(keys,values):
		msg += "[" + k + "]" + str(v) + "\n"
	
	msg += get_story() + "\n"
	msg += _TAGS +" #力3" +"\n"

	index = _slice_tweet(msg)
	msg = msg[:index]

	if img:
		media_id = _img_tweet(req,img)
	params = {"status":msg}
	if media_id:
		params["media_ids"] = media_id
	
	res = req.post(URL,params=params)

	if res.status_code != 200:
		print(f"tweet_with_story api error:{res.status_code}")
		res = res.json()
		print(res)

if __name__ == "__main__":
	test = ["全力","TEST"]
	im = "./report.png"
	tweet2(*test,img=im)