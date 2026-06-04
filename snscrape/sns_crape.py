import pandas as pd
import snscrape.modules.twitter as sntwitter
import itertools
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import re

from wordcloud import WordCloud
import matplotlib.pyplot as plt
#검색단어
search_word = '책'
#검색기간
start_day = '2023-10-01'
end_day = '2023-10-31'

search_query = search_word + 'since:' + start_day + 'until' + end_day
# 지정한 기간에서 검색하고 싶은 단어를 포함한 tweet를 획득
scraped_tweets = sntwitter.TwitterSearchScraper(search_query).get_items()
# 처음부터 1000개의 tweets를 취득
sliced_scraper_tweets = itertools.islice(scraped_tweets, 1000)

df = pd.DataFrame(sliced_scraper_tweets)
df = df[df['content'].str.contains('책|도서|소설|자기계발')]

#트윗에서 불용어들을 삭제해주는 함수
def CleanText(readData, Num=True, Eng=True):
    text = re.sub('RT @[\w_]+:', '', readData)
    text = re.sub('@[\w_]+', '', text)
    text = re.sub(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", ' ',text)
    text = re.sub(r'[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{2,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)', ' ',text)
    text = re.sub(r'#', ' ', text)
    text = re.sub('[&]+[a-z]+', ' ',text)
    text = re.sub(r'[^0-9a-zA-Zㄱ-ㅎ가-힣]', ' ', text)
    text = re.sub(r'(출처.*)', ' ', text)
    text = text.replace('\n', ' ')
    
    if Num is True:
        text = re.sub(r'\d+', ' ', text)
    if Eng is True:
        text = re.sub('[a-zA-z]', ' ', text)
    text = ' '.join(text.split())
    return text

cleaned_tweets_all = []

for tweet in df.content:
    cleaned_tweet = []
    cleaned_tweet_string = CleanText(tweet, Num=True, Eng=False)
    tweet_tokens = word_tokenize(cleaned_tweet_string)
    for token in tweet_tokens:
        cleaned_tweet.append(token)
    cleaned_tweets_all.append(cleaned_tweet)

all_words = []
for cleaned_tweet in cleaned_tweets_all:
    for word in cleaned_tweet:
        all_words.append(word)
all_words_str = ' '.join(all_words)

def generate_wordcloud(text):
    wordcloud = WordCloud(
        width=800, height=400,
        relative_scaling=1.0,
        font_path='malgun',
        stopwords={'to','of'}
    ).generate(text)

fig = plt.figure(1, figsize=(8, 4))
plt.axis('off')
plt.imshow(WordCloud)
plt.axis('off')
plt.show()