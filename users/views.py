"""" Users views. """
#django
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from django.views.generic import DetailView, FormView, UpdateView
from django.urls import reverse, reverse_lazy

#Forms
from users.forms import PrestamistaForm

def login_view(request):
    """ Login view. """
    if request.method == 'GET':
        if request.user.is_authenticated:
            return redirect('inicio')
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('inicio')
        else:
            return render(request, 'users/login.html', {'error': 'invalid username and password'})
    return render(request, 'users/login.html')


def logout_view(request):
    """ Logout a user. """
    logout(request)
    return redirect('login')


class PrestamistaView(FormView):
    """ Users sign up view."""
    template_name = 'users/signup1.html'
    form_class = PrestamistaForm
    success_url = reverse_lazy('users:login')

    def form_valid(self, form):
        """ Save form data. """
        form.save()
        return super().form_valid(form)

