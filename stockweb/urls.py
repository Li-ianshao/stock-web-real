from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('accounts/', include('accounts.urls')),  # 登入功能專用路由
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
]
