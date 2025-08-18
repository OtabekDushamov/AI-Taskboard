from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from apps.webapp.models import BotUser


def home_view(request):
    """Home page view - redirects to profile if authenticated, otherwise to auth"""
    if request.user.is_authenticated:
        return redirect('main:profile')
    else:
        return redirect('webapp:auth')


@login_required
def profile_view(request):
    """Profile page view - requires authentication"""
    try:
        bot_user = request.user.bot_user
    except BotUser.DoesNotExist:
        # If no BotUser exists, redirect to auth
        return redirect('webapp:auth')
    
    # If it's an AJAX request, return JSON data
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
        user_data = {
            'id': bot_user.id,
            'telegram_id': bot_user.telegram_id,
            'first_name': bot_user.first_name,
            'last_name': bot_user.last_name,
            'username': bot_user.username,
            'language_code': bot_user.language_code,
            'profile_image': bot_user.profile_image,
            'register_date': bot_user.register_date.isoformat() if bot_user.register_date else None,
            'last_login': bot_user.last_login.isoformat() if bot_user.last_login else None,
            'email': bot_user.user.email,
        }
        return JsonResponse({'success': True, 'user': user_data})
    
    # Regular request - show profile page
    context = {
        'bot_user': bot_user,
        'user': request.user
    }
    return render(request, 'main/profile.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def users_list_view(request):
    """Users list view - requires superuser permissions"""
    # Get query parameters
    page = request.GET.get('page', 1)
    search = request.GET.get('search', '')
    name_filter = request.GET.get('name_filter', '')
    username_filter = request.GET.get('username_filter', '')
    language_filter = request.GET.get('language_filter', '')
    sort_field = request.GET.get('sort', 'first_name')
    sort_direction = request.GET.get('direction', 'asc')
    
    # Build queryset
    queryset = BotUser.objects.select_related('user').all()
    
    # Apply search filter
    if search:
        queryset = queryset.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(username__icontains=search) |
            Q(user__email__icontains=search) |
            Q(telegram_id__icontains=search)
        )
    
    # Apply specific filters
    if name_filter:
        queryset = queryset.filter(first_name__istartswith=name_filter)
    
    if username_filter:
        queryset = queryset.filter(username__istartswith=username_filter)
    
    if language_filter:
        queryset = queryset.filter(language_code=language_filter)
    
    # Apply sorting
    if sort_direction == 'desc':
        sort_field = f'-{sort_field}'
    queryset = queryset.order_by(sort_field)
    
    # Pagination
    paginator = Paginator(queryset, 20)  # 20 users per page
    try:
        users_page = paginator.page(page)
    except:
        users_page = paginator.page(1)
    
    # Prepare context
    context = {
        'users': users_page,
        'search': search,
        'name_filter': name_filter,
        'username_filter': username_filter,
        'language_filter': language_filter,
        'sort_field': sort_field.replace('-', ''),
        'sort_direction': sort_direction,
        'total_users': paginator.count,
        'total_pages': paginator.num_pages,
        'current_page': users_page.number,
        'has_previous': users_page.has_previous(),
        'has_next': users_page.has_next(),
        'previous_page_number': users_page.previous_page_number() if users_page.has_previous() else None,
        'next_page_number': users_page.next_page_number() if users_page.has_next() else None,
        'page_range': list(paginator.page_range),
    }
    
    return render(request, 'main/users.html', context)
