# SPDX-License-Identifier: MIT
"""Safe Store: cifrado en reposo del data de core.config_entries.

El core lee core.config_entries una sola vez, antes de cargar los custom
components. Por eso el shim hace dos cosas: intercepta el guardado para cifrar,
y descifra en caliente lo que ya se cargó, recargando las entradas afectadas.

Sin master key disponible no se arma: el archivo queda como está y HA sigue en
modo tradicional. Con el archivo cifrado y sin key, no escribe nada (escribir
datos a medio cifrar corrompe todas las integraciones a la vez).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
from typing import Any

import aiohttp
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from homeassistant.config_entries import ConfigEntries, ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    ADDON_PORT,
    ADDON_SLUG,
    ADDON_TIMEOUT,
    DUMP_FILE,
    EXCLUIDOS,
    STORAGE_FILE,
    SUPERVISOR_URL,
    TOKEN_FILE,
)
from .crypto import MARCA, cifrar, descifrar, esta_cifrado
from .paper import async_setup_panel

_LOGGER = logging.getLogger(__name__)

_aes: AESGCM | None = None


# --------------------------------------------------------------------------- #
# Obtención de la master key
# --------------------------------------------------------------------------- #
def _leer_o_crear_token() -> str:
    """Token compartido con el add-on. Se crea la primera vez, con 600."""
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text().strip()
    token = secrets.token_hex(32)
    TOKEN_FILE.write_text(token)
    os.chmod(TOKEN_FILE, 0o600)
    _LOGGER.warning("safe_store: token del add-on creado en %s", TOKEN_FILE)
    return token


async def _url_addon() -> str | None:
    """Pregunta al Supervisor dónde escucha el add-on.

    El listado no trae la dirección: hay que pedir el detalle del add-on. Se
    prefiere su IP, que no depende de la resolución de nombres interna.
    """
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        return None

    cabeceras = {"Authorization": f"Bearer {token}"}
    timeout = aiohttp.ClientTimeout(total=ADDON_TIMEOUT)
    try:
        async with aiohttp.ClientSession(timeout=timeout, headers=cabeceras) as sesion:
            async with sesion.get(f"{SUPERVISOR_URL}/addons") as resp:
                if resp.status != 200:
                    return None
                listado = await resp.json()

            slug = next(
                (
                    addon["slug"]
                    for addon in (listado.get("data") or {}).get("addons", [])
                    if str(addon.get("slug", "")).endswith(ADDON_SLUG)
                ),
                None,
            )
            if not slug:
                return None

            async with sesion.get(f"{SUPERVISOR_URL}/addons/{slug}/info") as resp:
                if resp.status != 200:
                    return None
                detalle = await resp.json()
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        _LOGGER.warning("safe_store: no pude consultar el add-on: %s", err)
        return None

    datos = detalle.get("data") or {}
    host = datos.get("ip_address") or datos.get("hostname")
    return f"http://{host}:{ADDON_PORT}/unlock" if host else None


async def _clave_desde_addon(hass: HomeAssistant) -> bytes | None:
    """Pide la master key al add-on. Devuelve None si no está disponible."""
    url = await _url_addon()
    if not url:
        _LOGGER.info("safe_store: el add-on no está disponible")
        return None

    try:
        token = await hass.async_add_executor_job(_leer_o_crear_token)
        timeout = aiohttp.ClientTimeout(total=ADDON_TIMEOUT)
        async with (
            aiohttp.ClientSession(timeout=timeout) as sesion,
            sesion.post(url, headers={"Authorization": f"Bearer {token}"}) as resp,
        ):
            if resp.status != 200:
                _LOGGER.warning("safe_store: el add-on respondió %s, sigo sin key", resp.status)
                return None
            cuerpo = await resp.json()
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        _LOGGER.warning("safe_store: no pude hablar con el add-on: %s", err)
        return None

    clave = cuerpo.get("key") if isinstance(cuerpo, dict) else None
    if not clave:
        return None
    try:
        return bytes.fromhex(clave)
    except ValueError:
        _LOGGER.error("safe_store: el add-on devolvió una key con formato inválido")
        return None


def _archivo_cifrado() -> bool:
    """¿El archivo de entradas ya está cifrado?

    Si lo está y el add-on no responde, no se puede generar una clave nueva:
    las entradas viejas quedarían ilegibles para siempre.
    """
    try:
        return MARCA in STORAGE_FILE.read_text(encoding="utf-8")
    except OSError:
        return False


async def _obtener_clave(hass: HomeAssistant) -> bytes | None:
    """Add-on primero. Sin add-on no hay clave: nunca se inventa una.

    Generar una clave local cuando el add-on todavía no arrancó deja dos claves
    distintas en el sistema: la local y la que el add-on crea despues. El
    archivo queda cifrado con una que el add-on no conoce, y nada lo puede leer.
    Es preferible que la integracion quede en reintento y el add-on entregue la
    suya cuando este.
    """
    if (clave := await _clave_desde_addon(hass)) is not None:
        _LOGGER.info("safe_store: master key obtenida del add-on")
        return clave

    if await hass.async_add_executor_job(_archivo_cifrado):
        _LOGGER.error(
            "safe_store: el archivo está cifrado y el add-on no responde. "
            "No se crea una clave nueva para no dejarlo ilegible."
        )
    else:
        _LOGGER.error(
            "safe_store: el add-on no responde. No se crea una clave local: "
            "quedaría distinta de la del add-on y el archivo sería ilegible."
        )
    return None


# --------------------------------------------------------------------------- #
# Descifrado de entradas vivas
# --------------------------------------------------------------------------- #
def _descifrar_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Descifra entry.data con la API oficial. Devuelve True si cambió algo."""
    if _aes is None or not esta_cifrado(entry.data):
        return False
    hass.config_entries.async_update_entry(entry, data=descifrar(_aes, entry.data))
    # El fragmento serializado está cacheado sobre el data viejo.
    entry.__dict__.pop("as_storage_fragment", None)
    return True


