from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count
from django.utils import timezone
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json

from .models import (
    Project, Category, Task, ProjectMember, TaskComment, 
    TaskAttachment, TaskDependency, ProjectLabel, TaskActivity
)
from .forms import (
    ProjectForm, TaskForm, TaskCommentForm, TaskAttachmentForm,
    ProjectMemberForm, ProjectLabelForm, TaskDependencyForm, CategoryForm
)
from apps.webapp.models import BotUser


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
    """Dashboard view with real data"""
    try:
        # Get or create BotUser for the current user
        bot_user = BotUser.objects.get(user=request.user)
    except BotUser.DoesNotExist:
        # Create BotUser if it doesn't exist
        bot_user = BotUser.objects.create(
            user=request.user,
            telegram_id=0,  # Placeholder
            first_name=request.user.first_name or 'User',
            last_name=request.user.last_name or '',
            username=request.user.username or ''
        )
    
    # Get user's projects
    user_projects = Project.objects.filter(
        Q(creator=bot_user) | Q(members=bot_user)
    ).distinct()
    
    # Get today's tasks
    today = timezone.now().date()
    today_tasks = Task.objects.filter(
        Q(assignees=bot_user) | Q(creator=bot_user),
        deadline__date=today,
        status__in=['todo', 'in_progress']
    ).distinct()
    
    # Get recent activity
    recent_activities = TaskActivity.objects.filter(
        task__in=Task.objects.filter(
            Q(assignees=bot_user) | Q(creator=bot_user)
        )
    ).order_by('-created_at')[:10]
    
    # Get upcoming deadlines
    upcoming_deadlines = Task.objects.filter(
        Q(assignees=bot_user) | Q(creator=bot_user),
        deadline__gte=timezone.now(),
        status__in=['todo', 'in_progress']
    ).order_by('deadline')[:5]
    
    # Calculate completion rate for this week
    week_start = timezone.now().date() - timezone.timedelta(days=7)
    week_tasks = Task.objects.filter(
        Q(assignees=bot_user) | Q(creator=bot_user),
        created_at__date__gte=week_start
    )
    completed_week_tasks = week_tasks.filter(status='completed')
    completion_rate = (completed_week_tasks.count() / week_tasks.count() * 100) if week_tasks.count() > 0 else 0
    
    context = {
        'user_projects': user_projects,
        'today_tasks': today_tasks,
        'recent_activities': recent_activities,
        'upcoming_deadlines': upcoming_deadlines,
        'completion_rate': round(completion_rate, 1),
        'total_projects': user_projects.count(),
        'open_tasks': Task.objects.filter(
            Q(assignees=bot_user) | Q(creator=bot_user),
            status__in=['todo', 'in_progress']
        ).count(),
        'completed_tasks_week': completed_week_tasks.count(),
    }
    
    return render(request, 'main/dashboard.html', context)


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
    """Project list view with real data"""
    try:
        bot_user = BotUser.objects.get(user=request.user)
    except BotUser.DoesNotExist:
        bot_user = BotUser.objects.create(
            user=request.user,
            telegram_id=0,
            first_name=request.user.first_name or 'User',
            last_name=request.user.last_name or '',
            username=request.user.username or ''
        )
    
    # Get user's projects
    projects = Project.objects.filter(
        Q(creator=bot_user) | Q(members=bot_user)
    ).distinct().order_by('-created_at')
    
    # Add pagination
    paginator = Paginator(projects, 12)
    page_number = request.GET.get('page')
    projects = paginator.get_page(page_number)
    
    context = {
        'projects': projects,
        'total_projects': Project.objects.filter(
            Q(creator=bot_user) | Q(members=bot_user)
        ).distinct().count(),
    }
    
    return render(request, 'main/project-list.html', context)


