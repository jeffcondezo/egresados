from functools import wraps
from typing import Optional

from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import (
    EgresadoApellidoForm,
    EgresadoDNForm,
    EgresadoPerfilForm,
    GestorAuthenticationForm,
)
from .models import Egresado
from .utils import normalize_dni

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
