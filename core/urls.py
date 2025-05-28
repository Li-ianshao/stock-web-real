from django.urls import path
from . import views

urlpatterns = [
    path('', views.tab_dividend_view, name='tab_dividend'),
]
