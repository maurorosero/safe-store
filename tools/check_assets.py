# SPDX-License-Identifier: MIT
"""Valida los assets que Home Assistant y el Marketplace esperan.

- brand/icon.png y brand/logo.png de la integración.
- icon.png 128x128 y logo.png 250x100 del add-on.
- translations/en.json con las mismas claves que strings.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parents[1]
COMP = RAIZ / "custom_components" / "safe_store"
ADDON = RAIZ / "secrets_unlocker"

errores: list[str] = []


def _claves(datos: object, prefijo: str = "") -> set[str]:
    """Aplana un JSON de traducciones en rutas de claves."""
    salida: set[str] = set()
    if isinstance(datos, dict):
        for clave, valor in datos.items():
            ruta = f"{prefijo}.{clave}" if prefijo else clave
            salida.add(ruta)
            salida |= _claves(valor, ruta)
    return salida


for ruta in (COMP / "brand" / "icon.png", COMP / "brand" / "logo.png"):
    if not ruta.exists():
        errores.append(f"falta {ruta.relative_to(RAIZ)}")

esperado = {
    ADDON / "icon.png": (128, 128),
    ADDON / "logo.png": (250, 100),
}
for ruta, tam in esperado.items():
    if not ruta.exists():
        errores.append(f"falta {ruta.relative_to(RAIZ)}")
        continue
    real = Image.open(ruta).size
    if real != tam:
        errores.append(f"{ruta.relative_to(RAIZ)} mide {real}, se espera {tam}")

strings = json.loads((COMP / "strings.json").read_text())
ingles = json.loads((COMP / "translations" / "en.json").read_text())
faltan = _claves(strings) - _claves(ingles)
if faltan:
    errores.append(f"translations/en.json no cubre: {sorted(faltan)}")

if errores:
    for e in errores:
        print(f"error: {e}", file=sys.stderr)
    sys.exit(1)

print("assets: ok")
