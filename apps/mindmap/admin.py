from django.contrib import admin
from .models import MindmapNode, MindmapConnection, MindmapProject


@admin.register(MindmapProject)
class MindmapProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'creator', 'created_at']
    list_filter = ['created_at', 'creator']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(MindmapNode)
class MindmapNodeAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'priority', 'creator', 'assignee', 'created_at']
    list_filter = ['status', 'priority', 'creator', 'assignee', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['creator', 'assignee', 'project']


@admin.register(MindmapConnection)
class MindmapConnectionAdmin(admin.ModelAdmin):
    list_display = ['from_node', 'to_node', 'connection_type', 'created_at']
    list_filter = ['connection_type', 'created_at']
    search_fields = ['from_node__title', 'to_node__title', 'label']
    readonly_fields = ['created_at']
    raw_id_fields = ['from_node', 'to_node']
