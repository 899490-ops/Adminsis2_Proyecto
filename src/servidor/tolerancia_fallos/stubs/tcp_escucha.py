"""
EscuchaTCP — implementación real que sustituye el stub original (CU4).

Crea un servidor TCP en PUERTO_TCP que acepta conexiones de clientes con
mensajes HEARTBEAT y RECONNECT_REQUEST, y los expone vía siguiente_heartbeat()
como pares (ip_cliente, mensaje).

En modo_fallo, simula que un cliente específico deja de enviar heartbeats
tras N mensajes, para probar CU4 sin matar un proceso real.
"""
from __future__ import annotations

import json
import os
import queue
import socket
import socketserver
import threading


def _cargar_config() -> dict:
    ruta = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "config", "config.json")
    )
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


class EscuchaTCP:
    def __init__(
        self,
        clientes: list[str],
        intervalo: float,
        modo_fallo: dict[str, int] | None = None,
    ) -> None:
        self._modo_fallo = modo_fallo or {}
        self._contadores: dict[str, int] = {}
        self._cola: queue.Queue[tuple[str, str]] = queue.Queue()

        config = _cargar_config()
        puerto = int(config["PUERTO_TCP"])

        self._srv = _TCPServer(("0.0.0.0", puerto), self._cola)
        self._hilo = threading.Thread(target=self._srv.serve_forever, daemon=True)
        self._hilo.start()

    def siguiente_heartbeat(self, timeout: float = 5) -> tuple[str, str] | None:
        try:
            ip, mensaje = self._cola.get(timeout=timeout)
        except queue.Empty:
            return None

        if ip in self._modo_fallo:
            cnt = self._contadores.get(ip, 0) + 1
            self._contadores[ip] = cnt
            if cnt > self._modo_fallo[ip]:
                return None

        return ip, mensaje

    def cerrar(self) -> None:
        self._srv.shutdown()


class _TCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

    def __init__(self, addr: tuple[str, int], cola: queue.Queue) -> None:
        self._cola = cola
        super().__init__(addr, _Handler)


class _Handler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        try:
            datos = self.request.recv(65535)
        except OSError:
            return
        if not datos:
            return

        mensaje = datos.decode("utf-8").strip()
        ip = self.client_address[0]

        if mensaje == "HEARTBEAT":
            self.request.sendall(b"HEARTBEAT_ACK")
        elif mensaje.startswith("RECONNECT_REQUEST"):
            self.request.sendall(b"RECONNECT_OK")
        else:
            return

        cola: queue.Queue = self.server._cola  # type: ignore[attr-defined]
        cola.put((ip, mensaje))
