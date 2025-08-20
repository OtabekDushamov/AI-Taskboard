from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, Http404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
from django.contrib import messages
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
import json

from apps.webapp.models import BotUser
from .models import Project, Category, Task, DailyTask, DailyTaskCompletion


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


# =============================================================================
# DASHBOARD AND OVERVIEW VIEWS
# =============================================================================

@login_required
def dashboard_view(request):
    """Main dashboard with overview statistics and today's tasks"""
    try:
        bot_user = request.user.bot_user
    except BotUser.DoesNotExist:
        return redirect('webapp:auth')
    
    today = timezone.now().date()
    
    # Get user's projects
    user_projects = Project.objects.filter(
        Q(creator=bot_user) | Q(members=bot_user)
    ).distinct()
    
    # Get user's tasks
    user_tasks = Task.objects.filter(
        Q(creator=bot_user) | Q(assignees=bot_user)
    ).distinct()
    
    # Get today's daily tasks
    today_weekday = today.weekday()
    daily_tasks_today = DailyTask.objects.filter(
        Q(creator=bot_user) | Q(assignees=bot_user),
        scheduled_days__contains=[today_weekday],
        is_active=True
    ).distinct()
    
    # Check which daily tasks are completed today
    completed_today = DailyTaskCompletion.objects.filter(
        user=bot_user,
        date=today
    ).values_list('daily_task_id', flat=True)
    
    # Statistics
    stats = {
        'total_projects': user_projects.count(),
        'active_projects': user_projects.filter(status='active').count(),
        'total_tasks': user_tasks.count(),
        'pending_tasks': user_tasks.filter(status__in=['todo', 'in_progress']).count(),
        'completed_tasks': user_tasks.filter(status='completed').count(),
        'overdue_tasks': user_tasks.filter(
            deadline__lt=timezone.now(),
            status__in=['todo', 'in_progress', 'review']
        ).count(),
        'daily_tasks_today': daily_tasks_today.count(),
        'daily_tasks_completed': len([dt for dt in daily_tasks_today if dt.id in completed_today]),
    }
    
    # Recent tasks
    recent_tasks = user_tasks.order_by('-updated_at')[:5]
    
    # Upcoming deadlines
    upcoming_tasks = user_tasks.filter(
        deadline__gte=timezone.now(),
        status__in=['todo', 'in_progress', 'review']
    ).order_by('deadline')[:5]
    
    context = {
        'bot_user': bot_user,
        'stats': stats,
        'recent_tasks': recent_tasks,
        'upcoming_tasks': upcoming_tasks,
        'daily_tasks_today': daily_tasks_today,
        'completed_today': completed_today,
        'today': today,
    }
    
    return render(request, 'main/dashboard.html', context)


# =============================================================================
# PROJECT MANAGEMENT VIEWS
# =============================================================================

