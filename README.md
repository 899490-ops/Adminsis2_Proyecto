# Adminsis2 — Sistema de Monitorización Distribuida

Sistema de monitorización distribuido con tolerancia a fallos para entornos Linux.
Gestiona N servidores y N clientes de forma autónoma, sin intervención del administrador.

---

## Estructura del proyecto

```
src/
├── cliente/
│   └── tolerancia_fallos/
│       ├── detector_servidor.py     # CU3 — Detecta caída del servidor y se reconecta
│       └── reconexion.py            # Lógica de reconexión a un nuevo servidor
└── servidor/
    ├── monitorizacion/
    │   └── logger.py                # Módulo de log compartido — usar desde cualquier componente
    ├── logs/
    │   └── eventos.log              # Fichero de eventos (generado en tiempo de ejecución)
    └── tolerancia_fallos/
        └── monitor_clientes.py      # CU4 — Detecta caída de clientes y notifica al admin

config/
└── config.json                      # Parámetros globales del sistema
```

---

## Módulos disponibles para el equipo

### `src/servidor/monitorizacion/logger.py` — Log de eventos (TODOS)

Módulo compartido para escribir en `src/servidor/logs/eventos.log`.
**Solo el servidor escribe en el log** (SRV-6).

```python
from monitorizacion.logger import _log

_log(ruta_log, "CAIDA_CLIENTE", "client_ip=192.168.1.20")
_log(ruta_log, "CAIDA_SERVIDOR", "server_ip=192.168.1.10")
_log(ruta_log, "RECONEXION",    "client_ip=192.168.1.30")
```

Formato de salida:
```
[2026-04-16 10:23:01] [CAIDA_SERVIDOR  ] server_ip=192.168.1.10
[2026-04-16 10:23:06] [RECONEXION      ] client_ip=192.168.1.30
[2026-04-16 10:25:00] [CAIDA_CLIENTE   ] client_ip=192.168.1.20
```

La ruta del log se obtiene desde `config.json` (`LOG_PATH`).

---

### `src/servidor/tolerancia_fallos/monitor_clientes.py` — CU4 (Persona 3)

Monitoriza los clientes asignados al servidor mediante heartbeats.
Detecta caídas y notifica al administrador.

**Mensajes que maneja:**

| Mensaje entrante | Acción |
|---|---|
| `HEARTBEAT` | Actualiza timestamp del cliente |
| `RECONNECT_REQUEST client server_caido=<ip>` | Registra caída del servidor anterior y acepta al cliente |

**Uso:**
```bash
cd src/servidor/tolerancia_fallos
python3 monitor_clientes.py <ip1> [<ip2> ...] [--modo-fallo <ip>]

# Ejemplo — monitorizar dos clientes:
python3 monitor_clientes.py 192.168.1.20 192.168.1.21

# Ejemplo — simular caída del cliente 192.168.1.20 (prueba CU4):
python3 monitor_clientes.py 192.168.1.20 --modo-fallo 192.168.1.20
```

---

### `src/cliente/tolerancia_fallos/detector_servidor.py` — CU3 (Persona 3)

Envía heartbeats al servidor asignado. Si el servidor no responde tras `MAX_FALLOS`
intentos, busca un nuevo servidor y se reconecta de forma transparente.
Al reconectarse informa al nuevo servidor del servidor que ha caído.

**Uso:**
```bash
cd src/cliente/tolerancia_fallos
python3 detector_servidor.py <ip_servidor> [--modo-fallo]

# Ejemplo — conectarse al servidor 192.168.1.10:
python3 detector_servidor.py 192.168.1.10

# Ejemplo — simular caída del servidor (prueba CU3):
python3 detector_servidor.py 192.168.1.10 --modo-fallo
```

---

## Protocolo de mensajes (acordado con Persona 2)

| Mensaje | Dirección | Descripción |
|---|---|---|
| `HEARTBEAT` | Cliente → Servidor | Comprobación de vida periódica |
| `HEARTBEAT_ACK` | Servidor → Cliente | Confirmación de que el servidor sigue activo |
| `RECONNECT_REQUEST client server_caido=<ip>` | Cliente → Nuevo Servidor | Solicitud de reconexión tras caída |
| `RECONNECT_OK` | Nuevo Servidor → Cliente | Reconexión aceptada |
| `CLIENT_DOWN` | Servidor → Admin | Notificación de caída de cliente |

---

## Configuración (`config/config.json`)

| Parámetro | Valor | Descripción |
|---|---|---|
| `HEARTBEAT_INTERVAL` | 3 | Segundos entre heartbeats |
| `HEARTBEAT_TIMEOUT` | 5 | Segundos máximos de espera de respuesta |
| `MAX_FALLOS` | 3 | Fallos consecutivos para declarar caída |
| `PUERTO_TCP` | 9000 | Puerto de comunicación entre nodos |
| `LOG_PATH` | `src/servidor/logs/eventos.log` | Ruta del fichero de eventos |

---