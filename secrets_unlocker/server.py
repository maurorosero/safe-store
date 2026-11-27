# SPDX-License-Identifier: MIT
"""Entrega la master key de Safe Store al core, por HTTP local y con token.

No expone nada fuera de la red interna de los add-ons: el token lo genera el
componente en /config/.ss.token y se compara en tiempo constante.

La interfaz (descargar el QR, restaurar la llave) vive en el componente, no acá:
es la única forma de que Home Assistant sepa quién llama y pueda limitarla a
administradores. Este add-on solo custodia la llave.

Fuentes de la key, en orden:
  1. opción master_key del add-on
  2. /data/master.key            archivo de 32 bytes en hex
  3. /data/secrets.env.enc       archivo SOPS, descifrado con la identidad age
                                 en /data/age.key
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8099
OPTIONS_FILE = "/data/options.json"
TOKEN_FILE = "/homeassistant/.ss.token"
KEY_FILE = "/data/master.key"
ENC_FILE = "/data/secrets.env.enc"
AGE_KEY_FILE = "/data/age.key"
SOPS_EXTRACT = '["SAFE_STORE_MASTER_KEY"]'


def _token() -> str:
    try:
        with open(TOKEN_FILE, encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return ""


def _opcion(nombre: str) -> str | None:
    """Lee una opción del panel de configuración del add-on."""
    try:
        with open(OPTIONS_FILE, encoding="utf-8") as fh:
            valor = json.load(fh).get(nombre)
    except (OSError, ValueError):
        return None
    return valor if isinstance(valor, str) and valor.strip() else None


def _huella(clave: str) -> str:
    """Primeros ocho del sha256: sirve para comparar dos copias sin verlas."""
    return hashlib.sha256(clave.encode()).hexdigest()[:8]


def _generar() -> str:
    """Crea la master key, la guarda en /data y la anuncia una sola vez."""
    clave = os.urandom(32).hex()
    with open(KEY_FILE, "w", encoding="utf-8") as fh:
        fh.write(clave)
    os.chmod(KEY_FILE, 0o600)
    print(
        "MASTER KEY generada: " + clave + "\n"
        "Guardala fuera de Home Assistant: /data no se respalda. Se puede volver "
        "a bajar desde el panel Safe Store mientras este add-on la conserve.",
        file=sys.stderr,
        flush=True,
    )
    return clave


def _clave() -> str | None:
    """Devuelve la master key en hex, o None si no hay fuente utilizable.

    Orden: configuración del add-on, archivo en /data, archivo SOPS.
    Si no hay ninguna, se genera una y se anuncian sus consecuencias.
    """
    if (desde_ui := _opcion("master_key")) is not None:
        return desde_ui.strip()

    try:
        with open(KEY_FILE, encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        pass

    if not os.path.exists(ENC_FILE):
        return _generar()

    env = dict(os.environ)
    env.setdefault("SOPS_AGE_KEY_FILE", AGE_KEY_FILE)
    try:
        salida = subprocess.run(
            ["sops", "-d", "--extract", SOPS_EXTRACT, ENC_FILE],
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as err:
        print(f"error ejecutando sops: {err}", file=sys.stderr)
        return None

    if salida.returncode != 0:
        print(f"sops falló: {salida.stderr.strip()}", file=sys.stderr)
        return None
    return salida.stdout.strip()


class Handler(BaseHTTPRequestHandler):
    """POST /unlock para el componente; GET /health y /status para diagnosticar."""

    server_version = "safe-store-unlocker"

    def _responder(self, codigo: int, cuerpo: dict) -> None:
        datos = json.dumps(cuerpo).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def _autorizado(self) -> bool:
        esperado = _token()
        if not esperado:
            return False
        recibido = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        return hmac.compare_digest(recibido, esperado)

    def do_POST(self) -> None:
        if self.path != "/unlock":
            self._responder(404, {"error": "not found"})
            return

        if not _token():
            self._responder(503, {"error": "token no configurado"})
            return
        if not self._autorizado():
            self._responder(401, {"error": "unauthorized"})
            return

        clave = _clave()
        if not clave:
            self._responder(503, {"error": "sin master key"})
            return
        self._responder(200, {"key": clave})

    def do_GET(self) -> None:
        if self.path == "/health":
            self._responder(200, {"status": "ok"})
            return

        if self.path == "/status":
            clave = _clave()
            self._responder(
                200,
                {"tiene_clave": bool(clave), "huella": _huella(clave) if clave else None},
            )
            return

        self._responder(404, {"error": "not found"})

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("unlocker: " + fmt % args + "\n")


if __name__ == "__main__":
    print(f"secrets-unlocker escuchando en :{PORT}", flush=True)
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
