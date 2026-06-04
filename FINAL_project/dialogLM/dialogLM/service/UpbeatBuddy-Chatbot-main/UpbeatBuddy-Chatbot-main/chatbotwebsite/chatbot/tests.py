from django.contrib.auth.models import User

# 사용자 이메일 중에서 "example@example.com"과 정확하게 일치하는 사용자 찾기
user = User.objects.filter(email__iexact="klmas1248@gmail.com").first()

# 찾은 사용자 출력
print(user)
