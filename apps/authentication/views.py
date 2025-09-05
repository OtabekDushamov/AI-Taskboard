from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.views.generic import CreateView
from .forms import CustomUserCreationForm


class CustomLoginView(LoginView):
    """Custom login view with beautiful styling"""
    template_name = 'authentication/login.html'
    redirect_authenticated_user = True
    next_page = reverse_lazy('main:home')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Sign In'
        return context

    def form_valid(self, form):
        messages.success(self.request, f'Welcome back, {form.get_user().first_name or form.get_user().username}!')
        return super().form_valid(form)


class CustomRegisterView(CreateView):
    """Custom register view with beautiful styling"""
    form_class = CustomUserCreationForm
    template_name = 'authentication/register.html'
    success_url = reverse_lazy('main:home')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Account'
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.instance
        user = authenticate(
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password1']
        )
        if user:
            login(self.request, user)
            messages.success(self.request, f'Welcome to AI Taskboard, {user.username}!')
        return response


def login_view(request):
    """Login view"""
    if request.user.is_authenticated:
        return redirect('main:home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            next_url = request.GET.get('next', 'main:home')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'authentication/login.html', {
        'title': 'Sign In'
    })


def register_view(request):
    """Register view"""
    if request.user.is_authenticated:
        return redirect('main:home')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            user = authenticate(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password1']
            )
            if user:
                login(request, user)
                messages.success(request, f'Welcome to AI Taskboard, {user.first_name or user.username}!')
                return redirect('main:home')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'authentication/register.html', {
        'form': form,
        'title': 'Create Account'
    })


@login_required
def profile_view(request):
    """User profile view"""
    return render(request, 'authentication/profile.html', {
        'user': request.user
    })