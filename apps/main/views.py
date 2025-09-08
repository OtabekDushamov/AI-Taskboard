from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, Case, When, IntegerField
from django.utils import timezone
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta
import json

from .models import (
    Project, Category, Task, ProjectMember, TaskComment, 
    TaskAttachment, TaskDependency, ProjectLabel, TaskActivity,
    DailyTask, DailyTaskCompletion
)
from .forms import (
    ProjectForm, TaskForm, TaskCommentForm, TaskAttachmentForm,
    ProjectMemberForm, ProjectLabelForm, TaskDependencyForm, CategoryForm,
    DailyTaskForm, DailyTaskCompletionForm
)
from apps.webapp.models import BotUser


# =============================================================================
# CORE PAGES
# =============================================================================

def profile_view(request):
    """Profile page view"""
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
    
    # Handle profile updates
    if request.method == 'POST':
        # Update BotUser fields
        bot_user.first_name = request.POST.get('first_name', bot_user.first_name)
        bot_user.last_name = request.POST.get('last_name', bot_user.last_name)
        bot_user.username = request.POST.get('username', bot_user.username)
        bot_user.save()
        
        # Update User fields
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('main:profile')
    
    context = {
        'bot_user': bot_user,
        'user': request.user,
    }
    return render(request, 'main/profile.html', context)


