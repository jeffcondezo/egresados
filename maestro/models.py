from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

from .utils import normalizar_escuela, normalize_apellido, normalize_dni


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


class Encuesta(models.Model):
    ESTADO_BORRADOR = 'borrador'
    ESTADO_PUBLICADA = 'publicada'
    ESTADO_CHOICES = [
        (ESTADO_BORRADOR, 'Borrador'),
        (ESTADO_PUBLICADA, 'Publicada'),
    ]
    ALCANCE_TODOS = 'todos'
    ALCANCE_ESCUELA = 'escuela'
    ALCANCE_CHOICES = [
        (ALCANCE_TODOS, 'Todos los egresados'),
        (ALCANCE_ESCUELA, 'Solo una escuela'),
    ]

    titulo = models.CharField('Título', max_length=200)
    descripcion = models.TextField('Descripción', blank=True)
    estado = models.CharField(
        'Estado',
        max_length=20,
        choices=ESTADO_CHOICES,
        default=ESTADO_BORRADOR,
    )
    alcance = models.CharField(
        'Alcance',
        max_length=20,
        choices=ALCANCE_CHOICES,
        default=ALCANCE_TODOS,
    )
    escuela = models.CharField('Escuela', max_length=180, blank=True)
    creado_por = models.ForeignKey(
        Gestor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='encuestas_creadas',
        verbose_name='Creado por',
    )
    creado_en = models.DateTimeField('Creado en', auto_now_add=True)
    actualizado_en = models.DateTimeField('Actualizado en', auto_now=True)

    class Meta:
        verbose_name = 'Encuesta'
        verbose_name_plural = 'Encuestas'
        ordering = ['-actualizado_en']

    def __str__(self) -> str:
        return self.titulo

    @property
    def es_editable(self) -> bool:
        return self.estado == self.ESTADO_BORRADOR

    def puede_publicarse(self) -> bool:
        preguntas = list(self.preguntas.all())
        if not preguntas:
            return False
        for pregunta in preguntas:
            if pregunta.requiere_opciones() and pregunta.opciones.count() < 2:
                return False
            if pregunta.requiere_filas_matriz() and pregunta.filas_matriz.count() < 1:
                return False
            try:
                pregunta.clean()
            except ValidationError:
                return False
        return True

    def visible_para_egresado(self, egresado: 'Egresado') -> bool:
        if self.estado != self.ESTADO_PUBLICADA:
            return False
        if self.alcance == self.ALCANCE_TODOS:
            return True
        if self.alcance != self.ALCANCE_ESCUELA:
            return False
        escuela_encuesta = normalizar_escuela(self.escuela)
        escuela_egresado = normalizar_escuela(egresado.escuela)
        return bool(escuela_encuesta) and escuela_encuesta == escuela_egresado

    @property
    def alcance_display(self) -> str:
        if self.alcance == self.ALCANCE_ESCUELA and self.escuela:
            return f'Escuela: {self.escuela}'
        return 'Todos los egresados'


class Pregunta(models.Model):
    TIPO_SELECCION_UNICA = 'seleccion_unica'
    TIPO_SELECCION_MULTIPLE = 'seleccion_multiple'
    TIPO_TEXTO_LARGO = 'texto_largo'
    TIPO_TEXTO_CORTO = 'texto_corto'
    TIPO_ENTERO = 'entero'
    TIPO_DECIMAL = 'decimal'
    TIPO_MATRIZ_SELECCION = 'matriz_seleccion'
    TIPO_CHOICES = [
        (TIPO_SELECCION_UNICA, 'Selección única (lista desplegable)'),
        (TIPO_SELECCION_MULTIPLE, 'Selección múltiple'),
        (TIPO_MATRIZ_SELECCION, 'Matriz de selección (escala por fila)'),
        (TIPO_TEXTO_LARGO, 'Texto amplio'),
        (TIPO_TEXTO_CORTO, 'Texto limitado'),
        (TIPO_ENTERO, 'Número entero'),
        (TIPO_DECIMAL, 'Número decimal'),
    ]
    TIPOS_SELECCION = {TIPO_SELECCION_UNICA, TIPO_SELECCION_MULTIPLE}
    TIPOS_CON_OPCIONES = TIPOS_SELECCION | {TIPO_MATRIZ_SELECCION}

    encuesta = models.ForeignKey(
        Encuesta,
        on_delete=models.CASCADE,
        related_name='preguntas',
        verbose_name='Encuesta',
    )
    orden = models.PositiveSmallIntegerField('Orden', default=1)
    titulo = models.CharField('Pregunta', max_length=500)
    tipo = models.CharField('Tipo de respuesta', max_length=30, choices=TIPO_CHOICES)
    texto_maximo = models.PositiveSmallIntegerField(
        'Máximo de caracteres',
        default=255,
        blank=True,
        null=True,
    )
    obligatoria = models.BooleanField('Obligatoria', default=True)

    class Meta:
        verbose_name = 'Pregunta'
        verbose_name_plural = 'Preguntas'
        ordering = ['orden', 'pk']

    def __str__(self) -> str:
        return self.titulo

    def requiere_opciones(self) -> bool:
        return self.tipo in self.TIPOS_CON_OPCIONES

    def requiere_filas_matriz(self) -> bool:
        return self.tipo == self.TIPO_MATRIZ_SELECCION

    def clean(self) -> None:
        super().clean()
        if self.tipo == self.TIPO_TEXTO_CORTO:
            if not self.texto_maximo or self.texto_maximo < 1:
                raise ValidationError(
                    {'texto_maximo': 'Indique un máximo de caracteres mayor a cero.'}
                )

    def save(self, *args, **kwargs) -> None:
        if self.tipo != self.TIPO_TEXTO_CORTO:
            self.texto_maximo = None
        elif self.texto_maximo is None:
            self.texto_maximo = 255
        super().save(*args, **kwargs)
        if not self.requiere_opciones():
            self.opciones.all().delete()
        if not self.requiere_filas_matriz():
            self.filas_matriz.all().delete()


