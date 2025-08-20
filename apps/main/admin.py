from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Project, Category, Task, DailyTask, DailyTaskCompletion


class CategoryInline(admin.TabularInline):
    model = Category
    extra = 1
    fields = ['name', 'description', 'color']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'creator', 'status', 'priority', 'progress_display', 'member_count', 'start_date', 'end_date', 'created_at')
    list_filter = ('status', 'priority', 'created_at', 'start_date')
    search_fields = ('name', 'description', 'creator__first_name', 'creator__last_name')
    filter_horizontal = ('members',)
    readonly_fields = ('created_at', 'updated_at', 'progress_display')
    date_hierarchy = 'created_at'
    inlines = [CategoryInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'creator')
        }),
        ('Project Settings', {
            'fields': ('status', 'priority', 'start_date', 'end_date')
        }),
        ('Team', {
            'fields': ('members',)
        }),
        ('Progress', {
            'fields': ('progress_display',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def progress_display(self, obj):
        if obj.pk:
            progress = obj.get_progress_percentage()
            color = 'green' if progress >= 80 else 'orange' if progress >= 50 else 'red'
            return format_html(
                '<div style="width: 100px; background-color: #f0f0f0; border-radius: 10px;">'
                '<div style="width: {}%; background-color: {}; height: 20px; border-radius: 10px; text-align: center; color: white; line-height: 20px; font-size: 12px;">'
                '{}%</div></div>',
                progress, color, progress
            )
        return '-'
    progress_display.short_description = 'Progress'
    
    def member_count(self, obj):
        return obj.members.count()
    member_count.short_description = 'Members'


class TaskInline(admin.TabularInline):
    model = Task
    extra = 1
    fields = ['title', 'status', 'priority', 'deadline', 'creator']
    readonly_fields = ['creator']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'color_display', 'task_count_display', 'completed_tasks_display', 'created_at')
    list_filter = ('project__status', 'created_at')
    search_fields = ('name', 'description', 'project__name')
    readonly_fields = ('created_at', 'updated_at', 'task_count_display', 'completed_tasks_display')
    inlines = [TaskInline]
    
    fieldsets = (
        ('Category Information', {
            'fields': ('name', 'description', 'project', 'color')
        }),
        ('Statistics', {
            'fields': ('task_count_display', 'completed_tasks_display'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def color_display(self, obj):
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; border-radius: 50%; display: inline-block;"></div> {}',
            obj.color, obj.color
        )
    color_display.short_description = 'Color'
    
    def task_count_display(self, obj):
        count = obj.get_task_count()
        return f"{count} task{'s' if count != 1 else ''}"
    task_count_display.short_description = 'Total Tasks'
    
    def completed_tasks_display(self, obj):
        completed = obj.get_completed_task_count()
        total = obj.get_task_count()
        if total > 0:
            percentage = round((completed / total) * 100, 1)
            return f"{completed}/{total} ({percentage}%)"
        return "0/0"
    completed_tasks_display.short_description = 'Completed Tasks'


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'status', 'priority', 'creator', 'assignee_list', 'deadline', 'is_overdue_display', 'created_at')
    list_filter = ('status', 'priority', 'category__project', 'deadline', 'created_at')
    search_fields = ('title', 'description', 'notes', 'category__name', 'creator__first_name', 'creator__last_name')
    filter_horizontal = ('assignees',)
    readonly_fields = ('created_at', 'updated_at', 'completed_at', 'is_overdue_display', 'assignee_list')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Task Information', {
            'fields': ('title', 'description', 'notes', 'category')
        }),
        ('Assignment', {
            'fields': ('creator', 'assignees', 'assignee_list')
        }),
        ('Status & Priority', {
            'fields': ('status', 'priority', 'deadline', 'is_overdue_display')
        }),
        ('Time Tracking', {
            'fields': ('estimated_hours', 'actual_hours'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def assignee_list(self, obj):
        assignees = obj.assignees.all()
        if assignees:
            return ", ".join([assignee.get_full_name() for assignee in assignees])
        return "No assignees"
    assignee_list.short_description = 'Assignees'
    
    def is_overdue_display(self, obj):
        if obj.is_overdue():
            return format_html('<span style="color: red; font-weight: bold;">⚠️ OVERDUE</span>')
        elif obj.deadline and obj.status not in ['completed', 'cancelled']:
            return format_html('<span style="color: green;">✓ On time</span>')
        return '-'
    is_overdue_display.short_description = 'Status'


@admin.register(DailyTask)
class DailyTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'creator', 'priority', 'scheduled_days_display', 'reminder_time', 'is_active', 'assignee_list', 'created_at')
    list_filter = ('priority', 'is_active', 'reminder_time', 'created_at')
    search_fields = ('title', 'description', 'notes', 'creator__first_name', 'creator__last_name')
    filter_horizontal = ('assignees',)
    readonly_fields = ('created_at', 'updated_at', 'scheduled_days_display', 'assignee_list', 'is_scheduled_today_display')
    
    fieldsets = (
        ('Task Information', {
            'fields': ('title', 'description', 'notes', 'creator')
        }),
        ('Assignment', {
            'fields': ('assignees', 'assignee_list')
        }),
        ('Schedule', {
            'fields': ('scheduled_days', 'scheduled_days_display', 'reminder_time', 'is_scheduled_today_display')
        }),
        ('Settings', {
            'fields': ('priority', 'estimated_minutes', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def scheduled_days_display(self, obj):
        return obj.get_scheduled_days_display()
    scheduled_days_display.short_description = 'Scheduled Days'
    
    def assignee_list(self, obj):
        assignees = obj.assignees.all()
        if assignees:
            return ", ".join([assignee.get_full_name() for assignee in assignees])
        return "No assignees"
    assignee_list.short_description = 'Assignees'
    
    def is_scheduled_today_display(self, obj):
        if obj.is_scheduled_today():
            return format_html('<span style="color: green; font-weight: bold;">✓ Scheduled Today</span>')
        return format_html('<span style="color: gray;">Not today</span>')
    is_scheduled_today_display.short_description = 'Today'


@admin.register(DailyTaskCompletion)
class DailyTaskCompletionAdmin(admin.ModelAdmin):
    list_display = ('daily_task', 'user', 'date', 'completed_at', 'actual_minutes', 'notes_preview')
    list_filter = ('date', 'completed_at', 'daily_task__priority')
    search_fields = ('daily_task__title', 'user__first_name', 'user__last_name', 'notes')
    readonly_fields = ('completed_at',)
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Completion Information', {
            'fields': ('daily_task', 'user', 'date', 'completed_at')
        }),
        ('Details', {
            'fields': ('actual_minutes', 'notes')
        }),
    )
    
    def notes_preview(self, obj):
        if obj.notes:
            return obj.notes[:50] + "..." if len(obj.notes) > 50 else obj.notes
        return "No notes"
    notes_preview.short_description = 'Notes'


# Customize admin site header and title
admin.site.site_header = "AI Taskboard Administration"
admin.site.site_title = "AI Taskboard Admin"
admin.site.index_title = "Welcome to AI Taskboard Administration"