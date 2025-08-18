from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.utils import timezone
from .models import BotUser
import json

def auth_view(request):
    """Authentication page view - handles Telegram user registration/login"""
    
    if request.method == 'POST':
        # Handle authentication request
        try:
            data = json.loads(request.body)
            telegram_user = data.get('telegram_user')
            
            if telegram_user:
                # Try to find existing BotUser
                try:
                    bot_user = BotUser.objects.get(telegram_id=telegram_user['id'])
                    # Update last login
                    bot_user.last_login = timezone.now()
                    bot_user.save()
                    
                    # Login the user
                    user = bot_user.user
                    login(request, user)
                    
                    return JsonResponse({'success': True, 'message': 'Login successful'})
                    
                except BotUser.DoesNotExist:
                    # Create new user and BotUser
                    user, bot_user = create_telegram_user(telegram_user)
                    
                    # Login the new user
                    login(request, user)
                    
                    return JsonResponse({'success': True, 'message': 'Registration successful'})
                    
        except Exception as e:
            print(f"Error processing authentication: {e}")
            return JsonResponse({'success': False, 'message': str(e)})
    
    # GET request - show auth page
    return render(request, 'webapp/auth.html')

def logout_view(request):
    """Logout view"""
    logout(request)
    return redirect('webapp:auth')

def create_telegram_user(telegram_data):
    """Create a new Django User and BotUser from Telegram data"""
    # Create Django User with unique username
    base_username = f"tg_{telegram_data['id']}"
    username = base_username
    counter = 1
    
    # Keep trying until we find a unique username
    while User.objects.filter(username=username).exists():
        username = f"{base_username}_{counter}"
        counter += 1
    
    email = f"{username}@telegram.local"
    
    user = User.objects.create_user(
        username=username,
        email=email,
        first_name=telegram_data.get('first_name', ''),
        last_name=telegram_data.get('last_name', ''),
        password=None  # No password for Telegram users
    )
    
    # Create BotUser
    bot_user = BotUser.objects.create(
        user=user,
        telegram_id=telegram_data['id'],
        profile_image=telegram_data.get('photo_url'),
        username=telegram_data.get('username'),
        first_name=telegram_data.get('first_name', ''),
        last_name=telegram_data.get('last_name'),
        language_code=telegram_data.get('language_code'),
        register_date=timezone.now(),
        last_login=timezone.now()
    )
    
    return user, bot_user
