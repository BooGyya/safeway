from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/accounts/', include('accounts.urls')),
]

# 미디어 파일 (프로필 이미지)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)