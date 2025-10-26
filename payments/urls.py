"""
payments/urls.py - URLs del módulo de pagos
"""

from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Pagos
    path('', views.pago_lista, name='pago_lista'),
    path('crear/', views.pago_crear, name='pago_crear'),
    path('<int:pk>/', views.pago_detalle, name='pago_detalle'),
    path('<int:pk>/anular/', views.pago_anular, name='pago_anular'),
    #path('<int:pk>/recibo/', views.pago_recibo_pdf, name='pago_recibo_pdf'),
    
    # Pago rápido
    path('rapido/', views.pago_rapido, name='pago_rapido'),
    
    # Reportes
    path('reporte-diario/', views.reporte_diario, name='reporte_diario'),
]

