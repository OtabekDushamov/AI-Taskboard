from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views

app_name = 'mindmap'

urlpatterns = [
    # Main mindmap view
    path('', login_required(views.mindmap_view), name='mindmap'),
    
    # AJAX endpoints for CRUD operations
    path('api/create-node/', login_required(views.create_node), name='create_node'),
    path('api/update-node/', login_required(views.update_node), name='update_node'),
    path('api/delete-node/', login_required(views.delete_node), name='delete_node'),
    path('api/create-connection/', login_required(views.create_connection), name='create_connection'),
    path('api/delete-connection/', login_required(views.delete_connection), name='delete_connection'),
    path('api/get-data/', login_required(views.get_mindmap_data), name='get_mindmap_data'),
]