def project_detail_view(request, project_id):
    """Project detail view with real data"""
    try:
        bot_user = BotUser.objects.get(user=request.user)
    except BotUser.DoesNotExist:
        bot_user = BotUser.objects.create(
            user=request.user,
            telegram_id=0,
            first_name=request.user.first_name or 'User',
            last_name=request.user.last_name or '',
            username=request.user.username or ''
        )
    
    project = get_object_or_404(Project, id=project_id)
    
    # Check if user has access to this project
    if not (project.creator == bot_user or bot_user in project.members.all()):
        messages.error(request, 'You do not have access to this project.')
        return redirect('main:project_list')
    
    # Get project categories and tasks
    categories = project.categories.all()
    tasks = Task.objects.filter(category__project=project).order_by('-created_at')
    
    # Get project members
    project_members = ProjectMember.objects.filter(project=project)
    
    # Get recent activities
    recent_activities = TaskActivity.objects.filter(
        task__category__project=project
    ).order_by('-created_at')[:10]
    
    context = {
        'project': project,
        'categories': categories,
        'tasks': tasks,
        'project_members': project_members,
        'recent_activities': recent_activities,
        'progress_percentage': project.get_progress_percentage(),
    }
    
    return render(request, 'main/project-detail.html', context)


def project_crud_view(request, project_id=None):
    """Project CRUD view with real functionality"""
    try:
        bot_user = BotUser.objects.get(user=request.user)
    except BotUser.DoesNotExist:
        bot_user = BotUser.objects.create(
            user=request.user,
            telegram_id=0,
            first_name=request.user.first_name or 'User',
            last_name=request.user.last_name or '',
            username=request.user.username or ''
        )
    
    project = None
    if project_id:
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            messages.error(request, 'Project not found.')
            return redirect('main:project_list')
    
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            project = form.save(commit=False)
            if not project_id:  # Only set creator for new projects
                project.creator = bot_user
            project.save()
            
            if not project_id:  # Only add creator as owner for new projects
                ProjectMember.objects.create(
                    project=project,
                    user=bot_user,
                    role='owner'
                )
            
            # Handle labels
            labels_text = request.POST.get('labels', '')
            if labels_text:
                labels = [label.strip() for label in labels_text.split(',') if label.strip()]
                for label_name in labels:
                    ProjectLabel.objects.get_or_create(
                        project=project,
                        name=label_name,
                        defaults={'color': '#3498db'}
                    )
            
            messages.success(request, f'Project "{project.name}" {"updated" if project_id else "created"} successfully!')
            return redirect('main:project_detail', project_id=project.id)
    else:
        form = ProjectForm(instance=project)
    
    context = {
        'form': form,
        'project': project,
        'users': BotUser.objects.all(),
    }
    
    return render(request, 'main/project-crud.html', context)


# =============================================================================
# TASK MANAGEMENT
# =============================================================================

def task_list_view(request):
    """Task list view with real data"""
    try:
        bot_user = BotUser.objects.get(user=request.user)
    except BotUser.DoesNotExist:
        bot_user = BotUser.objects.create(
            user=request.user,
            telegram_id=0,
            first_name=request.user.first_name or 'User',
            last_name=request.user.last_name or '',
            username=request.user.username or ''
        )
    
    # Get user's tasks
    tasks = Task.objects.filter(
        Q(assignees=bot_user) | Q(creator=bot_user)
    ).distinct().order_by('-created_at')
    
    # Apply filters
    status_filter = request.GET.get('status')
    priority_filter = request.GET.get('priority')
    project_filter = request.GET.get('project')
    
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    if priority_filter:
        tasks = tasks.filter(priority=priority_filter)
    if project_filter:
        tasks = tasks.filter(category__project_id=project_filter)
    
    # Add pagination
    paginator = Paginator(tasks, 20)
    page_number = request.GET.get('page')
    tasks = paginator.get_page(page_number)
    
    # Get filter options
    projects = Project.objects.filter(
        Q(creator=bot_user) | Q(members=bot_user)
    ).distinct()
    
    context = {
        'tasks': tasks,
        'projects': projects,
        'total_tasks': Task.objects.filter(
            Q(assignees=bot_user) | Q(creator=bot_user)
        ).distinct().count(),
    }
    
    return render(request, 'main/task-list.html', context)


