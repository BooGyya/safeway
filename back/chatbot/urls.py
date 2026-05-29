from django.urls import path
from . import views

urlpatterns = [
    path('chat/', views.chat, name='chat'),
    path('filter/', views.filter_content, name='filter_content'),
    path('admin/monitor/', views.admin_filter_monitor, name='admin_filter_monitor'),
]