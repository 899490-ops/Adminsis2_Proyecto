"""
Cliente de monitorización — RU4 (Persona 4: Monitorización y métricas)

Lógica principal del cliente:
  - Se registra en un servidor en ejecución.
  - Captura métricas locales del nodo Linux.
  - Envía periódicamente dichas métricas al servidor asignado.
  - Si el servidor responde con una reasignación, cambia al nuevo servidor
    de forma transparente y continúa enviando métricas.
  - Si el servidor no responde MAX_FALLOS veces consecutivas, intenta
    conectarse a otro servidor conocido (CU3 / RC6).
  - Si no hay ningún servidor disponible, termina su ejecución (RC3).

Uso:
    python cliente_monitor.py [<ip_servidor>] [--puerto 9000]
    python cliente_monitor.py --servidores 127.0.0.1:9000 127.0.0.1:9001

    Sin <ip_servidor> el cliente descubre el servidor automáticamente (RC1).
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import pwd
import shutil
import socket
import sys
import time
from typing import Any


# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

def _cargar_config() -> dict[str, Any]:
    ruta = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "config", "config.json"
    )
    with open(os.path.normpath(ruta), encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Métricas locales
# ---------------------------------------------------------------------------

def _leer_texto(ruta: str) -> str:
    try:
        with open(ruta, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def _interfaces_validas() -> list[str]:
    base = "/sys/class/net"
    if not os.path.isdir(base):
        return []

    interfaces = []
    for nombre in os.listdir(base):
        if nombre == "lo":
            continue
        if os.path.isdir(os.path.join(base, nombre)):
            interfaces.append(nombre)
    return sorted(interfaces)


def _tx_bytes_total() -> int:
    total = 0
    for interfaz in _interfaces_validas():
        ruta = f"/sys/class/net/{interfaz}/statistics/tx_bytes"
        try:
            total += int(_leer_texto(ruta) or "0")
        except ValueError:
            pass
    return total


def _usuarios_sistema() -> list[str]:
    usuarios = []
    for entrada in pwd.getpwall():
        if entrada.pw_uid >= 1000 and "nologin" not in entrada.pw_shell:
            usuarios.append(entrada.pw_name)
    return sorted(set(usuarios))


def _leer_meminfo() -> dict[str, int]:
    datos: dict[str, int] = {}
    try:
        with open("/proc/meminfo", encoding="utf-8") as f:
            for linea in f:
                partes = linea.replace(":", "").split()
                if len(partes) >= 2:
                    datos[partes[0]] = int(partes[1])
    except OSError:
        pass
    return datos


def _almacenamiento() -> dict[str, Any]:
    uso = shutil.disk_usage("/")
    dispositivos = []
    if os.path.isdir("/sys/block"):
        for nombre in sorted(os.listdir("/sys/block")):
            dispositivos.append(nombre)

    return {
        "raiz_total_bytes": uso.total,
        "raiz_usado_bytes": uso.used,
        "raiz_libre_bytes": uso.free,
        "dispositivos": dispositivos,
    }


def _tarjetas_red() -> list[dict[str, str]]:
    tarjetas = []
    for interfaz in _interfaces_validas():
        tarjetas.append(
            {
                "nombre": interfaz,
                "mac": _leer_texto(f"/sys/class/net/{interfaz}/address") or "desconocida",
                "estado": _leer_texto(f"/sys/class/net/{interfaz}/operstate") or "unknown",
            }
        )
    return tarjetas


def _leer_cpu_snapshot() -> tuple[int, int]:
    try:
        with open("/proc/stat", encoding="utf-8") as f:
            linea = f.readline().split()
    except OSError:
        return (0, 0)

    if not linea or linea[0] != "cpu":
        return (0, 0)

    valores = [int(x) for x in linea[1:]]
    idle = valores[3] + (valores[4] if len(valores) > 4 else 0)
    total = sum(valores)
    return idle, total


def _calcular_cpu_pct(anterior: tuple[int, int], actual: tuple[int, int]) -> float:
    idle_ant, total_ant = anterior
    idle_act, total_act = actual

    delta_idle = idle_act - idle_ant
    delta_total = total_act - total_ant

    if delta_total <= 0:
        return 0.0

    uso = 100.0 * (1.0 - (delta_idle / delta_total))
    return round(max(0.0, min(100.0, uso)), 2)


def _carga_media() -> dict[str, float]:
    try:
        uno, cinco, quince = os.getloadavg()
        return {
            "loadavg_1": round(uno, 2),
            "loadavg_5": round(cinco, 2),
            "loadavg_15": round(quince, 2),
        }
    except OSError:
        return {
            "loadavg_1": 0.0,
            "loadavg_5": 0.0,
            "loadavg_15": 0.0,
        }


def capturar_metricas(
    id_cliente: str,
    cpu_anterior: tuple[int, int],
    tx_anterior: int,
    instante_anterior: float,
) -> tuple[dict[str, Any], tuple[int, int], int, float]:
    ahora = time.time()
    actual_cpu = _leer_cpu_snapshot()
    actual_tx = _tx_bytes_total()
    meminfo = _leer_meminfo()

    mem_total_kb = meminfo.get("MemTotal", 0)
    mem_disp_kb = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
    mem_usada_kb = max(0, mem_total_kb - mem_disp_kb)
    mem_pct = round((mem_usada_kb / mem_total_kb) * 100, 2) if mem_total_kb else 0.0

    intervalo = max(1e-6, ahora - instante_anterior)
    subida_bps = round((actual_tx - tx_anterior) / intervalo, 2)

    metricas = {
        "type": "METRICS",
        "client_id": id_cliente,
        "client_ip": _mi_ip(),
        "timestamp": round(ahora, 3),
        "bandwidth_upload_Bps": max(0.0, subida_bps),
        "system": {
            "hostname": platform.node(),
            "os": platform.system(),
            "os_version": platform.version(),
            "platform": platform.platform(),
            "kernel": platform.release(),
            "arquitectura": platform.machine(),
        },
        "users": _usuarios_sistema(),
        "cpu": {
            "cores": os.cpu_count() or 1,
            "usage_pct": _calcular_cpu_pct(cpu_anterior, actual_cpu),
            **_carga_media(),
        },
        "memory": {
            "total_kb": mem_total_kb,
            "used_kb": mem_usada_kb,
            "available_kb": mem_disp_kb,
            "usage_pct": mem_pct,
        },
        "storage": _almacenamiento(),
        "network": {
            "interfaces": _tarjetas_red(),
        },
    }

    return metricas, actual_cpu, actual_tx, ahora


# ---------------------------------------------------------------------------
# Comunicación
# ---------------------------------------------------------------------------

def _mi_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return socket.gethostbyname(socket.gethostname())
    finally:
        s.close()


def _enviar_mensaje(ip: str, puerto: int, payload: dict[str, Any]) -> str | None:
    mensaje = (json.dumps(payload) + "\n").encode("utf-8")

    try:
        with socket.create_connection((ip, puerto), timeout=5) as sock:
            sock.sendall(mensaje)
            sock.shutdown(socket.SHUT_WR)
            respuesta = sock.recv(4096)
    except OSError:
        return None

    if not respuesta:
        return None
    return respuesta.decode("utf-8").strip()


def _registrar_cliente(ip: str, puerto: int, id_cliente: str, servidores: list[str]) -> str | None:
    payload = {
        "type": "REGISTER",
        "client_id": id_cliente,
        "client_ip": _mi_ip(),
        "known_servers": servidores,
    }
    return _enviar_mensaje(ip, puerto, payload)


def _parsear_destino(texto: str) -> tuple[str, int] | None:
    partes = texto.split()
    if len(partes) != 3 or partes[0] != "REASSIGN":
        return None

    ip = partes[1]
    try:
        puerto = int(partes[2])
    except ValueError:
        return None
    return ip, puerto


# ---------------------------------------------------------------------------
# Autodiscovery UDP (RC1)
# ---------------------------------------------------------------------------

def _descubrir_servidor(puerto_discovery: int, timeout: float = 3.0) -> tuple[str, int] | None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(timeout)
    try:
        sock.sendto(b"SERVIDOR_DISPONIBLE?", ("255.255.255.255", puerto_discovery))
        try:
            sock.sendto(b"SERVIDOR_DISPONIBLE?", ("127.0.0.1", puerto_discovery))
        except OSError:
            pass

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                datos, _ = sock.recvfrom(1024)
                respuesta = datos.decode("utf-8").strip()
                if respuesta.startswith("SERVIDOR "):
                    partes = respuesta.split()[1].split(":")
                    return partes[0], int(partes[1])
            except socket.timeout:
                break
    except OSError:
        pass
    finally:
        sock.close()
    return None


# ---------------------------------------------------------------------------
# Reconexión ante fallo de métricas (CU3 / RC6)
# ---------------------------------------------------------------------------

def _buscar_servidor_alternativo(
    servidor_caido: tuple[str, int],
    servidores_txt: list[str],
    puerto_default: int,
    id_cliente: str,
) -> tuple[str, int] | None:
    for txt in servidores_txt:
        partes = txt.split(":", 1)
        try:
            ip = partes[0].strip()
            p = int(partes[1].strip()) if len(partes) > 1 else puerto_default
        except ValueError:
            continue
        if (ip, p) == servidor_caido:
            continue
        resp = _registrar_cliente(ip, p, id_cliente, servidores_txt)
        if resp == "REGISTER_OK":
            return (ip, p)
    return None


# ---------------------------------------------------------------------------
# Bucle principal
# ---------------------------------------------------------------------------

def ejecutar(
    ip_servidor: str,
    puerto: int,
    intervalo: float,
    id_cliente: str,
    servidores: list[str],
    max_fallos: int,
) -> None:
    cpu_anterior = _leer_cpu_snapshot()
    tx_anterior = _tx_bytes_total()
    instante_anterior = time.time()

    servidor_actual = (ip_servidor, puerto)

    respuesta = _registrar_cliente(ip_servidor, puerto, id_cliente, servidores)
    if respuesta is None:
        print("[ERROR] No se ha podido registrar el cliente en el servidor inicial.")
        return

    print(f"[INFO] Cliente monitorizado por {servidor_actual[0]}:{servidor_actual[1]}")

    fallos_consecutivos = 0

    try:
        while True:
            metricas, cpu_anterior, tx_anterior, instante_anterior = capturar_metricas(
                id_cliente=id_cliente,
                cpu_anterior=cpu_anterior,
                tx_anterior=tx_anterior,
                instante_anterior=instante_anterior,
            )

            respuesta = _enviar_mensaje(servidor_actual[0], servidor_actual[1], metricas)

            if respuesta is None:
                fallos_consecutivos += 1
                print(f"[WARN] Sin respuesta del servidor ({fallos_consecutivos}/{max_fallos})")

                if fallos_consecutivos >= max_fallos:
                    print(f"[INFO] Servidor {servidor_actual[0]} no responde. Buscando alternativa.")
                    nuevo = _buscar_servidor_alternativo(
                        servidor_caido=servidor_actual,
                        servidores_txt=servidores,
                        puerto_default=puerto,
                        id_cliente=id_cliente,
                    )
                    if nuevo is not None:
                        servidor_actual = nuevo
                        fallos_consecutivos = 0
                        print(f"[INFO] Cliente reasignado a {servidor_actual[0]}:{servidor_actual[1]}")
                    else:
                        print("[INFO] No hay servidores disponibles. Cerrando cliente.")
                        return

            elif respuesta == "METRICS_OK":
                fallos_consecutivos = 0

            elif respuesta.startswith("REASSIGN"):
                nuevo = _parsear_destino(respuesta)
                if nuevo is not None:
                    servidor_actual = nuevo
                    fallos_consecutivos = 0
                    print(f"[INFO] Cliente reasignado a {servidor_actual[0]}:{servidor_actual[1]}")
                    _registrar_cliente(
                        servidor_actual[0],
                        servidor_actual[1],
                        id_cliente,
                        servidores,
                    )

            time.sleep(intervalo)

    except KeyboardInterrupt:
        print("\n[INFO] Cliente de monitorización detenido manualmente.")


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cliente de monitorización (RU4)")
    parser.add_argument(
        "ip_servidor",
        nargs="?",
        default=None,
        help="IP del servidor inicial (omitir para descubrimiento automático)",
    )
    parser.add_argument(
        "--puerto",
        type=int,
        default=None,
        help="Puerto TCP del servidor (por defecto, el de config.json)",
    )
    parser.add_argument(
        "--intervalo",
        type=float,
        default=3.0,
        help="Segundos entre envíos de métricas",
    )
    parser.add_argument(
        "--id-cliente",
        default=platform.node() or socket.gethostname() or "cliente",
        help="Identificador lógico del cliente",
    )
    parser.add_argument(
        "--servidores",
        nargs="*",
        default=[],
        help="Lista conocida de servidores en formato ip:puerto",
    )
    args = parser.parse_args()

    config = _cargar_config()
    puerto = args.puerto if args.puerto is not None else int(config["PUERTO_TCP"])
    max_fallos = int(config["MAX_FALLOS"])
    puerto_discovery = int(config.get("PUERTO_DISCOVERY", 9099))

    ip_servidor = args.ip_servidor
    if ip_servidor is None:
        print("[INFO] Sin servidor indicado. Buscando servidor en la red...")
        descubierto = _descubrir_servidor(puerto_discovery)
        if descubierto is not None:
            ip_servidor, puerto = descubierto
            print(f"[INFO] Servidor encontrado: {ip_servidor}:{puerto}")
        else:
            print("[ERROR] No se ha encontrado ningún servidor. Cerrando cliente.")
            sys.exit(1)

    ejecutar(
        ip_servidor=ip_servidor,
        puerto=puerto,
        intervalo=args.intervalo,
        id_cliente=args.id_cliente,
        servidores=args.servidores,
        max_fallos=max_fallos,
    )
