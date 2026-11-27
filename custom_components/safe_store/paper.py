# SPDX-License-Identifier: MIT
"""Vista y panel de Safe Store: descargar la llave y restaurarla.

Vive en el componente y no en el add-on porque acá sí se sabe quién llama:
`request["hass_user"].is_admin` es la única forma de que el panel sea solo para
administradores de verdad, y no un panel que cualquiera con sesión puede abrir.

Las dos mitades:

  GET  /api/safe_store/paper   PNG con el QR de la master key
  POST /api/safe_store/paper   recibe ese PNG, extrae la llave y la guarda en el
                               add-on, que es quien la custodia
"""

from __future__ import annotations

import hashlib
import io
import os

import aiohttp
from aiohttp import web
from homeassistant.components.frontend import async_register_built_in_panel
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import ADDON_SLUG, SUPERVISOR_URL

URL = "/api/safe_store/paper"
PANEL_URL = "/safe_store_panel.js"
PANEL_PATH = "safe-store"

_clave: bytes | None = None


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
    """Llama al Supervisor con el token del core.

    Con aiohttp y no con urllib: Home Assistant aborta cualquier llamada
    bloqueante dentro del event loop.
    """
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


class PaperView(HomeAssistantView):
    """Descarga y restauración, solo para administradores."""

    url = URL
    name = "api:safe_store:paper"
    requires_auth = True

    @staticmethod
    def _admin(request) -> bool:
        # aiohttp.web.Request no tiene .get: se accede por clave.
        try:
            usuario = request["hass_user"]
        except KeyError:
            return False
        return bool(usuario and usuario.is_admin)

    async def get(self, request):
        if not self._admin(request):
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
        if not self._admin(request):
            return self.json_message("solo administradores", status_code=403)

        cuerpo = await request.read()
        if not cuerpo or len(cuerpo) > 5_000_000:
            return self.json_message("archivo vacío o demasiado grande", status_code=400)

        hass: HomeAssistant = request.app["hass"]
        nueva = await hass.async_add_executor_job(_decodificar, cuerpo)
        if nueva is None:
            return self.json_message("no encontré una clave válida en ese QR", status_code=400)

        slug = await _slug_addon()
        if not slug:
            return self.json_message("no encontré el add-on", status_code=503)

        guardado = await _supervisor(
            "POST", f"/addons/{slug}/options", {"options": {"master_key": nueva.hex()}}
        )
        if not guardado:
            return self.json_message("no pude guardar la configuración", status_code=500)

        # El Supervisor reescribe /data/options.json al recrear el contenedor.
        await _supervisor("POST", f"/addons/{slug}/restart")
        return self.json({"ok": True, "huella": huella(nueva)})


class PanelView(HomeAssistantView):
    """El JavaScript del panel. No lleva secretos: puede servirse sin sesión."""

    url = PANEL_URL
    name = "api:safe_store:panel"
    requires_auth = False

    async def get(self, request):
        return web.Response(text=JS_PANEL, content_type="text/javascript")


JS_PANEL = """
class SafeStorePanel extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    if (!this._listo) {
      this._armar();
      this._listo = true;
    }
  }

  _armar() {
    this.innerHTML = `
      <style>
        .caja { max-width: 560px; margin: 24px auto; font: 16px/1.5 system-ui, sans-serif; }
        section { border: 1px solid rgba(128,128,128,.3); border-radius: 12px; padding: 18px; margin-bottom: 18px; }
        h2 { font-size: 1rem; margin: 0 0 10px; }
        code { background: rgba(128,128,128,.15); padding: 2px 6px; border-radius: 6px; }
        button, a.boton { display: inline-block; margin-top: 12px; padding: 10px 16px; border-radius: 9px;
          border: 0; background: #03a9f4; color: #fff; font: inherit; font-weight: 600;
          text-decoration: none; cursor: pointer; }
        .aviso { color: #b3261e; font-weight: 600; }
        .ok { color: #1b7f3b; font-weight: 600; }
        #salida { margin-top: 12px; font-size: .9rem; }
      </style>
      <div class="caja">
        <h1>Safe Store</h1>
        <section>
          <h2>Tu llave</h2>
          <p>Huella: <code>${'?'}</code></p>
          <a class="boton" href="#" id="bajar">Descargar QR</a>
        </section>
        <section>
          <h2>Restaurar desde un archivo</h2>
          <p>Subí el PNG que guardaste. Se lee la llave y queda en el add-on.</p>
          <input type="file" id="archivo" accept="image/png">
          <button id="subir">Restaurar</button>
          <div id="salida"></div>
        </section>
      </div>`;

    const token = this._hass.auth.data.access_token;
    const bajar = this.querySelector('#bajar');
    const huellaEl = this.querySelector('code');
    const salida = this.querySelector('#salida');

    fetch('/api/safe_store/paper', { headers: { Authorization: 'Bearer ' + token } })
      .then(r => r.ok ? r.blob() : Promise.reject(r.status))
      .then(() => { huellaEl.textContent = 'disponible'; })
      .catch(e => {
        huellaEl.textContent = '-';
        bajar.style.display = 'none';
        const aviso = document.createElement('p');
        aviso.className = 'aviso';
        aviso.textContent = e === 403
          ? 'Solo administradores.'
          : 'No hay llave disponible todavía.';
        huellaEl.parentElement.appendChild(aviso);
      });

    bajar.addEventListener('click', async (ev) => {
      ev.preventDefault();
      const resp = await fetch('/api/safe_store/paper', {
        headers: { Authorization: 'Bearer ' + token },
      });
      if (!resp.ok) { salida.className = 'aviso'; salida.textContent = 'No se pudo bajar.'; return; }
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'safe-store-key.png'; a.click();
      URL.revokeObjectURL(url);
    });

    this.querySelector('#subir').addEventListener('click', async () => {
      const archivo = this.querySelector('#archivo').files[0];
      if (!archivo) { salida.textContent = 'Elegí un archivo primero.'; return; }
      salida.className = ''; salida.textContent = 'Leyendo el QR…';
      try {
        const resp = await fetch('/api/safe_store/paper', {
          method: 'POST',
          headers: { Authorization: 'Bearer ' + token, 'Content-Type': 'image/png' },
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
  }
}

customElements.define('safe-store-panel', SafeStorePanel);
"""


def async_setup_panel(hass: HomeAssistant, clave: bytes) -> None:
    """Registra la vista, el JS y el panel lateral solo para administradores."""
    global _clave
    _clave = clave

    hass.http.register_view(PaperView())
    hass.http.register_view(PanelView())

    async_register_built_in_panel(
        hass,
        component_name="custom",
        sidebar_title="Safe Store",
        sidebar_icon="mdi:shield-key",
        frontend_url_path=PANEL_PATH,
        config={"name": "safe-store-panel", "module_url": PANEL_URL},
        require_admin=True,
    )
