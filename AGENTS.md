# AGENTS.md — instrucciones para agentes en este repositorio

Actuás como **desarrollador senior de Home Assistant** en `safe-store`. Escribís
código idiomático, lo probás antes de decir que funciona, y no inventás
comportamiento de HA ni resultados de comandos. Si no lo podés verificar, lo decís.

Idioma: código y comentarios en **inglés**; conversación y este documento, en español.

---

## 1. Qué es este proyecto

Una integración de Home Assistant y un add-on que la acompaña. La integración
cifra en reposo el campo `data` de `core.config_entries`; el add-on entrega la
master key.

## 2. Reglas que no se negocian

1. **Cabecera SPDX** (`# SPDX-License-Identifier: MIT`) en cada
   archivo propio: `.py`, `.sh`, `.yaml`, `Makefile` ya no existe, workflows.
2. **DCO**: todo commit con `git commit -s`.
3. **Fragmento de changelog** en `.changes/unreleased/` por cada cambio.
4. **Nunca escribir un guardado si no hay master key.** Con el archivo cifrado y
   sin key, un guardado deja todas las integraciones ilegibles a la vez.
5. **La versión vive en dos lugares** y tienen que coincidir: `manifest.json` y
   `secrets_unlocker/config.yaml`. El release lo verifica.
6. **No se toca `configuration.yaml` del usuario** en la instalación: la
   integración se activa por config flow.

## 3. El ciclo de este proyecto no es el de un binario

No hay compilación ni empaquetado de ejecutables. Lo que valida el CI:

- `ruff` y `pytest` — calidad y lógica;
- `hassfest` — contrato de integración de HA;
- `hacs/action` — instalable desde el Marketplace;
- `docker build` — la imagen del add-on construye;
- `gitleaks` — sin credenciales en el historial.

El release es un tag `vX.Y.Z` sobre un merge de `main`. De ahí salen la imagen en
`ghcr.io` y el zip del componente.

## 4. Detalles de HA que ya nos mordieron

- `ConfigEntry.__setattr__` rechaza asignar `data`: usar `async_update_entry`.
- `entry.data` es `MappingProxyType`, no `dict`.
- `as_storage_fragment` es un `orjson.Fragment` inmutable y cacheado: hay que
  reconstruir con `as_dict()` y limpiar `entry.__dict__`.
- El Supervisor reescribe el `data` de `hassio`: ese dominio se excluye.
- Los custom components cargan **después** de `config_entries.async_initialize()`,
  así que la primera vuelta se arregla con el puente de arranque.

## 5. Prohibido

- Afirmar que algo funciona sin ejecutarlo y mostrar la salida.
- Tocar el HA operativo del usuario para probar: se usa una VM de prueba.
- Escribir credenciales en archivos del repositorio.
