from django.db import models
from django.conf import settings

class ChatHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_history'
    )
    message = models.TextField()        # 사용자 메시지
    response = models.TextField()       # AI 응답
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} - {self.created_at}'