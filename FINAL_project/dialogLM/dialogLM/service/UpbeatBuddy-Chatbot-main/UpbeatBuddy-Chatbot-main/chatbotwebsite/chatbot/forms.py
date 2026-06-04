from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import ChatbotUser, UserScore

# 기존의 로그인 폼
class YourLoginForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'id': 'login_username'}),
            'password': forms.PasswordInput(attrs={'id': 'login_password'}),
        }

# 기존의 회원가입 폼
class YourSignUpForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        widgets = {
            'username': forms.TextInput(attrs={'id': 'signup_username'}),
            'password1': forms.PasswordInput(attrs={'id': 'signup_password1'}),
            'password2': forms.PasswordInput(attrs={'id': 'signup_password2'}),
        }
class ChatbotUserForm(forms.ModelForm):
    class Meta:
        model = ChatbotUser
        fields = ('email', 'age',)
        labels = {
            "email": "email",
            "age": "age",
        }


class UserScoreForm(forms.ModelForm):
    class Meta:
        model = UserScore
        fields = '__all__'
