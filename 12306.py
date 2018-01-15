#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'LiFeiFei'

import requests
from setting import dict_setting
from damatuWeb import dmt
import time,re
import urllib.parse
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import asyncio

headers = {
	'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.108 Safari/537.36',
}
cookieTk = None;
leftTicket = None
key_check_isChange = None
train_location = None

def mail(msg,to_addr):
	msg = MIMEText(msg,'plain','utf-8')
	#12306账号
	from_addr = ''
	#密码
	password = ''
	#to_addr = '791173719@qq.com'
	smtp_server = 'smtp.qiye.163.com'
	server = smtplib.SMTP(smtp_server,25)
	server.set_debuglevel(1)
	server.login(from_addr, password)
	server.sendmail(from_addr, [to_addr], msg.as_string())
	server.quit()

class Tickter(object):

	def __init__(self,form,to,date):
		self.sessionId = None
		self.session = requests.Session()
		self.newDict = {}
		self.cityDict = {}
		for i in dict_setting.split('@'):
			if i:
				current = i.split('|')
				self.newDict[current[1]] = current[2]
				self.cityDict[current[2]] = current[1]
		try:
			self.form = self.newDict[form]
			self.to = self.newDict[to]
		except:
			raise KeyError('城市输入不正确')
		self.date = date

	def verifyCaptcha(self):
		count = 0
		while True:
			count+=1
			print('第%s次获取验证码...' % count)
			url = 'https://kyfw.12306.cn/passport/captcha/captcha-image?login_site=E&module=login&rand=sjrand&0.4711307417583588';
			r = self.session.get(url,headers=headers)
			with open('code.png','wb') as f:
				f.write(r.content)
			print('第%s次识别验证码...' % count)
			answer = dmt.decode('code.png',310)
			if isinstance(answer,int):
				print('打码兔请求失败,状态码:',answer)
				break
			answer = answer.replace('|',',').split(',')
			answer = ','.join([v if k % 2 == 0 else str(int(v)-30) for k,v in zip(range(len(answer)),answer)])
			print(answer)

			verify_url = 'https://kyfw.12306.cn/passport/captcha/captcha-check'
			data = {
				"answer" : answer,
				"login_site":"E",
				"rand":"sjrand"
			}
			try:
				res = self.session.post(verify_url,data=data,headers=headers)
				res = res.json()
			except Exception as e:
				print(e)
				time.sleep(3)
			else:
				print(res)
				if res['result_code'] == '4':
					print('识别成功')
					self._login()
					break
				else:
					time.sleep(3)
					print('识别失败',res)

	def _login(self):
		url = 'https://kyfw.12306.cn/passport/web/login'
		data = {
			"username":USERNAME,
			"password":PASSWORD,
			'appid':"otn"
		}

		print('开始登录...')
		res = None
		while True:
			try:
				r = self.session.post(url,data=data,headers=headers)
				res = r.json()
			except:
				r.encoding = 'utf-8'
				if not res:
					print('网络请求失败,正在重新登录...')
					time.sleep(2)
					continue
				else:
					print(res)
				exit()
			else:
				if res['result_code'] == 0:
					print('登录成功',res)
					while True:
						try:
							response = self.session.post('https://kyfw.12306.cn/otn/login/userLogin',data={"_json_att":""},headers=headers)
							response = self.session.post('https://kyfw.12306.cn/passport/web/auth/uamtk',data={"appid":"otn"},headers=headers)
							tk = response.json()['newapptk']
						except Exception as e:
							print(e)
							continue
							time.sleep(2)
						else:
							break
					res = self.session.post('https://kyfw.12306.cn/otn/uamauthclient',data={"tk":tk},headers=headers)
					#获取乘车人
					r = self.session.get('https://kyfw.12306.cn/otn/passengers/init',params={'_json_att':''})
					BusRider = eval(re.findall(r'passengers=(.*?);',r.text)[0])
					#第二页乘车人
					try:
						resu = self.session.post('https://kyfw.12306.cn/otn/passengers/query',data={'pageIndex':'2','pageSize':'10'})
						resu = resu.json()
					except:
						pass
					else:
						#合并乘车人
						BusRider = BusRider + resu['data']['datas']
					
					tickter_crew_list = []
					oldPassengerStr = []
					for i in BusRider:
						if i['passenger_name'] in BusRiders:
							if not tickter_crew_list:
								tickter_crew_list.extend(['3','0','1',i['passenger_name'],
									i['passenger_id_type_code']
									,i['passenger_id_no']
									,i['mobile_no']])
								oldPassengerStr.extend([i['passenger_name'],i['passenger_id_type_code']
									,i['passenger_id_no']])
							else:
								tickter_crew_list.extend(['N_3','0','1',i['passenger_name'],
									i['passenger_id_type_code']
									,i['passenger_id_no']
									,i['mobile_no']])
								oldPassengerStr.extend(['1_'+i['passenger_name'],
									i['passenger_id_type_code']
									,i['passenger_id_no']])

					tickter_crew_list.append('N')
					oldPassengerStr.append('1_')
					self.passengerTicketStr = ','.join(tickter_crew_list)
					self.oldPassengerStr = ','.join(oldPassengerStr)
					print(res.text)
					print(self.passengerTicketStr)
					print(self.oldPassengerStr)
					break
				else:
					print(res['result_message'])

	@asyncio.coroutine
	def order(self,*arg,**kw):
		print('下单开始...')
		while True:
			try:
				res = self.session.post('https://kyfw.12306.cn/otn/leftTicket/submitOrderRequest',data=arg[4],headers=headers,timeout=5)
				r = res.json()
			except requests.exceptions.Timeout:
				print('下单超时')
				continue
			except:
				print('订单发起失败',r.text)
				return
			else:
				print(r)
				break
		if r['status']:
			#下单页面获取乘车人信息
			token = self._repeat_submit_token()
			data = {
				"cancel_flag":"2",
				"bed_level_order_num":"000000000000000000000000000000",
				"passengerTicketStr":self.passengerTicketStr,
				"oldPassengerStr":self.oldPassengerStr,
				"tour_flag":"dc",
				"randCode":"",
				"whatsSelect":"1",
				"_json_att":"",
				"REPEAT_SUBMIT_TOKEN":token
			}
			r = self.session.post('https://kyfw.12306.cn/otn/confirmPassenger/checkOrderInfo',data=data,headers=headers)
			res = r.json()
			print(res)
			if res['data']['submitStatus']:
				t = time.strptime(self.date,'%Y-%m-%d')
				t = time.strftime('%a %b %d %Y 00:00:00 GMT+0800 (CST)',t)
				data = {
					"train_date":t,
					"train_no":arg[0],
					"stationTrainCode":arg[1],
					"seatType":"3",
					"fromStationTelecode":arg[2],
					"toStationTelecode":arg[3],
					"purpose_codes":"00",
					"train_location":train_location,
					"_json_att":"",
					"leftTicket":leftTicket[0],
					"REPEAT_SUBMIT_TOKEN":token
				}
				r = self.session.post('https://kyfw.12306.cn/otn/confirmPassenger/getQueueCount',data=data,headers=headers)
				r = r.json()
				print(r)
				#time.sleep()
				if r['status'] and int(r['data']['ticket']) > 1:
					#可以下单
					data = {
						'passengerTicketStr':self.passengerTicketStr,
						'oldPassengerStr' : self.oldPassengerStr,
						'randCode':'',
						'purpose_codes':'00',
						'key_check_isChange':key_check_isChange[0],
						'leftTicketStr':leftTicket[0],
						'train_location':train_location,
						'choose_seats':'',
						'seatDetailType':'000',
						'whatsSelect':'1',
						'roomType':'00',
						'dwAll':'N',
						'_json_att':'',
						'REPEAT_SUBMIT_TOKEN':token
					}
					print(data)
					r = self.session.post('https://kyfw.12306.cn/otn/confirmPassenger/confirmSingleForQueue',data=data,headers=headers)
					
					import random
					rand = random.randint(1000000000000,1599999999999)
					data = {
						'random':rand,
						'tourFlag':'dc',
						'_json_att':'',
						'REPEAT_SUBMIT_TOKEN':token
					}
					r = self.session.get('https://kyfw.12306.cn/otn/confirmPassenger/queryOrderWaitTime',params=data,headers=headers)
					print(r.json())
					
					rand = random.randint(1000000000000,1599999999999)
					data = {
						'random':rand,
						'tourFlag':'dc',
						'_json_att':'',
						'REPEAT_SUBMIT_TOKEN':token
					}
					r = self.session.get('https://kyfw.12306.cn/otn/confirmPassenger/queryOrderWaitTime',params=data,headers=headers)
					re = r.json()
					orderId = None
					print(re)
					if re['status'] and re['data']['queryOrderWaitTimeStatus']:
						orderId = re['data']['orderId']
						data = {
							'orderSequence_no':orderId,
							'_json_att':'',
							'REPEAT_SUBMIT_TOKEN':token
						}
						r = self.session.post('https://kyfw.12306.cn/otn/confirmPassenger/resultOrderForDcQueue',data=data,headers=headers)
						try:
							res = r.json()
						except:
							print('订单生成失败')
							return
						else:
							print(res)
							if res['status'] and res['data']['submitStatus']:
								print('订单生成成功',res)
								mail('抢票成功,请尽快登陆12306进行支付',)
								return 'ok'
					else:
						print(re['data']['msg'])
						
		else:
			if r['messages'][0].startswith('您还有未处理的订单'):
				return 'ok'
			print(r['messages'][0])
		
	def _repeat_submit_token(self):
		global leftTicket,key_check_isChange,train_location
		ress = self.session.post('https://kyfw.12306.cn/otn/confirmPassenger/initDc',data={"_json_att":""},headers=headers)
		token = re.findall(r"globalRepeatSubmitToken = '(.*?)'",ress.text)
		leftTicket = re.findall(r"'leftTicketStr':'(.*?)'",ress.text)
		key_check_isChange = re.findall(r"'key_check_isChange':'(.*?)'",ress.text)
		train_location = re.findall(r"ticketInfoForPassengerForm=(.*)",ress.text)[0]
		train_location = re.findall(r"'train_location':'(.*?)'",train_location)[0]
		print(train_location)
		if token:
			return token[0]

	@asyncio.coroutine
	def query(self,task):
		import string
		print('当前协程%s查询车次中...' % task)
		queryCount = 1
		flag = False
		result = None;
		while True:
			#for i in string.ascii_uppercase:
			url = 'https://kyfw.12306.cn/otn/leftTicket/queryZ?leftTicketDTO.train_date=%s&leftTicketDTO.from_station=%s&leftTicketDTO.to_station=%s&purpose_codes=ADULT' % (self.date,self.form,self.to)
			try:
				r = self.session.get(url,headers=headers,timeout=3)
				res = r.json()
			except requests.exceptions.Timeout:
				print('请求车次超时,重新请求')
				continue
			except:
				pass
			else:
				if isinstance(res,dict) and res['status']:
					print(url)
					result = res['data']['result']
					#break
			if result:
				for i in result:
					ll = i.split('|')
					#if (ll[23] != '' and ll[23] != '无') or (ll[28] != '' and ll[28] != '无'):
					
					if ll[28] != '' and ll[28] != '无' and ll[28] != '*':
						TrainStr = '|%4s|' % ll[3].center(12)
						starting = self.cityDict[ll[4]]
						ending = self.cityDict[ll[5]]
						startingPoint = '%4s|' % starting.center(12-len(starting))
						endingPoint = '%4s|' % ending.center(12-len(ending))
						departure_time = '%4s|' % ll[8].center(12)
						arrival_time = '%4s|' % ll[9].center(12)
						duration = '%4s|' % ll[10].center(12)
						if ll[23] == '有' or ll[23] == '无':
							softSleeper = '%4s|' % ll[23].center(12-len(ll[23]))
						else:
							softSleeper = '%4s|' % ll[23].center(12)
						if ll[28] == '有' or ll[28] == '无':
							hardSleeper = '%4s|' % ll[28].center(12-len(ll[28]))
						else:
							hardSleeper = '%4s|' % ll[28].center(12)
						print(TrainStr,startingPoint,endingPoint,departure_time,arrival_time,
							  duration,hardSleeper,softSleeper,sep='')
						while True:
							try:
								r = self.session.post('https://kyfw.12306.cn/otn/login/checkUser',data={'_json_att':''},headers=headers)
								rr = r.json()
							except:
								print(rr.text)
							else:
								if not rr['data']['flag']:
									#登陆失效重现登录
									print('登录失效,重新登录中')
									self.verifyCaptcha()
									break
								else:
									break
						#下单操作
						data = {
							"secretStr":urllib.parse.unquote(ll[0]),
							"train_date":self.date,
							"back_train_date":"2018-01-12",
							"tour_flag":"dc",
							"purpose_codes":"ADULT",
							"query_from_station_name":self.cityDict[self.form],
							"query_to_station_name":self.cityDict[self.to],
							"undefined":""
						}
						try:
							print('当前下单车次:%s' % ll[3])
							response = yield from self.order(ll[2],ll[3],ll[4],ll[5],data)
							yield from asyncio.sleep(3)
						except:
							print('下单失败')
						else:
							if response == 'ok':
								print('订单创建成功')
								mail('订单创建成功','791173719@qq.com')
								flag = True
							else:
								print('订单创建失败')
					else:
						pass
				print('暂无车次重新请求中...')
				queryCount += 1	
				print('第%s个协程第%s次请求' % (task,queryCount))
				yield from asyncio.sleep(1)
			if flag:
				break

"""
默认选择的硬卧
"""
				
BusRiders = ['孙清林'] #乘车人 
FromStation = '北京'
ToStation = '郑州'	
DATE = '2018-02-10' #乘车日期
USERNAME = '' #12306登录帐号
PASSWORD = '' #12306密码
t = Tickter(FromStation,ToStation,DATE)
t.verifyCaptcha()
print('|','------------|' * 8,sep='')
print('|%4s|%4s|%4s|%4s|%4s|%4s|%4s|%4s|' 
	% ('车次'.center(10),'起点'.center(10),'终点'.center(10),
		'发车时间'.center(8),'到站时间'.center(8),'历时'.center(10),
		'硬卧'.center(10),'软卧'.center(10)))
print('|','------------|' * 8,sep='')

loop = asyncio.get_event_loop()
tasks = [asyncio.ensure_future(t.query(1)),asyncio.ensure_future(t.query(2)),asyncio.ensure_future(t.query(3))]
loop.run_until_complete(asyncio.wait(tasks))
loop.close()