from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction

from .models import (
    Encuesta,
    Egresado,
    FilaMatrizPregunta,
    OpcionPregunta,
    Pregunta,
    RespuestaEncuesta,
    RespuestaMatriz,
    RespuestaPregunta,
    RespuestaPreguntaOpcion,
)


def validar_y_guardar_respuestas(
    encuesta: Encuesta,
    egresado: Egresado,
    post_data: Any,
) -> Tuple[Optional[RespuestaEncuesta], Dict[str, str]]:
    errores: Dict[str, str] = {}
    preguntas = list(
        encuesta.preguntas.prefetch_related('opciones', 'filas_matriz')
    )

    for pregunta in preguntas:
        mensaje = _validar_pregunta(post_data, pregunta)
        if mensaje:
            errores[f'pregunta_{pregunta.pk}'] = mensaje

    if errores:
        return None, errores

    with transaction.atomic():
        respuesta_encuesta = RespuestaEncuesta.objects.create(
            encuesta=encuesta,
            egresado=egresado,
        )
        for pregunta in preguntas:
            _guardar_pregunta(respuesta_encuesta, post_data, pregunta)

    return respuesta_encuesta, {}


def mapa_respuestas_guardadas(
    respuesta_encuesta: RespuestaEncuesta,
) -> Dict[int, dict]:
    """Mapa pregunta_id -> datos para plantilla de solo lectura."""
    resultado: Dict[int, dict] = {}

    for rp in respuesta_encuesta.respuestas_preguntas.select_related('opcion').prefetch_related(
        'opciones_seleccionadas__opcion',
    ):
        pregunta_id = rp.pregunta_id
        if rp.opcion_id:
            resultado[pregunta_id] = {'tipo': 'unica', 'opcion_id': rp.opcion_id, 'texto': rp.opcion.texto}
        elif rp.valor_texto:
            resultado[pregunta_id] = {'tipo': 'texto', 'valor': rp.valor_texto}
        elif rp.valor_entero is not None:
            resultado[pregunta_id] = {'tipo': 'entero', 'valor': rp.valor_entero}
        elif rp.valor_decimal is not None:
            resultado[pregunta_id] = {'tipo': 'decimal', 'valor': rp.valor_decimal}
        else:
            opciones = list(rp.opciones_seleccionadas.values_list('opcion_id', 'opcion__texto'))
            resultado[pregunta_id] = {
                'tipo': 'multiple',
                'opcion_ids': [o[0] for o in opciones],
                'textos': [o[1] for o in opciones],
            }

    matriz_por_pregunta: Dict[int, Dict[int, dict]] = {}
    for rm in respuesta_encuesta.respuestas_matriz.select_related('fila', 'opcion', 'fila__pregunta'):
        pid = rm.fila.pregunta_id
        matriz_por_pregunta.setdefault(pid, {})[rm.fila_id] = {
            'opcion_id': rm.opcion_id,
            'texto': rm.opcion.texto,
        }

    for pid, celdas in matriz_por_pregunta.items():
        resultado[pid] = {'tipo': 'matriz', 'celdas': celdas}

    return resultado


def _validar_pregunta(post_data: Any, pregunta: Pregunta) -> Optional[str]:
    if pregunta.tipo == Pregunta.TIPO_SELECCION_UNICA:
        return _validar_seleccion_unica(post_data, pregunta)
    if pregunta.tipo == Pregunta.TIPO_SELECCION_MULTIPLE:
        return _validar_seleccion_multiple(post_data, pregunta)
    if pregunta.tipo == Pregunta.TIPO_MATRIZ_SELECCION:
        return _validar_matriz(post_data, pregunta)
    if pregunta.tipo in (Pregunta.TIPO_TEXTO_LARGO, Pregunta.TIPO_TEXTO_CORTO):
        return _validar_texto(post_data, pregunta)
    if pregunta.tipo == Pregunta.TIPO_ENTERO:
        return _validar_entero(post_data, pregunta)
    if pregunta.tipo == Pregunta.TIPO_DECIMAL:
        return _validar_decimal(post_data, pregunta)
    return None


def _validar_seleccion_unica(post_data: Any, pregunta: Pregunta) -> Optional[str]:
    key = f'pregunta_{pregunta.pk}'
    valor = (post_data.get(key) or '').strip()
    if pregunta.obligatoria and not valor:
        return 'Seleccione una opción.'
    if valor and not _opcion_pertenece(pregunta, valor):
        return 'Opción no válida.'
    return None


def _validar_seleccion_multiple(post_data: Any, pregunta: Pregunta) -> Optional[str]:
    seleccionadas = _opciones_multiple_seleccionadas(post_data, pregunta)
    if pregunta.obligatoria and not seleccionadas:
        return 'Seleccione al menos una opción.'
    ids_validos = set(pregunta.opciones.values_list('pk', flat=True))
    if any(oid not in ids_validos for oid in seleccionadas):
        return 'Opción no válida.'
    return None


