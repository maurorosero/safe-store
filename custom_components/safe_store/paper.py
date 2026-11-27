# SPDX-License-Identifier: MIT
"""Panel de Safe Store: descargar la llave y restaurarla.

El panel es un `iframe`. Un iframe no puede enviar la cabecera `Authorization`
que pide Home Assistant, y por eso la pagina respondia 401 y quedaba en blanco.
La salida es un token propio del panel, generado en cada arranque y pasado en la
URL: el iframe lo lleva consigo y las vistas lo aceptan. Sin ese token todo sigue
exigiendo sesion de administrador, y el panel solo se ofrece a administradores.

  GET  /api/safe_store/page?t=…     la pagina del panel
  GET  /api/safe_store/status?t=…   si hay llave y su huella
  GET  /api/safe_store/paper?t=…    PNG con el QR
  POST /api/safe_store/paper?t=…    recibe ese PNG y guarda la llave en el add-on
"""

from __future__ import annotations

import hashlib
import io
import os
import secrets

import aiohttp
from aiohttp import web
from homeassistant.components.frontend import async_register_built_in_panel
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import ADDON_SLUG, SUPERVISOR_URL

URL_PAPER = "/api/safe_store/paper"
URL_STATUS = "/api/safe_store/status"
URL_PAGE = "/api/safe_store/page"
PANEL_PATH = "safe-store"

_clave: bytes | None = None
_token_panel = ""


def huella(clave: bytes) -> str:
    """Primeros ocho del sha256: sirve para comparar dos copias sin verlas."""
    return hashlib.sha256(clave.hex().encode()).hexdigest()[:8]


def _png(clave: bytes) -> bytes:
    """PNG con el QR de la clave y su huella impresa debajo."""
    import segno
    from PIL import Image, ImageDraw

    memoria = io.BytesIO()
    segno.make(clave.hex(), error="m").save(memoria, kind="png", scale=8, border=4)
    memoria.seek(0)
    codigo = Image.open(memoria).convert("RGB")

    ancho, alto = codigo.size
    banda = 46
    lienzo = Image.new("RGB", (ancho, alto + banda), "white")
    lienzo.paste(codigo, (0, 0))

    dibujo = ImageDraw.Draw(lienzo)
    leyenda = f"Safe Store - sha256 {huella(clave)}"
    caja = dibujo.textbbox((0, 0), leyenda)
    dibujo.text(((ancho - (caja[2] - caja[0])) // 2, alto + 14), leyenda, fill="black")

    salida = io.BytesIO()
    lienzo.save(salida, format="PNG")
    return salida.getvalue()


def _decodificar(png: bytes) -> bytes | None:
    """Extrae la clave de un PNG con QR."""
    from PIL import Image
    from pyzbar.pyzbar import decode

    try:
        with Image.open(io.BytesIO(png)) as imagen:
            resultados = decode(imagen)
    except (OSError, ValueError):
        return None

    for resultado in resultados:
        texto = resultado.data.decode("utf-8", "ignore").strip()
        if len(texto) == 64 and all(c in "0123456789abcdef" for c in texto):
            return bytes.fromhex(texto)
    return None


async def _slug_addon() -> str | None:
    """El slug real del add-on: lleva el hash del repositorio como prefijo."""
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        return None
    cabeceras = {"Authorization": f"Bearer {token}"}
    try:
        async with (
            aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10), headers=cabeceras
            ) as sesion,
            sesion.get(f"{SUPERVISOR_URL}/addons") as resp,
        ):
            if resp.status != 200:
                return None
            datos = await resp.json()
    except (aiohttp.ClientError, TimeoutError, ValueError):
        return None

    for addon in (datos.get("data") or {}).get("addons", []):
        if str(addon.get("slug", "")).endswith(ADDON_SLUG):
            return str(addon["slug"])
    return None


async def _supervisor(metodo: str, ruta: str, cuerpo: dict | None = None) -> bool:
    """Llama al Supervisor con el token del core, sin bloquear el event loop."""
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        return False
    cabeceras = {"Authorization": f"Bearer {token}"}
    try:
        async with (
            aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=20), headers=cabeceras
            ) as sesion,
            sesion.request(metodo, f"{SUPERVISOR_URL}{ruta}", json=cuerpo) as resp,
        ):
            return resp.status == 200
    except (aiohttp.ClientError, TimeoutError, ValueError):
        return False


class _PanelView(HomeAssistantView):
    """Base: token del panel, o sesion de administrador."""

    requires_auth = False

    @staticmethod
    def _permitido(request) -> bool:
        # El token viaja en la URL porque un iframe no puede poner cabeceras.
        if _token_panel and request.query.get("t") == _token_panel:
            return True
        try:
            usuario = request["hass_user"]
        except KeyError:
            return False
        return bool(usuario and usuario.is_admin)


class StatusView(_PanelView):
    url = URL_STATUS
    name = "api:safe_store:status"

    async def get(self, request):
        if not self._permitido(request):
            return self.json_message("solo administradores", status_code=403)
        if _clave is None:
            return self.json({"tiene_clave": False, "huella": None})
        return self.json({"tiene_clave": True, "huella": huella(_clave)})


