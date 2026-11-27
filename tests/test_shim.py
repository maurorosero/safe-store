# SPDX-License-Identifier: MIT
"""Unit tests del shim: cifrado al guardar, descifrado al cargar y dump.

No levantan Home Assistant. El shim recibe dobles mínimos que imitan solo lo
que usa: `_entries`, `as_dict()`, `async_update_entry` y el ejecutor.
"""

from __future__ import annotations

import json
import types

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

import custom_components.safe_store as ss
from custom_components.safe_store import crypto

CLAVE = AESGCM.generate_key(bit_length=256)


class EntradaFalsa:
    """Lo mínimo que el shim toca de un ConfigEntry."""

    def __init__(self, domain: str, data: dict, entry_id: str = "x") -> None:
        self.domain = domain
        self.data = dict(data)
        self.entry_id = entry_id

    def as_dict(self) -> dict:
        return {"domain": self.domain, "entry_id": self.entry_id, "data": dict(self.data)}


class HassFalso:
    """Lo mínimo que el shim toca del core."""

    def __init__(self, entradas: list[EntradaFalsa] | None = None) -> None:
        self.registros: dict[str, object] = {}
        contenedor = {e.entry_id: e for e in (entradas or [])}
        self.config_entries = types.SimpleNamespace(
            _entries=contenedor,
            async_update_entry=self._actualizar,
        )
        self.services = types.SimpleNamespace(
            async_register=lambda dominio, nombre, fn: self.registros.update({nombre: fn})
        )

    @staticmethod
    def _actualizar(entry: EntradaFalsa, data: dict) -> None:
        entry.data = dict(data)

    async def async_add_executor_job(self, fn, *args):
        return fn(*args)


def shim_con(entradas: list[EntradaFalsa]) -> ss.SafeConfigEntries:
    """Una instancia de la clase sin pasar por su __init__."""
    obj = object.__new__(ss.SafeConfigEntries)
    obj._entries = {e.entry_id: e for e in entradas}
    return obj


async def _sin_addon(_hass):
    return None


# --------------------------------------------------------------------------- #
# Guardado: _data_to_save
# --------------------------------------------------------------------------- #
def test_data_to_save_cifra_el_data(monkeypatch):
    monkeypatch.setattr(ss, "_aes", AESGCM(CLAVE))
    salida = shim_con([EntradaFalsa("ntfy", {"token": "t", "url": "u"})])._data_to_save()

    data = salida["entries"][0]["data"]
    assert crypto.MARCA in data
    assert crypto.descifrar(AESGCM(CLAVE), data) == {"token": "t", "url": "u"}


def test_data_to_save_no_toca_hassio(monkeypatch):
    monkeypatch.setattr(ss, "_aes", AESGCM(CLAVE))
    salida = shim_con([EntradaFalsa("hassio", {"user": "abc"})])._data_to_save()

    assert salida["entries"][0]["data"] == {"user": "abc"}
    assert "hassio" in ss.EXCLUIDOS


def test_data_to_save_no_recifra_lo_que_ya_esta_cifrado(monkeypatch):
    monkeypatch.setattr(ss, "_aes", AESGCM(CLAVE))
    cifrado = crypto.cifrar(AESGCM(CLAVE), {"a": "b"})
    salida = shim_con([EntradaFalsa("ntfy", cifrado)])._data_to_save()

    assert salida["entries"][0]["data"] == cifrado


def test_data_to_save_sin_clave_deja_el_data_intacto(monkeypatch):
    """Sin clave el shim no debería estar puesto; si lo estuviera, no cifra."""
    monkeypatch.setattr(ss, "_aes", None)
    salida = shim_con([EntradaFalsa("ntfy", {"token": "t"})])._data_to_save()

    assert salida["entries"][0]["data"] == {"token": "t"}


def test_data_to_save_devuelve_todas_las_entradas(monkeypatch):
    monkeypatch.setattr(ss, "_aes", AESGCM(CLAVE))
    entradas = [EntradaFalsa("ntfy", {"a": 1}, "1"), EntradaFalsa("hassio", {"b": 2}, "2")]
    salida = shim_con(entradas)._data_to_save()

    assert len(salida["entries"]) == 2