def task_detail_view(request, task_id):
    """Task detail view with real data"""
    try:
        bot_user = BotUser.objects.get(user=request.user)
    except BotUser.DoesNotExist:
        bot_user = BotUser.objects.create(
            user=request.user,
            telegram_id=0,
            first_name=request.user.first_name or 'User',
            last_name=request.user.last_name or '',
            username=request.user.username or ''
        )
    
    task = get_object_or_404(Task, id=task_id)
    
    # Check if user has access to this task
    if not (task.creator == bot_user or bot_user in task.assignees.all()):
        messages.error(request, 'You do not have access to this task.')
        return redirect('main:task_list')
    
    # Get task comments
    comments = task.comments.all().order_by('created_at')
    
    # Get task attachments
    attachments = task.attachments.all()
    
    # Get task activities
    activities = task.activities.all().order_by('-created_at')
    
    # Handle comment submission
    if request.method == 'POST' and 'comment' in request.POST:
        comment_form = TaskCommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.task = task
            comment.author = bot_user
            comment.save()
            
            # Create activity
            TaskActivity.objects.create(
                task=task,
                user=bot_user,
                action='commented',
                description=f'Added a comment: {comment.content[:50]}...'
            )
            
            messages.success(request, 'Comment added successfully!')
            return redirect('main:task_detail', task_id=task.id)
    else:
        comment_form = TaskCommentForm()
    
    context = {
        'task': task,
        'comments': comments,
        'attachments': attachments,
        'activities': activities,
        'comment_form': comment_form,
    }
    
    return render(request, 'main/task-detail.html', context)


def task_create_view(request):
    """Task create view with real functionality"""
    try:
        bot_user = BotUser.objects.get(user=request.user)
    except BotUser.DoesNotExist:
        bot_user = BotUser.objects.create(
            user=request.user,
            telegram_id=0,
            first_name=request.user.first_name or 'User',
            last_name=request.user.last_name or '',
            username=request.user.username or ''
        )
    
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.creator = bot_user
            task.save()
            
            # Save many-to-many relationships
            form.save_m2m()
            
            # Create activity
            TaskActivity.objects.create(
                task=task,
                user=bot_user,
                action='created',
                description=f'Created task: {task.title}'
            )
            
            messages.success(request, f'Task "{task.title}" created successfully!')
            return redirect('main:task_detail', task_id=task.id)
    else:
        form = TaskForm()
    
    # Get user's projects and categories
    user_projects = Project.objects.filter(
        Q(creator=bot_user) | Q(members=bot_user)
    ).distinct()
    
    context = {
        'form': form,
        'user_projects': user_projects,
        'users': BotUser.objects.all(),
    }
    
    return render(request, 'main/task-create.html', context)


def my_tasks_view(request):
    """My tasks Kanban view with real data"""
    try:
        bot_user = BotUser.objects.get(user=request.user)
    except BotUser.DoesNotExist:
        bot_user = BotUser.objects.create(
            user=request.user,
            telegram_id=0,
            first_name=request.user.first_name or 'User',
            last_name=request.user.last_name or '',
            username=request.user.username or ''
        )
    
    # Get user's tasks grouped by status
    tasks = Task.objects.filter(
        Q(assignees=bot_user) | Q(creator=bot_user)
    ).distinct()
    
    # Group tasks by status
    todo_tasks = tasks.filter(status='todo')
    in_progress_tasks = tasks.filter(status='in_progress')
    review_tasks = tasks.filter(status='review')
    done_tasks = tasks.filter(status='completed')
    
    context = {
        'todo_tasks': todo_tasks,
        'in_progress_tasks': in_progress_tasks,
        'review_tasks': review_tasks,
        'done_tasks': done_tasks,
        'projects': Project.objects.filter(
            Q(creator=bot_user) | Q(members=bot_user)
        ).distinct(),
    }
    
    return render(request, 'main/my-tasks.html', context)


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


