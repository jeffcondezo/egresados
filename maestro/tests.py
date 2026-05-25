from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import (
    Egresado,
    Encuesta,
    FilaMatrizPregunta,
    OpcionPregunta,
    Pregunta,
    RespuestaEncuesta,
    RespuestaMatriz,
    RespuestaPregunta,
)


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


class GestorEncuestasTests(TestCase):
    def setUp(self) -> None:
        self.gestor = get_user_model().objects.create_user(
            username='gestor_encuestas',
            password='Gestor123!',
        )
        self.encuesta = Encuesta.objects.create(
            titulo='Encuesta de prueba',
            descripcion='Descripción',
            creado_por=self.gestor,
        )

    def test_lista_encuestas_requiere_login(self) -> None:
        response = self.client.get(reverse('maestro:gestor_encuestas_lista'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/acceso/gestores/', response.url)

    def test_crear_encuesta_en_borrador(self) -> None:
        self.client.force_login(self.gestor)
        response = self.client.post(
            reverse('maestro:gestor_encuesta_crear'),
            {'titulo': 'Nueva encuesta', 'descripcion': 'Texto'},
        )
        self.assertEqual(response.status_code, 302)
        encuesta = Encuesta.objects.get(titulo='Nueva encuesta')
        self.assertEqual(encuesta.estado, Encuesta.ESTADO_BORRADOR)
        self.assertEqual(encuesta.creado_por, self.gestor)

    def test_crear_pregunta_seleccion_unica(self) -> None:
        self.client.force_login(self.gestor)
        response = self.client.post(
            reverse('maestro:gestor_pregunta_crear', args=[self.encuesta.pk]),
            {
                'titulo': '¿Cuál es su situación laboral?',
                'tipo': Pregunta.TIPO_SELECCION_UNICA,
                'obligatoria': True,
                'opciones-TOTAL_FORMS': 2,
                'opciones-INITIAL_FORMS': 0,
                'opciones-MIN_NUM_FORMS': 0,
                'opciones-MAX_NUM_FORMS': 1000,
                'opciones-0-texto': 'Empleado',
                'opciones-1-texto': 'Desempleado',
            },
        )
        self.assertEqual(response.status_code, 302)
        pregunta = self.encuesta.preguntas.get()
        self.assertEqual(pregunta.tipo, Pregunta.TIPO_SELECCION_UNICA)
        self.assertEqual(pregunta.opciones.count(), 2)

    def test_crear_pregunta_con_plantilla_satisfaccion(self) -> None:
        self.client.force_login(self.gestor)
        response = self.client.post(
            reverse('maestro:gestor_pregunta_crear', args=[self.encuesta.pk]),
            {
                'titulo': '¿Qué tan satisfecho está?',
                'tipo': Pregunta.TIPO_SELECCION_UNICA,
                'obligatoria': True,
                'opciones-TOTAL_FORMS': 4,
                'opciones-INITIAL_FORMS': 0,
                'opciones-MIN_NUM_FORMS': 0,
                'opciones-MAX_NUM_FORMS': 1000,
                'opciones-0-texto': 'Totalmente satisfecho',
                'opciones-1-texto': 'Satisfecho',
                'opciones-2-texto': 'Insatisfecho',
                'opciones-3-texto': 'Muy insatisfecho',
            },
        )
        self.assertEqual(response.status_code, 302)
        pregunta = self.encuesta.preguntas.get()
        self.assertEqual(pregunta.opciones.count(), 4)

    def test_crear_pregunta_matriz_seleccion(self) -> None:
        self.client.force_login(self.gestor)
        response = self.client.post(
            reverse('maestro:gestor_pregunta_crear', args=[self.encuesta.pk]),
            {
                'titulo': 'Califique su satisfacción con:',
                'tipo': Pregunta.TIPO_MATRIZ_SELECCION,
                'obligatoria': True,
                'opciones-TOTAL_FORMS': 4,
                'opciones-INITIAL_FORMS': 0,
                'opciones-MIN_NUM_FORMS': 0,
                'opciones-MAX_NUM_FORMS': 1000,
                'opciones-0-texto': 'Muy satisfecho',
                'opciones-1-texto': 'Satisfecho',
                'opciones-2-texto': 'Insatisfecho',
                'opciones-3-texto': 'Muy insatisfecho',
                'filas_matriz-TOTAL_FORMS': 3,
                'filas_matriz-INITIAL_FORMS': 0,
                'filas_matriz-MIN_NUM_FORMS': 0,
                'filas_matriz-MAX_NUM_FORMS': 1000,
                'filas_matriz-0-texto': 'Servicio de bienestar universitario',
                'filas_matriz-1-texto': 'El servicio de salud',
                'filas_matriz-2-texto': 'Los talleres deportivos, arte y cultura',
            },
        )
        self.assertEqual(response.status_code, 302)
        pregunta = self.encuesta.preguntas.get()
        self.assertEqual(pregunta.tipo, Pregunta.TIPO_MATRIZ_SELECCION)
        self.assertEqual(pregunta.opciones.count(), 4)
        self.assertEqual(pregunta.filas_matriz.count(), 3)

    def test_publicar_falla_matriz_sin_filas(self) -> None:
        pregunta = Pregunta.objects.create(
            encuesta=self.encuesta,
            orden=1,
            titulo='Matriz incompleta',
            tipo=Pregunta.TIPO_MATRIZ_SELECCION,
        )
        OpcionPregunta.objects.bulk_create([
            OpcionPregunta(pregunta=pregunta, texto='A', orden=1),
            OpcionPregunta(pregunta=pregunta, texto='B', orden=2),
        ])
        self.client.force_login(self.gestor)
        response = self.client.post(
            reverse('maestro:gestor_encuesta_publicar', args=[self.encuesta.pk]),
            {'alcance': Encuesta.ALCANCE_TODOS},
        )
        self.assertEqual(response.status_code, 302)
        self.encuesta.refresh_from_db()
        self.assertEqual(self.encuesta.estado, Encuesta.ESTADO_BORRADOR)

    def test_publicar_ok_con_matriz_valida(self) -> None:
        pregunta = Pregunta.objects.create(
            encuesta=self.encuesta,
            orden=1,
            titulo='Califique su satisfacción con:',
            tipo=Pregunta.TIPO_MATRIZ_SELECCION,
        )
        OpcionPregunta.objects.bulk_create([
            OpcionPregunta(pregunta=pregunta, texto='Muy satisfecho', orden=1),
            OpcionPregunta(pregunta=pregunta, texto='Satisfecho', orden=2),
        ])
        FilaMatrizPregunta.objects.create(
            pregunta=pregunta,
            texto='Servicio de salud',
            orden=1,
        )
        self.client.force_login(self.gestor)
        response = self.client.post(
            reverse('maestro:gestor_encuesta_publicar', args=[self.encuesta.pk]),
            {'alcance': Encuesta.ALCANCE_TODOS},
        )
        self.assertEqual(response.status_code, 302)
        self.encuesta.refresh_from_db()
        self.assertEqual(self.encuesta.estado, Encuesta.ESTADO_PUBLICADA)

    def test_publicar_falla_sin_preguntas(self) -> None:
        self.client.force_login(self.gestor)
        response = self.client.post(
            reverse('maestro:gestor_encuesta_publicar', args=[self.encuesta.pk]),
            {'alcance': Encuesta.ALCANCE_TODOS},
        )
        self.assertEqual(response.status_code, 302)
        self.encuesta.refresh_from_db()
        self.assertEqual(self.encuesta.estado, Encuesta.ESTADO_BORRADOR)

    def test_publicar_ok_con_pregunta_valida(self) -> None:
        pregunta = Pregunta.objects.create(
            encuesta=self.encuesta,
            orden=1,
            titulo='Comentario',
            tipo=Pregunta.TIPO_TEXTO_LARGO,
        )
        self.client.force_login(self.gestor)
        response = self.client.post(
            reverse('maestro:gestor_encuesta_publicar', args=[self.encuesta.pk]),
            {'alcance': Encuesta.ALCANCE_TODOS},
        )
        self.assertEqual(response.status_code, 302)
        self.encuesta.refresh_from_db()
        self.assertEqual(self.encuesta.estado, Encuesta.ESTADO_PUBLICADA)

    def test_publicar_con_alcance_escuela(self) -> None:
        Egresado.objects.create(
            dni='11111111',
            apellido_paterno='Lopez',
            escuela='Ingeniería de Sistemas',
        )
        pregunta = Pregunta.objects.create(
            encuesta=self.encuesta,
            orden=1,
            titulo='Comentario',
            tipo=Pregunta.TIPO_TEXTO_LARGO,
        )
        self.client.force_login(self.gestor)
        response = self.client.post(
            reverse('maestro:gestor_encuesta_publicar', args=[self.encuesta.pk]),
            {
                'alcance': Encuesta.ALCANCE_ESCUELA,
                'escuela': 'Ingeniería de Sistemas',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.encuesta.refresh_from_db()
        self.assertEqual(self.encuesta.estado, Encuesta.ESTADO_PUBLICADA)
        self.assertEqual(self.encuesta.alcance, Encuesta.ALCANCE_ESCUELA)
        self.assertEqual(self.encuesta.escuela, 'Ingeniería de Sistemas')

    def test_encuesta_publicada_no_permite_editar_pregunta(self) -> None:
        self.encuesta.estado = Encuesta.ESTADO_PUBLICADA
        self.encuesta.save()
        pregunta = Pregunta.objects.create(
            encuesta=self.encuesta,
            orden=1,
            titulo='Pregunta',
            tipo=Pregunta.TIPO_ENTERO,
        )
        self.client.force_login(self.gestor)
        response = self.client.get(
            reverse('maestro:gestor_pregunta_editar', args=[self.encuesta.pk, pregunta.pk]),
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('maestro:gestor_encuesta_detalle', args=[self.encuesta.pk]),
        )


class EgresadoEncuestasTests(TestCase):
    def setUp(self) -> None:
        self.egresado_sistemas = Egresado.objects.create(
            dni='22222222',
            apellido_paterno='Garcia',
            escuela='Sistemas',
        )
        self.egresado_otra = Egresado.objects.create(
            dni='33333333',
            apellido_paterno='Ruiz',
            escuela='Administración',
        )
        self.encuesta_todos = Encuesta.objects.create(
            titulo='Para todos',
            estado=Encuesta.ESTADO_PUBLICADA,
            alcance=Encuesta.ALCANCE_TODOS,
        )
        self.encuesta_escuela = Encuesta.objects.create(
            titulo='Solo Sistemas',
            estado=Encuesta.ESTADO_PUBLICADA,
            alcance=Encuesta.ALCANCE_ESCUELA,
            escuela='Sistemas',
        )
        self.pregunta_unica = Pregunta.objects.create(
            encuesta=self.encuesta_todos,
            orden=1,
            titulo='¿Situación laboral?',
            tipo=Pregunta.TIPO_SELECCION_UNICA,
        )
        self.opcion_a = OpcionPregunta.objects.create(
            pregunta=self.pregunta_unica,
            texto='Empleado',
            orden=1,
        )
        self.opcion_b = OpcionPregunta.objects.create(
            pregunta=self.pregunta_unica,
            texto='Desempleado',
            orden=2,
        )

    def _login_egresado(self, egresado: Egresado) -> None:
        session = self.client.session
        session['egresado_id'] = egresado.pk
        session.save()

    def test_lista_filtra_por_escuela(self) -> None:
        self._login_egresado(self.egresado_sistemas)
        response = self.client.get(reverse('maestro:egresado_encuestas_lista'))
        self.assertEqual(response.status_code, 200)
        titulos = [e.titulo for e in response.context['encuestas']]
        self.assertIn('Para todos', titulos)
        self.assertIn('Solo Sistemas', titulos)

        self._login_egresado(self.egresado_otra)
        response = self.client.get(reverse('maestro:egresado_encuestas_lista'))
        titulos = [e.titulo for e in response.context['encuestas']]
        self.assertIn('Para todos', titulos)
        self.assertNotIn('Solo Sistemas', titulos)

    def test_responder_seleccion_unica_y_ver_completada(self) -> None:
        self._login_egresado(self.egresado_sistemas)
        url = reverse('maestro:egresado_encuesta_responder', args=[self.encuesta_todos.pk])
        response = self.client.post(
            url,
            {f'pregunta_{self.pregunta_unica.pk}': str(self.opcion_a.pk)},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            RespuestaEncuesta.objects.filter(
                encuesta=self.encuesta_todos,
                egresado=self.egresado_sistemas,
            ).exists()
        )
        rp = RespuestaPregunta.objects.get(
            respuesta_encuesta__encuesta=self.encuesta_todos,
            pregunta=self.pregunta_unica,
        )
        self.assertEqual(rp.opcion_id, self.opcion_a.pk)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['solo_lectura'])
        self.assertContains(response, 'Completada')
        self.assertContains(response, 'Empleado')

    def test_segundo_envio_no_permitido(self) -> None:
        self._login_egresado(self.egresado_sistemas)
        url = reverse('maestro:egresado_encuesta_responder', args=[self.encuesta_todos.pk])
        self.client.post(
            url,
            {f'pregunta_{self.pregunta_unica.pk}': str(self.opcion_a.pk)},
        )
        count_antes = RespuestaEncuesta.objects.filter(
            encuesta=self.encuesta_todos,
            egresado=self.egresado_sistemas,
        ).count()
        self.client.post(
            url,
            {f'pregunta_{self.pregunta_unica.pk}': str(self.opcion_b.pk)},
        )
        count_despues = RespuestaEncuesta.objects.filter(
            encuesta=self.encuesta_todos,
            egresado=self.egresado_sistemas,
        ).count()
        self.assertEqual(count_antes, count_despues)
        rp = RespuestaPregunta.objects.get(
            respuesta_encuesta__encuesta=self.encuesta_todos,
            pregunta=self.pregunta_unica,
        )
        self.assertEqual(rp.opcion_id, self.opcion_a.pk)

    def test_matriz_persiste_respuestas(self) -> None:
        encuesta = Encuesta.objects.create(
            titulo='Matriz',
            estado=Encuesta.ESTADO_PUBLICADA,
            alcance=Encuesta.ALCANCE_TODOS,
        )
        pregunta = Pregunta.objects.create(
            encuesta=encuesta,
            orden=1,
            titulo='Califique',
            tipo=Pregunta.TIPO_MATRIZ_SELECCION,
        )
        col1 = OpcionPregunta.objects.create(pregunta=pregunta, texto='Bueno', orden=1)
        col2 = OpcionPregunta.objects.create(pregunta=pregunta, texto='Malo', orden=2)
        fila = FilaMatrizPregunta.objects.create(pregunta=pregunta, texto='Servicio', orden=1)
        self._login_egresado(self.egresado_sistemas)
        url = reverse('maestro:egresado_encuesta_responder', args=[encuesta.pk])
        self.client.post(url, {f'matriz_{fila.pk}': str(col1.pk)})
        rm = RespuestaMatriz.objects.get(
            respuesta_encuesta__encuesta=encuesta,
            fila=fila,
        )
        self.assertEqual(rm.opcion_id, col1.pk)
