# AGENTS.md

Guía para agentes de IA que trabajen en este repositorio. Complementa el
`README.md` (para humanos) con lo que un agente necesita para no equivocarse:
comandos, convenciones y el ciclo de desarrollo.

## Project

Integración de Home Assistant (`custom_components/safe_store`) más el add-on que
la acompaña (`secrets_unlocker`). La integración cifra en reposo el campo `data`
de `core.config_entries`; el add-on entrega la master key por HTTP local.

Licencia MIT. Código y docstrings en inglés; este documento y los PR en español.

## Setup commands

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements_test.txt
```

Si `PYTHONPATH` apunta a otro entorno, limpialo al invocar Python:
`env -u PYTHONPATH .venv/bin/python ...`.

## Development commands

```sh
.venv/bin/python -m pytest -q tests                 # tests
.venv/bin/ruff check custom_components tests        # lint
.venv/bin/ruff format --check custom_components tests   # formato
tools/hooks/spdx.sh                                  # cabeceras SPDX
python tools/check_assets.py                         # iconos y traducciones
tools/hooks/dco.sh origin/devs                       # firmas en los commits
tools/changelog.sh prepare X.Y.Z                     # sección de release
```

No hay `make`. La validación local es un script: `tools/check.sh`. La pesada la
hacen `hassfest` y la acción de HACS en el CI.

## Code style

- Python 3.12, `line-length = 100`. Lo impone `ruff` (`pyproject.toml`).
- Type hints en toda función pública, incluido `-> None`.
- `from __future__ import annotations` al inicio del módulo.
- `Mapping`/`Sequence` de `collections.abc` en firmas, no `dict`/`list`.
- `pathlib.Path` para rutas; f-strings para texto; `%s` con argumentos en logging.
- Docstrings en inglés, una línea de resumen y luego el detalle.

## Architecture

```
custom_components/safe_store/
  __init__.py       setup/unload, shim de cifrado, servicio dump
  config_flow.py    alta por UI (sin YAML)
  const.py          constantes
  crypto.py         cifrado puro, sin imports del paquete (testeable aislado)
  manifest.json     domain y name primero, resto alfabético
  strings.json      fuente de traducciones
  translations/     en.json generado desde strings.json
  brand/            icon.png y logo.png
secrets_unlocker/   add-on: Dockerfile (sops + age) y server.py
tools/              hooks de calidad y validación de assets
.changes/           fragmentos de changelog
```

## Home Assistant rules

- **Siempre `async_setup_entry`**, nunca `async_setup`.
- Todo lo configurable va por **config flow**; `configuration.yaml` no es una vía
  de instalación.
- Texto de usuario en `strings.json` / `translations/`, nunca en Python.
- `manifest.json` con `domain`, `name` y el resto alfabético: `hassfest` falla si no.
- `categories` solo con valores de la lista oficial; si dudás, no lo pongas.
- Servicios declarados en `services.yaml` y descritos en `strings.json`.
- Nunca bloquear el event loop: I/O con `async_add_executor_job`, red con timeout.

## Known pitfalls

- `ConfigEntry.__setattr__` rechaza asignar `data`: usar `async_update_entry`.
- `entry.data` es `MappingProxyType`, no `dict`.
- `as_storage_fragment` es un `orjson.Fragment` inmutable y cacheado: reconstruir
  con `as_dict()` y limpiar `entry.__dict__`.
- El Supervisor reescribe el `data` de `hassio`: ese dominio se excluye.
- Los custom components cargan después de `config_entries.async_initialize()`;
  la primera vuelta se arregla con el puente de arranque.
- Un add-on con `startup: initialize` arranca ~6s antes del core.

## Development workflow

```
tema/<algo>  →  devs  →  main  →  tag vX.Y.Z
```

1. **Rama de trabajo**

```sh
git checkout devs && git pull
git checkout -b tema/<algo>
```

2. **Cambio + fragmento de changelog**

`.changes/unreleased/<algo>.md`, una línea en imperativo.

3. **Commit firmado**

```sh
git add -A
git commit -s -m "tipo: resumen en imperativo"
```

4. **PR a `devs`**

```sh
git push -u origin tema/<algo>
gh pr create --base devs --fill
```

El CI tiene que quedar verde: `calidad`, `assets`, `hassfest`, `marketplace`,
`add-on`, `secretos`, `DCO`, `changelog`.

5. **Integración a `main`** (cuando `devs` está estable)

```sh
gh pr create --base main --head devs --title "release: <resumen>"
gh pr merge --merge
```

6. **Release**

```sh
git checkout main && git pull
tools/changelog.sh prepare X.Y.Z          # crea .changes/release-X.Y.Z.md
# subir "version" en manifest.json Y en secrets_unlocker/config.yaml
git add -A && git commit -s -m "chore: release X.Y.Z"
git push
git tag vX.Y.Z && git push --tags
```

El workflow de release aborta si el tag no es un merge de `main`, o si
`manifest.json` y `config.yaml` no dicen la misma versión.

## La documentación viaja con el cambio

Si hay un fragmento de tipo `added`, `changed`, `deprecated` o `removed`, el
mismo commit tiene que tocar `README.md`, `AGENTS.md`, `CONTRIBUTING.md`,
`custom_components/safe_store/strings.json` o `secrets_unlocker/config.yaml`.
Si de verdad no aplica, el fragmento lleva una línea `Docs: none` que no se
copia al changelog. `tools/changelog.sh guard` lo hace cumplir en CI, y en un PR
a `main` además falla si `CHANGELOG.md` no cambió.

Un release no empieza por el tag: empieza por el expediente.

```sh
tools/release-prep.sh v0.2.11   # fragmentos, commits, diff y qué documentos revisar
tools/changelog.sh prepare 0.2.11
tools/check.sh
git commit -s -m "changelog: 0.2.11"
```

El expediente existe porque escribir el changelog y actualizar el README de
memoria es exactamente cómo se pierden un badge o una tabla de estado.

## Definition of done

- Tests pasan y cubren la lógica nueva.
- `ruff` y el formato, limpios.
- SPDX en cada archivo tocado.
- Fragmento de changelog presente.
- Documentación actualizada o `Docs: none` en el fragmento.
- Si el release toca lo que el README describe: badges, número de versión y tabla de estado al día.
- Si cambia la UI: `strings.json` **y** `translations/en.json`.
- Si cambia una versión: `manifest.json` **y** `config.yaml`.
- CI verde en el PR.

## Constraints

- No probar nunca contra el Home Assistant operativo: se usa una VM de prueba.
- No escribir credenciales ni claves en archivos del repositorio.
- No añadir dependencias si alcanza con `cryptography` o `aiohttp`, que ya vienen
  con Home Assistant.
- Si no podés verificar algo, decilo; no lo afirmes.