def tasks_calendar_view(request):
    """Tasks calendar view"""
    return render(request, 'main/tasks-calendar.html')


def settings_view(request):
    """Settings view"""
    return render(request, 'main/settings.html')


def daily_tasks_view(request):
    """Daily tasks view"""
    return render(request, 'main/daily-tasks.html')


def daily_tasks_today_view(request):
    """Daily tasks today view"""
    return render(request, 'main/daily-tasks-today.html')


def daily_tasks_detail_view(request, daily_task_id):
    """Daily tasks detail view"""
    return render(request, 'main/daily-tasks-detail.html')


def category_list_view(request):
    """Category list view"""
    return render(request, 'main/category-list.html')


def category_detail_view(request, category_id):
    """Category detail view"""
    return render(request, 'main/category-detail.html')


def analytics_view(request):
    """Analytics view with real data"""
    try:
        # Get or create BotUser for the current user
        bot_user = BotUser.objects.get(user=request.user)
        
        # Get all projects the user has access to
        user_projects = Project.objects.filter(
            Q(owner=request.user) | Q(members__user=request.user)
        ).distinct()
        
        # Get all tasks from user's projects
        all_tasks = Task.objects.filter(category__project__in=user_projects)
        
        # Calculate metrics
        total_tasks = all_tasks.count()
        completed_tasks = all_tasks.filter(status='completed').count()
        in_progress_tasks = all_tasks.filter(status='in_progress').count()
        review_tasks = all_tasks.filter(status='review').count()
        todo_tasks = all_tasks.filter(status='todo').count()
        
        # Priority distribution
        urgent_tasks = all_tasks.filter(priority='urgent').count()
        high_tasks = all_tasks.filter(priority='high').count()
        medium_tasks = all_tasks.filter(priority='medium').count()
        low_tasks = all_tasks.filter(priority='low').count()
        
        # Completion rate
        completion_rate = round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1)
        
        # Team performance
        team_performance = []
        for project in user_projects:
            for member in project.members.all():
                member_tasks = Task.objects.filter(
                    category__project=project,
                    assignees=member.user
                )
                if member_tasks.exists():
                    team_performance.append({
                        'user': member.user,
                        'total_tasks': member_tasks.count(),
                        'completed_tasks': member_tasks.filter(status='completed').count(),
                        'completion_rate': round((member_tasks.filter(status='completed').count() / member_tasks.count() * 100) if member_tasks.count() > 0 else 0, 1),
                        'avg_time': 'N/A'  # This would need more complex calculation
                    })
        
        # Recent activities
        recent_activities = TaskActivity.objects.filter(
            task__category__project__in=user_projects
        ).order_by('-created_at')[:10]
        
        context = {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'in_progress_tasks': in_progress_tasks,
            'review_tasks': review_tasks,
            'todo_tasks': todo_tasks,
            'urgent_tasks': urgent_tasks,
            'high_tasks': high_tasks,
            'medium_tasks': medium_tasks,
            'low_tasks': low_tasks,
            'completion_rate': completion_rate,
            'projects': user_projects,
            'team_performance': team_performance,
            'recent_activities': recent_activities,
        }
        
    except BotUser.DoesNotExist:
        context = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'in_progress_tasks': 0,
            'review_tasks': 0,
            'todo_tasks': 0,
            'urgent_tasks': 0,
            'high_tasks': 0,
            'medium_tasks': 0,
            'low_tasks': 0,
            'completion_rate': 0,
            'projects': [],
            'team_performance': [],
            'recent_activities': [],
        }
    
    return render(request, 'main/analytics.html', context)


def project_analytics_view(request):
    """Project analytics view"""
    return render(request, 'main/project-analytics.html')


