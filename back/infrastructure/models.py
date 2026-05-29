from django.db import models


class TrafficLight(models.Model):
    # 위치
    sido = models.CharField(max_length=20)        # 시도명
    sigungu = models.CharField(max_length=20)     # 시군구명
    road_nm = models.CharField(max_length=100, blank=True)   # 도로명
    lat = models.FloatField()                     # 위도
    lng = models.FloatField()                     # 경도

    # 신호 정보
    sgn_asp_ordr = models.CharField(max_length=50, blank=True)  # 신호 순서
    sgn_asp_time = models.CharField(max_length=50, blank=True)  # 신호 시간

    # 교통약자 핵심 필드
    has_audio = models.BooleanField(default=False)   # 음향신호기 여부
    has_remndr = models.BooleanField(default=False)  # 잔여시간표시기 여부
    is_operating = models.BooleanField(default=True) # 운영 여부

    # 관리 정보
    manage_no = models.CharField(max_length=50, blank=True)
    ref_date = models.CharField(max_length=20, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['lat', 'lng']),
            models.Index(fields=['sido', 'sigungu']),
            models.Index(fields=['has_audio']),
        ]

    def get_pedestrian_green_time(self):
        """보행 녹색신호 시간(초) 파싱"""
        try:
            times = self.sgn_asp_time.split('+')
            return int(times[0])
        except Exception:
            return None

    def __str__(self):
        return f'{self.sido} {self.sigungu} ({self.lat}, {self.lng})'


class Facility(models.Model):
    # 시설 유형
    FACILITY_TYPE_CHOICES = [
        ('ramp', '경사로'),
        ('elevator', '엘리베이터'),
        ('braille', '점자블록'),
        ('toilet', '장애인 화장실'),
        ('parking', '장애인 주차구역'),
        ('other', '기타'),
    ]

    name = models.CharField(max_length=100)
    facility_type = models.CharField(
        max_length=20,
        choices=FACILITY_TYPE_CHOICES
    )
    sido = models.CharField(max_length=20, blank=True)
    sigungu = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    is_available = models.BooleanField(default=True)
    ref_date = models.CharField(max_length=20, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['lat', 'lng']),
            models.Index(fields=['facility_type']),
            models.Index(fields=['sido', 'sigungu']),
        ]

    def __str__(self):
        return f'{self.name} ({self.facility_type})'


class Elevator(models.Model):
    building_nm = models.CharField(max_length=100)  # 건물명
    sido = models.CharField(max_length=20, blank=True)
    sigungu = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    elevator_type = models.CharField(max_length=50, blank=True)  # 승강기 종류
    is_operating = models.BooleanField(default=True)
    install_place = models.CharField(max_length=100, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['lat', 'lng']),
            models.Index(fields=['sido', 'sigungu']),
        ]

    def __str__(self):
        return f'{self.building_nm} {self.install_place}'


class SupportCenter(models.Model):
    name = models.CharField(max_length=100)       # 센터명
    sido = models.CharField(max_length=20, blank=True)
    sigungu = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    is_operating = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=['lat', 'lng']),
            models.Index(fields=['sido', 'sigungu']),
        ]

    def __str__(self):
        return self.name