from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Egresado


class GestorConsultaAlumnosTests(TestCase):
    def setUp(self) -> None:
        self.gestor = get_user_model().objects.create_user(
            username='gestor_test',
            password='Gestor123!',
            first_name='Gestor',
            last_name='Prueba',
        )
        self.alumno = Egresado.objects.create(
            dni='12345678',
            codigo='20201234',
            apellido_paterno='Perez',
            apellido_materno='Lopez',
            nombres='Ana Lucia',
            facultad='Ingenieria',
            escuela='Sistemas',
        )

    def test_consulta_alumnos_inicia_vacia_sin_filtros(self) -> None:
        self.client.force_login(self.gestor)

        response = self.client.get(reverse('maestro:gestor_consulta_alumnos'))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['filtros_aplicados'])
        self.assertEqual(list(response.context['alumnos']), [])
        self.assertContains(response, 'Sin resultados aún')

    def test_consulta_alumnos_filtra_por_dni(self) -> None:
        self.client.force_login(self.gestor)

        response = self.client.get(
            reverse('maestro:gestor_consulta_alumnos'),
            {'dni': '12345678'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['filtros_aplicados'])
        self.assertEqual(list(response.context['alumnos']), [self.alumno])
        self.assertContains(response, 'Ana Lucia')

    def test_consulta_alumnos_filtra_por_codigo(self) -> None:
        self.client.force_login(self.gestor)

        response = self.client.get(
            reverse('maestro:gestor_consulta_alumnos'),
            {'codigo': '2020'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['filtros_aplicados'])
        self.assertEqual(list(response.context['alumnos']), [self.alumno])
        self.assertContains(response, '20201234')
