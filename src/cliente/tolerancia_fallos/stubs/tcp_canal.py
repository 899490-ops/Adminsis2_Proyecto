"""
CanalTCP — implementación real que sustituye el stub original (CU3).

Envía un mensaje TCP al servidor y lee su respuesta en pares envío/recepción.
En modo_fallo simula la caída del servidor tras N respuestas correctas, para
poder probar CU3 sin necesidad de matar un proceso real.
"""
from __future__ import annotations

import json
import os
import socket


def _cargar_config() -> dict:
    ruta = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "config", "config.json")
    )
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


class CanalTCP:
    def __init__(self, modo_fallo: bool = False, fallos_tras: int = 3) -> None:
        config = _cargar_config()
        self._timeout = float(config["HEARTBEAT_TIMEOUT"])
        self._modo_fallo = modo_fallo
        self._fallos_tras = fallos_tras
        self._exitos = 0
        self._sock: socket.socket | None = None

    def _en_fallo(self) -> bool:
        return self._modo_fallo and self._exitos >= self._fallos_tras

    def enviar(self, ip: str, puerto: int, mensaje: str) -> None:
        if self._en_fallo():
            self._sock = None
            return
        try:
            self._sock = socket.create_connection((ip, puerto), timeout=self._timeout)
            self._sock.sendall((mensaje + "\n").encode("utf-8"))
            self._sock.shutdown(socket.SHUT_WR)
        except OSError:
            self._sock = None

    def recibir(self, timeout: float | None = None) -> str | None:
        if self._en_fallo() or self._sock is None:
            return None
        try:
            self._sock.settimeout(timeout if timeout is not None else self._timeout)
            datos = self._sock.recv(1024)
            self._sock.close()
            self._sock = None
            if not datos:
                return None
            self._exitos += 1
            return datos.decode("utf-8").strip()
        except OSError:
            if self._sock is not None:
                try:
                    self._sock.close()
                except OSError:
                    pass
            self._sock = None
            return None

    def cerrar(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
