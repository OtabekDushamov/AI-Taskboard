from django.shortcuts import render


# =============================================================================
# CORE PAGES
# =============================================================================

def profile_view(request):
    """Profile page view"""
    return render(request, 'main/profile.html')


def users_view(request):
    """Users list view"""
    return render(request, 'main/users.html')


def mindmap_view(request):
    """Mindmap view"""
    return render(request, 'main/mindmap.html')


# =============================================================================
# DASHBOARD AND OVERVIEW
# =============================================================================

def dashboard_view(request):
    """Dashboard view"""
    return render(request, 'main/dashboard.html')


def analytics_view(request):
    """Analytics view"""
    return render(request, 'main/analytics.html')


def project_analytics_view(request):
    """Project analytics view"""
    return render(request, 'main/project-analytics.html')


# =============================================================================
# PROJECT MANAGEMENT
# =============================================================================

def project_list_view(request):
    """Project list view"""
    return render(request, 'main/project-list.html')


def project_detail_view(request, project_id):
    """Project detail view"""
    return render(request, 'main/project-detail.html')


def project_crud_view(request):
    """Project CRUD view"""
    return render(request, 'main/project-crud.html')


# =============================================================================
# TASK MANAGEMENT
# =============================================================================

def task_list_view(request):
    """Task list view"""
    return render(request, 'main/task-list.html')


def task_detail_view(request, task_id):
    """Task detail view"""
    return render(request, 'main/task-detail.html')


def task_create_view(request):
    """Task create view"""
    return render(request, 'main/task-create.html')


def my_tasks_view(request):
    """My tasks view"""
    return render(request, 'main/my-tasks.html')


# =============================================================================
# DAILY TASKS
# =============================================================================

def daily_tasks_view(request):
    """Daily tasks view"""
    return render(request, 'main/daily-tasks.html')


def daily_tasks_today_view(request):
    """Daily tasks today view"""
    return render(request, 'main/daily-tasks-today.html')


def daily_tasks_detail_view(request, daily_task_id):
    """Daily tasks detail view"""
    return render(request, 'main/daily-tasks-detail.html')


# =============================================================================
# CATEGORIES
# =============================================================================

def category_list_view(request):
    """Category list view"""
    return render(request, 'main/category-list.html')


def category_detail_view(request, category_id):
    """Category detail view"""
    return render(request, 'main/category-detail.html')


# =============================================================================
# HABITS AND SETTINGS
# =============================================================================

def habit_tracker_view(request):
    """Habit tracker view"""
    return render(request, 'main/habit-tracker.html')


def settings_view(request):
    """Settings view"""
    return render(request, 'main/settings.html')


def team_members_view(request):
    """Team members view"""
    return render(request, 'main/team-members.html')


def tasks_calendar_view(request):
    """Tasks calendar view"""
    return render(request, 'main/tasks-calendar.html')
