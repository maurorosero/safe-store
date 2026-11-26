# Safe Store

[![HACS Custom][hacs-badge]][hacs-url]
[![Release][release-badge]][release-url]
[![License][license-badge]][license-url]

Cifra en reposo las credenciales de tus integraciones de Home Assistant.

Las credenciales de las integraciones viven hoy en claro en
`.storage/core.config_entries`: las puede leer cualquier usuario del host y
viajan en cada backup. Safe Store cifra ese contenido con AES-256-GCM sin
cambiar nada en las integraciones.

[hacs-badge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg
[hacs-url]: https://github.com/hacs/integration
[release-badge]: https://img.shields.io/github/v/release/maurorosero/safe-store
[release-url]: https://github.com/maurorosero/safe-store/releases
[license-badge]: https://img.shields.io/github/license/maurorosero/safe-store
[license-url]: LICENSE

## Requisitos

- Home Assistant 2026.11 o superior.
- Home Assistant OS o Supervised, para el add-on.
- El add-on **Safe Store Unlocker** (entrega la master key) o una master key
  local en `/config/.ss.key`.

## Instalación

### Add-on

[![Abrir tu instancia y añadir el repositorio][add-repo-badge]][add-repo-url]

Ajustes → Apps → Repositorios → añadir `https://github.com/maurorosero/safe-store`,
e instalar **Safe Store Unlocker**.

En su `/data` tiene que quedar una de estas dos fuentes:

| Archivo | Descripción |
|---|---|
| `master.key` | 32 bytes en hexadecimal. Simple, sin SOPS. |
| `age.key` + `secrets.env.enc` | Identidad age y archivo SOPS con la clave `SAFE_STORE_MASTER_KEY`. |

Generar una key:

```sh
python3 -c "import os;print(os.urandom(32).hex())"
```

La identidad age **no** se respalda: `backup_exclude` la deja fuera a propósito.

### Integración

[![Abrir tu instancia y añadir el repositorio de HACS][add-hacs-badge]][add-hacs-url]

1. Marketplace → Repositorios → añadir `https://github.com/maurorosero/safe-store`.
2. Instalar **Safe Store**.
3. Reiniciar Home Assistant.
4. Ajustes → Dispositivos y servicios → **Añadir integración** → *Safe Store*.

[add-repo-badge]: https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg
[add-repo-url]: https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fmaurorosero%2Fsafe-store
[add-hacs-badge]: https://my.home-assistant.io/badges/hacs_repository.svg
[add-hacs-url]: https://my.home-assistant.io/redirect/hacs_repository/?owner=maurorosero&repository=safe-store&category=integration

## Cómo funciona

```
arranque
  add-on                 entrega la master key por HTTP local, con token
  core                   lee el archivo: el data llega cifrado
  Safe Store             descifra las entradas vivas, las recarga
  → las integraciones quedan operativas

cada guardado
  el data se cifra antes de escribir → en disco nunca hay texto plano
```

El archivo conserva legibles `entry_id`, `domain`, `title` y `version`. Solo el
`data` va cifrado:

```json
"data": { "__ss_v1__": "vHB/9a+5tQw16dAufppGUd/IzUG8jrk2D2qYRIT+Y2d..." }
```

## Servicios

### `safe_store.dump`

Escribe todas las credenciales descifradas en `/config/.ss_dump.json` con
permisos `600`. **Es obligatorio antes de desinstalar**: sin la key, el archivo
cifrado no se puede leer.

```yaml
action: safe_store.dump
```

## Qué no hace

- No toca `secrets.yaml` — ese archivo no pasa por este camino.
- No protege de root con la master key accesible.
- No cifra `hassio`: el Supervisor reescribe su `data` en cada arranque.

## Solución de problemas

**Las integraciones quedan en `setup_retry` después de arrancar**
El add-on no está entregando la key. Revisá sus logs en Ajustes → Apps →
Safe Store Unlocker → Registro.

**Quiero desinstalar**
Ejecutá `safe_store.dump` primero, verificá que `.ss_dump.json` tenga las
credenciales, y recién entonces desinstalá.

**Cambié la master key**
Hoy no hay rotación automática: el archivo queda ilegible. Volvé a la key
anterior, ejecutá `dump`, y re-cifrá desde una instalación limpia.

## Contribuir

Ver [CONTRIBUTING.md](CONTRIBUTING.md). El flujo es `tema/*` → `devs` → `main`,
y el release es un tag sobre el merge de `main`.

## Licencia

MIT — ver [LICENSE](LICENSE).
