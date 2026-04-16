"""
Detector de caída de servidor — CU3 (Persona 3: Tolerancia a Fallos)

Lógica principal del cliente:
  - Envía HEARTBEAT al servidor asignado cada HEARTBEAT_INTERVAL segundos.
  - Si no recibe HEARTBEAT_ACK en HEARTBEAT_TIMEOUT segundos, cuenta un fallo.
  - Tras MAX_FALLOS consecutivos sin respuesta, declara la caída del servidor.
  - Intenta reconectarse a otro servidor (CLI-6); al hacerlo informa al nuevo
    servidor del servidor caído para que éste registre el evento en el log.
  - Si no hay servidores disponibles, para su ejecución (CLI-3).

Uso:
    python detector_servidor.py <ip_servidor> [--modo-fallo]

    --modo-fallo   Activa el stub en modo fallo para probar CU3.
"""

import json
import os
import time
import argparse

from reconexion import intentar_reconexion
from stubs.tcp_canal import CanalTCP


# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

def _cargar_config() -> dict:
    ruta = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "config", "config.json"
    )
    with open(os.path.normpath(ruta), encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Bucle principal
# ---------------------------------------------------------------------------

def ejecutar(servidor_inicial: tuple[str, int], modo_fallo: bool = False) -> None:
    config = _cargar_config()

    intervalo: float = config["HEARTBEAT_INTERVAL"]
    timeout: float   = config["HEARTBEAT_TIMEOUT"]
    max_fallos: int  = config["MAX_FALLOS"]

    canal = CanalTCP(modo_fallo=modo_fallo, fallos_tras=max_fallos)
    servidor_actual = servidor_inicial
    fallos = 0

    print(f"[INFO] Cliente iniciado. Servidor asignado: {servidor_actual[0]}:{servidor_actual[1]}")

    try:
        while True:
            ip, puerto = servidor_actual
            canal.enviar(ip, puerto, "HEARTBEAT")
            respuesta = canal.recibir(timeout=timeout)

            if respuesta == "HEARTBEAT_ACK":
                fallos = 0
            else:
                fallos += 1
                print(f"[WARN] Sin respuesta del servidor ({fallos}/{max_fallos})")

                if fallos >= max_fallos:
                    print(f"[INFO] Servidor caído: {ip}. Iniciando reconexión.")

                    nuevo = intentar_reconexion(
                        servidor_caido=servidor_actual,
                        canal=canal,
                        heartbeat_timeout=timeout,
                    )

                    if nuevo is not None:
                        print(f"[INFO] Reconectado a nuevo servidor: {nuevo[0]}:{nuevo[1]}")
                        servidor_actual = nuevo
                        fallos = 0
                    else:
                        print("[INFO] No hay servidores disponibles. Cerrando cliente.")
                        break

            time.sleep(intervalo)

    except KeyboardInterrupt:
        print("\n[INFO] Cliente detenido manualmente.")
    finally:
        canal.cerrar()


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detector de caída de servidor (CU3)")
    parser.add_argument("ip_servidor", help="IP del servidor inicial")
    parser.add_argument(
        "--modo-fallo",
        action="store_true",
        help="Activa el stub en modo fallo para probar la detección de caída",
    )
    args = parser.parse_args()

    config = _cargar_config()
    servidor = (args.ip_servidor, config["PUERTO_TCP"])
    ejecutar(servidor, modo_fallo=args.modo_fallo)
