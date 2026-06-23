from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('delete/', views.delete_account, name='delete_account'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('sos/', views.send_sos, name='send_sos'),
    path('kakao/', views.kakao_login, name='kakao_login'),
    path('kakao/callback/', views.kakao_callback, name='kakao_callback'),
    path('mypage/', views.mypage, name='mypage'),
    path('users/<int:user_id>/', views.user_profile, name='user_profile'),
    path('admin/users/', views.admin_user_list, name='admin_user_list'),
    path('admin/users/<int:user_id>/', views.admin_user_status, name='admin_user_status'),
]