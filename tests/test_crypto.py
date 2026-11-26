# SPDX-License-Identifier: GPL-3.0-or-later
"""Pruebas del cifrado de campos."""

import base64
import json
import os

import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from safe_store_crypto import AAD, MARCA, cifrar, descifrar, esta_cifrado


def _aes() -> AESGCM:
    return AESGCM(os.urandom(32))


def test_cifra_y_descifra_ida_y_vuelta() -> None:
    aes = _aes()
    original = {"url": "https://ntfy.sh", "token": "secreto", "verify_ssl": True}
    blob = cifrar(aes, original)
    assert list(blob) == [MARCA]
    assert descifrar(aes, blob) == original


def test_no_deja_texto_plano_en_el_blob() -> None:
    blob = cifrar(_aes(), {"password": "no-debe-aparecer"})
    assert "no-debe-aparecer" not in json.dumps(blob)


def test_marca_detecta_cifrado() -> None:
    assert esta_cifrado({MARCA: "x"})
    assert not esta_cifrado({"url": "https://ntfy.sh"})
    assert esta_cifrado({"url": "x", MARCA: "y"})


def test_descifrar_conserva_las_claves_extra() -> None:
    aes = _aes()
    mezclado = cifrar(aes, {"user": "viejo"})
    mezclado["user"] = "nuevo"
    assert descifrar(aes, mezclado) == {"user": "nuevo"}


def test_un_blob_manipulado_no_descifra() -> None:
    aes = _aes()
    crudo = base64.b64decode(cifrar(aes, {"x": 1})[MARCA])
    corrupto = crudo[:-1] + bytes([crudo[-1] ^ 1])
    with pytest.raises(InvalidTag):
        descifrar(aes, {MARCA: base64.b64encode(corrupto).decode()})


def test_clave_distinta_no_descifra() -> None:
    blob = cifrar(_aes(), {"x": 1})
    with pytest.raises(InvalidTag):
        descifrar(_aes(), blob)


def test_aad_es_el_esperado() -> None:
    assert AAD == b"safe_store:core.config_entries"
