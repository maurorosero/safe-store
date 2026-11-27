# SPDX-License-Identifier: MIT
"""Unit tests de la vista: el QR y quién puede pedirlo.

El QR se genera con segno y se lee con pyzbar, las mismas librerías que usa
Home Assistant, así que el ciclo se puede cerrar sin salir del test.
"""

from __future__ import annotations

import io
import types

import pytest
from PIL import Image

import custom_components.safe_store.paper as paper

CLAVE = bytes.fromhex("0123456789abcdef" * 4)


def test_huella_es_estable_y_corta():
    assert paper.huella(CLAVE) == paper.huella(CLAVE)
    assert len(paper.huella(CLAVE)) == 8
    assert paper.huella(CLAVE) != paper.huella(bytes.fromhex("ff" * 32))


def test_png_es_una_imagen_valida():
    datos = paper._png(CLAVE)

    assert datos[:8] == b"\x89PNG\r\n\x1a\n"
    with Image.open(io.BytesIO(datos)) as imagen:
        assert imagen.width > 100 and imagen.height > imagen.width


def test_el_qr_vuelve_a_la_misma_clave():
    assert paper._decodificar(paper._png(CLAVE)) == CLAVE


def test_decodificar_rechaza_basura():
    assert paper._decodificar(b"no soy un png") is None
    assert paper._decodificar(paper._png(bytes.fromhex("ab" * 32))[:-500]) is None


@pytest.mark.parametrize(
    ("es_admin", "esperado"),
    [(True, True), (False, False), (None, False)],
)
def test_solo_admin_pasa(es_admin, esperado):
    request = {} if es_admin is None else {"hass_user": types.SimpleNamespace(is_admin=es_admin)}

    assert paper.PaperView._admin(request) is esperado


def test_la_vista_exige_autenticacion():
    assert paper.PaperView.requires_auth is True
    assert paper.PaperView.url == "/api/safe_store/paper"


def test_el_js_del_panel_no_pide_sesion():
    """El panel es solo JavaScript: no lleva secretos y no debe pedir token."""
    assert paper.PanelView.requires_auth is False
    assert "safe-store-panel" in paper.JS_PANEL
    assert "customElements.define" in paper.JS_PANEL
