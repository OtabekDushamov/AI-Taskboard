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
    path('project-crud/<int:project_id>/', login_required(views.project_crud_view), name='project_crud'),
    
    # Task management
    path('task-list/', login_required(views.task_list_view), name='task_list'),
    path('task-detail/<int:task_id>/', login_required(views.task_detail_view), name='task_detail'),
    path('task-crud/', login_required(views.task_crud_view), name='task_crud'),
    path('task-crud/<int:task_id>/', login_required(views.task_crud_view), name='task_crud'),
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
    path('team-members/<int:project_id>/', login_required(views.team_members_view), name='team_members'),
    path('tasks-calendar/', login_required(views.tasks_calendar_view), name='tasks_calendar'),
    
    # AJAX endpoints
    path('api/update-task-status/', login_required(views.update_task_status), name='update_task_status'),
    path('api/update-task-priority/', login_required(views.update_task_priority), name='update_task_priority'),
    path('api/add-task-comment/', login_required(views.add_task_comment), name='add_task_comment'),
    path('api/assign-task/', login_required(views.assign_task), name='assign_task'),
    path('api/project/<int:project_id>/categories/', login_required(views.get_project_categories), name='get_project_categories'),
    path('api/add-project-member/', login_required(views.add_project_member), name='add_project_member'),
    path('api/remove-project-member/', login_required(views.remove_project_member), name='remove_project_member'),
    path('api/update-member-role/', login_required(views.update_member_role), name='update_member_role'),
]
