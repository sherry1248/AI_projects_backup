from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()

urlpatterns = [
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('login/', views.loginPage, name='login'),
    path('chatpage/', views.chatPage, name='chatpage'),
    path('profile/', views.profilePage, name='profile'),
    path('logout/', views.logoutPage, name='logout'),
    path('linkpage/', views.linkPage, name='linkpage'),
    path('check_email/', views.check_email, name='check_email'),
]
