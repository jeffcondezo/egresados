from functools import wraps
from typing import Optional

from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Prefetch
from django.forms import ValidationError as FormValidationError
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from .encuesta_respuestas import mapa_respuestas_guardadas, validar_y_guardar_respuestas
from .forms import (
    EgresadoApellidoForm,
    EgresadoDNForm,
    EgresadoPerfilForm,
    EncuestaForm,
    EncuestaPublicarForm,
    FilaMatrizPreguntaFormSet,
    GestorAuthenticationForm,
    OpcionPreguntaFormSet,
    PreguntaForm,
    validar_filas_matriz_formset,
    validar_opciones_formset,
)
from .encuesta_opciones_plantillas import OPCIONES_PLANTILLAS, sugerencias_autocompletado
from .models import (
    Egresado,
    Encuesta,
    FilaMatrizPregunta,
    OpcionPregunta,
    Pregunta,
    RespuestaEncuesta,
)
from .utils import normalize_dni


def _contexto_pregunta_form(
    encuesta: Encuesta,
    form: PreguntaForm,
    formset: OpcionPreguntaFormSet,
    filas_formset: FilaMatrizPreguntaFormSet,
    *,
    pregunta: Optional[Pregunta] = None,
    opciones_error: Optional[str] = None,
    filas_error: Optional[str] = None,
) -> dict:
    return {
        'dashboard_section': 'encuestas',
        'encuesta': encuesta,
        'form': form,
        'formset': formset,
        'filas_formset': filas_formset,
        'pregunta': pregunta,
        'es_edicion': bool(pregunta),
        'opciones_error': opciones_error,
        'filas_error': filas_error,
        'opciones_plantillas': OPCIONES_PLANTILLAS,
        'opciones_sugerencias': sugerencias_autocompletado(),
    }

SESSION_EGRESADO_DNI = 'egresado_ingreso_dni'
SESSION_EGRESADO_ID = 'egresado_id'


class GestorLoginView(LoginView):
    template_name = 'maestro/gestor_login.html'
    authentication_form = GestorAuthenticationForm
    redirect_authenticated_user = True


class GestorLogoutView(LogoutView):
    next_page = reverse_lazy('maestro:egresado_ingreso_dni')


