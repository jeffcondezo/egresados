from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

from .utils import normalize_apellido, normalize_dni


class Gestor(AbstractUser):
    """Usuario interno: acceso con nombre de usuario y contraseña (auth Django)."""

    class Meta:
        verbose_name = 'Gestor'
        verbose_name_plural = 'Gestores'


class Egresado(models.Model):
    """Persona egresada: ingreso con DNI y apellido paterno (sin contraseña Django)."""

    SEXO_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Femenino'),
        ('O', 'Otro'),
    ]

    dni = models.CharField('DNI', max_length=20, unique=True, db_index=True)
    apellido_paterno = models.CharField('Apellido paterno', max_length=120)
    apellido_materno = models.CharField('Apellido materno', max_length=120, blank=True)
    nombres = models.CharField('Nombres', max_length=180, blank=True)
    fecha_nacimiento = models.DateField('Fecha de nacimiento', blank=True, null=True)
    correo = models.EmailField('Correo', blank=True)
    celular = models.CharField('Celular', max_length=20, blank=True)
    sexo = models.CharField('Sexo', max_length=1, choices=SEXO_CHOICES, blank=True)
    codigo = models.CharField('Código', max_length=30, blank=True)
    anio_ingreso = models.PositiveSmallIntegerField('Año de ingreso', blank=True, null=True)
    anio_egreso = models.PositiveSmallIntegerField('Año de egreso', blank=True, null=True)
    facultad = models.CharField('Facultad', max_length=180, blank=True)
    escuela = models.CharField('Escuela', max_length=180, blank=True)
    departamento_nacimiento = models.CharField('Departamento de nacimiento', max_length=120, blank=True)
    provincia_nacimiento = models.CharField('Provincia de nacimiento', max_length=120, blank=True)
    distrito_nacimiento = models.CharField('Distrito de nacimiento', max_length=120, blank=True)
    direccion = models.TextField('Dirección', blank=True)

    class Meta:
        verbose_name = 'Egresado'
        verbose_name_plural = 'Egresados'
        ordering = ['apellido_paterno', 'apellido_materno', 'nombres', 'dni']

    def __str__(self) -> str:
        return f'{self.nombre_completo} ({self.dni})'

    @property
    def nombre_completo(self) -> str:
        partes = [self.apellido_paterno, self.apellido_materno, self.nombres]
        return ' '.join(parte for parte in partes if parte).strip() or self.dni

    def clean(self) -> None:
        super().clean()
        nd = normalize_dni(self.dni)
        if not nd:
            raise ValidationError({'dni': 'Ingrese un DNI válido.'})
        if not (self.apellido_paterno or '').strip():
            raise ValidationError({'apellido_paterno': 'El apellido paterno es obligatorio.'})

    def save(self, *args, **kwargs) -> None:
        self.dni = normalize_dni(self.dni)
        super().save(*args, **kwargs)

    def coincide_apellido_paterno(self, raw_apellido: str) -> bool:
        return normalize_apellido(self.apellido_paterno) == normalize_apellido(raw_apellido)
