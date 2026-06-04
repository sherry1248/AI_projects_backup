import urllib.request
import json
import re
from konlpy.tag import Okt
from collections import Counter
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
import pandas as pd

def get_news():
    client_id = 'GMwZU19WAmS2hF8RDzOl'
    client_secret = '8FTrKpo7_6'

    keyword = input('뉴스 검색어를 입력해주세요')
    encText = urllib.parse.quote(keyword)
    tlist = []
    llist = []
    dlist = []

    for pagenum in range(1, 1000, 100):
        try:
            url = "https://openapi.naver.com/v1/search/news?query=" + encText +"&display=100&sort=sim&start="+str(pagenum)
            request  = urllib.request.Request(url)
            request.add_header("X-Naver-Client-Id",client_id)
            request.add_header("X-Naver-Client-Secret",client_secret)
            response = urllib.request.urlopen(request)
            rescode = response.getcode()
            if(rescode == 200):
                response_body = response.read()
                jtemp = response_body.decode('utf-8')
                jdata = json.loads(jtemp)
                jdata['items']

                for temp in jdata['items']:
                    hangul = re.compile('[^ ㄱ-ㅎ|가-힣]+')
                    tdata = temp['title']
                    ldata = temp['link']
                    ddata = hangul.sub(r'', temp['description'])

                    tlist.append(tdata)
                    llist.append(ldata)
                    dlist.append(ddata)
            else:
                print('Error Code'+ rescode)
        except:
            print('Error')
    result = []
    for temp in range(len(tlist)):
        temp1 = []
        temp1.append(tlist[temp])
        temp1.append(llist[temp])
        temp1.append(dlist[temp])

        result.append(temp1)
    f = open('{0} - 네이버API 뉴스검색.csv'.format(keyword), 'w', encoding='utf-8')
    f.write('제목'+'링크'+','+'내용'+'\n')
    for temp in result:
        f.write(temp[0]+','+temp[1]+','+temp[2]+'\n')
    f.close()
    return result

def clean_str(s):
    hangul = re.compile('[^ㄱ-ㅎ|가-힣]+')
    s = hangul.sub(r' ', s)

    cp = re.compile("["
                     u"\U00010000-\U0010FFFF"
                     "]+", flags=re.UNICODE)
    s = cp.sub(r' ',s)
    
    return s.strip()


def get_text(data):
    result_text = ""
    for temp in data:
        result_text = result_text + ' '+ temp[2]
    return result_text


def Wordcloud(data, savename, maskname=''):
    noun_text = ''
    for word in data:
        noun_text = noun_text + ' '+ word
    if maskname == '':
        wc = WordCloud(font_path='"C:\\Windows\\Fonts\\malgun.ttf"' , background_color='white', max_font_size=60, colormap='Blues').generate(noun_text)
    else:
        maskimg = np.array(Image.open(maskname))
        wc = WordCloud(font_path='C:\\Windows\\Fonts\\malgun.ttf' , background_color='white', mask=maskimg, max_font_size=60, colormap='Blues').generate(noun_text)

        plt.figure(figsize=(20, 10))
        plt.imshow(wc)
        plt.tight_layout(pad=0)
        plt.axis('off')
        plt.show()
        wc.to_file('C:\\sqlite\\mysql\\code\\AI\\Mid_project\\data\\' +savename+'.png')


bdata = get_news()
rtext = get_text(bdata)

# n = pd.read_csv('C:\\sqlite\\mysql\\code\\AI\\Mid_project\\data\\neg_pol_word.txt', sep = "\n")
with open('C:\\sqlite\\mysql\\code\\AI\\Mid_project\\data\\neg_pol_word.txt', 'r',encoding='UTF8') as f:
    n = f.readlines()
nag = []
# for i in n['0']:
#     nag.append(i)
for i in range(len(n)):
    nag.append(i)

# p = pd.read_csv('C:\\sqlite\\mysql\\code\\AI\\Mid_project\\data\\pos_pol_word.txt', sep = "\n")
with open('C:\\sqlite\\mysql\\code\\AI\\Mid_project\\data\\pos_pol_word.txt', 'r',encoding='UTF8') as f:
    p = f.readlines()
pos = []
# for i in p['0']:
#     pos.append(i)
for i in range(len(p)):
    pos.append(i)

stopwords = ['보호','스쿨존','구역','노인','어린이','등','교통','곳','지정','안전','사업','일','시설','위해','및','년','장애인','위','경로당','설치','주변',
            '교통사고','보행자','보행','환경','도로','시','유치원','이번','중','조례','복지','차량','올해','애인','개','개소','억','관내',
            '의원','전국','발생','추가','이','물','월','원','확대','내','현재','광주','리','지역','최근','대전','것','지난해','초등학교','관','인구',
            '존','완료','대한','투입','공단','기자','대해','지난','마을','로','수','총','시행','조성','추진','공원','경찰정','경찰','충남',
            '회','또','군','신규','계획','안','광주시','시스템','생활','활동','중구','어르신','윤','실버','서울시회관','경우','통행','기준','어린이집',
            '진행','구','경기도','만','윤','복지관','아산시','대책','기관','인근','행사','점검','부과','지원','대폭','도시','억원','횡단보도','전통','도',
            '서울시','시장','회관','운영','가운데','민주당','공사','제조','요양원','개정','이상','규칙','고','지자체','앞','억만원','운전',
            '자동차','릴레이','광양시','주차장','린지','인천','위원회','사진','행정안전부','도로교통법','확보','우산','정착','캠페인','무인','주민',
            '보험','울타리','문화','전남','청장','를','우선','체결','확산','주민','무인','경찰청','초록','현대차','충북','국비','통해','합동대선',
            '사고','교체','내용','경기','최','한국','대표','나눔','건','계층','폐지','자녀','봉사','자치','달','스프링','시작',
            '국토교통부','제공','건','대구','손해','본부장','어린이재단','판','숲','서울특별시','협약','국민']

for i in stopwords:
    pos.append(i)

def get_tags(text, ntags = 50):
    spliter = Okt()
    nouns = spliter.nouns(text)
    count = Counter(nouns)
    words = dict(count.most_common(ntags))

    for i in pos:
        if i in words:
            del words[i]

    return words

rtags = get_tags(rtext, ntags=400)
text = ' '.join(rtags.keys())
import PIL
icon = PIL.Image.open('C:\\sqlite\\mysql\\code\\AI\\Mid_project\\data\\196136962-걷는-아이들의-실루엣-그림.jpg').convert( "RGBA" )

img = PIL.Image.new('RGBA', icon.size, (255, 255, 255))
img.paste(icon, icon)
img = np.array(img)
wc = WordCloud(random_state=123, font_path='malgun', width=400, height=400, background_color='white', mask=img ,colormap = 'inferno')
img_wordcloud = wc.generate_from_frequencies(rtags)
plt.figure(figsize=(10, 10))
plt.axis('off')
plt.imshow(img_wordcloud)
plt.savefig('C:\sqlite\mysql\code\AI\Mid_project\data\\save.png')
