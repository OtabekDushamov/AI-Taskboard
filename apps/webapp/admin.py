from django.contrib import admin
from .models import BotUser

@admin.register(BotUser)
class BotUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'telegram_id', 'first_name', 'last_name', 'username', 'language_code', 'register_date', 'last_login')
    list_filter = ('language_code', 'register_date', 'last_login')
    search_fields = ('user__username', 'user__email', 'first_name', 'last_name', 'username', 'telegram_id')
    readonly_fields = ('register_date', 'last_login')
    ordering = ('-register_date',)
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'telegram_id')
        }),
        ('Profile Information', {
            'fields': ('profile_image', 'first_name', 'last_name', 'username', 'language_code')
        }),
        ('Timestamps', {
            'fields': ('register_date', 'last_login'),
            'classes': ('collapse',)
        }),
    )
