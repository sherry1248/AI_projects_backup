# from glob import glob
# from json import dump, dumps
from .forms import ChatbotUserForm
from django.shortcuts import render, redirect
from django.http import HttpResponse, request
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import UserScore, ChatbotUser
from datetime import datetime
import pytz
from requests.exceptions import ConnectionError
import requests
import sys
from django.utils import timezone
# from .models import Sentiment
from django.http import JsonResponse
from django.contrib import messages
sys.path.append('C:\\sqlite\\mysql\\code\\AI\\FINAL_project\\dialogLM\\dialogLM\\service')
from Demonstration.model.load_electra import DialogElectra 
from Demonstration.model.load_kogpt2 import AnswerGenerator
import json
from .models import ChatbotUser, UserScore
import traceback 
from django.contrib.auth.models import User


CHATS = []  # list of tuples (user_query,bot_response)
# External or default URL goes here
CHATBOT_URL = 'http://localhost:5000/'
# CHATBOT_URL = 'http://localhost:5200/'
SENTIMENT_URL = 'http://localhost:5500/'
# SENTIMENT_URL = 'http://localhost:5300/'

# New Analysis data
DataObj=None

# helper methods
def checkUrl(url):
    try:
        request = requests.get(url)
    except ConnectionError:
        return False
    else:
        return True


def getChatbotResponse(userQuery):
    global CHATBOT_URL
    response = requests.post(url=CHATBOT_URL, params={
                             'userQuery': str(userQuery)})
    responseJson = response.json()
    res = (responseJson['user_query'],
           responseJson['chatbot_response'],
           datetime.now(pytz.timezone('Asia/Seoul')
                        ).strftime("%d-%m-%Y %H:%M:%S"),
           )
    return res


def getSentenceListFromChats(chats):
    sentenceList = []
    for conv in chats:
        sentenceList.append(conv[0])
    return sentenceList


def getSentimentalResponse(sentenceList):
    global SENTIMENT_URL
    response = requests.post(url=SENTIMENT_URL, params={
                             'sentList': str(sentenceList)})
    responseJson = response.json()
    return responseJson


def setChatbotUrl(url):
    global CHATBOT_URL
    CHATBOT_URL = url


def setSentimentUrl(url):
    global SENTIMENT_URL
    SENTIMENT_URL = url


def getChatbotUrl():
    global CHATBOT_URL
    return CHATBOT_URL


def getSentimentUrl():
    global SENTIMENT_URL
    return SENTIMENT_URL


def index(request):
    return render(request, "index.html")


def about(request):
    return render(request, "about.html")


def loginPage(request):
    if request.method == 'POST':
        # 회원가입 처리
        if 'register' in request.POST:
            form1 = UserCreationForm(request.POST)
            form2 = ChatbotUserForm(request.POST)
            if form1.is_valid() and form2.is_valid():
                print('작동완료')
                user = form1.save()
                user.set_password(user.password)
                user.save()
                login(request, user)  # 사용자 로그인
                obj = form2.save(commit=False)
                obj.user = user
                obj.save()
                messages.success(request, '계정이 성공적으로 생성되었습니다.')
                return redirect('profile')
            else:
                messages.error(request, '양식에 오류가 있습니다.')
                messages.error(request, form1.errors)  # UserCreationForm 오류 메시지
                messages.error(request, form2.errors)
                return redirect('login')
        # 로그인 처리
        elif 'login' in request.POST:
            form3 = AuthenticationForm(data=request.POST)
            if form3.is_valid():
                username = form3.cleaned_data.get('username')
                password = form3.cleaned_data.get('password')
                user = authenticate(username=username, password=password)
                if user is not None:
                    login(request, user)
                    return redirect('about')
                else:
                    messages.error(request, '아이디 또는 비밀번호가 올바르지 않습니다.')
                    return redirect('login')
            else:
                messages.error(request, '로그인 양식에 오류가 있습니다.')
                return redirect('login')
        else:
            messages.error(request, '알 수 없는 POST 요청입니다.')
            return redirect('login')
    else:
        # GET 요청 처리 - 폼 전송
        form1 = UserCreationForm()
        form2 = ChatbotUserForm()
        form3 = AuthenticationForm()
        context = {'form1': form1, 'form2': form2, 'form3': form3}
        return render(request, "login.html", context)


from transformers import pipeline
def save_score(user, score, positive_count, negative_count):
    chatbotUserObj = ChatbotUser.objects.get(user=user)
    scoreObj = UserScore(owner=chatbotUserObj,
                         score=score,
                         posCount=positive_count,
                         negCount=negative_count)
    scoreObj.save()

def get_most_frequent_sentiment(sentiment_counts):
    max_val = max(sentiment_counts.values())
    max_keys = [k for k, v in sentiment_counts.items() if v == max_val]
    return max_keys[0] if max_keys else None  # 첫 번째 키를 반환하거나, 키가 없다면 None을 반환



