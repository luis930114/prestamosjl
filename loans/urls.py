"""
loans/urls.py - URLs del módulo de préstamos
"""

from django.urls import path
from . import views

app_name = 'loans'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Clientes
    path('clientes/', views.cliente_lista, name='cliente_lista'),
    path('clientes/crear/', views.cliente_crear, name='cliente_crear'),
    path('clientes/<int:pk>/', views.cliente_detalle, name='cliente_detalle'),
    path('clientes/<int:pk>/editar/', views.cliente_editar, name='cliente_editar'),
    path('clientes/<int:pk>/eliminar/', views.cliente_eliminar, name='cliente_eliminar'),
    
    # Co-deudores
    path('clientes/<int:cliente_pk>/codeudor/crear/', views.codeudor_crear, name='codeudor_crear'),
    
    # Préstamos
    path('prestamos/', views.prestamo_lista, name='prestamo_lista'),
    path('prestamos/crear/', views.prestamo_crear, name='prestamo_crear'),
    path('prestamos/<int:pk>/', views.prestamo_detalle, name='prestamo_detalle'),
    path('prestamos/<int:pk>/editar/', views.prestamo_editar, name='prestamo_editar'),
    path('prestamos/simular/', views.prestamo_simular, name='prestamo_simular'),
    
    # Reportes
    path('reportes/', views.reportes, name='reportes'),
    path('reportes/mora/', views.prestamos_mora, name='prestamos_mora'),
    path('reportes/vencer/', views.prestamos_vencer, name='prestamos_vencer'),
]





