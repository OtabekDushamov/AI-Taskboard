from django.db import models
from django.contrib.auth.models import User
from apps.webapp.models import BotUser


class MindmapNode(models.Model):
    STATUS_CHOICES = [
        ('todo', 'To Do'),
        ('in_progress', 'In Progress'),
        ('review', 'Under Review'),
        ('completed', 'Completed'),
        ('backlog', 'Backlog'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('med', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    # Basic node information
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='todo')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='med')
    
    # User and project relationships
    creator = models.ForeignKey(BotUser, on_delete=models.CASCADE, related_name='created_mindmap_nodes')
    assignee = models.ForeignKey(BotUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_mindmap_nodes')
    project = models.ForeignKey('MindmapProject', on_delete=models.CASCADE, related_name='nodes', null=True, blank=True)
    
    # Visual positioning and layout
    x_position = models.FloatField(default=0)
    y_position = models.FloatField(default=0)
    width = models.IntegerField(default=200)
    height = models.IntegerField(default=80)
    
    # Tags for categorization
    tags = models.JSONField(default=list, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Mindmap Node'
        verbose_name_plural = 'Mindmap Nodes'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
    
    def get_children(self):
        """Get all child nodes connected to this node"""
        return MindmapNode.objects.filter(
            id__in=self.outgoing_connections.values_list('to_node_id', flat=True)
        )
    
    def get_parents(self):
        """Get all parent nodes that connect to this node"""
        return MindmapNode.objects.filter(
            id__in=self.incoming_connections.values_list('from_node_id', flat=True)
        )


class MindmapConnection(models.Model):
    """Represents connections between mindmap nodes"""
    from_node = models.ForeignKey(MindmapNode, on_delete=models.CASCADE, related_name='outgoing_connections')
    to_node = models.ForeignKey(MindmapNode, on_delete=models.CASCADE, related_name='incoming_connections')
    
    # Connection metadata
    connection_type = models.CharField(max_length=50, default='dependency', blank=True)
    label = models.CharField(max_length=100, blank=True, null=True)
    
    # Visual properties
    color = models.CharField(max_length=7, default='#3b82f6', help_text='Hex color code')
    thickness = models.IntegerField(default=2)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Mindmap Connection'
        verbose_name_plural = 'Mindmap Connections'
        unique_together = ['from_node', 'to_node']
    
    def __str__(self):
        return f"{self.from_node.title} → {self.to_node.title}"


class MindmapProject(models.Model):
    """Represents a mindmap project/workspace"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    creator = models.ForeignKey(BotUser, on_delete=models.CASCADE, related_name='created_mindmap_projects')
    
    # Visual settings
    background_color = models.CharField(max_length=7, default='#ffffff', help_text='Hex color code')
    grid_enabled = models.BooleanField(default=True)
    snap_to_grid = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Mindmap Project'
        verbose_name_plural = 'Mindmap Projects'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def get_nodes(self):
        """Get all nodes in this project"""
        return MindmapNode.objects.filter(project=self)
    
    def get_connections(self):
        """Get all connections in this project"""
        node_ids = self.get_nodes().values_list('id', flat=True)
        return MindmapConnection.objects.filter(
            models.Q(from_node_id__in=node_ids) | models.Q(to_node_id__in=node_ids)
        )
