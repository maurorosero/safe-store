# SPDX-License-Identifier: MIT
"""Pruebas del panel: el token del iframe y la sesion de administrador."""

from __future__ import annotations

import types

import pytest

from custom_components.safe_store import paper


class _Peticion:
    """Lo que las vistas usan de un request: el usuario y el query."""

    def __init__(self, usuario=None, token=None):
        self._usuario = usuario
        self.query = {"t": token} if token else {}

    def __getitem__(self, clave):
        if clave == "hass_user" and self._usuario is not None:
            return self._usuario
        raise KeyError(clave)


def test_las_vistas_validad_por_su_cuenta():
    """Un iframe no manda cabeceras: la autorizacion se resuelve en el handler."""
    for vista in (paper.PaperView, paper.StatusView, paper.PageView):
        assert vista.requires_auth is False


def test_el_token_del_panel_abre_sin_sesion(monkeypatch):
    monkeypatch.setattr(paper, "_token_panel", "abc123")
    assert paper.PageView._permitido(_Peticion(token="abc123")) is True


def test_un_token_equivocado_no_abre(monkeypatch):
    monkeypatch.setattr(paper, "_token_panel", "abc123")
    assert paper.PageView._permitido(_Peticion(token="otro")) is False


def test_sin_token_y_sin_sesion_no_pasa(monkeypatch):
    monkeypatch.setattr(paper, "_token_panel", "abc123")
    assert paper.PageView._permitido(_Peticion()) is False


@pytest.mark.parametrize(("es_admin", "esperado"), [(True, True), (False, False)])
def test_la_sesion_vale_solo_si_es_admin(monkeypatch, es_admin, esperado):
    monkeypatch.setattr(paper, "_token_panel", "abc123")
    usuario = types.SimpleNamespace(is_admin=es_admin)
    assert paper.PaperView._permitido(_Peticion(usuario=usuario)) is esperado
