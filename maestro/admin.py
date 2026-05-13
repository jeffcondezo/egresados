from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Egresado, Gestor


@admin.register(Gestor)
class GestorAdmin(BaseUserAdmin):
    pass


@admin.register(Egresado)
class EgresadoAdmin(admin.ModelAdmin):
    list_display = ('dni', 'apellido_paterno', 'apellido_materno', 'nombres', 'codigo', 'facultad', 'escuela')
    search_fields = (
        'dni',
        'apellido_paterno',
        'apellido_materno',
        'nombres',
        'correo',
        'celular',
        'codigo',
        'facultad',
        'escuela',
    )
    list_filter = ('sexo', 'facultad', 'escuela', 'anio_ingreso', 'anio_egreso')
    ordering = ('apellido_paterno', 'apellido_materno', 'nombres', 'dni')
    fieldsets = (
        (
            'Identificación',
            {
                'fields': (
                    'dni',
                    'codigo',
                    ('apellido_paterno', 'apellido_materno'),
                    'nombres',
                    'sexo',
                    'fecha_nacimiento',
                )
            },
        ),
        (
            'Contacto',
            {
                'fields': (
                    'correo',
                    'celular',
                    'direccion',
                )
            },
        ),
        (
            'Datos académicos',
            {
                'fields': (
                    'anio_ingreso',
                    'anio_egreso',
                    'facultad',
                    'escuela',
                )
            },
        ),
        (
            'Lugar de nacimiento',
            {
                'fields': (
                    'departamento_nacimiento',
                    'provincia_nacimiento',
                    'distrito_nacimiento',
                )
            },
        ),
    )