def users_view(request):
    """Users list view"""
    return render(request, 'main/users.html')


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
        deadline__date=today
    ).distinct().annotate(
        priority_order=Case(
            When(priority='urgent', then=1),
            When(priority='high', then=2),
            When(priority='medium', then=3),
            When(priority='low', then=4),
            default=5,
            output_field=IntegerField(),
        )
    ).order_by('status', 'priority_order', 'category__project__name', 'deadline')
    
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
    
    # Calculate KPI subtitles
    # Projects: New projects this week
    week_start_projects = timezone.now().date() - timezone.timedelta(days=7)
    new_projects_week = user_projects.filter(created_at__date__gte=week_start_projects).count()
    
    # Open Tasks: Overdue tasks
    overdue_tasks = Task.objects.filter(
        Q(assignees=bot_user) | Q(creator=bot_user),
        deadline__date__lt=today,
        status__in=['todo', 'in_progress']
    ).count()
    
    # Completed Tasks: Compare with last week
    last_week_start = timezone.now().date() - timezone.timedelta(days=14)
    last_week_end = timezone.now().date() - timezone.timedelta(days=7)
    completed_last_week = Task.objects.filter(
        Q(assignees=bot_user) | Q(creator=bot_user),
        status='completed',
        updated_at__date__gte=last_week_start,
        updated_at__date__lt=last_week_end
    ).count()
    
    # Calculate streak (consecutive days with completed tasks)
    streak_days = 0
    current_date = today
    while True:
        day_tasks = Task.objects.filter(
            Q(assignees=bot_user) | Q(creator=bot_user),
            status='completed',
            updated_at__date=current_date
        )
        if day_tasks.exists():
            streak_days += 1
            current_date -= timezone.timedelta(days=1)
        else:
            break
    
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
        # KPI subtitles
        'new_projects_week': new_projects_week,
        'overdue_tasks': overdue_tasks,
        'completed_last_week': completed_last_week,
        'streak_days': streak_days,
        # Donut chart data
        'total_week_tasks': week_tasks.count(),
        'completed_week_tasks_count': completed_week_tasks.count(),
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
    ).distinct().order_by('created_at')
    
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
    
    # Get filtered task counts for the dashboard
    todo_tasks = tasks.filter(status='todo')
    in_progress_tasks = tasks.filter(status='in_progress')
    review_tasks = tasks.filter(status='review')
    completed_tasks = tasks.filter(status='completed')
    
    # Group tasks by status for Kanban board
    tasks_by_status = {
        'todo': todo_tasks,
        'in_progress': in_progress_tasks,
        'review': review_tasks,
        'completed': completed_tasks,
    }
    
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
        'todo_tasks': todo_tasks,
        'in_progress_tasks': in_progress_tasks,
        'review_tasks': review_tasks,
        'completed_tasks': completed_tasks,
        'tasks_by_status': tasks_by_status,
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
            # Check if user has access to edit this project
            if not (project.creator == bot_user or 
                    ProjectMember.objects.filter(project=project, user=bot_user, role__in=['owner', 'admin']).exists()):
                messages.error(request, 'You do not have permission to edit this project.')
                return redirect('main:project_list')
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
            
            # Handle labels - for both creation and editing
            labels_text = request.POST.get('labels', '')
            if labels_text:
                # Get current labels
                current_labels = set(project.labels.values_list('name', flat=True))
                
                # Parse new labels
                new_labels = [label.strip() for label in labels_text.split(',') if label.strip()]
                new_labels_set = set(new_labels)
                
                # Remove labels that are no longer in the list
                labels_to_remove = current_labels - new_labels_set
                project.labels.filter(name__in=labels_to_remove).delete()
                
                # Add new labels
                for label_name in new_labels:
                    ProjectLabel.objects.get_or_create(
                        project=project,
                        name=label_name,
                        defaults={'color': '#3498db'}
                    )
            else:
                # If no labels provided, remove all existing labels
                project.labels.all().delete()
            
            # Handle team members - for both creation and editing
            team_member_ids = request.POST.getlist('team_members')
            if team_member_ids:
                # Get current project members (excluding creator)
                current_members = set(ProjectMember.objects.filter(
                    project=project
                ).exclude(user=project.creator).values_list('user_id', flat=True))
                
                new_member_ids = set(int(id) for id in team_member_ids if id)
                
                # Remove members that are no longer selected
                members_to_remove = current_members - new_member_ids
                ProjectMember.objects.filter(
                    project=project,
                    user_id__in=members_to_remove
                ).delete()
                
                # Add new members
                for member_id in new_member_ids:
                    if member_id not in current_members:
                        ProjectMember.objects.get_or_create(
                            project=project,
                            user_id=member_id,
                            defaults={'role': 'viewer'}
                        )
            else:
                # If no team members provided, remove all members except creator
                ProjectMember.objects.filter(project=project).exclude(user=project.creator).delete()
            
            # Sync the members ManyToManyField with ProjectMember objects
            project_member_users = ProjectMember.objects.filter(project=project).values_list('user', flat=True)
            project.members.set(project_member_users)
            
            messages.success(request, f'Project "{project.name}" {"updated" if project_id else "created"} successfully!')
            return redirect('main:project_detail', project_id=project.id)
    else:
        form = ProjectForm(instance=project)
        # Pre-populate labels field for editing
        if project:
            existing_labels = ', '.join(project.labels.values_list('name', flat=True))
            form.fields['labels'].initial = existing_labels
    
    # Get available users (excluding current project members for editing)
    available_users = BotUser.objects.all()
    if project:
        current_member_ids = project.project_members.values_list('user_id', flat=True)
        available_users = available_users.exclude(id__in=current_member_ids)
    
    context = {
        'form': form,
        'project': project,
        'available_users': available_users,
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
    if request.method == 'POST' and 'content' in request.POST:
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


def task_crud_view(request, task_id=None):
    """Task CRUD view - handles both create and edit operations"""
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
    
    # Get project from URL parameter (for create mode)
    project_id = request.GET.get('project')
    selected_project = None
    if project_id:
        try:
            selected_project = Project.objects.get(id=project_id)
            # Check if user has access to this project
            if not (selected_project.creator == bot_user or bot_user in selected_project.members.all()):
                selected_project = None
        except Project.DoesNotExist:
            selected_project = None
    
    # Get task if editing
    task = None
    if task_id:
        task = get_object_or_404(Task, id=task_id)
        # Check if user has access to this task
        if not (task.creator == bot_user or bot_user in task.assignees.all()):
            messages.error(request, 'You do not have access to this task.')
            return redirect('main:task_list')
    
    if request.method == 'POST':
        # Get project and category from form
        project_id = request.POST.get('project')
        category_id = request.POST.get('category', '')
        
        # Create form data without category for validation
        form_data = request.POST.copy()
        form = TaskForm(form_data, instance=task)
        
        # Make category optional
        form.fields['category'].required = False
        
        if form.is_valid() and project_id:
            task_obj = form.save(commit=False)
            task_obj.creator = bot_user
            
            # Get the project
            try:
                project = Project.objects.get(id=project_id)
            except Project.DoesNotExist:
                messages.error(request, 'Selected project not found')
                return render(request, 'main/task-crud.html', context)
            
            # Handle category assignment
            if category_id:
                # Category was selected
                try:
                    category = Category.objects.get(id=category_id, project=project)
                    task_obj.category = category
                except Category.DoesNotExist:
                    messages.error(request, 'Selected category not found')
                    return render(request, 'main/task-crud.html', context)
            else:
                # No category selected, create a default one
                default_category, created = Category.objects.get_or_create(
                    project=project,
                    name='General',
                    defaults={
                        'description': 'Default category for tasks',
                        'color': '#3498db'
                    }
                )
                task_obj.category = default_category
                if created:
                    messages.info(request, f'Created default "General" category for project "{project.name}"')
            
            task_obj.save()
            
            # Save many-to-many relationships
            form.save_m2m()
            
            # Handle dependencies manually using TaskDependency model
            dependencies = request.POST.getlist('dependencies')
            if dependencies:
                # Clear existing dependencies
                TaskDependency.objects.filter(task=task_obj).delete()
                
                # Create new dependencies
                for dependency_id in dependencies:
                    if dependency_id:  # Make sure it's not empty
                        TaskDependency.objects.create(
                            task=task_obj,
                            depends_on_id=dependency_id
                        )
            
            # Create activity
            action = 'updated' if task else 'created'
            TaskActivity.objects.create(
                task=task_obj,
                user=bot_user,
                action=action,
                description=f'{action.title()} task: {task_obj.title}'
            )
            
            messages.success(request, f'Task "{task_obj.title}" {action} successfully!')
            return redirect('main:task_detail', task_id=task_obj.id)
        else:
            if not project_id:
                messages.error(request, 'Please select a project')
    else:
        form = TaskForm(instance=task)
    
    # Get user's projects and categories
    user_projects = Project.objects.filter(
        Q(creator=bot_user) | Q(members=bot_user)
    ).distinct()
    
    # Get available tasks for dependencies (exclude current task if editing)
    available_tasks = Task.objects.select_related('category__project').order_by('category__project__name', 'title')
    if task:
        available_tasks = available_tasks.exclude(id=task.id)
    
    # Get current dependencies if editing
    current_dependencies = []
    if task:
        current_dependencies = [dep.depends_on.id for dep in task.dependencies.all()]
    
    context = {
        'form': form,
        'user_projects': user_projects,
        'selected_project': selected_project,
        'task': task,
        'users': BotUser.objects.all(),
        'available_tasks': available_tasks,
        'current_dependencies': current_dependencies,
    }
    
    return render(request, 'main/task-crud.html', context)


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
    """Daily tasks management view with full CRUD functionality"""
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
    
    # Get user's daily tasks
    daily_tasks = DailyTask.objects.filter(
        Q(creator=bot_user) | Q(assignees=bot_user)
    ).distinct().order_by('reminder_time', 'title')
    
    # Handle form submissions
    if request.method == 'POST':
        if 'create_task' in request.POST:
            form = DailyTaskForm(request.POST)
            if form.is_valid():
                daily_task = form.save(commit=False)
                daily_task.creator = bot_user
                daily_task.save()
                form.save_m2m()
                messages.success(request, f'Daily task "{daily_task.title}" created successfully!')
                return redirect('main:daily_tasks')
        elif 'edit_task' in request.POST:
            task_id = request.POST.get('task_id')
            try:
                daily_task = DailyTask.objects.get(id=task_id)
                if daily_task.creator == bot_user or bot_user in daily_task.assignees.all():
                    form = DailyTaskForm(request.POST, instance=daily_task)
                    if form.is_valid():
                        form.save()
                        messages.success(request, f'Daily task "{daily_task.title}" updated successfully!')
                        return redirect('main:daily_tasks')
                    else:
                        # Debug: Log form errors
                        print("Form errors:", form.errors)
                        print("Form non-field errors:", form.non_field_errors())
                        messages.error(request, f'Form validation failed: {form.errors}')
                else:
                    messages.error(request, 'You do not have permission to edit this task.')
            except DailyTask.DoesNotExist:
                messages.error(request, 'Daily task not found.')
        elif 'delete_task' in request.POST:
            task_id = request.POST.get('task_id')
            try:
                daily_task = DailyTask.objects.get(id=task_id)
                if daily_task.creator == bot_user:
                    daily_task.delete()
                    messages.success(request, f'Daily task "{daily_task.title}" deleted successfully!')
                    return redirect('main:daily_tasks')
                else:
                    messages.error(request, 'You can only delete tasks you created.')
            except DailyTask.DoesNotExist:
                messages.error(request, 'Daily task not found.')
        elif 'toggle_active' in request.POST:
            task_id = request.POST.get('task_id')
            try:
                daily_task = DailyTask.objects.get(id=task_id)
                if daily_task.creator == bot_user or bot_user in daily_task.assignees.all():
                    daily_task.is_active = not daily_task.is_active
                    daily_task.save()
                    status = 'activated' if daily_task.is_active else 'deactivated'
                    messages.success(request, f'Daily task "{daily_task.title}" {status} successfully!')
                    return redirect('main:daily_tasks')
                else:
                    messages.error(request, 'You do not have permission to modify this task.')
            except DailyTask.DoesNotExist:
                messages.error(request, 'Daily task not found.')
    
    # Get completion data for the last 30 days
    from datetime import datetime, timedelta
    thirty_days_ago = timezone.now().date() - timedelta(days=30)
    completions = DailyTaskCompletion.objects.filter(
        daily_task__in=daily_tasks,
        date__gte=thirty_days_ago
    ).order_by('-date')
    
    context = {
        'daily_tasks': daily_tasks,
        'completions': completions,
        'form': DailyTaskForm(),
        'users': BotUser.objects.all(),
    }
    
    return render(request, 'main/daily-tasks.html', context)


def daily_tasks_today_view(request):
    """Today's daily tasks view with completion tracking"""
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
    
    today = timezone.now().date()
    today_weekday = today.weekday()
    
    # Get today's scheduled tasks
    all_daily_tasks = DailyTask.objects.filter(
        Q(creator=bot_user) | Q(assignees=bot_user),
        is_active=True
    ).distinct()

    # Filter in Python to check if today's weekday is in scheduled_days
    today_tasks = [task for task in all_daily_tasks if f"{today_weekday}" in (task.scheduled_days or [])]

    # Sort by reminder_time and title
    from datetime import time
    today_tasks.sort(key=lambda x: (x.reminder_time or time(23, 59), x.title))
    
    # Get completion status for today
    completed_today = DailyTaskCompletion.objects.filter(
        daily_task__in=today_tasks,
        user=bot_user,
        date=today
    ).values_list('daily_task_id', flat=True)
    
    # Handle completion form submission
    if request.method == 'POST':
        if 'complete_task' in request.POST:
            task_id = request.POST.get('task_id')
            notes = request.POST.get('notes', '')
            actual_minutes = request.POST.get('actual_minutes')
            
            try:
                daily_task = DailyTask.objects.get(id=task_id)
                if daily_task.creator == bot_user or bot_user in daily_task.assignees.all():
                    # Check if already completed today
                    existing_completion = DailyTaskCompletion.objects.filter(
                        daily_task=daily_task,
                        user=bot_user,
                        date=today
                    ).first()
                    
                    if existing_completion:
                        messages.info(request, f'You have already completed "{daily_task.title}" today.')
                    else:
                        DailyTaskCompletion.objects.create(
                            daily_task=daily_task,
                            user=bot_user,
                            date=today,
                            notes=notes,
                            actual_minutes=int(actual_minutes) if actual_minutes else None
                        )
                        messages.success(request, f'Great job completing "{daily_task.title}"!')
                        return redirect('main:daily_tasks_today')
                else:
                    messages.error(request, 'You do not have permission to complete this task.')
            except DailyTask.DoesNotExist:
                messages.error(request, 'Daily task not found.')
            except ValueError:
                messages.error(request, 'Please enter a valid number for actual minutes.')
    
    context = {
        'today_tasks': today_tasks,
        'completed_today': completed_today,
        'today': today,
        'completion_form': DailyTaskCompletionForm(),
    }
    
    return render(request, 'main/daily-tasks-today.html', context)


def daily_tasks_detail_view(request, daily_task_id):
    """Daily task detail view with completion history"""
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
    
    daily_task = get_object_or_404(DailyTask, id=daily_task_id)
    
    # Check if user has access to this task
    if not (daily_task.creator == bot_user or bot_user in daily_task.assignees.all()):
        messages.error(request, 'You do not have access to this daily task.')
        return redirect('main:daily_tasks')
    
    # Get completion history
    completions = DailyTaskCompletion.objects.filter(
        daily_task=daily_task,
        user=bot_user
    ).order_by('-date')[:30]  # Last 30 completions
    
    # Calculate statistics
    total_completions = completions.count()
    streak = 0
    current_date = timezone.now().date()
    
    # Calculate current streak
    while True:
        if DailyTaskCompletion.objects.filter(
            daily_task=daily_task,
            user=bot_user,
            date=current_date
        ).exists():
            streak += 1
            current_date -= timedelta(days=1)
        else:
            break
    
    # Calculate completion rate for the last 30 days
    from datetime import datetime, timedelta
    thirty_days_ago = timezone.now().date() - timedelta(days=30)
    scheduled_days = []
    current_date = thirty_days_ago
    while current_date <= timezone.now().date():
        if current_date.weekday() in daily_task.scheduled_days:
            scheduled_days.append(current_date)
        current_date += timedelta(days=1)
    
    completion_rate = (total_completions / len(scheduled_days) * 100) if scheduled_days else 0
    
    context = {
        'daily_task': daily_task,
        'completions': completions,
        'total_completions': total_completions,
        'streak': streak,
        'completion_rate': round(completion_rate, 1),
        'scheduled_days_count': len(scheduled_days),
    }
    
    return render(request, 'main/daily-tasks-detail.html', context)


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
    """Tasks calendar view with full CRUD functionality"""
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
    
    # Get current date and view parameters
    today = timezone.now().date()
    year = request.GET.get('year', today.year)
    month = request.GET.get('month', today.month)
    
    try:
        year = int(year)
        month = int(month)
        current_date = timezone.datetime(year, month, 1).date()
    except (ValueError, TypeError):
        current_date = today
    
    # Get user's tasks with deadlines
    tasks_with_deadlines = Task.objects.filter(
        Q(assignees=bot_user) | Q(creator=bot_user),
        deadline__isnull=False
    ).distinct().order_by('deadline')
    
    # Get user's daily tasks
    daily_tasks = DailyTask.objects.filter(
        Q(creator=bot_user) | Q(assignees=bot_user),
        is_active=True
    ).distinct()
    
    # Create calendar events
    calendar_events = []
    
    # Add regular tasks
    for task in tasks_with_deadlines:
        if task.deadline:
            calendar_events.append({
                'id': f'task_{task.id}',
                'title': task.title,
                'date': task.deadline.date().strftime('%Y-%m-%d'),
                'time': task.deadline.time().strftime('%H:%M:%S'),
                'type': 'task',
                'priority': task.priority,
                'status': task.status,
                'project': task.category.project.name if task.category else 'No Project',
                'assignee': task.get_assignee_names(),
                'description': task.description,
                'notes': task.notes,
                'creator': task.creator.get_full_name(),
                'actual_hours': task.actual_hours,
                'created_at': task.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': task.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                'completed_at': task.completed_at.strftime('%Y-%m-%d %H:%M:%S') if task.completed_at else None,
                'is_overdue': task.is_overdue(),
                'task_id': task.id,
            })
    
    # Add daily tasks for the month
    for daily_task in daily_tasks:
        # Generate events for each scheduled day in the month
        for day_num in daily_task.scheduled_days:
            # Find all dates in the current month that match this weekday
            first_day = current_date.replace(day=1)
            last_day = (first_day + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            current_day = first_day
            while current_day <= last_day:
                if current_day.weekday() == day_num:
                    calendar_events.append({
                        'id': f'daily_task_{daily_task.id}_{current_day}',
                        'title': daily_task.title,
                        'date': current_day.strftime('%Y-%m-%d'),
                        'time': daily_task.reminder_time,
                        'type': 'daily_task',
                        'priority': daily_task.priority,
                        'status': 'scheduled',
                        'project': 'Daily Tasks',
                        'assignee': daily_task.get_assignee_names(),
                        'description': daily_task.description,
                        'notes': daily_task.notes,
                        'creator': daily_task.creator.get_full_name(),
                        'estimated_minutes': daily_task.estimated_minutes,
                        'scheduled_days': daily_task.scheduled_days,
                        'is_active': daily_task.is_active,
                        'created_at': daily_task.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'daily_task_id': daily_task.id,
                    })
                current_day += timedelta(days=1)
    
    # Handle AJAX requests for calendar data
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'events': calendar_events,
            'current_date': current_date.isoformat(),
        })
    
    # Get user's projects for filtering
    user_projects = Project.objects.filter(
        Q(creator=bot_user) | Q(members=bot_user)
    ).distinct()
    
    # Convert calendar events to JSON-serializable format
    import json
    calendar_events_json = json.dumps(calendar_events, default=str)
    
    context = {
        'calendar_events': calendar_events_json,
        'current_date': current_date,
        'today': today,
        'user_projects': user_projects,
        'users': BotUser.objects.all(),
        'task_form': TaskForm(),
        'daily_task_form': DailyTaskForm(),
    }
    
    return render(request, 'main/tasks-calendar.html', context)


