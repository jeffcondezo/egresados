from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    Egresado,
    Encuesta,
    FilaMatrizPregunta,
    Gestor,
    OpcionPregunta,
    Pregunta,
    RespuestaEncuesta,
    RespuestaMatriz,
    RespuestaPregunta,
)


class OpcionPreguntaInline(admin.TabularInline):
    model = OpcionPregunta
    extra = 1


class FilaMatrizPreguntaInline(admin.TabularInline):
    model = FilaMatrizPregunta
    extra = 1


class PreguntaInline(admin.TabularInline):
    model = Pregunta
    extra = 0
    show_change_link = True


class RespuestaPreguntaInline(admin.TabularInline):
    model = RespuestaPregunta
    extra = 0
    readonly_fields = ('pregunta', 'valor_texto', 'valor_entero', 'valor_decimal', 'opcion')


class RespuestaMatrizInline(admin.TabularInline):
    model = RespuestaMatriz
    extra = 0
    readonly_fields = ('fila', 'opcion')


@admin.register(RespuestaEncuesta)
class RespuestaEncuestaAdmin(admin.ModelAdmin):
    list_display = ('encuesta', 'egresado', 'completada_en')
    list_filter = ('encuesta',)
    search_fields = ('egresado__dni', 'egresado__apellido_paterno', 'encuesta__titulo')
    inlines = [RespuestaPreguntaInline, RespuestaMatrizInline]


@admin.register(Encuesta)
class EncuestaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'estado', 'alcance', 'escuela', 'creado_por', 'actualizado_en')
    list_filter = ('estado', 'alcance')
    search_fields = ('titulo', 'descripcion', 'escuela')
    inlines = [PreguntaInline]


@admin.register(Pregunta)
class PreguntaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'encuesta', 'tipo', 'orden', 'obligatoria')
    list_filter = ('tipo', 'encuesta')
    inlines = [OpcionPreguntaInline, FilaMatrizPreguntaInline]


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
