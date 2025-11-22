"""
Modelos para el sistema de pagos
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from loans.models import Prestamo


class Pago(models.Model):
    """Registro de pago realizado a un préstamo"""
    
    TIPO_PAGO_CHOICES = [
        ('INTERES', 'Solo Interés'),
        ('CAPITAL', 'Solo Capital'),
        ('MIXTO', 'Interés + Capital'),
        ('COMPLETO', 'Pago Completo'),
    ]
    
    METODO_PAGO_CHOICES = [
        ('EFECTIVO', 'Efectivo'),
        ('TRANSFERENCIA', 'Transferencia'),
        ('CONSIGNACION', 'Consignación'),
        ('CHEQUE', 'Cheque'),
        ('OTRO', 'Otro'),
    ]
    
    # Identificación
    recibo_numero = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text="Número de recibo autogenerado"
    )
    
    # Relación
    prestamo = models.ForeignKey(
        Prestamo,
        on_delete=models.PROTECT,
        related_name='pagos'
    )
    
    # Montos
    valor_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Valor total del pago"
    )
    valor_interes = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Valor destinado a intereses"
    )
    valor_capital = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Valor destinado a capital"
    )
    
    # Información del pago
    tipo = models.CharField(
        max_length=10,
        choices=TIPO_PAGO_CHOICES,
        default='MIXTO'
    )
    metodo_pago = models.CharField(
        max_length=15,
        choices=METODO_PAGO_CHOICES,
        default='EFECTIVO'
    )
    fecha_pago = models.DateField(default=timezone.now)
    
    # Información adicional
    referencia = models.CharField(
        max_length=100,
        blank=True,
        help_text="Número de referencia de transferencia/consignación"
    )
    observaciones = models.TextField(blank=True)
    comprobante = models.FileField(
        upload_to='pagos/comprobantes/',
        blank=True,
        null=True,
        help_text="Comprobante de pago escaneado"
    )
    
    # Control
    recibo_impreso = models.BooleanField(default=False)
    anulado = models.BooleanField(default=False)
    fecha_anulacion = models.DateTimeField(null=True, blank=True)
    motivo_anulacion = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='pagos_registrados'
    )
    
    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        ordering = ['-fecha_pago', '-created_at']
        indexes = [
            models.Index(fields=['recibo_numero']),
            models.Index(fields=['fecha_pago']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['prestamo', 'anulado']),
        ]
    
    def __str__(self):
        return f"{self.recibo_numero} - {self.prestamo.codigo} - ${self.valor_total}"
    
    def save(self, *args, **kwargs):
        # Generar número de recibo si es nuevo
        if not self.recibo_numero:
            self.recibo_numero = self.generar_recibo()
        
        # Validar que la suma de interés y capital no exceda el total
        if self.valor_interes + self.valor_capital != self.valor_total:
            # Auto-ajustar si no están definidos
            if self.valor_interes == 0 and self.valor_capital == 0:
                # Por defecto, todo va a capital si no se especifica
                self.valor_capital = self.valor_total
            elif self.valor_interes > 0 and self.valor_capital == 0:
                self.valor_capital = self.valor_total - self.valor_interes
            elif self.valor_capital > 0 and self.valor_interes == 0:
                self.valor_interes = self.valor_total - self.valor_capital
        
        # Determinar tipo de pago automáticamente
        if self.valor_interes > 0 and self.valor_capital > 0:
            self.tipo = 'MIXTO'
        elif self.valor_interes > 0 and self.valor_capital == 0:
            self.tipo = 'INTERES'
        elif self.valor_capital > 0 and self.valor_interes == 0:
            self.tipo = 'CAPITAL'
        
        #is_new = not self.pk
        
        super().save(*args, **kwargs)
        
        # Aplicar el pago al préstamo (solo si no está anulado y es nuevo)
        #if is_new and not self.anulado:
        #    self.prestamo.aplicar_pago(self.valor_interes, self.valor_capital)
    
    def generar_recibo(self):
        """Genera un número único de recibo"""
        from django.conf import settings
        prefix = getattr(settings, 'LOAN_SETTINGS', {}).get('RECEIPT_PREFIX', 'REC')
        
        # Obtener el último recibo
        ultimo_pago = Pago.objects.all().order_by('-id').first()
        if ultimo_pago and ultimo_pago.recibo_numero:
            try:
                ultimo_num = int(ultimo_pago.recibo_numero.replace(prefix, ''))
                nuevo_num = ultimo_num + 1
            except ValueError:
                nuevo_num = 1
        else:
            nuevo_num = 1
        
        return f"{prefix}{nuevo_num:08d}"
    
    def anular(self, motivo, usuario=None):
        """Anula el pago y revierte el saldo del préstamo"""
        if self.anulado:
            return False
        
        self.anulado = True
        self.fecha_anulacion = timezone.now()
        self.motivo_anulacion = motivo
        self.save()
        
        # Revertir el pago en el préstamo
        self.prestamo.saldo_actual += self.valor_capital
        self.prestamo.actualizar_estado()
        
        return True
    
    @property
    def dias_desde_pago(self):
        """Días transcurridos desde el pago"""
        return (timezone.now().date() - self.fecha_pago).days
    

class PlanPago(models.Model):
    """Plan de pagos proyectado para un préstamo"""
    
    prestamo = models.ForeignKey(
        Prestamo,
        on_delete=models.CASCADE,
        related_name='plan_pagos'
    )
    numero_cuota = models.PositiveIntegerField()
    fecha_vencimiento = models.DateField()
    
    valor_cuota = models.DecimalField(max_digits=12, decimal_places=2)
    valor_interes = models.DecimalField(max_digits=12, decimal_places=2)
    valor_capital = models.DecimalField(max_digits=12, decimal_places=2)
    saldo_pendiente = models.DecimalField(max_digits=12, decimal_places=2)
    
    pagado = models.BooleanField(default=False)
    fecha_pago = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Plan de Pago"
        verbose_name_plural = "Planes de Pago"
        ordering = ['prestamo', 'numero_cuota']
        unique_together = ['prestamo', 'numero_cuota']
    
    def __str__(self):
        return f"{self.prestamo.codigo} - Cuota {self.numero_cuota}"
    
    @property
    def esta_vencido(self):
        """Verifica si la cuota está vencida"""
        if not self.pagado:
            return timezone.now().date() > self.fecha_vencimiento
        return False
