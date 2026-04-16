"""
Stub del canal TCP que implementará Persona 2.

Cuando Persona 2 entregue su módulo 'comunicacion/tcp_canal.py',
sustituir este import en detector_servidor.py:

    # Stub (desarrollo):
    from stubs.tcp_canal import CanalTCP

    # Real (integración):
    from comunicacion.tcp_canal import CanalTCP

La interfaz (métodos y firmas) debe mantenerse igual.
"""

import time
import queue
import threading


class CanalTCP:
    """
    Simula en memoria el canal TCP que proveerá Persona 2.

    Parámetros
    ----------
    modo_fallo : bool
        Si True, simula que el servidor deja de responder tras
        `fallos_tras` mensajes enviados (para probar CU3).
    fallos_tras : int
        Número de HEARTBEATs enviados antes de simular la caída.
    """

    def __init__(self, modo_fallo: bool = False, fallos_tras: int = 3):
        self._modo_fallo = modo_fallo
        self._fallos_tras = fallos_tras
        self._enviados = 0
        self._buzón = queue.Queue()
        self._cerrado = False

    # ------------------------------------------------------------------
    # Interfaz pública (la misma que tendrá el canal real de Persona 2)
    # ------------------------------------------------------------------

    def enviar(self, ip: str, puerto: int, mensaje: str) -> None:
        """Envía un mensaje al nodo (ip, puerto)."""
        if self._cerrado:
            return

        self._enviados += 1

        # Simula que el servidor responde con HEARTBEAT_ACK si no hay fallo
        if mensaje == "HEARTBEAT":
            if not self._modo_fallo or self._enviados <= self._fallos_tras:
                # El servidor "responde" tras un breve retardo
                threading.Timer(0.1, lambda: self._buzón.put("HEARTBEAT_ACK")).start()

        elif mensaje.startswith("RECONNECT_REQUEST"):
            # Nueva conexión TCP al nuevo servidor: resetear contador y desactivar modo fallo
            self._enviados = 0
            self._modo_fallo = False
            threading.Timer(0.1, lambda: self._buzón.put("RECONNECT_OK")).start()

    def recibir(self, timeout: float) -> str | None:
        """
        Espera hasta `timeout` segundos por un mensaje entrante.
        Devuelve el mensaje o None si no llega nada.
        """
        try:
            return self._buzón.get(timeout=timeout)
        except queue.Empty:
            return None

    def cerrar(self) -> None:
        """Cierra el canal y libera recursos."""
        self._cerrado = True
