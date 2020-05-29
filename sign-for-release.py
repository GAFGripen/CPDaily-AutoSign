import base64
import json
import re
import time
import random

import requests
import urllib3
from pyDes import *
from requests.utils import dict_from_cookiejar

urllib3.disable_warnings()

session = requests.session()
session.headers = {
	'Content-Type': 'application/json',
	'User-Agent': 'Mozilla/5.0 (Linux; Android 8.1.0; 16th Build/OPM1.171019.026; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/65.0.3325.110 Mobile Safari/537.36 yiban/8.1.7 cpdaily/8.1.7 wisedu/8.1.7',
}

# 此处配置你的账号
USERCODE = '学号'
# 此处配置你的密码
USERPWD = '密码'
# 此处填写最新的App版本
APP_VERSION = '8.1.12'

# 签到模式 custom：自定义位置；auto: 自动获取第一个签到范围内的位置
MOD = 'custom'

# 此处填写你的签到地址信息
POSITION = '自行填写'

# 当签到模式为custom时有效
# 此处填写地址经纬度
LON = 精度，小数点后六位+random.randint(0,100)/10000000
LAT = 纬度，小数点后六位+random.randint(0,100)/10000000
# 如果准备签到的位置在签到范围外，则在此处填写原因
REASON = ''


# des加密
def encrypt(s, key='ST83=@XV'):
	key = key
	iv = b"\x01\x02\x03\x04\x05\x06\x07\x08"
	k = des(key, CBC, iv, pad=None, padmode=PAD_PKCS5)
	EncryptStr = k.encrypt(s)
	return base64.b64encode(EncryptStr).decode()  # 转base64编码返回


def createCpdailyInfo(lon, lat, open_id):
	"""
	headers中的CpdailyInfo参数
	:param lon: 定位经度
	:param lat: 定位纬度
	:param open_id: 学生学号
	:return: CpdailyInfo
	"""
	s = r'{"systemName":"android","systemVersion":"8.1.0","model":"16th",' \
	    r'"deviceId":"ffd1df5b-e69a-4938-9624-38d575039f83","appVersion":"8.1.11","lon":' + str(
		lon) + ',"lat":' + str(lat) + ',"userId":"' + open_id + '"}'
	info = encrypt(s)
	return info



def getSignInfoInOneDay():
	"""
	:url: https://cqmu.cpdaily.com/wec-counselor-sign-apps/stu/sign/getStuSignInfosInOneDay
	:method: POST
	:data: {}
	"""
	url = 'https://cqmu.cpdaily.com/wec-counselor-sign-apps/stu/sign/getStuSignInfosInOneDay'
	data = json.dumps({})
	res = session.post(url=url, data=data, allow_redirects=False, verify=False)
	if res.status_code == 302:
		print('login expired')
		return None
	datas = res.json().get('datas', {})
	signedTasks = datas.get('signedTasks')
	unSignedTasks = datas.get('unSignedTasks')

	tasks = {'signedTasks': signedTasks, 'unSignedTasks': unSignedTasks}
	return tasks


def getSignDetail(us_task):
	"""
	签到任务详情
	url: https://cqmu.cpdaily.com/wec-counselor-sign-apps/stu/sign/detailSignInstance
	method: POST
	:param us_task: 未签到的任务
	data: {
		signInstanceWid: signInstanceWid,
		signWid: signWid
		}
	data-type: json
	"""
	url = 'https://cqmu.cpdaily.com/wec-counselor-sign-apps/stu/sign/detailSignInstance'
	data = json.dumps({
		'signInstanceWid': us_task.get('signInstanceWid'),
		'signWid': us_task.get('signWid'),
	})
	res = session.post(url=url, data=data, verify=False)
	unSignedTaskDetail = res.json().get('datas')
	return unSignedTaskDetail




def submitSign(wid, lon, lat, reason, photo_url, position):
	"""
	提交签到
	url: 'https://cqmu.cpdaily.com/wec-counselor-sign-apps/stu/sign/submitSign'
	method: POST
	:param wid: 任务id string
	:param lon: 经度 float
	:param lat: 纬度 float
	:param reason: 补充原因 string
	:param photo_url: 签到图片url string
	:param position: 位置信息 string
	:return:
	"""
	url = 'https://cqmu.cpdaily.com/wec-counselor-sign-apps/stu/sign/submitSign'
	data = json.dumps({
		'signInstanceWid': wid,
		'longitude': lon,
		'latitude': lat,
		'isMalposition': 0,
		'abnormalReason': reason,
		'signPhotoUrl': "",
		'position': position,
		'isNeedExtra': 1,
		"extraFieldItems": [
			{
				"extraFieldItemValue": "体温正常",
				"extraFieldItemWid": 122010
			}
		]
	})
	cpdaily_extension = createCpdailyInfo(lon=lon, lat=lat, open_id=USERCODE)
	session.headers['Content-Type'] = 'application/json;charset=UTF-8'
	res = session.post(url=url, headers={'Cpdaily-Extension': cpdaily_extension}, data=data, verify=False)
	message = res.json().get('message')
	return message


