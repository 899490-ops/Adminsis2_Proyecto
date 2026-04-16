"""
Módulo de logging compartido — SRV-6

Todos los componentes del servidor que necesiten escribir en logs/eventos.log
deben importar _log desde aquí.
"""

import os
from datetime import datetime


def _log(ruta_log: str, evento: str, detalle: str) -> None:
    """Escribe una línea en logs/eventos.log con el formato acordado."""
    marca = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"[{marca}] [{evento:<16}] {detalle}\n"

    os.makedirs(os.path.dirname(ruta_log), exist_ok=True)
    with open(ruta_log, "a", encoding="utf-8") as f:
        f.write(linea)

    print(linea, end="")