# --------------------------------------------------------------------------- #
# Clase que reemplaza a ConfigEntries en runtime
# --------------------------------------------------------------------------- #
def _a_dict(frag: Any) -> dict[str, Any]:
    """Convierte el fragmento del core en un dict mutable.

    `as_storage_fragment` devuelve un `orjson.Fragment`, que es opaco: no expone
    su contenido. Se recupera serializandolo y volviendolo a leer, para cambiar
    solo el `data` y conservar todos los campos que armo Home Assistant.
    """
    if isinstance(frag, dict):
        return dict(frag)
    import orjson

    return orjson.loads(orjson.dumps(frag))


class SafeConfigEntries(ConfigEntries):
    """Cifra el data de cada entrada antes de escribir el archivo."""

    @callback
    def _data_to_save(self) -> dict[str, list[dict[str, Any]]]:
        """Cifra el data de cada entrada sobre lo que ya arma Home Assistant.

        Se parte del resultado de super() para no perder campos que el core
        agregue al archivo: aca solo se transforma el `data` de cada entrada.
        Si una entrada no se puede cifrar, se aborta el guardado en vez de
        escribirla en claro.
        """
        datos = super()._data_to_save()
        if not isinstance(datos, dict) or not isinstance(datos.get("entries"), list):
            _LOGGER.error(
                "safe_store: el core devolvió un formato inesperado; no se escribe el archivo"
            )
            return datos
        if not datos["entries"] and self._entries:
            _LOGGER.error(
                "safe_store: el core devolvió cero entradas habiendo %s; no se escribe",
                len(self._entries),
            )
            raise RuntimeError("safe_store: no se escribe un archivo vacio")
        entradas: list[dict[str, Any]] = []
        for frag in datos["entries"]:
            trozo = _a_dict(frag)
            if trozo.get("domain") in EXCLUIDOS or _aes is None:
                entradas.append(trozo)
                continue
            data = trozo.get("data") or {}
            if esta_cifrado(data):
                entradas.append(trozo)
                continue
            try:
                trozo["data"] = cifrar(_aes, data)
            except Exception:
                _LOGGER.exception(
                    "safe_store: no pude cifrar %s, no se escribe el archivo",
                    trozo.get("domain"),
                )
                raise
            entradas.append(trozo)
        return {"entries": entradas}

    async def async_initialize(self) -> None:
        """Carga normal y después descifra lo que venga cifrado."""
        await super().async_initialize()
        cambiadas = sum(1 for e in self._entries.values() if _descifrar_entry(self.hass, e))
        if cambiadas:
            _LOGGER.warning("safe_store: %s entradas descifradas al cargar", cambiadas)


