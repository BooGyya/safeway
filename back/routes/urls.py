from django.urls import path
from . import views

urlpatterns = [
    # 경로 탐색
    path('search/', views.search_route, name='search_route'),

    # 주소 검색
    path('address/', views.search_address, name='search_address'),

    # 즐겨찾기
    path('favorites/', views.favorite_list, name='favorite_list'),
    path('favorites/<int:favorite_id>/', views.favorite_detail, name='favorite_detail'),

    # 히스토리
    path('history/', views.route_history, name='route_history'),

    # 실시간 보행신호 잔여시간 (좌표 기준 재조회)
    path('realtime-signal/', views.realtime_signal_for_point, name='realtime_signal_for_point'),
]