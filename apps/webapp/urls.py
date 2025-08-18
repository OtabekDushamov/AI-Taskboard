from django.urls import path
from . import views

app_name = 'webapp'

urlpatterns = [
    path('auth/', views.auth_view, name='auth'),
    path('logout/', views.logout_view, name='logout'),
]