# --------------------------------------------------------------------------- #
# Servicio de emergencia
# --------------------------------------------------------------------------- #
def _registrar_servicios(hass: HomeAssistant) -> None:
    async def _dump(call: ServiceCall) -> None:
        """Escribe el archivo en claro. Obligatorio antes de desinstalar."""
        if _aes is None:
            _LOGGER.error("safe_store: sin master key, no puedo volcar")
            return

        entradas: list[dict[str, Any]] = []
        for entry in hass.config_entries._entries.values():
            frag = entry.as_dict()
            data = dict(entry.data)
            if entry.domain not in EXCLUIDOS and esta_cifrado(data):
                data = descifrar(_aes, data)
            frag["data"] = data
            entradas.append(frag)

        def _escribir() -> None:
            DUMP_FILE.write_text(json.dumps({"entries": entradas}, indent=2, ensure_ascii=False))
            os.chmod(DUMP_FILE, 0o600)

        await hass.async_add_executor_job(_escribir)
        _LOGGER.warning("safe_store: volcado en claro en %s", DUMP_FILE)

    hass.services.async_register("safe_store", "dump", _dump)


# --------------------------------------------------------------------------- #
# Setup / unload
# --------------------------------------------------------------------------- #
async def _recargar_de_a_una(hass: HomeAssistant, entry_ids: list[str]) -> None:
    """Recarga las entradas una detrás de otra, sin saturar el event loop."""
    for entry_id in entry_ids:
        await hass.config_entries.async_reload(entry_id)
        await asyncio.sleep(0.2)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Arma el shim. Si no hay key, no se arma y HA queda en modo tradicional."""
    global _aes

    clave = await _obtener_clave(hass)
    if clave is None:
        raise ConfigEntryNotReady("safe_store: sin master key disponible")

    _aes = AESGCM(clave)

    if not isinstance(hass.config_entries, SafeConfigEntries):
        clase_previa = type(hass.config_entries).__name__
        hass.config_entries.__class__ = SafeConfigEntries
        _LOGGER.warning("safe_store: ConfigEntries %s -> SafeConfigEntries", clase_previa)

    # Puente: el core ya cargó el archivo antes de este setup.
    descifradas: list[str] = []
    for viva in list(hass.config_entries._entries.values()):
        if _descifrar_entry(hass, viva):
            descifradas.append(viva.entry_id)
    if descifradas:
        _LOGGER.warning("safe_store: puente de arranque, %s entradas", len(descifradas))

    # Solo se recargan las que se acaban de descifrar y quedaron en error: son
    # las que fallaron por leer datos cifrados. Lanzarlas todas de golpe deja
    # una tormenta de recargas en el log y compite por el mismo event loop.
    pendientes = [
        entry_id
        for entry_id in descifradas
        if (viva := hass.config_entries._entries.get(entry_id)) is not None
        and viva.state.name in ("SETUP_ERROR", "SETUP_RETRY")
    ]
    if pendientes:
        hass.async_create_task(_recargar_de_a_una(hass, pendientes))

    _registrar_servicios(hass)
    async_setup_panel(hass, clave)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """No se desarma: la clase sigue puesta hasta el próximo reinicio."""
    _LOGGER.warning(
        "safe_store: la integración se descargó, pero el shim sigue activo "
        "hasta reiniciar. Ejecutá safe_store.dump si vas a desinstalar."
    )
    return True
