from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class BotUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='bot_user')
    telegram_id = models.BigIntegerField()
    profile_image = models.URLField(max_length=500, blank=True, null=True)
    username = models.CharField(max_length=100, blank=True, null=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    language_code = models.CharField(max_length=10, blank=True, null=True)
    register_date = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Bot User'
        verbose_name_plural = 'Bot Users'
    
    def __str__(self):
        return f"{self.first_name} {self.last_name or ''} (@{self.username or 'no_username'})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name or ''}".strip()
    
    def get_telegram_username(self):
        return f"@{self.username}" if self.username else None
