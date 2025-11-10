"""
users/urls.py - Actualizar tus URLs de usuarios
"""

from django.urls import path
from . import views
from users import views as users_views
#from aplicacion import views as aplicacion_views

app_name = 'users'

urlpatterns = [
    path('login/', users_views.login_view, name='login'),
    path('logout/', users_views.logout_view, name='logout'),
    path('registro/', users_views.PrestamistaView.as_view(), name='signup'),
   # path('inicio/', aplicacion_views.inicio_view, name='inicio'),
]