def startSign():
	"""
	签到流程控制
	:return:
	"""
	tasks = getSignInfoInOneDay()
	text = ''
	if tasks is None:
		if reLogin():
			print('==>relogin success')
			text += '==>重新登陆成功'
			tasks = getSignInfoInOneDay()
		else:
			text += '==>账号或密码错误、或者需要验证码'
			return text
	unSignedTasks = tasks.get('unSignedTasks')
	if unSignedTasks:
		print('now with{}sign undergoing'.format(len(unSignedTasks)))
		print('start sign')
		for unSignedTask in unSignedTasks:
			unSignedDetailTask = getSignDetail(us_task=unSignedTask)
			# 判断是否在签到时间
			currentTime = unSignedDetailTask.get('currentTime')
			taskDate = unSignedDetailTask.get('rateSignDate')[0:10]
			taskStartTime = unSignedDetailTask.get('rateTaskBeginTime')
			taskEndTime = unSignedDetailTask.get('rateTaskEndTime')
			dt1 = '{} {}'.format(taskDate, taskStartTime)
			dt2 = '{} {}'.format(taskDate, taskEndTime)
			timeArray1 = time.strptime(dt1, '%Y-%m-%d %H:%M')
			timeArray2 = time.strptime(dt2, '%Y-%m-%d %H:%M')
			timeArray3 = time.strptime(currentTime, '%Y-%m-%d %H:%M:%S')
			timestamp1 = time.mktime(timeArray1)
			timestamp2 = time.mktime(timeArray2)
			timestamp3 = time.mktime(timeArray3)
			if timestamp3 <= timestamp1 or timestamp3 >= timestamp2:
				print("not in sign time")
				text += '==>未到签到时间'
				break
			filename = uploadPic()
			photo_url = getPhotoUrl(filename=filename)
			# 地址信息
			reason = ''
			if MOD == 'custom':
				longitude = LON
				latitude = LAT
				reason = REASON
			else:
				place = unSignedDetailTask.get('signPlaceSelected')[0]
				longitude = place.get('longitude')
				latitude = place.get('latitude')
			text += "==>" + submitSign(wid=unSignedDetailTask.get('signInstanceWid'), lon=longitude, lat=latitude, reason=reason, photo_url=photo_url, position=POSITION)
			session.get('https://sc.ftqq.com/**********你server酱的SCKEY**********.send?text=今日校园签到&desp=' + text)
		return text
	else:
		print("no sign task for now")
		return '==>暂时没有签到任务'


def reLogin():
	"""
	重新登陆
	:return: 成功True/失败False
	"""
	url = 'https://cqmu.cpdaily.com/iap/doLogin'  # POST
	lt_url = 'https://cqmu.cpdaily.com/iap/security/lt'  # POST
	doLogin_headers = {
		'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
		'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36',
		'Referer': 'https://cqmu.cpdaily.com/iap/login/pc.html'
	}
	redirect_headers = {
		'Referer': 'https://cqmu.cpdaily.com/wec-amp-portal/login.html',
	    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36'
	}
	lt_data = {
		'lt': ''
	}
	lt = session.post(url=lt_url, data=lt_data, verify=False).json().get('result').get('_lt')
	data = {
		# 此处配置你的账号
		'username': USERCODE,
		# 此处配置你的密码
		'password': USERPWD,
		'mobile': '',
		'dllt': '',
		'lt': lt,
		'captcha': '',
		'rememberMe': 'false'
	}
	# 更新部分cookie
	session.post(url=url, headers=doLogin_headers, data=data, verify=False)
	# login
	resp = session.get(url='https://cqmu.cpdaily.com/wec-amp-portal/login',
	                   headers=redirect_headers, allow_redirects=False, verify=False)
	location = resp.headers['Location']
	# service
	resp = session.get(url=location,
	                   headers=redirect_headers, allow_redirects=False, verify=False)
	location = resp.headers['Location']
	# ticket
	resp = session.get(url=location,
	                   headers=redirect_headers, allow_redirects=False, verify=False)
	dict_of_cookies = dict_from_cookiejar(session.cookies)
	c_key = dict_of_cookies.get('MOD_AUTH_CAS')
	if c_key:
		return True
	return False


if __name__ == '__main__':
	time.sleep(random.randint(0, 600))
	text = startSign()
	session.get(
		'https://sc.ftqq.com/**********你server酱的SCKEY**********.send?text=今日校园签到&desp=' + text)