def settings_view(request):
    """Settings view"""
    return render(request, 'main/settings.html')


def analytics_view(request):
    """Analytics view with real data"""
    try:
        # Get or create BotUser for the current user
        bot_user, created = BotUser.objects.get_or_create(
            user=request.user,
            defaults={
                'telegram_id': 0,
                'first_name': request.user.first_name or 'User',
                'last_name': request.user.last_name or '',
                'username': request.user.username or ''
            }
        )
        
        # Get all projects the user has access to
        user_projects = Project.objects.filter(
            Q(creator=bot_user) | Q(members=bot_user)
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
                    assignees=member
                )
                if member_tasks.exists():
                    team_performance.append({
                        'user': member.user,
                        'total_tasks': member_tasks.count(),
                        'completed_tasks': member_tasks.filter(status='completed').count(),
                        'completion_rate': round((member_tasks.filter(status='completed').count() / member_tasks.count() * 100) if member_tasks.count() > 0 else 0, 1),
                        'avg_time': 'N/A'  # This would need more complex calculation
                    })
        
        # Calculate project progress
        projects_with_progress = []
        for project in user_projects:
            project_tasks = Task.objects.filter(category__project=project)
            total_tasks = project_tasks.count()
            completed_tasks = project_tasks.filter(status='completed').count()
            progress = round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1)
            
            projects_with_progress.append({
                'project': project,
                'progress': progress,
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks
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
            'projects': projects_with_progress,
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


def team_members_view(request, project_id=None):
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
    
    # If a specific project is requested, get its details
    selected_project = None
    project_members = []
    if project_id:
        try:
            selected_project = Project.objects.get(id=project_id)
            # Check if user has access to this project
            if not (selected_project.creator == bot_user or bot_user in selected_project.members.all()):
                messages.error(request, 'You do not have access to this project.')
                return redirect('main:team_members')
            
            project_members = ProjectMember.objects.filter(project=selected_project)
        except Project.DoesNotExist:
            messages.error(request, 'Project not found.')
            return redirect('main:team_members')
    
    context = {
        'all_users': all_users,
        'user_memberships': user_memberships,
        'manageable_projects': manageable_projects,
        'selected_project': selected_project,
        'project_members': project_members,
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
def update_task_priority(request):
    """Update task priority via AJAX"""
    try:
        data = json.loads(request.body)
        task_id = data.get('task_id')
        new_priority = data.get('priority')
        
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
        
        old_priority = task.priority
        task.priority = new_priority
        task.save()
        
        # Create activity
        TaskActivity.objects.create(
            task=task,
            user=bot_user,
            action='priority_changed',
            description=f'Priority changed from {old_priority} to {new_priority}'
        )
        
        return JsonResponse({'success': True, 'priority': new_priority})
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
        
        # Sync the members ManyToManyField
        project_member_users = ProjectMember.objects.filter(project=project).values_list('user', flat=True)
        project.members.set(project_member_users)
        
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
        
        # Sync the members ManyToManyField
        project_member_users = ProjectMember.objects.filter(project=project).values_list('user', flat=True)
        project.members.set(project_member_users)
        
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
        
        # Sync the members ManyToManyField (in case role change affects membership)
        project_member_users = ProjectMember.objects.filter(project=project).values_list('user', flat=True)
        project.members.set(project_member_users)
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def toggle_task_completion(request):
    """Toggle task completion status via AJAX"""
    try:
        data = json.loads(request.body)
        task_id = data.get('task_id')
        completed = data.get('completed', False)
        
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
        new_status = 'completed' if completed else 'todo'
        task.status = new_status
        task.save()
        
        # Create activity
        TaskActivity.objects.create(
            task=task,
            user=bot_user,
            action='status_changed',
            description=f'Status changed from {old_status} to {new_status}'
        )
        
        return JsonResponse({
            'success': True, 
            'status': new_status,
            'completed': completed
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)