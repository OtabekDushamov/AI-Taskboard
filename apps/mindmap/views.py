from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
import json

from .models import MindmapNode, MindmapConnection, MindmapProject
from apps.webapp.models import BotUser


@login_required
def mindmap_view(request):
    """Main mindmap view"""
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
    
    # Get all projects for the user
    projects = MindmapProject.objects.filter(creator=bot_user).order_by('-created_at')
    
    # Get all users for assignee dropdown
    users = BotUser.objects.all()
    
    # Get the last selected project from session
    last_project_id = request.session.get('last_selected_project_id')
    current_project = None
    
    if last_project_id:
        try:
            current_project = MindmapProject.objects.get(id=last_project_id, creator=bot_user)
        except MindmapProject.DoesNotExist:
            # If the project doesn't exist or user doesn't have access, clear the session
            request.session.pop('last_selected_project_id', None)
    
    # If no current project, use the first available project
    if not current_project and projects.exists():
        current_project = projects.first()
        request.session['last_selected_project_id'] = current_project.id
    
    context = {
        'projects': projects,
        'users': users,
        'current_project': current_project,
    }
    
    return render(request, 'mindmap/mindmap.html', context)


@require_http_methods(["POST"])
@csrf_exempt
@login_required
def create_node(request):
    """Create a new mindmap node via AJAX"""
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
    
    try:
        data = json.loads(request.body)
        
        # Get project ID from request data
        project_id = data.get('project_id')
        if not project_id:
            return JsonResponse({'success': False, 'error': 'Project ID required'}, status=400)
        
        try:
            project = MindmapProject.objects.get(id=project_id, creator=bot_user)
        except MindmapProject.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Project not found'}, status=404)
        
        # Create the node
        node = MindmapNode.objects.create(
            title=data.get('title', 'New Node'),
            description=data.get('description', ''),
            status=data.get('status', 'todo'),
            priority=data.get('priority', 'med'),
            x_position=data.get('x', 0),
            y_position=data.get('y', 0),
            width=data.get('width', 200),
            height=data.get('height', 80),
            tags=data.get('tags', []),
            creator=bot_user,
            project=project,
        )
        
        # Set assignee if provided
        if data.get('assignee_id'):
            try:
                assignee = BotUser.objects.get(id=data['assignee_id'])
                node.assignee = assignee
                node.save()
            except BotUser.DoesNotExist:
                pass
        
        return JsonResponse({
            'success': True,
            'node': {
                'id': node.id,
                'title': node.title,
                'description': node.description,
                'status': node.status,
                'priority': node.priority,
                'x': node.x_position,
                'y': node.y_position,
                'width': node.width,
                'height': node.height,
                'tags': node.tags,
                'assignee': {
                    'id': node.assignee.id,
                    'name': node.assignee.get_full_name(),
                    'avatar': 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80'
                } if node.assignee else None,
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
@login_required
def update_node(request):
    """Update an existing mindmap node via AJAX"""
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
    
    try:
        data = json.loads(request.body)
        node_id = data.get('id')
        
        if not node_id:
            return JsonResponse({'success': False, 'error': 'Node ID required'}, status=400)
        
        node = get_object_or_404(MindmapNode, id=node_id)
        
        # Check if user has permission to edit this node
        if node.creator != bot_user:
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
        # Update node fields
        if 'title' in data:
            node.title = data['title']
        if 'description' in data:
            node.description = data['description']
        if 'status' in data:
            node.status = data['status']
        if 'priority' in data:
            node.priority = data['priority']
        if 'x' in data:
            node.x_position = data['x']
        if 'y' in data:
            node.y_position = data['y']
        if 'width' in data:
            node.width = data['width']
        if 'height' in data:
            node.height = data['height']
        if 'tags' in data:
            node.tags = data['tags']
        
        # If this is a main project node and title changed, update project name
        if 'title' in data and node.tags and 'project' in node.tags and 'main' in node.tags:
            if node.project and node.project.name != data['title']:
                node.project.name = data['title']
                node.project.save()
        
        # Update assignee
        if 'assignee_id' in data:
            if data['assignee_id']:
                try:
                    assignee = BotUser.objects.get(id=data['assignee_id'])
                    node.assignee = assignee
                except BotUser.DoesNotExist:
                    node.assignee = None
            else:
                node.assignee = None
        
        node.save()
        
        return JsonResponse({
            'success': True,
            'node': {
                'id': node.id,
                'title': node.title,
                'description': node.description,
                'status': node.status,
                'priority': node.priority,
                'x': node.x_position,
                'y': node.y_position,
                'width': node.width,
                'height': node.height,
                'tags': node.tags,
                'assignee': {
                    'id': node.assignee.id,
                    'name': node.assignee.get_full_name(),
                    'avatar': 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80'
                } if node.assignee else None,
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
@login_required
def delete_node(request):
    """Delete a mindmap node via AJAX"""
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
    
    try:
        data = json.loads(request.body)
        node_id = data.get('id')
        
        if not node_id:
            return JsonResponse({'success': False, 'error': 'Node ID required'}, status=400)
        
        node = get_object_or_404(MindmapNode, id=node_id)
        
        # Check if user has permission to delete this node
        if node.creator != bot_user:
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
        node.delete()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
@login_required
def create_connection(request):
    """Create a connection between nodes via AJAX"""
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
    
    try:
        data = json.loads(request.body)
        from_node_id = data.get('from_node_id')
        to_node_id = data.get('to_node_id')
        
        if not from_node_id or not to_node_id:
            return JsonResponse({'success': False, 'error': 'Both node IDs required'}, status=400)
        
        from_node = get_object_or_404(MindmapNode, id=from_node_id)
        to_node = get_object_or_404(MindmapNode, id=to_node_id)
        
        # Check if user has permission to create connections for these nodes
        # Allow connections if both nodes belong to the same project and user owns that project
        if (from_node.project != to_node.project or 
            not from_node.project or 
            from_node.project.creator != bot_user):
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
        # Create the connection
        connection = MindmapConnection.objects.create(
            from_node=from_node,
            to_node=to_node,
            connection_type=data.get('connection_type', 'dependency'),
            label=data.get('label', ''),
            color=data.get('color', '#3b82f6'),
            thickness=data.get('thickness', 2),
        )
        
        return JsonResponse({
            'success': True,
            'connection': {
                'id': connection.id,
                'from_node_id': connection.from_node.id,
                'to_node_id': connection.to_node.id,
                'connection_type': connection.connection_type,
                'label': connection.label,
                'color': connection.color,
                'thickness': connection.thickness,
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
@login_required
def delete_connection(request):
    """Delete a connection between nodes via AJAX"""
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
    
    try:
        data = json.loads(request.body)
        connection_id = data.get('id')
        
        if not connection_id:
            return JsonResponse({'success': False, 'error': 'Connection ID required'}, status=400)
        
        connection = get_object_or_404(MindmapConnection, id=connection_id)
        
        # Check if user has permission to delete this connection
        if connection.from_node.creator != bot_user or connection.to_node.creator != bot_user:
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
        connection.delete()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["GET"])
@login_required
def get_mindmap_data(request):
    """Get all mindmap data for the current user via AJAX"""
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
    
    try:
        # Get project ID from request parameters
        project_id = request.GET.get('project_id')
        if not project_id:
            return JsonResponse({
                'success': True,
                'nodes': [],
                'connections': [],
                'message': 'No project selected'
            })
        
        try:
            project = MindmapProject.objects.get(id=project_id, creator=bot_user)
        except MindmapProject.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Project not found'}, status=404)
        
        # Get all nodes
        nodes = MindmapNode.objects.filter(project=project).order_by('-created_at')
        nodes_data = []
        
        for node in nodes:
            nodes_data.append({
                'id': str(node.id),
                'title': node.title,
                'description': node.description,
                'status': node.status,
                'priority': node.priority,
                'x': node.x_position,
                'y': node.y_position,
                'width': node.width,
                'height': node.height,
                'tags': node.tags,
                'assignee': {
                    'id': str(node.assignee.id),
                    'name': node.assignee.get_full_name(),
                    'avatar': 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80'
                } if node.assignee else None,
                'children': [],  # Will be populated based on connections
            })
        
        # Get all connections
        connections = MindmapConnection.objects.filter(
            from_node__project=project
        ).select_related('from_node', 'to_node')
        
        connections_data = []
        for connection in connections:
            connections_data.append({
                'id': connection.id,
                'from_node_id': str(connection.from_node.id),
                'to_node_id': str(connection.to_node.id),
                'connection_type': connection.connection_type,
                'label': connection.label,
                'color': connection.color,
                'thickness': connection.thickness,
            })
            
            # Update children arrays
            for node_data in nodes_data:
                if node_data['id'] == str(connection.from_node.id):
                    node_data['children'].append(str(connection.to_node.id))
        
        return JsonResponse({
            'success': True,
            'nodes': nodes_data,
            'connections': connections_data,
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["GET"])
@login_required
def get_projects(request):
    """Get all projects for the current user via AJAX"""
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
    
    try:
        projects = MindmapProject.objects.filter(creator=bot_user).order_by('-created_at')
        projects_data = []
        
        for project in projects:
            node_count = project.get_nodes().count()
            projects_data.append({
                'id': project.id,
                'name': project.name,
                'description': project.description,
                'node_count': node_count,
                'created_at': project.created_at.isoformat(),
                'updated_at': project.updated_at.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'projects': projects_data,
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
@login_required
def create_project(request):
    """Create a new project via AJAX"""
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
    
    try:
        data = json.loads(request.body)
        
        # Create the project
        project = MindmapProject.objects.create(
            name=data.get('name', 'New Project'),
            description=data.get('description', ''),
            creator=bot_user,
        )
        
        # Create a main project node
        MindmapNode.objects.create(
            project=project,
            creator=bot_user,
            title=project.name,
            description=project.description or 'Main project node',
            status='in_progress',
            priority='high',
            x_position=400,
            y_position=300,
            width=250,
            height=100,
            tags=['project', 'main']
        )
        
        return JsonResponse({
            'success': True,
            'project': {
                'id': project.id,
                'name': project.name,
                'description': project.description,
                'node_count': 1,
                'created_at': project.created_at.isoformat(),
                'updated_at': project.updated_at.isoformat(),
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
@login_required
def update_project(request):
    """Update an existing project via AJAX"""
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
    
    try:
        data = json.loads(request.body)
        project_id = data.get('id')
        
        if not project_id:
            return JsonResponse({'success': False, 'error': 'Project ID required'}, status=400)
        
        project = get_object_or_404(MindmapProject, id=project_id)
        
        # Check if user has permission to edit this project
        if project.creator != bot_user:
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
        # Update project fields
        if 'name' in data:
            project.name = data['name']
        if 'description' in data:
            project.description = data['description']
        
        project.save()
        
        # Update the main project node title if name changed
        if 'name' in data:
            main_node = MindmapNode.objects.filter(
                project=project,
                tags__contains=['project', 'main']
            ).first()
            if main_node:
                main_node.title = project.name
                main_node.save()
        
        return JsonResponse({
            'success': True,
            'project': {
                'id': project.id,
                'name': project.name,
                'description': project.description,
                'node_count': project.get_nodes().count(),
                'created_at': project.created_at.isoformat(),
                'updated_at': project.updated_at.isoformat(),
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
@login_required
def delete_project(request):
    """Delete a project via AJAX"""
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
    
    try:
        data = json.loads(request.body)
        project_id = data.get('id')
        
        if not project_id:
            return JsonResponse({'success': False, 'error': 'Project ID required'}, status=400)
        
        project = get_object_or_404(MindmapProject, id=project_id)
        
        # Check if user has permission to delete this project
        if project.creator != bot_user:
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
        project.delete()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
@login_required
def switch_project(request):
    """Switch to a different project via AJAX"""
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
    
    try:
        data = json.loads(request.body)
        project_id = data.get('project_id')
        
        if not project_id:
            return JsonResponse({'success': False, 'error': 'Project ID required'}, status=400)
        
        project = get_object_or_404(MindmapProject, id=project_id)
        
        # Check if user has permission to access this project
        if project.creator != bot_user:
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
        # Save the selected project ID to session
        request.session['last_selected_project_id'] = project_id
        
        # Get all nodes and connections for the project
        nodes = MindmapNode.objects.filter(project=project).order_by('-created_at')
        connections = MindmapConnection.objects.filter(
            from_node__project=project
        ).select_related('from_node', 'to_node')
        
        nodes_data = []
        for node in nodes:
            # Get child node IDs for this node
            child_connections = connections.filter(from_node=node)
            children_ids = [str(conn.to_node.id) for conn in child_connections]
            
            nodes_data.append({
                'id': str(node.id),
                'title': node.title,
                'description': node.description,
                'status': node.status,
                'priority': node.priority,
                'x': node.x_position,
                'y': node.y_position,
                'width': node.width,
                'height': node.height,
                'tags': node.tags,
                'children': children_ids,
                'assignee': {
                    'id': str(node.assignee.id),
                    'name': node.assignee.get_full_name(),
                    'avatar': 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80'
                } if node.assignee else None,
            })
        
        connections_data = []
        for connection in connections:
            connections_data.append({
                'id': connection.id,
                'from_node_id': str(connection.from_node.id),
                'to_node_id': str(connection.to_node.id),
                'connection_type': connection.connection_type,
                'label': connection.label,
                'color': connection.color,
                'thickness': connection.thickness,
            })
        
        return JsonResponse({
            'success': True,
            'project': {
                'id': project.id,
                'name': project.name,
                'description': project.description,
            },
            'nodes': nodes_data,
            'connections': connections_data,
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
