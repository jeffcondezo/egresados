import unicodedata


def normalize_dni(value: str) -> str:
    """Solo dígitos, para comparar DNIs con o sin formato."""
    return ''.join(c for c in (value or '') if c.isdigit())


def normalize_apellido(value: str) -> str:
    """Comparación insensible a mayúsculas y tildes."""
    s = (value or '').strip().lower()
    s = ''.join(
        c
        for c in unicodedata.normalize('NFD', s)
        if unicodedata.category(c) != 'Mn'
    )
    return s