@login_required
def projects_list_view(request):
    """List all projects with filtering and search"""
    try:
        bot_user = request.user.bot_user
    except BotUser.DoesNotExist:
        return redirect('webapp:auth')
    
    # Get projects where user is creator or member
    projects = Project.objects.filter(
        Q(creator=bot_user) | Q(members=bot_user)
    ).distinct().annotate(
        total_tasks=Count('categories__tasks'),
        completed_tasks=Count('categories__tasks', filter=Q(categories__tasks__status='completed'))
    )
    
    # Apply filters
    status_filter = request.GET.get('status')
    priority_filter = request.GET.get('priority')
    search = request.GET.get('search', '')
    
    if status_filter:
        projects = projects.filter(status=status_filter)
    
    if priority_filter:
        projects = projects.filter(priority=priority_filter)
    
    if search:
        projects = projects.filter(
            Q(name__icontains=search) | Q(description__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(projects, 12)
    page = request.GET.get('page')
    projects_page = paginator.get_page(page)
    
    context = {
        'projects': projects_page,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'search': search,
        'status_choices': Project.STATUS_CHOICES,
        'priority_choices': Project.PRIORITY_CHOICES,
    }
    
    return render(request, 'main/projects/list.html', context)


@login_required
def project_detail_view(request, project_id):
    """Project detail view with categories and tasks"""
    try:
        bot_user = request.user.bot_user
    except BotUser.DoesNotExist:
        return redirect('webapp:auth')
    
    project = get_object_or_404(
        Project.objects.prefetch_related('categories__tasks', 'members'),
        Q(creator=bot_user) | Q(members=bot_user),
        id=project_id
    )
    
    # Get categories with task counts
    categories = project.categories.annotate(
        total_tasks=Count('tasks'),
        completed_tasks=Count('tasks', filter=Q(tasks__status='completed'))
    )
    
    # Get recent tasks
    recent_tasks = Task.objects.filter(
        category__project=project
    ).order_by('-updated_at')[:10]
    
    # Statistics
    total_tasks = Task.objects.filter(category__project=project).count()
    completed_tasks = Task.objects.filter(
        category__project=project,
        status='completed'
    ).count()
    
    context = {
        'project': project,
        'categories': categories,
        'recent_tasks': recent_tasks,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'progress_percentage': project.get_progress_percentage(),
    }
    
    return render(request, 'main/projects/detail.html', context)


# =============================================================================
# TASK MANAGEMENT VIEWS
# =============================================================================

@login_required
def tasks_list_view(request):
    """List all tasks with advanced filtering"""
    try:
        bot_user = request.user.bot_user
    except BotUser.DoesNotExist:
        return redirect('webapp:auth')
    
    # Get user's tasks
    tasks = Task.objects.filter(
        Q(creator=bot_user) | Q(assignees=bot_user)
    ).distinct().select_related('category', 'creator', 'category__project')
    
    # Apply filters
    status_filter = request.GET.get('status')
    priority_filter = request.GET.get('priority')
    project_filter = request.GET.get('project')
    category_filter = request.GET.get('category')
    search = request.GET.get('search', '')
    
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    
    if priority_filter:
        tasks = tasks.filter(priority=priority_filter)
    
    if project_filter:
        tasks = tasks.filter(category__project_id=project_filter)
    
    if category_filter:
        tasks = tasks.filter(category_id=category_filter)
    
    if search:
        tasks = tasks.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(notes__icontains=search)
        )
    
    # Get filter options
    user_projects = Project.objects.filter(
        Q(creator=bot_user) | Q(members=bot_user)
    ).distinct()
    
    user_categories = Category.objects.filter(
        project__in=user_projects
    )
    
    # Pagination
    paginator = Paginator(tasks, 20)
    page = request.GET.get('page')
    tasks_page = paginator.get_page(page)
    
    context = {
        'tasks': tasks_page,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'project_filter': project_filter,
        'category_filter': category_filter,
        'search': search,
        'status_choices': Task.STATUS_CHOICES,
        'priority_choices': Task.PRIORITY_CHOICES,
        'user_projects': user_projects,
        'user_categories': user_categories,
    }
    
    return render(request, 'main/tasks/list.html', context)


@login_required
def task_detail_view(request, task_id):
    """Task detail view"""
    try:
        bot_user = request.user.bot_user
    except BotUser.DoesNotExist:
        return redirect('webapp:auth')
    
    task = get_object_or_404(
        Task.objects.select_related('category', 'creator', 'category__project').prefetch_related('assignees'),
        Q(creator=bot_user) | Q(assignees=bot_user),
        id=task_id
    )
    
    context = {
        'task': task,
        'is_overdue': task.is_overdue(),
        'can_edit': task.creator == bot_user,
    }
    
    return render(request, 'main/tasks/detail.html', context)


@login_required
def my_tasks_view(request):
    """Current user's assigned tasks"""
    try:
        bot_user = request.user.bot_user
    except BotUser.DoesNotExist:
        return redirect('webapp:auth')
    
    # Get tasks assigned to current user
    tasks = Task.objects.filter(
        assignees=bot_user
    ).select_related('category', 'creator', 'category__project')
    
    # Separate by status
    todo_tasks = tasks.filter(status='todo')
    in_progress_tasks = tasks.filter(status='in_progress')
    review_tasks = tasks.filter(status='review')
    completed_tasks = tasks.filter(status='completed')
    
    # Get overdue tasks
    overdue_tasks = tasks.filter(
        deadline__lt=timezone.now(),
        status__in=['todo', 'in_progress', 'review']
    )
    
    context = {
        'todo_tasks': todo_tasks,
        'in_progress_tasks': in_progress_tasks,
        'review_tasks': review_tasks,
        'completed_tasks': completed_tasks,
        'overdue_tasks': overdue_tasks,
    }
    
    return render(request, 'main/tasks/my_tasks.html', context)


# =============================================================================
# DAILY TASKS VIEWS
# =============================================================================

@login_required
def daily_tasks_list_view(request):
    """List all daily tasks"""
    try:
        bot_user = request.user.bot_user
    except BotUser.DoesNotExist:
        return redirect('webapp:auth')
    
    daily_tasks = DailyTask.objects.filter(
        Q(creator=bot_user) | Q(assignees=bot_user)
    ).distinct()
    
    # Apply filters
    active_filter = request.GET.get('active')
    priority_filter = request.GET.get('priority')
    search = request.GET.get('search', '')
    
    if active_filter is not None:
        daily_tasks = daily_tasks.filter(is_active=active_filter == 'true')
    
    if priority_filter:
        daily_tasks = daily_tasks.filter(priority=priority_filter)
    
    if search:
        daily_tasks = daily_tasks.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )
    
    context = {
        'daily_tasks': daily_tasks,
        'active_filter': active_filter,
        'priority_filter': priority_filter,
        'search': search,
        'priority_choices': DailyTask.PRIORITY_CHOICES,
    }
    
    return render(request, 'main/daily_tasks/list.html', context)


