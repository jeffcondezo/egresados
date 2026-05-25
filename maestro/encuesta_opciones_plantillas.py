"""Plantillas de opciones frecuentes para preguntas de selección."""

from typing import TypedDict


class PlantillaOpciones(TypedDict):
    id: str
    nombre: str
    opciones: list[str]


OPCIONES_PLANTILLAS: list[PlantillaOpciones] = [
    {
        'id': 'satisfaccion_4',
        'nombre': 'Satisfacción (4 niveles)',
        'opciones': [
            'Totalmente satisfecho',
            'Satisfecho',
            'Insatisfecho',
            'Muy insatisfecho',
        ],
    },
    {
        'id': 'satisfaccion_matriz_4',
        'nombre': 'Satisfacción matriz (Muy satisfecho … Muy insatisfecho)',
        'opciones': [
            'Muy satisfecho',
            'Satisfecho',
            'Insatisfecho',
            'Muy insatisfecho',
        ],
    },
    {
        'id': 'acuerdo_4',
        'nombre': 'Nivel de acuerdo (4 niveles)',
        'opciones': [
            'Totalmente de acuerdo',
            'De acuerdo',
            'En desacuerdo',
            'Totalmente en desacuerdo',
        ],
    },
    {
        'id': 'frecuencia_4',
        'nombre': 'Frecuencia (4 niveles)',
        'opciones': [
            'Siempre',
            'A menudo',
            'A veces',
            'Nunca',
        ],
    },
    {
        'id': 'si_no',
        'nombre': 'Sí / No',
        'opciones': ['Sí', 'No'],
    },
    {
        'id': 'si_no_na',
        'nombre': 'Sí / No / No aplica',
        'opciones': ['Sí', 'No', 'No aplica'],
    },
    {
        'id': 'escala_1_5',
        'nombre': 'Escala numérica 1 a 5',
        'opciones': ['1', '2', '3', '4', '5'],
    },
]


def sugerencias_autocompletado() -> list[str]:
    vistas: list[str] = []
    for plantilla in OPCIONES_PLANTILLAS:
        for opcion in plantilla['opciones']:
            if opcion not in vistas:
                vistas.append(opcion)
    return vistas
