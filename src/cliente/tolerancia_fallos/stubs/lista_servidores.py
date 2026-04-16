"""
Stub de la lista de servidores activos que gestionará Persona 1.

Cuando Persona 1 entregue su módulo, sustituir el import en reconexion.py:

    # Stub (desarrollo):
    from stubs.lista_servidores import obtener_servidores

    # Real (integración):
    from alta.lista_servidores import obtener_servidores

La firma de la función debe mantenerse igual.
"""

# Lista hardcoded de servidores disponibles en la red.
# Modifica estas IPs para adaptarlas a tu entorno de pruebas.
_SERVIDORES = [
    ("192.168.1.10", 9000),
    ("192.168.1.11", 9000),
    ("192.168.1.12", 9000),
]


def obtener_servidores() -> list[tuple[str, int]]:
    """
    Devuelve la lista de servidores activos en el sistema
    como pares (ip, puerto).
    """
    return list(_SERVIDORES)