@login_required
def daily_tasks_today_view(request):
    """Today's scheduled daily tasks"""
    try:
        bot_user = request.user.bot_user
    except BotUser.DoesNotExist:
        return redirect('webapp:auth')
    
    today = timezone.now().date()
    today_weekday = today.weekday()
    
    # Get today's daily tasks
    daily_tasks = DailyTask.objects.filter(
        Q(creator=bot_user) | Q(assignees=bot_user),
        scheduled_days__contains=[today_weekday],
        is_active=True
    ).distinct()
    
    # Check which tasks are completed today
    completed_today = DailyTaskCompletion.objects.filter(
        user=bot_user,
        date=today
    )
    
    completed_task_ids = list(completed_today.values_list('daily_task_id', flat=True))
    
    context = {
        'daily_tasks': daily_tasks,
        'completed_today': completed_today,
        'completed_task_ids': completed_task_ids,
        'today': today,
    }
    
    return render(request, 'main/daily_tasks/today.html', context)


@login_required
def daily_task_detail_view(request, daily_task_id):
    """Daily task detail with completion history"""
    try:
        bot_user = request.user.bot_user
    except BotUser.DoesNotExist:
        return redirect('webapp:auth')
    
    daily_task = get_object_or_404(
        DailyTask.objects.prefetch_related('assignees'),
        Q(creator=bot_user) | Q(assignees=bot_user),
        id=daily_task_id
    )
    
    # Get completion history (last 30 days)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    completions = DailyTaskCompletion.objects.filter(
        daily_task=daily_task,
        user=bot_user,
        date__gte=start_date,
        date__lte=end_date
    ).order_by('-date')
    
    # Calculate streak
    current_date = end_date
    streak = 0
    for i in range(30):  # Check last 30 days
        check_date = current_date - timedelta(days=i)
        if check_date.weekday() in (daily_task.scheduled_days or []):
            if completions.filter(date=check_date).exists():
                streak += 1
            else:
                break
    
    context = {
        'daily_task': daily_task,
        'completions': completions,
        'streak': streak,
        'can_edit': daily_task.creator == bot_user,
    }
    
    return render(request, 'main/daily_tasks/detail.html', context)