class PaperView(_PanelView):
    url = URL_PAPER
    name = "api:safe_store:paper"

    async def get(self, request):
        if not self._permitido(request):
            return self.json_message("solo administradores", status_code=403)
        if _clave is None:
            return self.json_message("sin master key", status_code=503)

        datos = await request.app["hass"].async_add_executor_job(_png, _clave)
        return web.Response(
            body=datos,
            content_type="image/png",
            headers={"Content-Disposition": 'attachment; filename="safe-store-key.png"'},
        )

    async def post(self, request):
        if not self._permitido(request):
            return self.json_message("solo administradores", status_code=403)

        cuerpo = await request.read()
        if not cuerpo or len(cuerpo) > 5_000_000:
            return self.json_message("archivo vacio o demasiado grande", status_code=400)

        hass: HomeAssistant = request.app["hass"]
        nueva = await hass.async_add_executor_job(_decodificar, cuerpo)
        if nueva is None:
            return self.json_message("no encontre una clave valida en ese QR", status_code=400)

        slug = await _slug_addon()
        if not slug:
            return self.json_message("no encontre el add-on", status_code=503)

        guardado = await _supervisor(
            "POST", f"/addons/{slug}/options", {"options": {"master_key": nueva.hex()}}
        )
        if not guardado:
            return self.json_message("no pude guardar la configuracion", status_code=500)

        await _supervisor("POST", f"/addons/{slug}/restart")
        return self.json({"ok": True, "huella": huella(nueva)})


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
 section { border: 1px solid rgba(128,128,128,.3); border-radius: 12px;
           padding: 18px; margin-bottom: 18px; }
 h2 { font-size: 1rem; margin: 0 0 10px; }
 code { background: rgba(128,128,128,.15); padding: 2px 6px; border-radius: 6px; }
 .aviso { color: #b3261e; font-weight: 600; }
 .ok { color: #1b7f3b; font-weight: 600; }
 a.boton, button { display: inline-block; margin-top: 12px; padding: 10px 16px;
        border-radius: 9px; border: 0; background: #03a9f4; color: #fff;
        font: inherit; font-weight: 600; text-decoration: none; cursor: pointer; }
 input[type=file] { margin-top: 10px; display: block; }
 #salida { margin-top: 12px; font-size: .9rem; }
</style>
<h1>Safe Store</h1>
<p class="sub">La llave que cifra las credenciales de este Home Assistant.</p>

<section>
 <h2>Tu llave</h2>
 <p id="linea">Consultando...</p>
 <a class="boton" id="bajar" style="display:none">Descargar QR</a>
</section>

<section>
 <h2>Restaurar desde un archivo</h2>
 <p>Si perdiste la llave o restauraste un backup, subi el PNG que guardaste.</p>
 <input type="file" id="archivo" accept="image/png">
 <button id="subir">Restaurar</button>
 <div id="salida"></div>
</section>

<script>
 const t = new URLSearchParams(location.search).get('t') || '';
 const q = t ? ('?t=' + encodeURIComponent(t)) : '';
 const linea = document.getElementById('linea');
 const bajar = document.getElementById('bajar');
 const salida = document.getElementById('salida');

 fetch('/api/safe_store/status' + q)
   .then(r => r.ok ? r.json() : Promise.reject(r.status))
   .then(d => {
     if (d.tiene_clave) {
       linea.innerHTML = 'Huella: <code>' + d.huella + '</code>';
       bajar.href = '/api/safe_store/paper' + q;
       bajar.style.display = 'inline-block';
     } else {
       linea.textContent = 'Todavia no hay llave.';
     }
   })
   .catch(e => {
     linea.className = 'aviso';
     linea.textContent = e === 403 ? 'Solo administradores.' : 'No pude consultar el estado.';
   });

 document.getElementById('subir').addEventListener('click', async () => {
   const archivo = document.getElementById('archivo').files[0];
   if (!archivo) { salida.textContent = 'Elegi un archivo primero.'; return; }
   salida.className = ''; salida.textContent = 'Leyendo el QR...';
   try {
     const resp = await fetch('/api/safe_store/paper' + q, {
       method: 'POST',
       headers: { 'Content-Type': 'image/png' },
       body: archivo,
     });
     const datos = await resp.json();
     if (resp.ok && datos.ok) {
       salida.className = 'ok';
       salida.textContent = 'Llave restaurada (' + datos.huella + '). El add-on se reinicia.';
     } else {
       salida.className = 'aviso';
       salida.textContent = datos.message || 'No se pudo restaurar.';
     }
   } catch (err) {
     salida.className = 'aviso';
     salida.textContent = 'Error: ' + err;
   }
 });
</script>
</html>
"""


class PageView(_PanelView):
    """La pagina del panel, con el token del iframe adentro."""

    url = URL_PAGE
    name = "api:safe_store:page"

    async def get(self, request):
        if not self._permitido(request):
            return web.Response(text="solo administradores", status=403)
        return web.Response(text=PAGINA, content_type="text/html")


def async_setup_panel(hass: HomeAssistant, clave: bytes) -> None:
    """Registra las vistas y el panel lateral, solo para administradores."""
    global _clave, _token_panel
    _clave = clave
    _token_panel = secrets.token_hex(16)

    hass.http.register_view(StatusView())
    hass.http.register_view(PaperView())
    hass.http.register_view(PageView())

    async_register_built_in_panel(
        hass,
        component_name="iframe",
        sidebar_title="Safe Store",
        sidebar_icon="mdi:shield-key",
        frontend_url_path=PANEL_PATH,
        config={"url": f"{URL_PAGE}?t={_token_panel}"},
        require_admin=True,
    )
