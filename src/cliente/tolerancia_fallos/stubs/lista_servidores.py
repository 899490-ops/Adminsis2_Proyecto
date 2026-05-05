"""
Persistencia de la lista de servidores conocidos por el cliente.

guardar_servidores() se llama en detector_servidor.py al arrancar.
obtener_servidores() se llama desde reconexion.py para encontrar
un servidor alternativo tras la caída del servidor actual (CU3).
"""
from __future__ import annotations

import json
import os

_RUTA = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "servidores_conocidos.json")
)


def obtener_servidores() -> list[tuple[str, int]]:
    try:
        with open(_RUTA, encoding="utf-8") as f:
            datos = json.load(f)
        return [(s["ip"], int(s["puerto"])) for s in datos]
    except (OSError, KeyError, ValueError, json.JSONDecodeError):
        return []


def guardar_servidores(servidores: list[tuple[str, int]]) -> None:
    datos = [{"ip": ip, "puerto": puerto} for ip, puerto in servidores]
    with open(_RUTA, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
