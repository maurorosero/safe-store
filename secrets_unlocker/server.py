# SPDX-License-Identifier: MIT
"""Entrega la master key de Safe Store al core, por HTTP local y con token.

No expone nada fuera de la red interna de los add-ons: el token lo genera el
componente en /config/.ss.token y se compara en tiempo constante.

Fuentes de la key, en orden:
  1. /data/master.key            archivo de 32 bytes en hex (simple)
  2. /data/secrets.env.enc       archivo SOPS, descifrado con la identidad age
                                 en /data/age.key
"""

from __future__ import annotations

import hashlib
import hmac
import io
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8099
OPTIONS_FILE = "/data/options.json"
TOKEN_FILE = "/homeassistant/.ss.token"
KEY_FILE = "/data/master.key"
ENC_FILE = "/data/secrets.env.enc"
AGE_KEY_FILE = "/data/age.key"
SOPS_EXTRACT = '["SAFE_STORE_MASTER_KEY"]'
PAPER_FLAG = "/data/paper.saved"
SUPERVISOR = "http://supervisor"


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
        "Guardala en la configuración del add-on si vas a restaurar en otra "
        "instancia: /data no se respalda.",
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


def _qr_png(clave: str) -> bytes:
    """PNG con el QR de la clave y su huella impresa debajo."""
    import qrcode
    from PIL import Image, ImageDraw
    from qrcode.image.pil import PilImage

    codigo = qrcode.make(clave, box_size=8, border=4, image_factory=PilImage).convert("RGB")
    ancho, alto = codigo.size
    banda = 46
    lienzo = Image.new("RGB", (ancho, alto + banda), "white")
    lienzo.paste(codigo, (0, 0))

    dibujo = ImageDraw.Draw(lienzo)
    leyenda = f"Safe Store - sha256 {_huella(clave)}"
    caja = dibujo.textbbox((0, 0), leyenda)
    dibujo.text(((ancho - (caja[2] - caja[0])) // 2, alto + 14), leyenda, fill="black")

    buffer = io.BytesIO()
    lienzo.save(buffer, format="PNG")
    return buffer.getvalue()


def _guardar_clave(clave: str) -> bool:
    """Escribe master_key en las opciones del add-on, vía Supervisor.

    Las opciones sí viajan en los backups, así que después de esto la clave
    sobrevive a un restore. El add-on puede escribir su propia configuración
    sin pedir hassio_api.
    """
    token = os.environ.get("SUPERVISOR_TOKEN", "")
    if not token:
        return False
    datos = json.dumps({"options": {"master_key": clave}}).encode()
    peticion = urllib.request.Request(
        f"{SUPERVISOR}/addons/self/options",
        data=datos,
        method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(peticion, timeout=20) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError, ValueError) as err:
        print(f"no pude guardar la opción: {err}", file=sys.stderr)
        return False


def _decodificar(png: bytes) -> str | None:
    """Extrae la clave de un PNG con QR.

    Se usa pyzbar sobre PIL: el CLI zbarimg necesita el delegate de PNG de
    ImageMagick, que esta imagen no trae.
    """
    from PIL import Image
    from pyzbar.pyzbar import decode

    ruta = "/tmp/upload.png"
    with open(ruta, "wb") as fh:
        fh.write(png)

    try:
        with Image.open(ruta) as imagen:
            resultados = decode(imagen)
    except (OSError, ValueError) as err:
        print(f"no pude abrir la imagen: {err}", file=sys.stderr)
        return None

    for resultado in resultados:
        texto = resultado.data.decode("utf-8", "ignore").strip()
        if len(texto) == 64 and all(c in "0123456789abcdef" for c in texto):
            return texto
    return None


PAGINA = """<!doctype html>
<html lang="es">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Safe Store</title>
<style>
 :root { color-scheme: light dark; }
 body { font: 16px/1.5 system-ui, sans-serif; margin: 0; padding: 24px;
        max-width: 560px; margin-inline: auto; }
 h1 { font-size: 1.35rem; margin: 0 0 4px; }
 p.sub { margin: 0 0 24px; opacity: .7; font-size: .9rem; }
 section { border: 1px solid #8883; border-radius: 12px; padding: 18px; margin-bottom: 18px; }
 h2 { font-size: 1rem; margin: 0 0 10px; }
 code { background: #8882; padding: 2px 6px; border-radius: 6px; }
 .aviso { color: #b3261e; font-weight: 600; }
 .ok { color: #1b7f3b; font-weight: 600; }
 a.boton, button { display: inline-block; margin-top: 12px; padding: 10px 16px;
        border-radius: 9px; border: 0; background: #03a9f4; color: #fff;
        font: inherit; font-weight: 600; text-decoration: none; cursor: pointer; }
 input[type=file] { margin-top: 10px; display: block; }
 #resultado { margin-top: 12px; font-size: .9rem; }
</style>
<h1>Safe Store</h1>
<p class="sub">La master key que cifra las credenciales de este Home Assistant.</p>

<section>
 <h2>Tu llave</h2>
 __ESTADO__
</section>

<section>
 <h2>Restaurar desde un archivo</h2>
 <p>Si perdiste la clave o restauraste un backup, subí el PNG que guardaste.
    Se lee la clave y queda en la configuración del add-on.</p>
 <input type="file" id="archivo" accept="image/png">
 <button id="subir">Restaurar</button>
 <div id="resultado"></div>
</section>

<script>
 const boton = document.getElementById('subir');
 boton.addEventListener('click', async () => {
   const archivo = document.getElementById('archivo').files[0];
   const salida = document.getElementById('resultado');
   if (!archivo) { salida.textContent = 'Elegí un archivo primero.'; return; }
   boton.disabled = true;
   salida.className = '';
   salida.textContent = 'Leyendo el QR…';
   try {
     const resp = await fetch('__BASE__restore', { method: 'POST', body: archivo });
     const datos = await resp.json();
     if (datos.ok) {
       salida.className = 'ok';
       salida.textContent = 'Clave restaurada (' + datos.huella + '). El add-on se reinicia.';
     } else {
       salida.className = 'aviso';
       salida.textContent = datos.mensaje || 'No se pudo restaurar.';
     }
   } catch (err) {
     salida.className = 'aviso';
     salida.textContent = 'Error: ' + err;
   }
   boton.disabled = false;
 });
</script>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    """Un solo endpoint: POST /unlock con Authorization: Bearer <token>."""

    server_version = "safe-store-unlocker"

    def _responder(self, codigo: int, cuerpo: dict) -> None:
        datos = json.dumps(cuerpo).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def _ruta(self) -> str:
        """Quita el prefijo de Ingress para que las rutas sean comparables."""
        base = self.headers.get("X-Ingress-Path", "").rstrip("/")
        ruta = self.path
        if base and ruta.startswith(base):
            ruta = ruta[len(base) :]
        return ruta or "/"

    def _autorizado(self) -> bool:
        esperado = _token()
        if not esperado:
            return False
        recibido = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        return hmac.compare_digest(recibido, esperado)

    def do_POST(self) -> None:
        ruta = self._ruta()

        if ruta == "/unlock":
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
            return

        if ruta == "/restore":
            largo = int(self.headers.get("Content-Length", "0") or 0)
            if largo <= 0 or largo > 5_000_000:
                self._responder(400, {"ok": False, "mensaje": "archivo vacío o demasiado grande"})
                return
            clave = _decodificar(self.rfile.read(largo))
            if not clave:
                self._responder(
                    400, {"ok": False, "mensaje": "no encontré una clave válida en ese QR"}
                )
                return
            if not _guardar_clave(clave):
                self._responder(500, {"ok": False, "mensaje": "no pude guardar la configuración"})
                return
            print(
                f"clave restaurada desde QR - sha256 {_huella(clave)}",
                file=sys.stderr,
                flush=True,
            )
            self._responder(200, {"ok": True, "huella": _huella(clave)})
            os._exit(0)  # s6 lo vuelve a levantar, ya con la opción nueva
            return

        self._responder(404, {"error": "not found"})

    def do_GET(self) -> None:
        ruta = self._ruta()

        if ruta == "/health":
            self._responder(200, {"status": "ok"})
            return

        if ruta == "/status":
            clave = _clave()
            self._responder(
                200,
                {
                    "tiene_clave": bool(clave),
                    "huella": _huella(clave) if clave else None,
                    "copia_descargada": os.path.exists(PAPER_FLAG),
                },
            )
            return

        if ruta == "/qr.png":
            clave = _clave()
            if not clave:
                self._responder(503, {"error": "sin master key"})
                return
            png = _qr_png(clave)
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Disposition", 'attachment; filename="safe-store-key.png"')
            self.send_header("Content-Length", str(len(png)))
            self.end_headers()
            self.wfile.write(png)
            try:
                with open(PAPER_FLAG, "w", encoding="utf-8") as fh:
                    fh.write(_huella(clave))
            except OSError:
                pass
            return

        if ruta == "/":
            clave = _clave()
            base = self.headers.get("X-Ingress-Path", "").rstrip("/") + "/"
            if clave:
                aviso = ""
                if not os.path.exists(PAPER_FLAG):
                    aviso = (
                        '<p class="aviso">Esta clave no tiene copia descargada. '
                        "Bajá el QR y guardalo fuera de Home Assistant.</p>"
                    )
                estado = (
                    f"<p>Huella: <code>{_huella(clave)}</code></p>"
                    f"{aviso}"
                    '<a class="boton" href="qr.png" download="safe-store-key.png">'
                    "Descargar QR</a>"
                )
            else:
                estado = "<p>No hay clave todavía: se crea cuando agregás la integración.</p>"
            datos = PAGINA.replace("__ESTADO__", estado).replace("__BASE__", base).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            self.wfile.write(datos)
            return

        self._responder(404, {"error": "not found"})

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("unlocker: " + fmt % args + "\n")


if __name__ == "__main__":
    print(f"secrets-unlocker escuchando en :{PORT}", flush=True)
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
