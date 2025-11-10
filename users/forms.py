"""" Users forms. """

from django import forms
from django.contrib.auth.models import User
from users.models import Prestamista, Profile


class PrestamistaForm(forms.ModelForm):
    """ Prestamista model form - Mejorado """
    
    class Meta:
        model = Prestamista
        fields = (
            'nombres', 'apellidos', 'cedula', 
            'telefono', 'email', 'direccion',
            'porcentaje_prestamo', 'activo'
        )
        widgets = {
            'nombres': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombres'
            }),
            'apellidos': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Apellidos'
            }),
            'cedula': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Cédula'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Teléfono'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email'
            }),
            'direccion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Dirección'
            }),
            'porcentaje_prestamo': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '4.0',
                'step': '0.1'
            }),
        }
    
    def clean_cedula(self):
        cedula = self.cleaned_data.get('cedula')
        if Prestamista.objects.filter(cedula=cedula).exists():
            if not self.instance or self.instance.cedula != cedula:
                raise forms.ValidationError('Esta cédula ya está registrada')
        return cedula


class SignUpForm(forms.Form):
    """ Formulario completo de registro Usuario + Prestamista """
    
    # Datos de usuario
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Usuario'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contraseña'
        })
    )
    password_confirmation = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmar contraseña'
        })
    )
    
    # Datos de prestamista
    nombres = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombres'
        })
    )
    apellidos = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Apellidos'
        })
    )
    cedula = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Cédula'
        })
    )
    telefono = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Teléfono'
        })
    )
    
    def clean(self):
        data = super().clean()
        password = data.get('password')
        password_confirmation = data.get('password_confirmation')
        
        if password != password_confirmation:
            raise forms.ValidationError('Las contraseñas no coinciden')
        
        return data
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Este usuario ya existe')
        return username
    
    def save(self):
        # Crear usuario
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            password=self.cleaned_data['password']
        )
        
        # Crear prestamista
        prestamista = Prestamista.objects.create(
            nombres=self.cleaned_data['nombres'],
            apellidos=self.cleaned_data['apellidos'],
            cedula=self.cleaned_data['cedula'],
            telefono=self.cleaned_data.get('telefono', '')
        )
        
        # Crear perfil
        profile = Profile.objects.create(
            user=user,
            prestamista=prestamista,
            phone_number=self.cleaned_data.get('telefono', '')
        )
        
        return user