class OpcionPregunta(models.Model):
    pregunta = models.ForeignKey(
        Pregunta,
        on_delete=models.CASCADE,
        related_name='opciones',
        verbose_name='Pregunta',
    )
    texto = models.CharField('Opción', max_length=300)
    orden = models.PositiveSmallIntegerField('Orden', default=1)

    class Meta:
        verbose_name = 'Opción'
        verbose_name_plural = 'Opciones'
        ordering = ['orden', 'pk']

    def __str__(self) -> str:
        return self.texto

    def save(self, *args, **kwargs) -> None:
        if self.orden is None:
            self.orden = 1
        super().save(*args, **kwargs)


class FilaMatrizPregunta(models.Model):
    pregunta = models.ForeignKey(
        Pregunta,
        on_delete=models.CASCADE,
        related_name='filas_matriz',
        verbose_name='Pregunta',
    )
    texto = models.CharField('Ítem', max_length=500)
    orden = models.PositiveSmallIntegerField('Orden', default=1)

    class Meta:
        verbose_name = 'Fila de matriz'
        verbose_name_plural = 'Filas de matriz'
        ordering = ['orden', 'pk']

    def __str__(self) -> str:
        return self.texto

    def save(self, *args, **kwargs) -> None:
        if self.orden is None:
            self.orden = 1
        super().save(*args, **kwargs)


class RespuestaEncuesta(models.Model):
    encuesta = models.ForeignKey(
        Encuesta,
        on_delete=models.CASCADE,
        related_name='respuestas',
        verbose_name='Encuesta',
    )
    egresado = models.ForeignKey(
        Egresado,
        on_delete=models.CASCADE,
        related_name='respuestas_encuestas',
        verbose_name='Egresado',
    )
    completada_en = models.DateTimeField('Completada en', auto_now_add=True)

    class Meta:
        verbose_name = 'Respuesta de encuesta'
        verbose_name_plural = 'Respuestas de encuestas'
        constraints = [
            models.UniqueConstraint(
                fields=['encuesta', 'egresado'],
                name='uniq_respuesta_encuesta_egresado',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.egresado} — {self.encuesta}'


class RespuestaPregunta(models.Model):
    respuesta_encuesta = models.ForeignKey(
        RespuestaEncuesta,
        on_delete=models.CASCADE,
        related_name='respuestas_preguntas',
        verbose_name='Respuesta de encuesta',
    )
    pregunta = models.ForeignKey(
        Pregunta,
        on_delete=models.CASCADE,
        related_name='respuestas',
        verbose_name='Pregunta',
    )
    valor_texto = models.TextField('Texto', blank=True)
    valor_entero = models.IntegerField('Entero', blank=True, null=True)
    valor_decimal = models.DecimalField(
        'Decimal',
        max_digits=12,
        decimal_places=4,
        blank=True,
        null=True,
    )
    opcion = models.ForeignKey(
        OpcionPregunta,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='respuestas_seleccion',
        verbose_name='Opción seleccionada',
    )

    class Meta:
        verbose_name = 'Respuesta a pregunta'
        verbose_name_plural = 'Respuestas a preguntas'
        constraints = [
            models.UniqueConstraint(
                fields=['respuesta_encuesta', 'pregunta'],
                name='uniq_respuesta_pregunta',
            ),
        ]


class RespuestaPreguntaOpcion(models.Model):
    respuesta_pregunta = models.ForeignKey(
        RespuestaPregunta,
        on_delete=models.CASCADE,
        related_name='opciones_seleccionadas',
    )
    opcion = models.ForeignKey(
        OpcionPregunta,
        on_delete=models.CASCADE,
        related_name='respuestas_multiples',
    )

    class Meta:
        verbose_name = 'Opción seleccionada (múltiple)'
        verbose_name_plural = 'Opciones seleccionadas (múltiple)'
        constraints = [
            models.UniqueConstraint(
                fields=['respuesta_pregunta', 'opcion'],
                name='uniq_respuesta_pregunta_opcion',
            ),
        ]


class RespuestaMatriz(models.Model):
    respuesta_encuesta = models.ForeignKey(
        RespuestaEncuesta,
        on_delete=models.CASCADE,
        related_name='respuestas_matriz',
        verbose_name='Respuesta de encuesta',
    )
    fila = models.ForeignKey(
        FilaMatrizPregunta,
        on_delete=models.CASCADE,
        related_name='respuestas',
        verbose_name='Fila',
    )
    opcion = models.ForeignKey(
        OpcionPregunta,
        on_delete=models.CASCADE,
        related_name='respuestas_matriz_celda',
        verbose_name='Columna seleccionada',
    )

    class Meta:
        verbose_name = 'Respuesta de matriz'
        verbose_name_plural = 'Respuestas de matriz'
        constraints = [
            models.UniqueConstraint(
                fields=['respuesta_encuesta', 'fila'],
                name='uniq_respuesta_matriz_fila',
            ),
        ]