def _validar_matriz(post_data: Any, pregunta: Pregunta) -> Optional[str]:
    filas = list(pregunta.filas_matriz.all())
    ids_columnas = set(pregunta.opciones.values_list('pk', flat=True))
    for fila in filas:
        key = f'matriz_{fila.pk}'
        valor = (post_data.get(key) or '').strip()
        if pregunta.obligatoria and not valor:
            return f'Complete todas las filas de «{pregunta.titulo}».'
        if valor:
            try:
                opcion_id = int(valor)
            except (TypeError, ValueError):
                return 'Respuesta de matriz no válida.'
            if opcion_id not in ids_columnas:
                return 'Columna seleccionada no válida.'
    return None


def _validar_texto(post_data: Any, pregunta: Pregunta) -> Optional[str]:
    key = f'pregunta_{pregunta.pk}'
    valor = (post_data.get(key) or '').strip()
    if pregunta.obligatoria and not valor:
        return 'Este campo es obligatorio.'
    if pregunta.tipo == Pregunta.TIPO_TEXTO_CORTO and pregunta.texto_maximo:
        if len(valor) > pregunta.texto_maximo:
            return f'Máximo {pregunta.texto_maximo} caracteres.'
    return None


def _validar_entero(post_data: Any, pregunta: Pregunta) -> Optional[str]:
    key = f'pregunta_{pregunta.pk}'
    valor = (post_data.get(key) or '').strip()
    if pregunta.obligatoria and not valor:
        return 'Ingrese un número entero.'
    if not valor:
        return None
    try:
        int(valor)
    except (TypeError, ValueError):
        return 'Ingrese un número entero válido.'
    return None


def _validar_decimal(post_data: Any, pregunta: Pregunta) -> Optional[str]:
    key = f'pregunta_{pregunta.pk}'
    valor = (post_data.get(key) or '').strip()
    if pregunta.obligatoria and not valor:
        return 'Ingrese un número.'
    if not valor:
        return None
    try:
        Decimal(valor)
    except (InvalidOperation, TypeError, ValueError):
        return 'Ingrese un número válido.'
    return None


def _guardar_pregunta(
    respuesta_encuesta: RespuestaEncuesta,
    post_data: Any,
    pregunta: Pregunta,
) -> None:
    if pregunta.tipo == Pregunta.TIPO_MATRIZ_SELECCION:
        _guardar_matriz(respuesta_encuesta, post_data, pregunta)
        return

    rp = RespuestaPregunta.objects.create(
        respuesta_encuesta=respuesta_encuesta,
        pregunta=pregunta,
    )

    if pregunta.tipo == Pregunta.TIPO_SELECCION_UNICA:
        valor = (post_data.get(f'pregunta_{pregunta.pk}') or '').strip()
        if valor:
            rp.opcion_id = int(valor)
            rp.save(update_fields=['opcion_id'])
    elif pregunta.tipo == Pregunta.TIPO_SELECCION_MULTIPLE:
        for opcion_id in _opciones_multiple_seleccionadas(post_data, pregunta):
            RespuestaPreguntaOpcion.objects.create(
                respuesta_pregunta=rp,
                opcion_id=opcion_id,
            )
    elif pregunta.tipo in (Pregunta.TIPO_TEXTO_LARGO, Pregunta.TIPO_TEXTO_CORTO):
        valor = (post_data.get(f'pregunta_{pregunta.pk}') or '').strip()
        if valor:
            rp.valor_texto = valor
            rp.save(update_fields=['valor_texto'])
    elif pregunta.tipo == Pregunta.TIPO_ENTERO:
        valor = (post_data.get(f'pregunta_{pregunta.pk}') or '').strip()
        if valor:
            rp.valor_entero = int(valor)
            rp.save(update_fields=['valor_entero'])
    elif pregunta.tipo == Pregunta.TIPO_DECIMAL:
        valor = (post_data.get(f'pregunta_{pregunta.pk}') or '').strip()
        if valor:
            rp.valor_decimal = Decimal(valor)
            rp.save(update_fields=['valor_decimal'])


def _guardar_matriz(
    respuesta_encuesta: RespuestaEncuesta,
    post_data: Any,
    pregunta: Pregunta,
) -> None:
    for fila in pregunta.filas_matriz.all():
        valor = (post_data.get(f'matriz_{fila.pk}') or '').strip()
        if valor:
            RespuestaMatriz.objects.create(
                respuesta_encuesta=respuesta_encuesta,
                fila=fila,
                opcion_id=int(valor),
            )


def _opciones_multiple_seleccionadas(post_data: Any, pregunta: Pregunta) -> List[int]:
    ids: List[int] = []
    for opcion in pregunta.opciones.all():
        key = f'pregunta_{pregunta.pk}_{opcion.pk}'
        if post_data.get(key):
            ids.append(opcion.pk)
    return ids


def _opcion_pertenece(pregunta: Pregunta, valor: str) -> bool:
    try:
        opcion_id = int(valor)
    except (TypeError, ValueError):
        return False
    return pregunta.opciones.filter(pk=opcion_id).exists()
