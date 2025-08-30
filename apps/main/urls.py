from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views

app_name = 'main'

urlpatterns = [
    # Core pages - Dashboard is now the main page
    path('', login_required(views.dashboard_view), name='home'),
    path('profile/', login_required(views.profile_view), name='profile'),
    path('users/', login_required(views.users_view), name='users'),
    path('mindmap/', login_required(views.mindmap_view), name='mindmap'),
    
    # Dashboard and overview
    path('analytics/', login_required(views.analytics_view), name='analytics'),
    path('project-analytics/', login_required(views.project_analytics_view), name='project_analytics'),
    
    # Project management
    path('project-list/', login_required(views.project_list_view), name='project_list'),
    path('project-detail/<int:project_id>/', login_required(views.project_detail_view), name='project_detail'),
    path('project-crud/', login_required(views.project_crud_view), name='project_crud'),
    
    # Task management
    path('task-list/', login_required(views.task_list_view), name='task_list'),
    path('task-detail/<int:task_id>/', login_required(views.task_detail_view), name='task_detail'),
    path('task-create/', login_required(views.task_create_view), name='task_create'),
    path('my-tasks/', login_required(views.my_tasks_view), name='my_tasks'),
    
    # Daily tasks
    path('daily-tasks/', login_required(views.daily_tasks_view), name='daily_tasks'),
    path('daily-tasks-today/', login_required(views.daily_tasks_today_view), name='daily_tasks_today'),
    path('daily-tasks-detail/<int:daily_task_id>/', login_required(views.daily_tasks_detail_view), name='daily_tasks_detail'),
    
    # Categories
    path('category-list/', login_required(views.category_list_view), name='category_list'),
    path('category-detail/<int:category_id>/', login_required(views.category_detail_view), name='category_detail'),
    
    # Habits and settings
    path('habit-tracker/', login_required(views.habit_tracker_view), name='habit_tracker'),
    path('settings/', login_required(views.settings_view), name='settings'),
    path('team-members/', login_required(views.team_members_view), name='team_members'),
    path('tasks-calendar/', login_required(views.tasks_calendar_view), name='tasks_calendar'),
]
