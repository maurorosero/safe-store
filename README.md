# Safe Store

Cifra en reposo las credenciales de tus integraciones de Home Assistant.

Hoy viven en claro en `/config/.storage/core.config_entries`: legibles por
cualquier usuario del host y presentes en cada backup. Safe Store las cifra con
AES-256-GCM sin que ninguna integración se entere.

## Cómo funciona

```
arranque
  add-on secrets_unlocker   entrega la master key por HTTP local, con token
  core lee el archivo       el data llega cifrado: {"__ss_v1__": "<blob>"}
  Safe Store carga          descifra las entradas vivas y las recarga
  → las integraciones quedan funcionando

cada guardado
  el data se cifra antes de escribir → en disco nunca hay texto plano
```

El archivo conserva legibles `entry_id`, `domain`, `title` y `version`. Solo el
`data` va cifrado.

## Instalación

**1. El add-on** (entrega la master key)

Ajustes → Apps → Repositorios → añadir:

```
https://github.com/maurorosero/safe-store
```

Instalar **Safe Store Unlocker**. En su `/data` tiene que quedar una de estas dos:

- `master.key` — 32 bytes en hexadecimal. Simple, sin SOPS.
- `age.key` + `secrets.env.enc` — identidad age y archivo SOPS con la clave
  `SAFE_STORE_MASTER_KEY`. La identidad **no** va en el backup (`backup_exclude`).

Generar una key:

```sh
python3 -c "import os;print(os.urandom(32).hex())"
```

**2. La integración**

Marketplace → Repositorios → añadir `https://github.com/maurorosero/safe-store` →
instalar **Safe Store**. O copiar `custom_components/safe_store` a `/config/custom_components/`.

**3. Activar**

Ajustes → Dispositivos y servicios → Añadir integración → **Safe Store** → reiniciar.

## Antes de desinstalar

El archivo queda cifrado y HA no puede leerlo sin la key. Volcá todo en claro:

```yaml
service: safe_store.dump
```

Escribe `/config/.ss_dump.json` (permisos 600). Recién entonces desinstalá.

Si el add-on no está disponible y el archivo está cifrado, Safe Store **no
escribe nada**: las integraciones quedan en `setup_retry` hasta que vuelva la key.
Un guardado con datos a medio cifrar corrompería todas a la vez.

## Qué no hace

- No toca `secrets.yaml` (no pasa por este camino).
- No protege de root con la master key accesible.
- No cifra `hassio`: el Supervisor reescribe su `data` en cada arranque.

## Estado

`0.1.0`. La integración está probada sobre Home Assistant OS 2026.11 (cifra,
descifra, recarga, volcado y reinicios). El add-on se entrega con la key desde
`/data`; SOPS y age son opcionales.
