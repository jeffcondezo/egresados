from django.urls import path

from . import views

app_name = 'maestro'

urlpatterns = [
    path('', views.egresado_ingreso_dni, name='egresado_ingreso_dni'),
    path('acceso/gestores/', views.GestorLoginView.as_view(), name='gestor_login'),
    path('gestores/login/', views.GestorLoginView.as_view()),
    path('gestores/logout/', views.GestorLogoutView.as_view(), name='gestor_logout'),
    path('gestores/panel/', views.gestor_panel, name='gestor_panel'),
    path('gestores/alumnos/', views.gestor_consulta_alumnos, name='gestor_consulta_alumnos'),
    path('acceso/egresados/', views.egresado_ingreso_dni),
    path('acceso/egresados/apellido/', views.egresado_ingreso_apellido, name='egresado_ingreso_apellido'),
    path('egresados/ingreso/', views.egresado_ingreso_dni),
    path('egresados/ingreso/apellido/', views.egresado_ingreso_apellido),
    path('egresados/salir/', views.egresado_logout, name='egresado_logout'),
    path('egresados/panel/', views.egresado_panel, name='egresado_panel'),
    path('egresados/perfil/', views.egresado_perfil, name='egresado_perfil'),
    path('egresados/perfil/editar/', views.egresado_perfil_editar, name='egresado_perfil_editar'),
]
