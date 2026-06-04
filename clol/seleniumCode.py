from selenium import webdriver as wd
import time
import pandas as pd
from bs4 import BeautifulSoup

period = 1

while period < 2:
    try:    
        driver = wd.Chrome() # 경로
        driver.maximize_window() # 크기 최대
        url = 'https://www.melon.com/chart/index.htm'
        driver.get(url)

        # 차트파인더 클릭
        driver.find_element('xpath', '//*[@id="gnb_menu"]/ul[1]/li[1]/div/div/button/span').click()

        # 차트선택
        driver.find_element('xpath', '//*[@id="d_chart_search"]/div/h4[2]/a').click()
        time.sleep(2)

        # 차트선택 - 연대선택2022년대
        driver.find_element('xpath', '//*[@id="d_chart_search"]/div/div/div[1]/div[1]/ul/li[1]/span/label').click()
        time.sleep(2)

        # 차트선택 - 연대선택2022년대 - 연도선택2023년
        driver.find_element('xpath', '//*[@id="d_chart_search"]/div/div/div[2]/div[1]/ul/li[1]/span/label').click()
        time.sleep(2)

        # 차트선택 - 연대선택2022년대 - 연도선택2023년 - 월간선택10월
        driver.find_element('xpath', '//*[@id="d_chart_search"]/div/div/div[3]/div[1]/ul/li[10]/span/label').click()
        time.sleep(2)

        # 차트선택 - 연대선택2022년대 - 연도선택2023년 - 월간선택10월
        driver.find_element('xpath', '//*[@id="d_chart_search"]/div/div/div[5]/div[1]/ul/li[3]/span/label').click()
        time.sleep(2)

        # 검색 클릭
        driver.find_element('xpath', '//*[@id="d_srch_form"]/div[2]/button/span/span').click()
        time.sleep(2)

        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')

        title_list = [title.find('a').get_text() for title in soup.find_all('div',attrs={'class':'ellipsis rank01'})] # 노래제목 랭킹
            

        singer_list = [singer.find('a').get_text() for singer in soup.find_all('span',attrs={'class':'checkEllipsis'})] # 가수 이름 랭킹
            

        rank = [title.find('a').get_text() for title in soup.find_all('div',attrs={'class':'ellipsis rank01'})] # 랭킹
        rank_list = []
        for i in range(len(rank)): # 가수 이름 랭킹
            rank_list.append(i+1)

        result_df = pd.DataFrame()
        df = pd.DataFrame({'순위':rank_list, '노래 제목':title_list,'가수이름':singer_list})
        result_df = pd.concat([result_df, df], ignore_index=True)
        period += 2
        
    except:
        # print(period)

        break
    driver.quit()
    print(result_df.to_string(index=False))
    result_df.to_csv('C:\\sqlite\\mysql\\code\\AI\\clol\\멜론차트.csv',encoding='ANSI',index=False)