# =============================================================================
# API ENDPOINTS
# =============================================================================

@login_required
@require_POST
def complete_task_api(request, task_id):
    """API endpoint to mark task as complete"""
    try:
        bot_user = request.user.bot_user
    except BotUser.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'})
    
    try:
        task = Task.objects.get(
            Q(creator=bot_user) | Q(assignees=bot_user),
            id=task_id
        )
        task.status = 'completed'
        task.save()
        
        return JsonResponse({'success': True})
    except Task.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Task not found'})


@login_required
@require_POST
def update_task_status_api(request, task_id):
    """API endpoint to update task status"""
    try:
        bot_user = request.user.bot_user
    except BotUser.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'})
    
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
        
        if new_status not in dict(Task.STATUS_CHOICES):
            return JsonResponse({'success': False, 'error': 'Invalid status'})
        
        task = Task.objects.get(
            Q(creator=bot_user) | Q(assignees=bot_user),
            id=task_id
        )
        task.status = new_status
        task.save()
        
        return JsonResponse({'success': True})
    except Task.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Task not found'})
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'})


@login_required
@require_POST
def complete_daily_task_api(request, daily_task_id):
    """API endpoint to mark daily task as complete for today"""
    try:
        bot_user = request.user.bot_user
    except BotUser.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'})
    
    try:
        daily_task = DailyTask.objects.get(
            Q(creator=bot_user) | Q(assignees=bot_user),
            id=daily_task_id
        )
        
        today = timezone.now().date()
        
        # Check if already completed today
        completion, created = DailyTaskCompletion.objects.get_or_create(
            daily_task=daily_task,
            user=bot_user,
            date=today,
            defaults={'notes': ''}
        )
        
        if created:
            return JsonResponse({'success': True, 'message': 'Task marked as complete!'})
        else:
            return JsonResponse({'success': False, 'error': 'Task already completed today'})
            
    except DailyTask.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Daily task not found'})


@login_required
def dashboard_stats_api(request):
    """API endpoint for dashboard statistics"""
    try:
        bot_user = request.user.bot_user
    except BotUser.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'})
    
    today = timezone.now().date()
    
    # Get user's projects and tasks
    user_projects = Project.objects.filter(
        Q(creator=bot_user) | Q(members=bot_user)
    ).distinct()
    
    user_tasks = Task.objects.filter(
        Q(creator=bot_user) | Q(assignees=bot_user)
    ).distinct()
    
    # Get today's daily tasks
    today_weekday = today.weekday()
    daily_tasks_today = DailyTask.objects.filter(
        Q(creator=bot_user) | Q(assignees=bot_user),
        scheduled_days__contains=[today_weekday],
        is_active=True
    ).distinct()
    
    completed_today = DailyTaskCompletion.objects.filter(
        user=bot_user,
        date=today
    ).count()
    
    stats = {
        'total_projects': user_projects.count(),
        'active_projects': user_projects.filter(status='active').count(),
        'total_tasks': user_tasks.count(),
        'pending_tasks': user_tasks.filter(status__in=['todo', 'in_progress']).count(),
        'completed_tasks': user_tasks.filter(status='completed').count(),
        'overdue_tasks': user_tasks.filter(
            deadline__lt=timezone.now(),
            status__in=['todo', 'in_progress', 'review']
        ).count(),
        'daily_tasks_today': daily_tasks_today.count(),
        'daily_tasks_completed': completed_today,
    }
    
    return JsonResponse({'success': True, 'stats': stats})
