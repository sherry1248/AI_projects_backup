import pandas as pd

from selenium import webdriver # 브라우저 자동화
import chromedriver_autoinstaller # 크롬자동설치
from selenium.webdriver.common.by import By

import time # 시간 지연
# 워닝 무시
import warnings
warnings.filterwarnings('ignore')

query_txt = input('1. 크롤링할 키워드 : ')# '구로디지털단지 맛집'

chrome_path = chromedriver_autoinstaller.install()
driver = webdriver.Chrome(chrome_path)
driver.get('https://www.naver.com/')
time.sleep(1)

element = driver.find_element('id','query') # naver 검색창 html id=query
element.send_keys(query_txt) # 검색할 키워드
element.submit() # 검색어 제출
time.sleep(1)

driver.find_element(By.LINK_TEXT, "VIEW").click() # VIEW클릭
driver.find_element(By.LINK_TEXT, '옵션').click()
time.sleep(3)

item_li = driver.find_element(By.XPATH,'//*[@id="snb"]/div[2]/ul/li[3]/div/div[1]/a[6]').click()  

# 스크롤을 밑으로 내려주는 스크립트
def scroll_down(driver):
    driver.execute_script("window.scrollTo(0,999999999);")
    time.sleep(1)

# 스크롤
n = 3
i = 0
while i < n:
    scroll_down(driver)
    i = i+1

by = By.CLASS_NAME
value = "title_link._cross_trigger"
value_t = "title_area"
elements = driver.find_elements(by, value)
elements_t = driver.find_elements(by, value_t)


# 블로그 url 수집
import time


url_list = []
title_list = []

for article in elements:
    url = article.get_attribute('href')
    url_list.append(url)
time.sleep(1)

for article in elements_t:
    title = article.text
    title_list.append(title)


df = pd.DataFrame({'url':url_list, 'title':title_list})
# df = pd.DataFrame({'title':title_list})

print(df)
driver.close()
df.to_excel('C:\\sqlite\\mysql\\code\\AI\\clol\\food.xlsx')