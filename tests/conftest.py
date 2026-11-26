# SPDX-License-Identifier: MIT
"""Carga crypto.py por ruta, sin ejecutar el __init__ del componente (que importa HA)."""

import importlib.util
import sys
from pathlib import Path

RUTA = Path(__file__).resolve().parents[1] / "custom_components" / "safe_store" / "crypto.py"

spec = importlib.util.spec_from_file_location("safe_store_crypto", RUTA)
assert spec and spec.loader
modulo = importlib.util.module_from_spec(spec)
sys.modules["safe_store_crypto"] = modulo
spec.loader.exec_module(modulo)
