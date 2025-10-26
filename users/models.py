""" Users models."""

from django.contrib.auth.models import User
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class Prestamista(models.Model):
    """ Prestamista model """
    
    # Identificación
    codigo = models.CharField(
        max_length=20, 
        unique=True,
        blank=True,
        null=True,
        help_text="Código único del prestamista"
    )
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    cedula = models.CharField(max_length=20, unique=True)  # CharField es mejor para cédulas
    
    # Información de contacto
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    direccion = models.TextField(blank=True)
    
    # Configuración de préstamos
    porcentaje_prestamo = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=4.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Porcentaje de interés por defecto (mensual)"
    )
    
    # Estado
    activo = models.BooleanField(default=True)
    
    # Metadata
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Prestamista"
        verbose_name_plural = "Prestamistas"
        ordering = ['apellidos', 'nombres']
    
    def __str__(self):
        return f"{self.nombres} {self.apellidos}"
    
    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}"
    
    @property
    def total_prestado(self):
        """Total de dinero prestado actualmente"""
        from loans.models import Prestamo
        return Prestamo.objects.filter(
            prestamista=self,
            estado__in=['ACTIVO', 'VENCIDO', 'MORA']
        ).aggregate(
            total=models.Sum('saldo_actual')
        )['total'] or Decimal('0')
    
    @property
    def prestamos_activos(self):
        """Cantidad de préstamos activos"""
        from loans.models import Prestamo
        return Prestamo.objects.filter(
            prestamista=self,
            estado='ACTIVO'
        ).count()
    
    def save(self, *args, **kwargs):
        # Generar código automático si no existe
        if not self.codigo:
            ultimo = Prestamista.objects.all().order_by('-id').first()
            if ultimo:
                num = int(ultimo.codigo[2:]) + 1 if ultimo.codigo else 1
            else:
                num = 1
            self.codigo = f"PR{num:03d}"
        super().save(*args, **kwargs)


class Profile(models.Model):
    """ Profile model - Conectado con User y Prestamista """
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    prestamista = models.OneToOneField(
        Prestamista, 
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    
    phone_number = models.CharField(max_length=20, blank=True)
    foto = models.ImageField(
        upload_to='users/profiles/',
        blank=True,
        null=True
    )
    
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Perfil"
        verbose_name_plural = "Perfiles"
    
    def __str__(self):
        return self.user.username