kogpt2_model = AnswerGenerator()


nlp_general = pipeline('sentiment-analysis', model='daekeun-ml/koelectra-small-v3-nsmc')
nlp_detailed = pipeline("sentiment-analysis", model="nlp04/korean_sentiment_analysis_kcelectra")
@login_required(login_url='login')
def chatPage(request):
    chat = ''
    most_recent_sentiment = "데이터 없음"

    if request.method == 'GET':
        request.session['sentiment_scores'] = {}
        request.session.modified = True

    try:
        current = ChatbotUser.objects.get(user=request.user)
    except ChatbotUser.DoesNotExist:
        default_age = 0
        default_email = "default@email.com"
        current = ChatbotUser.objects.create(user=request.user, age=default_age, email=default_email)

    if current is not None:
        bar_sentiments = ['기쁨(행복한)', '즐거운(신나는)', '고마운', '일상적인', '사랑하는', '생각이 많은', '설레는(기대하는)', '슬픔(우울한)', '짜증남', '걱정스러운(불안한)', '힘듦(지침)']
        user_scores = UserScore.objects.filter(owner=current)
        if user_scores:
            user_score = user_scores.first()
        else:
            user_score = UserScore.objects.create(owner=current, sentiment_scores={sentiment: 0 for sentiment in bar_sentiments})

    if request.method == 'POST':
        if 'send' in request.POST:
            userQuery = request.POST.get('userquery').strip()
            if userQuery:
                dialog_model = DialogElectra(
                                model_path="C:\\sqlite\\mysql\\code\\AI\\FINAL_project\\dialogLM\\dialogLM\\service\\Demonstration\\data\\koelectra-wellness-text-classification-25.pth",
                                category_path="C:\\sqlite\\mysql\\code\\AI\\FINAL_project\\dialogLM\\dialogLM\\service\\Demonstration\\data\\wellness_dialog_category.txt",
                                answer_path="C:\\sqlite\\mysql\\code\\AI\\FINAL_project\\dialogLM\\dialogLM\\service\\Demonstration\\data\\wellness_dialog_answer.txt")
                chat = dialog_model.get_response(userQuery)
                send_value = request.POST.get('send')

                if send_value == 'somevalue':
                    result_general = nlp_general(userQuery)[0]

                    result_detailed = nlp_detailed(userQuery)[0]
                    try:
                        label = result_detailed['label']  # 이건 감정 확인 버튼에 들어가는 라벨
                        score = result_detailed['score']

                        # 'emotion_category'는 프로필 페이지에 들어가는 감정 카테고리
                        result_label = int(result_general['label'])
                        emotion_category = '긍정적(기쁨, 즐거움)' if result_label == 1 else '부정적(슬픔, 짜증남)'

                        print(f'emotion_category:{emotion_category}')
                        
                        user_score.emotion_category = emotion_category
                        # user_score.sentiment_scores[emotion_category] = user_score.sentiment_scores.get(emotion_category, 0) + 1
                        user_score.sentiment_scores[label] = user_score.sentiment_scores.get(label, 0) + 1

                        today = timezone.now().date().isoformat()  # 현재 날짜를 문자열로 변환
                        if today not in user_score.daily_sentiment_scores:
                            user_score.daily_sentiment_scores[today] = {sentiment: 0 for sentiment in bar_sentiments}
                        user_score.daily_sentiment_scores[today][emotion_category] = user_score.daily_sentiment_scores[today].get(emotion_category, 0) + 1
                        # user_score.daily_sentiment_scores[today][label] = user_score.daily_sentiment_scores[today].get(label, 0) + 1

                        user_score.save()
                        if 'sentiment_scores' not in request.session:
                            request.session['sentiment_scores'] = {}

                        # request.session['sentiment_scores'] = {}
                        sentiment_scores = request.session['sentiment_scores']
                        sentiment_scores[label] = sentiment_scores.get(label, 0) + 1
                        request.session['sentiment_scores'] = sentiment_scores
                        # print(f'Sentiment scores{sentiment_scores}')

                        if sentiment_scores:
                            most_recent_sentiment = max(sentiment_scores, key=sentiment_scores.get)
                            print(f'most_recent_sentiment{most_recent_sentiment}')
                            
                        else:
                            most_recent_sentiment = "데이터 없음"

                        request.session['most_recent_sentiment'] = most_recent_sentiment
                        request.session['sentiment_scores'] = sentiment_scores
                        request.session.modified = True

                    except Exception as e:
                        print(f"감정 분석 중 에러 발생: {e}")
                        traceback.print_exc()

                    if 'userQueries' not in request.session:
                        request.session['userQueries'] = []
                    request.session['userQueries'].append(userQuery)
                    request.session.modified = True

                    now = timezone.now().astimezone(pytz.timezone('Asia/Seoul')).strftime("%d-%m-%Y %H:%M:%S")

                    if request.is_ajax():
                        response_data = {
                            'chat': chat,
                            'sentiments': sentiment_scores,
                            'most_recent_sentiment': most_recent_sentiment,
                            'now': now,
                            'label': label
                        }
                        return JsonResponse(response_data)

    context = {
    'chat': chat,
    'sentiments': request.session.get('sentiment_scores', {}),
    'most_recent_sentiment': request.session.get('most_recent_sentiment', most_recent_sentiment),
    'now': timezone.now().astimezone(pytz.timezone('Asia/Seoul')).strftime("%d-%m-%Y %H:%M:%S")
    }
    return render(request, "chatpage.html", context=context)






