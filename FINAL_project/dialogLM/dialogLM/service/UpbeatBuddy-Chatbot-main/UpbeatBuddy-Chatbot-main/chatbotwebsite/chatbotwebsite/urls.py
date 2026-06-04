"""chatbotwebsite URL Configuration

urlpatterns 목록은 URL을 뷰로 라우팅합니다. 자세한 내용은 다음 링크를 참조하세요
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
예시:
함수 기반 뷰
1. import 추가: from my_app import views
2. urlpatterns에 URL 추가: path('', views.home, name='home')
클래스 기반 뷰
1. import 추가: from other_app.views import Home
2. urlpatterns에 URL 추가: path('', Home.as_view(), name='home')
다른 URL 구성 포함
1. include() 함수를 import: from django.urls import include, path
2. urlpatterns에 URL 추가: path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
# from .. import chatbot

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('chatbot.urls')),
    path('accounts/', include('django.contrib.auth.urls')), 
    path('', include('chatbot.urls')),
]
