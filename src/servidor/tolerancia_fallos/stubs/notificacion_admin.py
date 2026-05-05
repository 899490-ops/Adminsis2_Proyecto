"""
Notificación al administrador de la caída de un cliente (RS-10).

Registra el evento CAIDA_CLIENTE en el log de eventos del servidor.
"""
from __future__ import annotations

import json
import os
import sys


def _cargar_config() -> dict:
    ruta = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "config", "config.json")
    )
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def notificar_admin(ip_cliente: str) -> None:
    config = _cargar_config()
    ruta_log = os.path.normpath(
        os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "..", config["LOG_PATH"]
        )
    )

    _src = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    if _src not in sys.path:
        sys.path.insert(0, _src)

    from servidor.monitorizacion.logger import _log
    _log(ruta_log, "CAIDA_CLIENTE", f"ADMIN_NOTIFICADO client_ip={ip_cliente}")
