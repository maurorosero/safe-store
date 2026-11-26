# SPDX-License-Identifier: MIT
"""Constants for the Safe Store integration."""

from __future__ import annotations

from pathlib import Path

from .crypto import AAD, MARCA  # noqa: F401 - se reexportan

DOMAIN = "safe_store"

# Clave local, solo para instalaciones sin el add-on.
KEY_FILE = Path("/config/.ss.key")

# Token compartido con el add-on para autorizar el endpoint local.
TOKEN_FILE = Path("/config/.ss.token")

# Salida de emergencia: el archivo en claro que hace falta antes de desinstalar.
DUMP_FILE = Path("/config/.ss_dump.json")

# Add-on que entrega la master key.
ADDON_HOST = "secrets-unlocker"
ADDON_PORT = 8099
ADDON_UNLOCK = f"http://{ADDON_HOST}:{ADDON_PORT}/unlock"
ADDON_TIMEOUT = 10

# Dominios cuyo data escribe otra parte (el Supervisor) y no contiene credenciales.
EXCLUIDOS = frozenset({"hassio"})
