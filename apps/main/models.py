from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from apps.webapp.models import BotUser


class Project(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    creator = models.ForeignKey(BotUser, on_delete=models.CASCADE, related_name='created_projects')
    members = models.ManyToManyField(BotUser, related_name='projects', blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active')
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def get_progress_percentage(self):
        """Calculate project completion percentage based on tasks"""
        total_tasks = self.categories.aggregate(
            total=models.Count('tasks')
        )['total'] or 0
        
        if total_tasks == 0:
            return 0
            
        completed_tasks = self.categories.aggregate(
            completed=models.Count('tasks', filter=models.Q(tasks__status='completed'))
        )['completed'] or 0
        
        return round((completed_tasks / total_tasks) * 100, 1)
    
    def get_task_count(self):
        """Get total number of tasks in this project"""
        return self.categories.aggregate(
            total=models.Count('tasks')
        )['total'] or 0


class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='categories')
    color = models.CharField(max_length=7, default='#3498db', help_text='Hex color code')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        unique_together = ['project', 'name']
        ordering = ['name']
    
    def __str__(self):
        return f"{self.project.name} - {self.name}"
    
    def get_task_count(self):
        return self.tasks.count()
    
    def get_completed_task_count(self):
        return self.tasks.filter(status='completed').count()


class Task(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('todo', 'To Do'),
        ('in_progress', 'In Progress'),
        ('review', 'Under Review'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True, help_text='Additional notes and comments')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='tasks')
    creator = models.ForeignKey(BotUser, on_delete=models.CASCADE, related_name='created_tasks')
    assignees = models.ManyToManyField(BotUser, related_name='assigned_tasks', blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='todo')
    deadline = models.DateTimeField(blank=True, null=True)
    actual_hours = models.PositiveIntegerField(blank=True, null=True, help_text='Actual hours spent')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'Task'
        verbose_name_plural = 'Tasks'
        ordering = ['-priority', 'deadline', '-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.category.project.name})"
    
    def save(self, *args, **kwargs):
        # Automatically set completed_at when status changes to completed
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
        elif self.status != 'completed':
            self.completed_at = None
        super().save(*args, **kwargs)
    
    def is_overdue(self):
        """Check if task is overdue"""
        if self.deadline and self.status not in ['completed', 'cancelled']:
            return timezone.now() > self.deadline
        return False
    
    def get_assignee_names(self):
        """Get comma-separated list of assignee names"""
        return ", ".join([assignee.get_full_name() for assignee in self.assignees.all()])


class DailyTask(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    WEEKDAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'), 
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    creator = models.ForeignKey(BotUser, on_delete=models.CASCADE, related_name='created_daily_tasks')
    assignees = models.ManyToManyField(BotUser, related_name='assigned_daily_tasks', blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    scheduled_days = models.JSONField(default=list, help_text='List of weekday numbers (0=Monday, 6=Sunday)')
    estimated_minutes = models.PositiveIntegerField(blank=True, null=True, help_text='Estimated minutes to complete')
    reminder_time = models.TimeField(blank=True, null=True, help_text='Time to send reminder')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Daily Task'
        verbose_name_plural = 'Daily Tasks'
        ordering = ['reminder_time', 'title']
    
    def __str__(self):
        days = self.get_scheduled_days_display()
        return f"{self.title} ({days})"
    
    def clean(self):
        # Validate scheduled_days contains valid weekday numbers
        if self.scheduled_days:
            valid_days = [0, 1, 2, 3, 4, 5, 6]
            for day in self.scheduled_days:
                if day not in valid_days:
                    raise ValidationError(f'Invalid weekday: {day}. Must be 0-6.')
    
    def get_scheduled_days_display(self):
        """Get human-readable scheduled days"""
        if not self.scheduled_days:
            return 'No days scheduled'
        
        day_names = {0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu', 4: 'Fri', 5: 'Sat', 6: 'Sun'}
        return ', '.join([day_names[day] for day in sorted(self.scheduled_days)])
    
    def is_scheduled_today(self):
        """Check if task is scheduled for today"""
        today = timezone.now().weekday()
        return today in (self.scheduled_days or [])
    
    def get_assignee_names(self):
        """Get comma-separated list of assignee names"""
        return ", ".join([assignee.get_full_name() for assignee in self.assignees.all()])


class DailyTaskCompletion(models.Model):
    daily_task = models.ForeignKey(DailyTask, on_delete=models.CASCADE, related_name='completions')
    user = models.ForeignKey(BotUser, on_delete=models.CASCADE, related_name='daily_task_completions')
    date = models.DateField(default=timezone.now)
    completed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    actual_minutes = models.PositiveIntegerField(blank=True, null=True, help_text='Actual minutes spent')
    
    class Meta:
        verbose_name = 'Daily Task Completion'
        verbose_name_plural = 'Daily Task Completions'
        unique_together = ['daily_task', 'user', 'date']
        ordering = ['-date', '-completed_at']
    
    def __str__(self):
        return f"{self.daily_task.title} - {self.user.get_full_name()} ({self.date})"


# =============================================================================
# ADDITIONAL MODELS FOR KANBAN FUNCTIONALITY
# =============================================================================

class ProjectMember(models.Model):
    """Project team member with role"""
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('editor', 'Editor'),
        ('viewer', 'Viewer'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_members')
    user = models.ForeignKey(BotUser, on_delete=models.CASCADE, related_name='project_memberships')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='viewer')
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['project', 'user']
        verbose_name = 'Project Member'
        verbose_name_plural = 'Project Members'
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.project.name} ({self.role})"


class TaskComment(models.Model):
    """Comments on tasks"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(BotUser, on_delete=models.CASCADE, related_name='task_comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Task Comment'
        verbose_name_plural = 'Task Comments'
    
    def __str__(self):
        return f"Comment by {self.author.get_full_name()} on {self.task.title}"


class TaskAttachment(models.Model):
    """File attachments for tasks"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='task_attachments/')
    filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    uploaded_by = models.ForeignKey(BotUser, on_delete=models.CASCADE, related_name='task_attachments')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Task Attachment'
        verbose_name_plural = 'Task Attachments'
    
    def __str__(self):
        return f"{self.filename} - {self.task.title}"


class TaskDependency(models.Model):
    """Task dependencies - which tasks must be completed before this one"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='dependencies')
    depends_on = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='dependent_tasks')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['task', 'depends_on']
        verbose_name = 'Task Dependency'
        verbose_name_plural = 'Task Dependencies'
    
    def __str__(self):
        return f"{self.task.title} depends on {self.depends_on.title}"


class TaskActivity(models.Model):
    """Activity log for tasks"""
    ACTION_CHOICES = [
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('assigned', 'Assigned'),
        ('status_changed', 'Status Changed'),
        ('priority_changed', 'Priority Changed'),
        ('commented', 'Commented'),
        ('attachment_added', 'Attachment Added'),
        ('completed', 'Completed'),
    ]
    
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='activities')
    user = models.ForeignKey(BotUser, on_delete=models.CASCADE, related_name='task_activities')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Task Activity'
        verbose_name_plural = 'Task Activities'
    
    def __str__(self):
        return f"{self.user.get_full_name()} {self.action} {self.task.title}"


class ProjectLabel(models.Model):
    """Labels/tags for projects"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='labels')
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default='#3498db', help_text='Hex color code')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['project', 'name']
        verbose_name = 'Project Label'
        verbose_name_plural = 'Project Labels'
    
    def __str__(self):
        return f"{self.name} ({self.project.name})"