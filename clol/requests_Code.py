import requests, json, time
from bs4 import BeautifulSoup
from datetime import datetime

def get_code(company_code): 
    url = 'https://finance.naver.com/item/main.nhn?code='+company_code
    result = requests.get(url)
    bs_obj = BeautifulSoup(result.content, 'html.parser')
    return bs_obj, url

def get_name(company_code):
    bs_obj, url = get_code(company_code)
    name = bs_obj.select_one('#middle > div.h_company > div.wrap_company > h2 > a').text # html에서 해당 경로로 들어가 a 태크 추출
    return name, url

def get_price(company_code):
    bs_obj, url = get_code(company_code)
    no_today = bs_obj.find('p', {'class': 'no_today'}) # html 삼성전사 실시간 가격
    blind = no_today.find("span", {"class": "blind"}) # 고가등 현재가 추출
    now_price = blind.text
    return now_price, url

def get_chart(company_code):
    url = 'https://finance.naver.com/item/main.nhn?code='+company_code
    result = requests.get(url)
    bs_obj = BeautifulSoup(result.content, "html.parser")
    images = bs_obj.findAll('img', {"alt" : "이미지 차트"})
    if images:
        image_url = images[0]["src"]
    else:
        image_url = None
    
    return image_url

def get_mobile_url(company_code):
    url = "https://m.stock.naver.com/item/main.nhn#/stocks/"+company_code+"/total"
    return url
company_codes = ["005930"] # 모바일 사이트 주소
try_price = 60000 # 60000원 이하 설정
kakao_token = '개인 카카오 토큰' # 카카오 토큰


while True:
    now = datetime.now()
    
    for item in company_codes:
        now_price, url = get_price(item)
        name, url = get_name(item)
        image_url = get_chart(item)
        mobile_url = get_mobile_url(item)

        # if int(now_price.replace(',','')) <= try_price:
        k_url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
        headers = {
                "Authorization": "Bearer " + kakao_token 
                        }
        data = {
                "template_object" : json.dumps({
                    "object_type" : "text",
                    "text" : f'가격이'+try_price+'까지 떨어졌습니다', 
                    "link" : {
                    "web_url" : url,
                    "mobile_web_url" : mobile_url                         
                    }
                })
        }
            
        response = requests.post(k_url, headers=headers, data=data)
            
        print(str(now)[:-7])
        if response.json().get('result_code') == 0:
                print('메시지 전송 성공')
        else:
                print('Error. code : ' + str(response.json()))
            
        print("-------------------------------")
        
        time.sleep(10)