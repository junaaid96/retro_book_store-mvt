from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.contrib import messages
from django.views import View
from django.views.generic import FormView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import login, logout
from .forms import UserRegistrationForm, UserProfileUpdateForm
from django.contrib.auth.mixins import LoginRequiredMixin

# Create your views here.


class UserRegistrationView(FormView):
    template_name = 'register.html'
    form_class = UserRegistrationForm
    success_url = reverse_lazy('profile')

    def form_valid(self, form):
        user = form.save()
        messages.success(self.request, 'Your account has been created!')
        login(self.request, user)
        return super().form_valid(form)

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:  # check if user is logged in
            return redirect('profile')  # redirect to profile page
        return super().dispatch(request, *args, **kwargs)  # otherwise, proceed as normal


class UserLoginView(LoginView):
    template_name = 'login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('home')


class UserLogout(LogoutView):
    template_name = ''

    def get_success_url(self):
        logout(self.request)
        return reverse_lazy('login')


class UserProfileUpdateView(LoginRequiredMixin, View):
    template_name = 'profile_update.html'

    def get(self, request):
        form = UserProfileUpdateForm(instance=request.user)
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = UserProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('profile')
        else:
            print(form.errors)
        return render(request, self.template_name, {'form': form})