nlp = pipeline('sentiment-analysis', model='daekeun-ml/koelectra-small-v3-nsmc')


@login_required(login_url='login')
def profilePage(request):
    try:
        # 현재 사용자 정보 가져오기
        chatbot_user = ChatbotUser.objects.get(user=request.user)
    except ChatbotUser.DoesNotExist:
        default_age = 0
        default_email = "default@email.com"
        chatbot_user = ChatbotUser.objects.create(user=request.user, age=default_age, email=default_email)

    line_sentiments = ['긍정적(기쁨, 즐거움)', '부정적(슬픔, 짜증남)']
    bar_sentiments = ['기쁨(행복한)', '즐거운(신나는)', '고마운', '일상적인', '사랑하는', '생각이 많은', '설레는(기대하는)', '슬픔(우울한)', '짜증남', '걱정스러운(불안한)', '힘듦(지침)']

    # 사용자의 모든 감정 점수를 조회합니다.
    all_scores = UserScore.objects.filter(owner=chatbot_user)

    # 감정 점수를 날짜별로 정렬합니다.
    line_scores = {}
    for score in all_scores:
        date = score.date.strftime('%Y-%m-%d')
        if date not in line_scores:
            line_scores[date] = {sentiment: score.daily_sentiment_scores.get(date, {}).get(sentiment, 0) for sentiment in line_sentiments}
            print(f'line_scores on {date}: {line_scores[date]}')
        else:
            print(f'{date}는 이미 처리 되었습니다.')



    # 가장 최신의 감정 점수를 가져옵니다.
    latest_score = all_scores.order_by('-date').first()
    # bar_scores = {sentiment: latest_score.sentiment_scores.get(sentiment, 0) for sentiment in bar_sentiments}
    # print(f'bar_scores: {bar_scores}')
    today = timezone.now().date()

    today_score = all_scores.filter(date=today).first()

    bar_scores = {}
    if today_score is not None:
        bar_scores = {sentiment: today_score.sentiment_scores.get(sentiment, 0) for sentiment in bar_sentiments if today_score.sentiment_scores.get(sentiment, 0) != 0}
    print(f'bar_scores: {bar_scores}')        


    context = {
        'scores': latest_score,
        'age': chatbot_user.age,
        'email': chatbot_user.email,
        'line_scores': json.dumps(line_scores, ensure_ascii=False),  # line_scores를 JSON 형식으로 변환하여 컨텍스트에 추가합니다.
        'bar_scores': json.dumps(bar_scores, ensure_ascii=False),
        'most_frequent_sentiment': request.session.get('most_recent_sentiment', "데이터 없음"),
    }

    return render(request, "profile.html", context=context)





def logoutPage(request):
    logout(request)
    global CHATS
    global DataObj
    DataObj=None
    CHATS = []
    return render(request, 'logout.html')


@login_required(login_url='login')
def linkPage(request):
    chatbot_url = getChatbotUrl()
    sentiment_url = getSentimentUrl()
    chatbotAPIStatus = False
    sentimentAPIStatus = False
    if(checkUrl(chatbot_url)):
        chatbotAPIStatus = True
    if(checkUrl(sentiment_url)):
        sentimentAPIStatus = True
    context = {'chatbotAPI': chatbotAPIStatus,
               'sentimentAPI': sentimentAPIStatus}
    if request.method == 'POST':
        newChatbotURL = request.POST.get('chatbotLink')
        newSentimentURL = request.POST.get('sentimentLink')
        print("새로운 Chatbot URL: ", newChatbotURL) 
        print("새로운 Sentiment URL: ", newSentimentURL) 
        if(newChatbotURL is not None and newChatbotURL != ''):
            setChatbotUrl(newChatbotURL)
        if(newSentimentURL is not None and newSentimentURL != ''):
            setSentimentUrl(newSentimentURL)
        return redirect('chatpage')
    return render(request, 'link.html', context=context)



def check_email(request):
    email = request.GET.get('email', None)
    data = {
        'is_taken': User.objects.filter(email__iexact=email).exists()
    }
    return JsonResponse(data)

