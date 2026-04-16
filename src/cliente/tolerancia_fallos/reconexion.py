"""
Lógica de reconexión del cliente a un nuevo servidor (CU3).

Cuando el cliente detecta que su servidor actual ha caído, este módulo
busca otro servidor disponible en la lista y establece una nueva conexión.
"""

from stubs.lista_servidores import obtener_servidores
from stubs.tcp_canal import CanalTCP


def intentar_reconexion(
    servidor_caido: tuple[str, int],
    canal: CanalTCP,
    heartbeat_timeout: float,
) -> tuple[str, int] | None:
    """
    Intenta conectar el cliente a un servidor alternativo.

    Parámetros
    ----------
    servidor_caido : tuple[str, int]
        IP y puerto del servidor que ha caído (se excluye de la búsqueda).
    canal : CanalTCP
        Canal de comunicación para enviar RECONNECT_REQUEST.
    heartbeat_timeout : float
        Segundos máximos de espera por respuesta del nuevo servidor.

    Retorna
    -------
    tuple[str, int] | None
        El nuevo servidor (ip, puerto) si la reconexión tuvo éxito,
        o None si no queda ningún servidor disponible.
    """
    servidores = obtener_servidores()
    candidatos = [s for s in servidores if s != servidor_caido]

    for ip, puerto in candidatos:
        canal.enviar(ip, puerto, f"RECONNECT_REQUEST client server_caido={servidor_caido[0]}")
        respuesta = canal.recibir(timeout=heartbeat_timeout)

        if respuesta == "RECONNECT_OK":
            return (ip, puerto)

    return None
