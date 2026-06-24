from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    
    USER_TYPE_CHOICES = [
        ('disabled', '장애인'),
        ('elderly', '노인'),
        ('wheelchair', '휠체어'),
        ('pregnant', '임산부'),
        ('normal', '일반'),
    ]
    
    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default='normal'
    )
    
    # 별명
    nickname = models.CharField(max_length=50, blank=True)
    
    # 실명
    name = models.CharField(max_length=50, blank=True)
    
    # 전화번호
    phone = models.CharField(max_length=20, blank=True)
    
    # 약관 동의
    terms_agreed = models.BooleanField(default=False)
    privacy_agreed = models.BooleanField(default=False)
    
    # 보행 속도 (m/s)
    walk_speed = models.FloatField(default=1.0)
    
    # 프로필 이미지
    profile_image = models.ImageField(
        upload_to='profiles/',
        blank=True,
        null=True
    )
    
    FONT_SIZE_CHOICES = [
        ('small', '작게'),
        ('medium', '보통'),
        ('large', '크게'),
        ('xlarge', '더 크게'),
    ]
    font_size = models.CharField(
        max_length=10,
        choices=FONT_SIZE_CHOICES,
        default='medium'
    )
    
    voice_type = models.CharField(max_length=20, default='female')
    voice_volume = models.IntegerField(default=70)
    
    sos_number = models.CharField(max_length=20, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.username