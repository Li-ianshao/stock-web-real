from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect


urlpatterns = [
    path('', lambda request: redirect('stock_input_view')),
    path('accounts/', include('accounts.urls')),  # 登入功能專用路由
    path('admin/', admin.site.urls),
    path('core/', include('core.urls')),
]
