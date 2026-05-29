from django.urls import path
from . import views

urlpatterns = [
    # 게시글
    path('posts/', views.post_list, name='post_list'),
    path('posts/<int:post_id>/', views.post_detail, name='post_detail'),
    
    # 댓글
    path('posts/<int:post_id>/comments/', views.comment_create, name='comment_create'),
    path('posts/<int:post_id>/comments/<int:comment_id>/', views.comment_detail, name='comment_detail'),
    
    # 좋아요
    path('posts/<int:post_id>/like/', views.post_like, name='post_like'),
    
    # 팔로우
    path('users/<int:user_id>/follow/', views.follow_toggle, name='follow_toggle'),
    path('follow/', views.follow_list, name='follow_list'),

    # 관리자
    path('admin/posts/', views.admin_post_list, name='admin_post_list'),
    path('admin/posts/<int:post_id>/', views.admin_post_delete, name='admin_post_delete'),
    path('admin/posts/<int:post_id>/reliability/', views.admin_post_reliability, name='admin_post_reliability'),
    path('admin/ranking/', views.admin_reporter_ranking, name='admin_reporter_ranking'),
]