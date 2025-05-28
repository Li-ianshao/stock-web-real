from django.http import HttpResponse
from django.contrib.auth.decorators import login_required 

@login_required
def home(request):
    return HttpResponse("🎉 登入成功！這是股票平台首頁")
