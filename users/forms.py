"""" Users forms. """

#django
from django import forms

from users.models import Prestamista

class PrestamistaForm(forms.ModelForm):
    """ Prestamista model form """
    class meta:
        """ forms settings. """
        model = Prestamista
        fields = ('nombres', 'apellidos', 'cedula', 'porcentaje_prestamo')