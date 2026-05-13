from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import Egresado

_AUTH_INPUT = 'auth-input'


class GestorAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label='Usuario',
        widget=forms.TextInput(
            attrs={
                'class': _AUTH_INPUT,
                'autofocus': True,
                'autocomplete': 'username',
                'autocapitalize': 'none',
            }
        ),
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(
            attrs={'class': _AUTH_INPUT, 'autocomplete': 'current-password'}
        ),
    )


class EgresadoDNForm(forms.Form):
    dni = forms.CharField(
        label='DNI',
        max_length=20,
        widget=forms.TextInput(
            attrs={
                'class': _AUTH_INPUT,
                'autocomplete': 'off',
                'autofocus': True,
                'inputmode': 'numeric',
                'placeholder': 'Ej. 12345678',
            }
        ),
    )


class EgresadoApellidoForm(forms.Form):
    apellido_paterno = forms.CharField(
        label='Apellido paterno',
        max_length=120,
        widget=forms.TextInput(
            attrs={
                'class': _AUTH_INPUT,
                'autocomplete': 'off',
                'autofocus': True,
                'placeholder': 'Como figura en su registro',
            }
        ),
    )


class EgresadoPerfilForm(forms.ModelForm):
    class Meta:
        model = Egresado
        fields = [
            'apellido_paterno',
            'apellido_materno',
            'nombres',
            'fecha_nacimiento',
            'correo',
            'celular',
            'sexo',
            'codigo',
            'anio_ingreso',
            'anio_egreso',
            'facultad',
            'escuela',
            'departamento_nacimiento',
            'provincia_nacimiento',
            'distrito_nacimiento',
            'direccion',
        ]
        widgets = {
            'apellido_paterno': forms.TextInput(),
            'apellido_materno': forms.TextInput(),
            'nombres': forms.TextInput(),
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}),
            'correo': forms.EmailInput(),
            'celular': forms.TextInput(),
            'sexo': forms.Select(),
            'codigo': forms.TextInput(),
            'anio_ingreso': forms.NumberInput(),
            'anio_egreso': forms.NumberInput(),
            'facultad': forms.TextInput(),
            'escuela': forms.TextInput(),
            'departamento_nacimiento': forms.TextInput(),
            'provincia_nacimiento': forms.TextInput(),
            'distrito_nacimiento': forms.TextInput(),
            'direccion': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'anio_ingreso': 'Año de ingreso',
            'anio_egreso': 'Año de egreso',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                css_class = 'egresado-form__select'
            elif isinstance(field.widget, forms.Textarea):
                css_class = 'egresado-form__textarea'
            else:
                css_class = 'egresado-form__input'
            field.widget.attrs['class'] = css_class