# --------------------------------------------------------------------------- #
# Carga: _descifrar_entry
# --------------------------------------------------------------------------- #
def test_descifrar_entry_actualiza_el_data(monkeypatch):
    monkeypatch.setattr(ss, "_aes", AESGCM(CLAVE))
    entrada = EntradaFalsa("ntfy", crypto.cifrar(AESGCM(CLAVE), {"a": 1}))
    hass = HassFalso([entrada])

    assert ss._descifrar_entry(hass, entrada) is True
    assert entrada.data == {"a": 1}


def test_descifrar_entry_ignora_lo_que_esta_en_claro(monkeypatch):
    monkeypatch.setattr(ss, "_aes", AESGCM(CLAVE))
    entrada = EntradaFalsa("ntfy", {"a": 1})

    assert ss._descifrar_entry(HassFalso([entrada]), entrada) is False
    assert entrada.data == {"a": 1}


def test_descifrar_entry_sin_clave_no_hace_nada(monkeypatch):
    monkeypatch.setattr(ss, "_aes", None)
    cifrado = crypto.cifrar(AESGCM(CLAVE), {"a": 1})
    entrada = EntradaFalsa("ntfy", cifrado)

    assert ss._descifrar_entry(HassFalso([entrada]), entrada) is False
    assert entrada.data == cifrado


# --------------------------------------------------------------------------- #
# Obtención de la clave
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_sin_addon_y_archivo_cifrado_no_crea_una_clave_nueva(monkeypatch, tmp_path):
    monkeypatch.setattr(ss, "_clave_desde_addon", _sin_addon)
    monkeypatch.setattr(ss, "_archivo_cifrado", lambda: True)
    monkeypatch.setattr(ss, "KEY_FILE", tmp_path / ".ss.key")

    assert await ss._obtener_clave(HassFalso()) is None
    assert not (tmp_path / ".ss.key").exists()


@pytest.mark.asyncio
async def test_archivo_en_claro_usa_la_clave_local(monkeypatch, tmp_path):
    monkeypatch.setattr(ss, "_clave_desde_addon", _sin_addon)
    monkeypatch.setattr(ss, "_archivo_cifrado", lambda: False)
    monkeypatch.setattr(ss, "KEY_FILE", tmp_path / ".ss.key")

    clave = await ss._obtener_clave(HassFalso())

    assert clave is not None and len(clave) == 32
    assert (tmp_path / ".ss.key").exists()
    assert (tmp_path / ".ss.key").stat().st_mode & 0o777 == 0o600


@pytest.mark.asyncio
async def test_con_addon_usa_la_clave_del_addon(monkeypatch, tmp_path):
    async def _con_addon(_hass):
        return CLAVE

    monkeypatch.setattr(ss, "_clave_desde_addon", _con_addon)
    monkeypatch.setattr(ss, "KEY_FILE", tmp_path / ".ss.key")

    assert await ss._obtener_clave(HassFalso()) == CLAVE
    assert not (tmp_path / ".ss.key").exists()


# --------------------------------------------------------------------------- #
# Dump de emergencia
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_dump_escribe_las_entradas_en_claro(monkeypatch, tmp_path):
    monkeypatch.setattr(ss, "_aes", AESGCM(CLAVE))
    monkeypatch.setattr(ss, "DUMP_FILE", tmp_path / "dump.json")
    entrada = EntradaFalsa("ntfy", crypto.cifrar(AESGCM(CLAVE), {"token": "t"}))
    hass = HassFalso([entrada])

    ss._registrar_servicios(hass)
    await hass.registros["dump"](None)

    volcado = json.loads((tmp_path / "dump.json").read_text())
    assert volcado["entries"][0]["data"] == {"token": "t"}
    assert crypto.MARCA not in json.dumps(volcado)
    assert (tmp_path / "dump.json").stat().st_mode & 0o777 == 0o600


@pytest.mark.asyncio
async def test_dump_sin_clave_no_escribe(monkeypatch, tmp_path):
    monkeypatch.setattr(ss, "_aes", None)
    monkeypatch.setattr(ss, "DUMP_FILE", tmp_path / "dump.json")
    hass = HassFalso([EntradaFalsa("ntfy", {"token": "t"})])

    ss._registrar_servicios(hass)
    await hass.registros["dump"](None)

    assert not (tmp_path / "dump.json").exists()
