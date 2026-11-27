# SPDX-License-Identifier: MIT
"""Dobles mínimos para correr los tests sin Home Assistant instalado.

El componente importa `homeassistant.core`, `homeassistant.config_entries` y
`aiohttp`. Los tests usan una parte pequeña de esos módulos, así que se siembran
versiones mínimas: el CI no necesita instalar Home Assistant entero y el test
sigue siendo unitario.
"""

import importlib.util
import sys
import types
from pathlib import Path


def _sembrar_dobles() -> None:
    if "homeassistant" in sys.modules:
        return

    aiohttp = types.ModuleType("aiohttp")

    class ClientTimeout:
        def __init__(self, total=None):
            self.total = total

    class ClientSession:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        def get(self, *args, **kwargs):
            raise RuntimeError("los tests no salen a la red")

        def post(self, *args, **kwargs):
            raise RuntimeError("los tests no salen a la red")

    class ClientError(Exception):
        pass

    aiohttp.ClientTimeout = ClientTimeout
    aiohttp.ClientSession = ClientSession
    aiohttp.ClientError = ClientError
    sys.modules["aiohttp"] = aiohttp

    core = types.ModuleType("homeassistant.core")

    class HomeAssistant:
        pass

    class ServiceCall:
        pass

    def callback(func):
        return func

    core.HomeAssistant = HomeAssistant
    core.ServiceCall = ServiceCall
    core.callback = callback

    config_entries = types.ModuleType("homeassistant.config_entries")

    class ConfigEntry:
        pass

    class ConfigEntries:
        """Solo lo que el shim hereda y usa."""

        def __init__(self):
            self._entries = {}
            self.hass = None

        async def async_initialize(self):
            return None

        def async_update_entry(self, entry, data=None, **kwargs):
            if data is not None:
                entry.data = dict(data)

        async def async_reload(self, entry_id):
            return None

    config_entries.ConfigEntry = ConfigEntry
    config_entries.ConfigEntries = ConfigEntries

    exceptions = types.ModuleType("homeassistant.exceptions")

    class ConfigEntryNotReady(Exception):  # noqa: N818 - replica el nombre de HA
        pass

    exceptions.ConfigEntryNotReady = ConfigEntryNotReady

    http = types.ModuleType("homeassistant.components.http")

    class HomeAssistantView:
        url = ""
        name = ""
        requires_auth = True

        @staticmethod
        def json_message(mensaje, status_code=200):
            return {"mensaje": mensaje, "status": status_code}

        @staticmethod
        def json(datos, status_code=200):
            return datos

        @staticmethod
        def response(datos, content_type=None, headers=None):
            return datos

    http.HomeAssistantView = HomeAssistantView

    frontend = types.ModuleType("homeassistant.components.frontend")
    frontend.async_register_built_in_panel = lambda *a, **k: None

    components = types.ModuleType("homeassistant.components")
    components.http = http
    components.frontend = frontend

    homeassistant = types.ModuleType("homeassistant")
    homeassistant.core = core
    homeassistant.config_entries = config_entries
    homeassistant.exceptions = exceptions
    homeassistant.components = components

    for nombre, modulo in (
        ("homeassistant", homeassistant),
        ("homeassistant.core", core),
        ("homeassistant.config_entries", config_entries),
        ("homeassistant.exceptions", exceptions),
        ("homeassistant.components", components),
        ("homeassistant.components.http", http),
        ("homeassistant.components.frontend", frontend),
    ):
        sys.modules[nombre] = modulo


_sembrar_dobles()

RUTA = Path(__file__).resolve().parents[1] / "custom_components" / "safe_store" / "crypto.py"

spec = importlib.util.spec_from_file_location("safe_store_crypto", RUTA)
assert spec and spec.loader
modulo = importlib.util.module_from_spec(spec)
sys.modules["safe_store_crypto"] = modulo
spec.loader.exec_module(modulo)
