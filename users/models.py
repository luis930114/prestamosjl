""" Users models."""

#Django
from django.contrib.auth.models import User
from django.db import models


class Prestamista(models.Model):
    """ Prestamista model """
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    cedula = models.IntegerField()
    porcentaje_prestamo = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return self.nombres + self.apellidos


class Profile(models.Model):
    """ Profile model.

        Proxy model that extends the base data with other information.
        https://docs.djangoproject.com/en/dev/topics/auth/customizing/#extending-the-existing-user-model
    """
    prestamista = models.OneToOneField(Prestamista, on_delete=models.CASCADE)

    phone_number = models.CharField(max_length=20, blank=True)

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        """ return username."""
        return self.user.username