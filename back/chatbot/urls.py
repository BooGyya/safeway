from django.urls import path
from . import views

urlpatterns = [
    path('chat/', views.chat, name='chat'),
    path('filter/', views.filter_content, name='filter_content'),
]