def team_members_view(request):
    """Team members view with real functionality"""
    try:
        bot_user = BotUser.objects.get(user=request.user)
    except BotUser.DoesNotExist:
        bot_user = BotUser.objects.create(
            user=request.user,
            telegram_id=0,
            first_name=request.user.first_name or 'User',
            last_name=request.user.last_name or '',
            username=request.user.username or ''
        )
    
    # Get all users for invitation
    all_users = BotUser.objects.all()
    
    # Get project memberships for the current user
    user_memberships = ProjectMember.objects.filter(user=bot_user)
    
    # Get projects where user is owner/admin
    owned_projects = Project.objects.filter(creator=bot_user)
    admin_projects = ProjectMember.objects.filter(
        user=bot_user, 
        role__in=['owner', 'admin']
    ).values_list('project', flat=True)
    
    manageable_projects = Project.objects.filter(
        Q(id__in=owned_projects.values_list('id', flat=True)) |
        Q(id__in=admin_projects)
    ).distinct()
    
    context = {
        'all_users': all_users,
        'user_memberships': user_memberships,
        'manageable_projects': manageable_projects,
    }
    
    return render(request, 'main/team-members.html', context)


# =============================================================================
# AJAX ENDPOINTS
# =============================================================================

@require_http_methods(["POST"])
@csrf_exempt
def update_task_status(request):
    """Update task status via AJAX"""
    try:
        data = json.loads(request.body)
        task_id = data.get('task_id')
        new_status = data.get('status')
        
        try:
            bot_user = BotUser.objects.get(user=request.user)
        except BotUser.DoesNotExist:
            bot_user = BotUser.objects.create(
                user=request.user,
                telegram_id=0,
                first_name=request.user.first_name or 'User',
                last_name=request.user.last_name or '',
                username=request.user.username or ''
            )
        
        task = get_object_or_404(Task, id=task_id)
        
        # Check if user has access to this task
        if not (task.creator == bot_user or bot_user in task.assignees.all()):
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        old_status = task.status
        task.status = new_status
        task.save()
        
        # Create activity
        TaskActivity.objects.create(
            task=task,
            user=bot_user,
            action='status_changed',
            description=f'Status changed from {old_status} to {new_status}'
        )
        
        return JsonResponse({'success': True, 'status': new_status})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def add_task_comment(request):
    """Add comment to task via AJAX"""
    try:
        data = json.loads(request.body)
        task_id = data.get('task_id')
        content = data.get('content')
        
        try:
            bot_user = BotUser.objects.get(user=request.user)
        except BotUser.DoesNotExist:
            bot_user = BotUser.objects.create(
                user=request.user,
                telegram_id=0,
                first_name=request.user.first_name or 'User',
                last_name=request.user.last_name or '',
                username=request.user.username or ''
            )
        
        task = get_object_or_404(Task, id=task_id)
        
        # Check if user has access to this task
        if not (task.creator == bot_user or bot_user in task.assignees.all()):
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        comment = TaskComment.objects.create(
            task=task,
            author=bot_user,
            content=content
        )
        
        # Create activity
        TaskActivity.objects.create(
            task=task,
            user=bot_user,
            action='commented',
            description=f'Added a comment: {content[:50]}...'
        )
        
        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'author': comment.author.get_full_name(),
                'created_at': comment.created_at.isoformat()
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def assign_task(request):
    """Assign task to user via AJAX"""
    try:
        data = json.loads(request.body)
        task_id = data.get('task_id')
        user_id = data.get('user_id')
        
        try:
            bot_user = BotUser.objects.get(user=request.user)
        except BotUser.DoesNotExist:
            bot_user = BotUser.objects.create(
                user=request.user,
                telegram_id=0,
                first_name=request.user.first_name or 'User',
                last_name=request.user.last_name or '',
                username=request.user.username or ''
            )
        
        task = get_object_or_404(Task, id=task_id)
        assignee = get_object_or_404(BotUser, id=user_id)
        
        # Check if user has access to this task
        if not (task.creator == bot_user or bot_user in task.assignees.all()):
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        task.assignees.add(assignee)
        
        # Create activity
        TaskActivity.objects.create(
            task=task,
            user=bot_user,
            action='assigned',
            description=f'Assigned task to {assignee.get_full_name()}'
        )
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_project_categories(request, project_id):
    """Get categories for a project via AJAX"""
    try:
        project = get_object_or_404(Project, id=project_id)
        categories = project.categories.all()
        
        categories_data = []
        for category in categories:
            categories_data.append({
                'id': category.id,
                'name': category.name,
                'color': category.color
            })
        
        return JsonResponse({'categories': categories_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def add_project_member(request):
    """Add member to project via AJAX"""
    try:
        data = json.loads(request.body)
        project_id = data.get('project_id')
        user_id = data.get('user_id')
        role = data.get('role', 'member')
        
        try:
            bot_user = BotUser.objects.get(user=request.user)
        except BotUser.DoesNotExist:
            bot_user = BotUser.objects.create(
                user=request.user,
                telegram_id=0,
                first_name=request.user.first_name or 'User',
                last_name=request.user.last_name or '',
                username=request.user.username or ''
            )
        
        project = get_object_or_404(Project, id=project_id)
        member = get_object_or_404(BotUser, id=user_id)
        
        # Check if user has permission to add members
        if not (project.creator == bot_user or 
                ProjectMember.objects.filter(project=project, user=bot_user, role__in=['owner', 'admin']).exists()):
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Check if member is already in project
        if ProjectMember.objects.filter(project=project, user=member).exists():
            return JsonResponse({'error': 'User is already a member of this project'}, status=400)
        
        # Add member
        ProjectMember.objects.create(
            project=project,
            user=member,
            role=role
        )
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def remove_project_member(request):
    """Remove member from project via AJAX"""
    try:
        data = json.loads(request.body)
        project_id = data.get('project_id')
        user_id = data.get('user_id')
        
        try:
            bot_user = BotUser.objects.get(user=request.user)
        except BotUser.DoesNotExist:
            bot_user = BotUser.objects.create(
                user=request.user,
                telegram_id=0,
                first_name=request.user.first_name or 'User',
                last_name=request.user.last_name or '',
                username=request.user.username or ''
            )
        
        project = get_object_or_404(Project, id=project_id)
        member = get_object_or_404(BotUser, id=user_id)
        
        # Check if user has permission to remove members
        if not (project.creator == bot_user or 
                ProjectMember.objects.filter(project=project, user=bot_user, role__in=['owner', 'admin']).exists()):
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Don't allow removing the project creator
        if project.creator == member:
            return JsonResponse({'error': 'Cannot remove project creator'}, status=400)
        
        # Remove member
        ProjectMember.objects.filter(project=project, user=member).delete()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def update_member_role(request):
    """Update member role via AJAX"""
    try:
        data = json.loads(request.body)
        project_id = data.get('project_id')
        user_id = data.get('user_id')
        new_role = data.get('role')
        
        try:
            bot_user = BotUser.objects.get(user=request.user)
        except BotUser.DoesNotExist:
            bot_user = BotUser.objects.create(
                user=request.user,
                telegram_id=0,
                first_name=request.user.first_name or 'User',
                last_name=request.user.last_name or '',
                username=request.user.username or ''
            )
        
        project = get_object_or_404(Project, id=project_id)
        member = get_object_or_404(BotUser, id=user_id)
        
        # Check if user has permission to update roles
        if not (project.creator == bot_user or 
                ProjectMember.objects.filter(project=project, user=bot_user, role='owner').exists()):
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Don't allow changing the project creator's role
        if project.creator == member:
            return JsonResponse({'error': 'Cannot change project creator role'}, status=400)
        
        # Update role
        ProjectMember.objects.filter(project=project, user=member).update(role=new_role)
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
