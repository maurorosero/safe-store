# SPDX-License-Identifier: MIT
"""Cifrado simétrico de los campos sensibles de una config entry.

Este módulo es autocontenido a propósito: no importa nada del paquete, para que
las pruebas puedan cargarlo sin arrastrar Home Assistant.
"""

from __future__ import annotations

import base64
import json
import os
from collections.abc import Mapping
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Marca que identifica un data cifrado dentro de core.config_entries.
MARCA = "__ss_v1__"

# Datos asociados al cifrado (AAD): ata el blob a su propósito.
AAD = b"safe_store:core.config_entries"


def cifrar(aes: AESGCM, data: Mapping[str, Any]) -> dict[str, str]:
    """Devuelve el data envuelto en un blob AES-256-GCM."""
    nonce = os.urandom(12)
    blob = aes.encrypt(nonce, json.dumps(dict(data)).encode(), AAD)
    return {MARCA: base64.b64encode(nonce + blob).decode()}


def descifrar(aes: AESGCM, payload: Mapping[str, Any]) -> dict[str, Any]:
    """Descifra el blob y conserva lo que otras partes hayan añadido al data."""
    raw = base64.b64decode(payload[MARCA])
    base: dict[str, Any] = json.loads(aes.decrypt(raw[:12], raw[12:], AAD))
    base.update({k: v for k, v in payload.items() if k != MARCA})
    return base


def esta_cifrado(data: Any) -> bool:
    """True si el data contiene la marca de cifrado."""
    return isinstance(data, Mapping) and MARCA in data
