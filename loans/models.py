"""
Modelos de préstamos - Integrado con users.Prestamista
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

# Importar Prestamista desde users
from users.models import Prestamista


class Cliente(models.Model):
    """Cliente que recibe el préstamo"""
    
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    cedula = models.CharField(max_length=20, unique=True)
    direccion_principal = models.TextField()
    direccion_secundaria = models.TextField(blank=True)
    celular = models.CharField(max_length=15)
    celular_alternativo = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    
    observaciones = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['apellido', 'nombre']
    
    def __str__(self):
        return f"{self.nombre} {self.apellido} - {self.cedula}"
    
    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"


class CoDeudor(models.Model):
    """Co-deudor opcional para un cliente"""
    
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name='codeudores'
    )
    nombre_completo = models.CharField(max_length=200)
    cedula = models.CharField(max_length=20)
    celular = models.CharField(max_length=15)
    direccion = models.TextField()
    relacion = models.CharField(max_length=200)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.nombre_completo} (Co-deudor de {self.cliente.nombre_completo})"


class Prestamo(models.Model):
    """Préstamo realizado a un cliente"""
    
    TIPO_INTERES_CHOICES = [
        ('ANTICIPADO', 'Anticipado'),
        ('VENCIDO', 'Vencido'),
    ]
    
    ESTADO_CHOICES = [
        ('ACTIVO', 'Activo'),
        ('PAGADO', 'Pagado'),
        ('VENCIDO', 'Vencido'),
        ('MORA', 'En Mora'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    # Identificación
    codigo = models.CharField(max_length=20, unique=True, editable=False, blank=True, null=True)

    
    # Relaciones - AQUÍ USAMOS TU PRESTAMISTA
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='prestamos')
    prestamista = models.ForeignKey(Prestamista, on_delete=models.PROTECT, related_name='prestamos')
    codeudor = models.ForeignKey(CoDeudor, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Montos
    valor_inicial = models.DecimalField(max_digits=12, decimal_places=2)
    saldo_actual = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Intereses
    porcentaje_interes = models.DecimalField(max_digits=5, decimal_places=2)
    tipo_interes = models.CharField(max_length=11, choices=TIPO_INTERES_CHOICES, default='VENCIDO')
    
    # Fechas
    fecha_prestamo = models.DateField()
    fecha_vencimiento = models.DateField(null=True, blank=True)
    plazo_meses = models.PositiveIntegerField(null=True, blank=True)
    
    # NUEVO: Foto de la letra/pagaré
    letra_foto = models.ImageField(
        upload_to='prestamos/letras/%Y/%m/',
        blank=True,
        null=True,
        help_text="Foto de la letra o pagaré firmado"
    )
    letra_foto_reverso = models.ImageField(
        upload_to='prestamos/letras/%Y/%m/',
        blank=True,
        null=True,
        help_text="Foto del reverso de la letra (opcional)"
    )
    
    # Estado
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='ACTIVO')
    observaciones = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    fecha_pago_completo = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Préstamo"
        verbose_name_plural = "Préstamos"
        ordering = ['-fecha_prestamo']
    
    def __str__(self):
        return f"{self.codigo} - {self.cliente.nombre_completo} - ${self.saldo_actual}"
    
    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self.generar_codigo()
        if not self.pk:
            self.saldo_actual = self.valor_inicial
        super().save(*args, **kwargs)
    
    def generar_codigo(self):
        ultimo = Prestamo.objects.all().order_by('-id').first()
        if ultimo and ultimo.codigo:
            try:
                num = int(ultimo.codigo.replace('PR', '')) + 1
            except:
                num = 1
        else:
            num = 1
        return f"PR{num:06d}"
    
    @property
    def interes_mensual(self):
        return (self.saldo_actual * self.porcentaje_interes / 100).quantize(Decimal('0.01'))