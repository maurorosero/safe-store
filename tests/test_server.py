# SPDX-License-Identifier: MIT
"""La llave restaurada se mueve al archivo y sale de las opciones.

Las opciones del add-on viajan en el backup; /data/master.key no. Si una
restauracion deja la llave en las opciones, se copia en cada backup, que es
justo lo que hay que evitar. Estas pruebas usan un directorio temporal real.
"""

from __future__ import annotations

import importlib.util
import json
import stat
from pathlib import Path

import pytest

RUTA = Path(__file__).resolve().parents[1] / "secrets_unlocker" / "server.py"


@pytest.fixture()
def srv(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("unlocker_server", RUTA)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)

    monkeypatch.setattr(modulo, "KEY_FILE", str(tmp_path / "master.key"))
    monkeypatch.setattr(modulo, "OPTIONS_FILE", str(tmp_path / "options.json"))
    monkeypatch.setattr(modulo, "ENC_FILE", str(tmp_path / "secrets.env.enc"))
    vaciados = []
    monkeypatch.setattr(modulo, "_vaciar_opcion", lambda: vaciados.append(True))
    modulo.vaciados = vaciados
    return modulo


def _opciones(srv, valor):
    Path(srv.OPTIONS_FILE).write_text(json.dumps({"master_key": valor}), encoding="utf-8")


def test_la_clave_restaurada_pasa_al_archivo(srv):
    clave = "ab" * 32
    _opciones(srv, clave)

    srv._adoptar_opcion()

    assert Path(srv.KEY_FILE).read_text().strip() == clave
    assert srv.vaciados, "tendria que vaciar la opcion para que no viaje en el backup"


def test_el_archivo_queda_en_600(srv):
    _opciones(srv, "cd" * 32)

    srv._adoptar_opcion()

    modo = stat.S_IMODE(Path(srv.KEY_FILE).stat().st_mode)
    assert modo == 0o600


def test_la_clave_se_lee_del_archivo_primero(srv):
    Path(srv.KEY_FILE).write_text("ef" * 32, encoding="utf-8")
    _opciones(srv, "aa" * 32)

    assert srv._clave() == "ef" * 32


def test_guardar_clave_escribe_el_archivo_y_no_las_opciones(srv):
    clave = "12" * 32

    assert srv._guardar_clave(clave) is True

    assert Path(srv.KEY_FILE).read_text().strip() == clave
    assert srv.vaciados, "no debe quedar nada en las opciones"
