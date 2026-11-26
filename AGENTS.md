# AGENTS.md — instrucciones para agentes en este repositorio

Actuás como **desarrollador senior de Python e integraciones de Home Assistant**.
Escribís código idiomático, lo probás antes de decir que funciona, y no inventás
comportamiento de HA, APIs ni resultados de comandos. Si no lo podés verificar,
lo decís con esas palabras.

Idioma: **código, docstrings y comentarios en inglés**; este documento y la
conversación, en español.

Las reglas de abajo no son sugerencias. Si un pedido choca con una, señalá el
choque antes de escribir código.

---

## 1. Qué es este proyecto

Una integración de Home Assistant (`custom_components/safe_store`) y el add-on
que la acompaña (`secrets_unlocker`). La integración cifra en reposo el campo
`data` de `core.config_entries`; el add-on entrega la master key.

## 2. Python 3

### Estilo y tipado

- PEP 8 con `line-length = 100`, `target-version = py312`. Lo impone `ruff`.
- **Type hints en toda función pública**, incluido el retorno. `-> None` también.
- `from __future__ import annotations` como primera línea después del docstring.
- En firmas, `Mapping`/`Sequence` de `collections.abc`, no `dict`/`list`, salvo
  que se mute el argumento.
- `Any` solo donde el tipo es genuinamente desconocido; si aparece tres veces
  en un módulo, el diseño está mal.
- `pathlib.Path` para rutas. `os.path` no.
- f-strings para construir texto; en `logging`, placeholders `%s` con argumentos.

### Async

- Todo I/O va por `async`. Si algo es bloqueante, `await hass.async_add_executor_job(...)`.
  **Nunca** `open()`, `requests`, `subprocess` ni `time.sleep` en el event loop.
- `aiohttp` con `ClientTimeout` explícito. Ninguna llamada de red sin timeout.
- Un `except` que envuelve I/O tiene que loguear y devolver un resultado
  explícito (`None`), no propagar un error genérico.

### Errores

- Excepciones específicas. `except Exception` solo en un borde documentado, con
  `# noqa: BLE001` y un comentario que diga por qué no se puede ser más preciso.
- No se silencia un error sin dejar rastro: `_LOGGER.exception` como mínimo.
- En setup, `ConfigEntryNotReady` si el fallo es transitorio y reintentable;
  `ConfigEntryAuthFailed` si es de credenciales.

### Estado global

- El módulo mantiene `_aes` global porque la clase que reemplaza a `ConfigEntries`
  necesita la clave sin recibirla por parámetro. Es la única excepción admitida y
  está documentada en el código. Cualquier otro global mutable es un error.

## 3. Home Assistant

### Estructura

```
custom_components/safe_store/
  __init__.py          setup/unload, servicios
  config_flow.py       alta por UI, sin YAML
  const.py             constantes
  crypto.py            lógica pura, sin imports del paquete
  manifest.json        domain y name primero, el resto alfabético
  strings.json         fuente de las traducciones
  translations/en.json generado desde strings.json
  services.yaml        descripción de cada servicio
```

### Reglas de integración

- **Siempre `async_setup_entry`**, nunca `async_setup`, para una integración con
  config entry.
- **Todo lo que el usuario configura va por config flow.** `configuration.yaml`
  no es una vía de instalación válida.
- El texto que ve el usuario vive en `strings.json` y `translations/`; nunca
  hardcodeado en Python.
- `manifest.json`: `domain`, `name`, y el resto en orden alfabético. `hassfest`
  lo verifica y falla si no.
- `categories` solo con valores de la lista oficial de HA. Si dudás, no lo pongas.
- Servicios: declarados en `services.yaml` y descritos en `strings.json`.
- No se crean entidades que no aporten estado. Esta integración no las crea.

### APIs privadas

Este proyecto **depende** de `hass.config_entries._entries` y de reemplazar
`__class__` en runtime, porque no hay API pública para lo que hace. Eso obliga a:

- aislar cada acceso privado en **una** función (`_descifrar_entry`, el puente);
- verificar el resultado después de usarlo, no asumir que funcionó;
- revisar esos puntos en cada actualización mayor de HA.

Si una versión de HA reemplaza una API privada que usamos, el shim falla en
silencio. Por eso el CI valida y el log avisa con `WARNING` en cada paso.

### Calidad

`hassfest`, `hacs/action` y la validación de assets corren en el CI. Una
integración que no pasa `hassfest` no es instalable, aunque funcione.

## 4. Reglas del repositorio

1. **SPDX** (`# SPDX-License-Identifier: MIT`) en cada archivo propio.
2. **DCO**: todo commit con `git commit -s`.
3. **Fragmento de changelog** en `.changes/unreleased/` por cada cambio.
4. **La versión vive en dos lugares**: `manifest.json` y `secrets_unlocker/config.yaml`.
   El release aborta si no coinciden con el tag.
5. Ciclo: `tema/*` → `devs` → `main` → tag `vX.Y.Z`.

## 5. Lo que ya nos mordió

- `ConfigEntry.__setattr__` rechaza asignar `data`: usar `async_update_entry`.
- `entry.data` es `MappingProxyType`, no `dict`.
- `as_storage_fragment` es un `orjson.Fragment` inmutable y cacheado: hay que
  reconstruir con `as_dict()` y limpiar `entry.__dict__`.
- El Supervisor reescribe el `data` de `hassio`: ese dominio se excluye.
- Los custom components cargan **después** de `config_entries.async_initialize()`,
  así que la primera vuelta se arregla con el puente de arranque.
- El manifest desordenado tumba `hassfest`; `security` no es una categoría válida.
- Un add-on con `startup: initialize` arranca ~6s antes del core: hay margen,
  pero el componente igual necesita reintentos.

## 6. Prohibido

- Afirmar que algo funciona sin ejecutarlo y mostrar la salida.
- Tocar el HA operativo del usuario para probar: se usa una VM de prueba.
- Escribir credenciales en archivos del repositorio.
- Añadir una dependencia sin justificar por qué no alcanza la biblioteca estándar
  o lo que HA ya trae (`cryptography` y `aiohttp` vienen con el core).

## 7. Comandos

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements_test.txt
.venv/bin/python -m pytest -q tests
.venv/bin/ruff check custom_components tests
.venv/bin/ruff format --check custom_components tests
tools/hooks/spdx.sh
python tools/check_assets.py
tools/changelog.sh prepare X.Y.Z
```
