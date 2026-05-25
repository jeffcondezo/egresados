from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.forms import inlineformset_factory

from .models import Egresado, Encuesta, FilaMatrizPregunta, OpcionPregunta, Pregunta

_FORM_INPUT = 'egresado-form__input'
_FORM_SELECT = 'egresado-form__select'
_FORM_TEXTAREA = 'egresado-form__textarea'

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


class EncuestaForm(forms.ModelForm):
    class Meta:
        model = Encuesta
        fields = ['titulo', 'descripcion']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': _FORM_INPUT}),
            'descripcion': forms.Textarea(attrs={'class': _FORM_TEXTAREA, 'rows': 4}),
        }


class PreguntaForm(forms.ModelForm):
    class Meta:
        model = Pregunta
        fields = ['titulo', 'tipo', 'texto_maximo', 'obligatoria']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': _FORM_INPUT}),
            'tipo': forms.Select(attrs={'class': _FORM_SELECT, 'id': 'id_tipo'}),
            'texto_maximo': forms.NumberInput(attrs={'class': _FORM_INPUT, 'min': 1}),
            'obligatoria': forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tipo = None
        if self.is_bound:
            tipo = self.data.get('tipo')
        elif self.instance.pk:
            tipo = self.instance.tipo
        if tipo != Pregunta.TIPO_TEXTO_CORTO:
            self.fields['texto_maximo'].required = False

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get('tipo')
        if tipo == Pregunta.TIPO_TEXTO_CORTO:
            maximo = cleaned.get('texto_maximo')
            if not maximo or maximo < 1:
                self.add_error(
                    'texto_maximo',
                    'Indique un máximo de caracteres mayor a cero.',
                )
        else:
            cleaned['texto_maximo'] = None
        return cleaned


class OpcionPreguntaForm(forms.ModelForm):
    class Meta:
        model = OpcionPregunta
        fields = ['texto']
        widgets = {
            'texto': forms.TextInput(
                attrs={
                    'class': f'{_FORM_INPUT} encuesta-opcion-texto',
                    'placeholder': 'Texto de la opción',
                    'list': 'opciones-sugerencias',
                    'autocomplete': 'off',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['texto'].required = False

    def clean(self):
        cleaned = super().clean()
        if cleaned and not cleaned.get('DELETE') and not (cleaned.get('texto') or '').strip():
            cleaned['DELETE'] = True
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.orden is None:
            instance.orden = 1
        if commit:
            instance.save()
        return instance


OpcionPreguntaFormSet = inlineformset_factory(
    Pregunta,
    OpcionPregunta,
    form=OpcionPreguntaForm,
    fields=['texto'],
    extra=3,
    can_delete=True,
)


def validar_opciones_formset(formset, tipo_pregunta: str) -> None:
    if tipo_pregunta not in Pregunta.TIPOS_CON_OPCIONES:
        return
    opciones_validas = 0
    for form in formset.forms:
        if not hasattr(form, 'cleaned_data'):
            continue
        if form.cleaned_data.get('DELETE'):
            continue
        texto = (form.cleaned_data.get('texto') or '').strip()
        if texto:
            opciones_validas += 1
    if opciones_validas < 2:
        raise forms.ValidationError(
            'Debe definir al menos 2 columnas de la escala con texto.'
        )


class FilaMatrizPreguntaForm(forms.ModelForm):
    class Meta:
        model = FilaMatrizPregunta
        fields = ['texto']
        widgets = {
            'texto': forms.TextInput(
                attrs={
                    'class': f'{_FORM_INPUT} encuesta-fila-texto',
                    'placeholder': 'Descripción del ítem a calificar',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['texto'].required = False

    def clean(self):
        cleaned = super().clean()
        if cleaned and not cleaned.get('DELETE') and not (cleaned.get('texto') or '').strip():
            cleaned['DELETE'] = True
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.orden is None:
            instance.orden = 1
        if commit:
            instance.save()
        return instance


FilaMatrizPreguntaFormSet = inlineformset_factory(
    Pregunta,
    FilaMatrizPregunta,
    form=FilaMatrizPreguntaForm,
    fields=['texto'],
    extra=3,
    can_delete=True,
)


def listar_escuelas_egresados():
    return sorted(
        Egresado.objects.exclude(escuela='')
        .values_list('escuela', flat=True)
        .distinct(),
        key=lambda s: s.lower(),
    )


class EncuestaPublicarForm(forms.Form):
    ALCANCE_TODOS = Encuesta.ALCANCE_TODOS
    ALCANCE_ESCUELA = Encuesta.ALCANCE_ESCUELA

    alcance = forms.ChoiceField(
        label='¿A quién se dirige la encuesta?',
        choices=Encuesta.ALCANCE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'encuesta-alcance-radio'}),
        initial=ALCANCE_TODOS,
    )
    escuela = forms.ChoiceField(
        label='Escuela',
        required=False,
        widget=forms.Select(attrs={'class': _FORM_SELECT, 'id': 'id_escuela_publicar'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        escuelas = listar_escuelas_egresados()
        self.fields['escuela'].choices = [('', '— Seleccione una escuela —')] + [
            (e, e) for e in escuelas
        ]

    def clean(self):
        cleaned = super().clean()
        alcance = cleaned.get('alcance')
        escuela = (cleaned.get('escuela') or '').strip()
        if alcance == self.ALCANCE_ESCUELA and not escuela:
            self.add_error('escuela', 'Seleccione la escuela para esta encuesta.')
        if alcance == self.ALCANCE_TODOS:
            cleaned['escuela'] = ''
        return cleaned


def validar_filas_matriz_formset(formset, tipo_pregunta: str) -> None:
    if tipo_pregunta != Pregunta.TIPO_MATRIZ_SELECCION:
        return
    filas_validas = 0
    for form in formset.forms:
        if not hasattr(form, 'cleaned_data'):
            continue
        if form.cleaned_data.get('DELETE'):
            continue
        texto = (form.cleaned_data.get('texto') or '').strip()
        if texto:
            filas_validas += 1
    if filas_validas < 1:
        raise forms.ValidationError(
            'Debe definir al menos 1 fila (ítem a calificar) con texto.'
        )
