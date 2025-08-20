from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    # Core pages
    path('', views.home_view, name='home'),
    path('profile/', views.profile_view, name='profile'),
    path('users/', views.users_list_view, name='users_list'),
    
    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # Projects
    path('projects/', views.projects_list_view, name='projects_list'),
    path('projects/<int:project_id>/', views.project_detail_view, name='project_detail'),
    
    # Tasks
    path('tasks/', views.tasks_list_view, name='tasks_list'),
    path('tasks/<int:task_id>/', views.task_detail_view, name='task_detail'),
    path('my-tasks/', views.my_tasks_view, name='my_tasks'),
    
    # Daily Tasks
    path('daily-tasks/', views.daily_tasks_list_view, name='daily_tasks_list'),
    path('daily-tasks/today/', views.daily_tasks_today_view, name='daily_tasks_today'),
    path('daily-tasks/<int:daily_task_id>/', views.daily_task_detail_view, name='daily_task_detail'),
    
    # API Endpoints
    path('api/tasks/<int:task_id>/complete/', views.complete_task_api, name='complete_task_api'),
    path('api/tasks/<int:task_id>/status/', views.update_task_status_api, name='update_task_status_api'),
    path('api/daily-tasks/<int:daily_task_id>/complete/', views.complete_daily_task_api, name='complete_daily_task_api'),
    path('api/stats/', views.dashboard_stats_api, name='dashboard_stats_api'),
]
