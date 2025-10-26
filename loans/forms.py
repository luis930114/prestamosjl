"""
Formularios del sistema de préstamos
"""

from django import forms
from .models import Cliente, Prestamo, CoDeudor
from payments.models import Pago


class ClienteForm(forms.ModelForm):
    """Formulario para crear/editar clientes"""
    
    class Meta:
        model = Cliente
        fields = [
            'nombre', 'apellido', 'cedula',
            'direccion_principal', 'direccion_secundaria',
            'celular', 'celular_alternativo', 'email',
            'observaciones', 'activo'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del cliente'
            }),
            'apellido': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Apellido del cliente'
            }),
            'cedula': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de cédula'
            }),
            'direccion_principal': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Dirección principal'
            }),
            'direccion_secundaria': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Dirección secundaria (opcional)'
            }),
            'celular': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '3001234567'
            }),
            'celular_alternativo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '3001234567 (opcional)'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com (opcional)'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observaciones adicionales...'
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def clean_cedula(self):
        cedula = self.cleaned_data.get('cedula')
        # Verificar que no exista otra con la misma cédula
        qs = Cliente.objects.filter(cedula=cedula)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Ya existe un cliente con esta cédula')
        return cedula


class CoDeudorForm(forms.ModelForm):
    """Formulario para agregar co-deudor"""
    
    class Meta:
        model = CoDeudor
        fields = ['nombre_completo', 'cedula', 'celular', 'direccion', 'relacion']
        widgets = {
            'nombre_completo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre completo del co-deudor'
            }),
            'cedula': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Cédula'
            }),
            'celular': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Celular'
            }),
            'direccion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Dirección'
            }),
            'relacion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Hermano, Amigo, Esposo/a'
            }),
        }


class PrestamoForm(forms.ModelForm):
    """Formulario para crear/editar préstamos"""
    
    class Meta:
        model = Prestamo
        fields = [
            'prestamista','cliente', 'codeudor', 'valor_inicial',
            'porcentaje_interes', 'tipo_interes',
            'fecha_prestamo', 'fecha_vencimiento', 'plazo_meses',
            'letra_foto', 'letra_foto_reverso',
            'observaciones'
        ]
        widgets = {
            'cliente': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'codeudor': forms.Select(attrs={
                'class': 'form-select'
            }),
            'valor_inicial': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '1000000',
                'step': '1000',
                'min': '0'
            }),
            'porcentaje_interes': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '4.0',
                'step': '0.1',
                'min': '0',
                'max': '100'
            }),
            'tipo_interes': forms.Select(attrs={
                'class': 'form-select'
            }),
            'fecha_prestamo': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'fecha_vencimiento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'plazo_meses': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '12',
                'min': '1'
            }),
            'letra_foto': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'letra_foto_reverso': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observaciones adicionales...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ordenar clientes por apellido
        self.fields['cliente'].queryset = Cliente.objects.filter(activo=True).order_by('apellido', 'nombre')
        
        # Si hay un cliente seleccionado, mostrar solo sus co-deudores
        if 'cliente' in self.data:
            try:
                cliente_id = int(self.data.get('cliente'))
                self.fields['codeudor'].queryset = CoDeudor.objects.filter(cliente_id=cliente_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.cliente:
            self.fields['codeudor'].queryset = self.instance.cliente.codeudores.all()
        else:
            self.fields['codeudor'].queryset = CoDeudor.objects.none()
    
    def clean(self):
        cleaned_data = super().clean()
        valor = cleaned_data.get('valor_inicial')
        
        # Validar monto mínimo
        if valor and valor < 50000:
            raise forms.ValidationError('El monto mínimo del préstamo es $50,000')
        
        return cleaned_data


class PagoRapidoForm(forms.ModelForm):
    """Formulario para registrar pagos rápidamente"""
    
    class Meta:
        model = Pago
        fields = [
            'prestamo', 'valor_total', 'valor_interes', 'valor_capital',
            'metodo_pago', 'fecha_pago', 'referencia', 'observaciones'
        ]
        widgets = {
            'prestamo': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'valor_total': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '100000',
                'step': '1000',
                'min': '0'
            }),
            'valor_interes': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '40000',
                'step': '1000',
                'min': '0'
            }),
            'valor_capital': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '60000',
                'step': '1000',
                'min': '0'
            }),
            'metodo_pago': forms.Select(attrs={
                'class': 'form-select'
            }),
            'fecha_pago': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'referencia': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de referencia (opcional)'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Observaciones...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mostrar solo préstamos activos
        self.fields['prestamo'].queryset = Prestamo.objects.filter(
            estado__in=['ACTIVO', 'VENCIDO', 'MORA']
        ).select_related('cliente').order_by('-fecha_prestamo')
    
    def clean(self):
        cleaned_data = super().clean()
        valor_total = cleaned_data.get('valor_total')
        valor_interes = cleaned_data.get('valor_interes', 0)
        valor_capital = cleaned_data.get('valor_capital', 0)
        prestamo = cleaned_data.get('prestamo')
        
        # Validar que la suma cuadre
        if valor_interes + valor_capital != valor_total:
            # Auto-ajustar si solo se dio el total
            if valor_interes == 0 and valor_capital == 0:
                # Calcular interés del mes y el resto a capital
                if prestamo:
                    interes_mes = prestamo.interes_mensual
                    cleaned_data['valor_interes'] = min(interes_mes, valor_total)
                    cleaned_data['valor_capital'] = valor_total - cleaned_data['valor_interes']
            else:
                raise forms.ValidationError(
                    f'La suma de interés (${valor_interes}) y capital (${valor_capital}) '
                    f'debe ser igual al total (${valor_total})'
                )
        
        # Validar que no exceda el saldo
        if prestamo and valor_capital > prestamo.saldo_actual:
            raise forms.ValidationError(
                f'El pago de capital (${valor_capital}) excede el saldo actual (${prestamo.saldo_actual})'
            )
        
        return cleaned_data


class BuscarClienteForm(forms.Form):
    """Formulario de búsqueda rápida de clientes"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por nombre, cédula o teléfono...',
            'autocomplete': 'off'
        })
    )