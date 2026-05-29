from django.urls import path
from . import views

urlpatterns = [
    # 신호등
    path('traffic-lights/', views.nearby_traffic_lights, name='nearby_traffic_lights'),
    path('traffic-lights/audio/', views.audio_traffic_lights, name='audio_traffic_lights'),
    path('traffic-lights/realtime/', views.realtime_signal, name='realtime_signal'),

    # 장애인 편의시설
    path('facilities/', views.nearby_facilities, name='nearby_facilities'),

    # 교통약자 이동지원센터
    path('support-centers/', views.nearby_support_centers, name='nearby_support_centers'),

    # 서울 실시간 혼잡도
    path('congestion/', views.seoul_congestion, name='seoul_congestion'),
]