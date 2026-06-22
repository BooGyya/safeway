from django.db import models
from django.conf import settings


class Route(models.Model):
    # 사용자
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='routes'
    )

    # 출발지
    origin_name = models.CharField(max_length=255)
    origin_lat = models.FloatField()
    origin_lng = models.FloatField()

    # 목적지
    dest_name = models.CharField(max_length=255)
    dest_lat = models.FloatField()
    dest_lng = models.FloatField()

    # 경로 정보
    distance = models.FloatField(default=0)       # 거리 (m)
    duration = models.IntegerField(default=0)     # 소요시간 (초)
    safety_score = models.FloatField(default=0)   # 안전도 점수 (0~1)

    # 경로 데이터 (JSON)
    waypoints = models.JSONField(default=list)

    # 날씨 반영 여부
    weather_applied = models.BooleanField(default=False)

    # 이동 수단
    TRANSPORT_TYPE_CHOICES = [
        ('walk', '도보'),
        ('bus', '대중교통'),
        ('taxi', '택시'),
    ]
    transport_type = models.CharField(
        max_length=10,
        choices=TRANSPORT_TYPE_CHOICES,
        default='walk'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.origin_name} → {self.dest_name}'


class RouteFavorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favorites'
    )
    route = models.ForeignKey(
        Route,
        on_delete=models.CASCADE,
        related_name='favorites'
    )
    nickname = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'route']

    def __str__(self):
        return f'{self.user.username} - {self.route}'


class RouteHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='route_history'
    )
    route = models.ForeignKey(
        Route,
        on_delete=models.CASCADE,
        related_name='history'
    )
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-used_at']

    def __str__(self):
        return f'{self.user.username} - {self.route}'