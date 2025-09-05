from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = 'authentication'

urlpatterns = [
    # Authentication views
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('register/', views.CustomRegisterView.as_view(), name='register'),
    path('logout/', LogoutView.as_view(next_page='authentication:login'), name='logout'),
    path('profile/', views.profile_view, name='profile'),
]