def gestor_login_required(view_func):
    @wraps(view_func)
    def _wrapped(request: HttpRequest, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('maestro:gestor_login')
        return view_func(request, *args, **kwargs)

    return _wrapped


@gestor_login_required
def gestor_panel(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        'maestro/gestor_panel.html',
        {'dashboard_section': 'inicio'},
    )


@gestor_login_required
def gestor_consulta_alumnos(request: HttpRequest) -> HttpResponse:
    dni = normalize_dni(request.GET.get('dni', ''))
    codigo = (request.GET.get('codigo', '') or '').strip()

    filtros_aplicados = bool(dni or codigo)
    alumnos = Egresado.objects.none()

    if filtros_aplicados:
        alumnos = Egresado.objects.all()
        if dni:
            alumnos = alumnos.filter(dni=dni)
        if codigo:
            alumnos = alumnos.filter(codigo__icontains=codigo)

    return render(
        request,
        'maestro/gestor_consulta_alumnos.html',
        {
            'dashboard_section': 'consulta_alumnos',
            'alumnos': alumnos,
            'filtros_aplicados': filtros_aplicados,
            'dni_buscado': dni,
            'codigo_buscado': codigo,
        },
    )


def _get_encuesta_gestor(pk: int) -> Encuesta:
    return get_object_or_404(Encuesta, pk=pk)


def _get_pregunta_encuesta(encuesta_pk: int, pregunta_pk: int) -> Pregunta:
    encuesta = _get_encuesta_gestor(encuesta_pk)
    return get_object_or_404(encuesta.preguntas, pk=pregunta_pk)


def _redirect_si_no_editable(request: HttpRequest, encuesta: Encuesta) -> Optional[HttpResponse]:
    if encuesta.es_editable:
        return None
    messages.warning(
        request,
        'Esta encuesta está publicada y no puede modificarse.',
    )
    return redirect('maestro:gestor_encuesta_detalle', pk=encuesta.pk)


def _asignar_orden_opciones(pregunta_guardada: Pregunta) -> None:
    orden = 1
    for opcion in pregunta_guardada.opciones.order_by('pk'):
        if (opcion.texto or '').strip():
            opcion.orden = orden
            opcion.save(update_fields=['orden'])
            orden += 1


def _asignar_orden_filas_matriz(pregunta_guardada: Pregunta) -> None:
    orden = 1
    for fila in pregunta_guardada.filas_matriz.order_by('pk'):
        if (fila.texto or '').strip():
            fila.orden = orden
            fila.save(update_fields=['orden'])
            orden += 1


def _guardar_pregunta_completa(
    request: HttpRequest,
    encuesta: Encuesta,
    pregunta: Optional[Pregunta],
) -> HttpResponse:
    instance = pregunta or Pregunta(encuesta=encuesta)
    form = PreguntaForm(request.POST, instance=instance)
    opciones_error = None
    filas_error = None
    formset = None
    filas_formset = None

    if form.is_valid():
        try:
            with transaction.atomic():
                pregunta_guardada = form.save(commit=False)
                if not pregunta_guardada.pk:
                    ultimo = (
                        encuesta.preguntas.order_by('-orden')
                        .values_list('orden', flat=True)
                        .first()
                    )
                    pregunta_guardada.orden = (ultimo or 0) + 1
                pregunta_guardada.encuesta = encuesta
                pregunta_guardada.save()

                tipo = form.cleaned_data['tipo']

                if pregunta_guardada.requiere_opciones():
                    formset = OpcionPreguntaFormSet(request.POST, instance=pregunta_guardada)
                    if not formset.is_valid():
                        raise FormValidationError('Revise las columnas de la escala ingresadas.')
                    validar_opciones_formset(formset, tipo)
                    formset.save()
                    _asignar_orden_opciones(pregunta_guardada)
                else:
                    formset = OpcionPreguntaFormSet(instance=pregunta_guardada)

                if pregunta_guardada.requiere_filas_matriz():
                    filas_formset = FilaMatrizPreguntaFormSet(
                        request.POST, instance=pregunta_guardada
                    )
                    if not filas_formset.is_valid():
                        raise FormValidationError('Revise las filas de la matriz ingresadas.')
                    validar_filas_matriz_formset(filas_formset, tipo)
                    filas_formset.save()
                    _asignar_orden_filas_matriz(pregunta_guardada)
                else:
                    filas_formset = FilaMatrizPreguntaFormSet(instance=pregunta_guardada)
        except FormValidationError as exc:
            mensaje = exc.messages[0]
            if 'fila' in mensaje.lower() or 'ítem' in mensaje.lower():
                filas_error = mensaje
            else:
                opciones_error = mensaje
            instancia_formset = pregunta if pregunta else None
            formset = OpcionPreguntaFormSet(request.POST, instance=instancia_formset)
            filas_formset = FilaMatrizPreguntaFormSet(request.POST, instance=instancia_formset)
        else:
            if pregunta:
                messages.success(request, 'Pregunta actualizada correctamente.')
            else:
                messages.success(request, 'Pregunta agregada correctamente.')
            return redirect('maestro:gestor_encuesta_editar', pk=encuesta.pk)
    else:
        instancia = instance if instance.pk else None
        formset = OpcionPreguntaFormSet(request.POST, instance=instancia)
        filas_formset = FilaMatrizPreguntaFormSet(request.POST, instance=instancia)
        formset.is_valid()
        filas_formset.is_valid()

    if formset is None:
        formset = OpcionPreguntaFormSet(instance=instance if instance.pk else None)
    if filas_formset is None:
        filas_formset = FilaMatrizPreguntaFormSet(instance=instance if instance.pk else None)

    return render(
        request,
        'maestro/gestor_pregunta_form.html',
        _contexto_pregunta_form(
            encuesta,
            form,
            formset,
            filas_formset,
            pregunta=pregunta,
            opciones_error=opciones_error,
            filas_error=filas_error,
        ),
    )


def _guardar_pregunta_con_opciones(
    request: HttpRequest,
    encuesta: Encuesta,
    pregunta: Optional[Pregunta],
) -> HttpResponse:
    return _guardar_pregunta_completa(request, encuesta, pregunta)


@gestor_login_required
def gestor_encuestas_lista(request: HttpRequest) -> HttpResponse:
    encuestas = Encuesta.objects.annotate(num_preguntas=Count('preguntas'))
    return render(
        request,
        'maestro/gestor_encuestas_lista.html',
        {
            'dashboard_section': 'encuestas',
            'encuestas': encuestas,
        },
    )


@gestor_login_required
def gestor_encuesta_crear(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = EncuestaForm(request.POST)
        if form.is_valid():
            encuesta = form.save(commit=False)
            encuesta.creado_por = request.user
            encuesta.save()
            messages.success(request, 'Encuesta creada. Agregue las preguntas.')
            return redirect('maestro:gestor_encuesta_editar', pk=encuesta.pk)
    else:
        form = EncuestaForm()

    return render(
        request,
        'maestro/gestor_encuesta_form.html',
        {
            'dashboard_section': 'encuestas',
            'form': form,
            'es_edicion': False,
        },
    )


@gestor_login_required
def gestor_encuesta_detalle(request: HttpRequest, pk: int) -> HttpResponse:
    encuesta = _get_encuesta_gestor(pk)
    preguntas = encuesta.preguntas.prefetch_related(
        Prefetch(
            'opciones',
            queryset=OpcionPregunta.objects.order_by('orden', 'pk'),
        ),
        Prefetch(
            'filas_matriz',
            queryset=FilaMatrizPregunta.objects.order_by('orden', 'pk'),
        ),
    )
    return render(
        request,
        'maestro/gestor_encuesta_detalle.html',
        {
            'dashboard_section': 'encuestas',
            'encuesta': encuesta,
            'preguntas': preguntas,
        },
    )


@gestor_login_required
def gestor_encuesta_editar(request: HttpRequest, pk: int) -> HttpResponse:
    encuesta = _get_encuesta_gestor(pk)
    bloqueo = _redirect_si_no_editable(request, encuesta)
    if bloqueo:
        return bloqueo

    if request.method == 'POST':
        form = EncuestaForm(request.POST, instance=encuesta)
        if form.is_valid():
            form.save()
            messages.success(request, 'Datos de la encuesta actualizados.')
            return redirect('maestro:gestor_encuesta_editar', pk=encuesta.pk)
    else:
        form = EncuestaForm(instance=encuesta)

    preguntas = encuesta.preguntas.prefetch_related('opciones', 'filas_matriz')
    return render(
        request,
        'maestro/gestor_encuesta_editar.html',
        {
            'dashboard_section': 'encuestas',
            'encuesta': encuesta,
            'form': form,
            'preguntas': preguntas,
        },
    )


@gestor_login_required
def gestor_encuesta_publicar(request: HttpRequest, pk: int) -> HttpResponse:
    encuesta = _get_encuesta_gestor(pk)
    bloqueo = _redirect_si_no_editable(request, encuesta)
    if bloqueo:
        return bloqueo

    if not encuesta.puede_publicarse():
        messages.error(
            request,
            'No se puede publicar: agregue al menos una pregunta válida '
            '(las de selección requieren 2 opciones o más).',
        )
        return redirect('maestro:gestor_encuesta_editar', pk=encuesta.pk)

    preguntas = encuesta.preguntas.prefetch_related('opciones', 'filas_matriz')

    if request.method == 'POST':
        form = EncuestaPublicarForm(request.POST)
        if form.is_valid():
            encuesta.alcance = form.cleaned_data['alcance']
            encuesta.escuela = form.cleaned_data.get('escuela') or ''
            encuesta.estado = Encuesta.ESTADO_PUBLICADA
            encuesta.save(update_fields=['alcance', 'escuela', 'estado', 'actualizado_en'])
            messages.success(request, 'Encuesta publicada correctamente.')
            return redirect('maestro:gestor_encuesta_detalle', pk=encuesta.pk)
    else:
        form = EncuestaPublicarForm(
            initial={
                'alcance': encuesta.alcance or Encuesta.ALCANCE_TODOS,
                'escuela': encuesta.escuela,
            }
        )

    return render(
        request,
        'maestro/gestor_encuesta_publicar.html',
        {
            'dashboard_section': 'encuestas',
            'encuesta': encuesta,
            'preguntas': preguntas,
            'form': form,
        },
    )


@gestor_login_required
def gestor_pregunta_crear(request: HttpRequest, pk: int) -> HttpResponse:
    encuesta = _get_encuesta_gestor(pk)
    bloqueo = _redirect_si_no_editable(request, encuesta)
    if bloqueo:
        return bloqueo

    if request.method == 'POST':
        return _guardar_pregunta_con_opciones(request, encuesta, None)

    form = PreguntaForm()
    formset = OpcionPreguntaFormSet()
    filas_formset = FilaMatrizPreguntaFormSet()
    return render(
        request,
        'maestro/gestor_pregunta_form.html',
        _contexto_pregunta_form(encuesta, form, formset, filas_formset),
    )


@gestor_login_required
def gestor_pregunta_editar(request: HttpRequest, pk: int, pregunta_pk: int) -> HttpResponse:
    encuesta = _get_encuesta_gestor(pk)
    bloqueo = _redirect_si_no_editable(request, encuesta)
    if bloqueo:
        return bloqueo

    pregunta = _get_pregunta_encuesta(pk, pregunta_pk)

    if request.method == 'POST':
        return _guardar_pregunta_con_opciones(request, encuesta, pregunta)

    form = PreguntaForm(instance=pregunta)
    formset = OpcionPreguntaFormSet(instance=pregunta)
    filas_formset = FilaMatrizPreguntaFormSet(instance=pregunta)
    return render(
        request,
        'maestro/gestor_pregunta_form.html',
        _contexto_pregunta_form(encuesta, form, formset, filas_formset, pregunta=pregunta),
    )


@gestor_login_required
@require_POST
def gestor_pregunta_eliminar(request: HttpRequest, pk: int, pregunta_pk: int) -> HttpResponse:
    encuesta = _get_encuesta_gestor(pk)
    bloqueo = _redirect_si_no_editable(request, encuesta)
    if bloqueo:
        return bloqueo

    pregunta = _get_pregunta_encuesta(pk, pregunta_pk)
    pregunta.delete()
    messages.success(request, 'Pregunta eliminada.')
    return redirect('maestro:gestor_encuesta_editar', pk=encuesta.pk)


def egresado_ingreso_dni(request: HttpRequest) -> HttpResponse:
    if request.session.get(SESSION_EGRESADO_ID):
        return redirect('maestro:egresado_panel')

    if request.method == 'POST':
        form = EgresadoDNForm(request.POST)
        if form.is_valid():
            nd = normalize_dni(form.cleaned_data['dni'])
            if Egresado.objects.filter(dni=nd).exists():
                request.session[SESSION_EGRESADO_DNI] = nd
                return redirect('maestro:egresado_ingreso_apellido')
            messages.error(request, 'No hay un egresado registrado con ese DNI.')
    else:
        form = EgresadoDNForm()

    return render(request, 'maestro/egresado_ingreso_dni.html', {'form': form})


def egresado_ingreso_apellido(request: HttpRequest) -> HttpResponse:
    if request.session.get(SESSION_EGRESADO_ID):
        return redirect('maestro:egresado_panel')

    dni = request.session.get(SESSION_EGRESADO_DNI)
    if not dni:
        messages.warning(request, 'Primero ingrese su DNI.')
        return redirect('maestro:egresado_ingreso_dni')

    try:
        egresado = Egresado.objects.get(dni=dni)
    except Egresado.DoesNotExist:
        request.session.pop(SESSION_EGRESADO_DNI, None)
        messages.error(request, 'No hay un egresado registrado con ese DNI.')
        return redirect('maestro:egresado_ingreso_dni')

    if request.method == 'POST':
        form = EgresadoApellidoForm(request.POST)
        if form.is_valid():
            if egresado.coincide_apellido_paterno(form.cleaned_data['apellido_paterno']):
                request.session.cycle_key()
                request.session[SESSION_EGRESADO_ID] = egresado.pk
                request.session.pop(SESSION_EGRESADO_DNI, None)
                messages.success(request, 'Bienvenido.')
                return redirect('maestro:egresado_panel')
            messages.error(request, 'El apellido paterno no coincide con nuestros registros.')
    else:
        form = EgresadoApellidoForm()

    return render(
        request,
        'maestro/egresado_ingreso_apellido.html',
        {'form': form, 'dni_mostrado': dni},
    )


def egresado_logout(request: HttpRequest) -> HttpResponse:
    request.session.pop(SESSION_EGRESADO_ID, None)
    request.session.pop(SESSION_EGRESADO_DNI, None)
    messages.info(request, 'Ha cerrado sesión como egresado.')
    return redirect('maestro:egresado_ingreso_dni')


def _egresado_desde_sesion(request: HttpRequest) -> Optional[Egresado]:
    eid = request.session.get(SESSION_EGRESADO_ID)
    if not eid:
        return None
    return Egresado.objects.filter(pk=eid).first()


def _egresado_autenticado(request: HttpRequest) -> Optional[Egresado]:
    egresado = _egresado_desde_sesion(request)
    if not egresado:
        return None
    return egresado


def egresado_panel(request: HttpRequest) -> HttpResponse:
    egresado = _egresado_autenticado(request)
    if not egresado:
        return redirect('maestro:egresado_ingreso_dni')
    return render(
        request,
        'maestro/egresado_panel.html',
        {'egresado': egresado, 'dashboard_section': 'inicio'},
    )


def egresado_perfil(request: HttpRequest) -> HttpResponse:
    egresado = _egresado_autenticado(request)
    if not egresado:
        return redirect('maestro:egresado_ingreso_dni')
    return render(
        request,
        'maestro/egresado_perfil.html',
        {'egresado': egresado, 'dashboard_section': 'perfil'},
    )


def _encuestas_visibles_para_egresado(egresado: Egresado):
    respuesta_subq = RespuestaEncuesta.objects.filter(
        encuesta=OuterRef('pk'),
        egresado=egresado,
    )
    candidatas = (
        Encuesta.objects.filter(estado=Encuesta.ESTADO_PUBLICADA)
        .annotate(ya_respondio=Exists(respuesta_subq))
        .order_by('-actualizado_en')
    )
    return [e for e in candidatas if e.visible_para_egresado(egresado)]


def _items_pregunta_respuesta(
    preguntas,
    respuestas_mapa: dict,
    errores_pregunta: dict,
    post_data,
    *,
    solo_lectura: bool,
) -> list:
    items = []
    for pregunta in preguntas:
        saved = respuestas_mapa.get(pregunta.pk)
        item = {
            'pregunta': pregunta,
            'error': errores_pregunta.get(f'pregunta_{pregunta.pk}'),
            'saved': saved,
        }
        if pregunta.tipo == Pregunta.TIPO_MATRIZ_SELECCION:
            seleccion_por_fila = {}
            if saved and saved.get('tipo') == 'matriz':
                for fila_id, celda in saved.get('celdas', {}).items():
                    seleccion_por_fila[fila_id] = celda.get('opcion_id')
            if post_data and not solo_lectura:
                for fila in pregunta.filas_matriz.all():
                    raw = (post_data.get(f'matriz_{fila.pk}') or '').strip()
                    if raw:
                        seleccion_por_fila[fila.pk] = int(raw)
            item['matriz_filas'] = [
                {
                    'fila': fila,
                    'opcion_id': seleccion_por_fila.get(fila.pk),
                }
                for fila in pregunta.filas_matriz.all()
            ]
        if post_data and not solo_lectura:
            item['post_valor'] = post_data.get(f'pregunta_{pregunta.pk}', '')
            if pregunta.tipo == Pregunta.TIPO_SELECCION_MULTIPLE:
                item['post_check_ids'] = [
                    opcion.pk
                    for opcion in pregunta.opciones.all()
                    if post_data.get(f'pregunta_{pregunta.pk}_{opcion.pk}')
                ]
        items.append(item)
    return items


def _get_encuesta_egresado(pk: int, egresado: Egresado) -> Encuesta:
    encuesta = get_object_or_404(Encuesta, pk=pk, estado=Encuesta.ESTADO_PUBLICADA)
    if not encuesta.visible_para_egresado(egresado):
        raise Http404('Encuesta no disponible.')
    return encuesta


def egresado_encuestas_lista(request: HttpRequest) -> HttpResponse:
    egresado = _egresado_autenticado(request)
    if not egresado:
        return redirect('maestro:egresado_ingreso_dni')

    encuestas = _encuestas_visibles_para_egresado(egresado)
    return render(
        request,
        'maestro/egresado_encuestas_lista.html',
        {
            'egresado': egresado,
            'dashboard_section': 'encuestas',
            'encuestas': encuestas,
        },
    )


def egresado_encuesta_responder(request: HttpRequest, pk: int) -> HttpResponse:
    egresado = _egresado_autenticado(request)
    if not egresado:
        return redirect('maestro:egresado_ingreso_dni')

    encuesta = _get_encuesta_egresado(pk, egresado)
    respuesta_guardada = RespuestaEncuesta.objects.filter(
        encuesta=encuesta,
        egresado=egresado,
    ).first()

    preguntas = encuesta.preguntas.prefetch_related(
        Prefetch(
            'opciones',
            queryset=OpcionPregunta.objects.order_by('orden', 'pk'),
        ),
        Prefetch(
            'filas_matriz',
            queryset=FilaMatrizPregunta.objects.order_by('orden', 'pk'),
        ),
    )

    errores_pregunta: dict = {}
    solo_lectura = respuesta_guardada is not None

    if request.method == 'POST' and not solo_lectura:
        respuesta_guardada, errores_pregunta = validar_y_guardar_respuestas(
            encuesta,
            egresado,
            request.POST,
        )
        if respuesta_guardada:
            messages.success(request, 'Encuesta enviada correctamente.')
            return redirect('maestro:egresado_encuesta_responder', pk=encuesta.pk)
        solo_lectura = False

    respuestas_mapa = {}
    if respuesta_guardada:
        respuestas_mapa = mapa_respuestas_guardadas(respuesta_guardada)

    preguntas_items = _items_pregunta_respuesta(
        preguntas,
        respuestas_mapa,
        errores_pregunta,
        request.POST if errores_pregunta else None,
        solo_lectura=solo_lectura,
    )

    return render(
        request,
        'maestro/egresado_encuesta_responder.html',
        {
            'egresado': egresado,
            'dashboard_section': 'encuestas',
            'encuesta': encuesta,
            'preguntas_items': preguntas_items,
            'solo_lectura': solo_lectura,
            'respuesta_guardada': respuesta_guardada,
        },
    )


def egresado_perfil_editar(request: HttpRequest) -> HttpResponse:
    egresado = _egresado_autenticado(request)
    if not egresado:
        return redirect('maestro:egresado_ingreso_dni')

    if request.method == 'POST':
        form = EgresadoPerfilForm(request.POST, instance=egresado)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil actualizado correctamente.')
            return redirect('maestro:egresado_perfil')
    else:
        form = EgresadoPerfilForm(instance=egresado)

    return render(
        request,
        'maestro/egresado_perfil_editar.html',
        {
            'egresado': egresado,
            'form': form,
            'dashboard_section': 'perfil',
        },
    )
