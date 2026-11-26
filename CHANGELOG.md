# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y
versionado [SemVer](https://semver.org/lang/es/).

## [0.2.5] - 2026-11-26

- El add-on se declara como servicio s6, que es como arranca la base de Home Assistant

## [0.2.4] - 2026-11-26

- El add-on arranca con la ruta absoluta de python3, que s6 no resuelve por PATH

## [0.2.3] - 2026-11-26

- El Dockerfile del add-on define una base por defecto cuando el Supervisor no pasa BUILD_FROM

## [0.2.2] - 2026-11-26

- El add-on construye sobre la base de Home Assistant e instala python3 con apk
- El release publica una imagen por arquitectura y las une en un manifest

## [0.2.1] - 2026-11-26

- La master key se configura desde la pestaña de configuración del add-on
- El add-on genera una master key y la anuncia en su log si no recibe ninguna
- El README explica cómo obtener y conservar la key sin acceso al filesystem

## [0.2.0] - 2026-11-26

### Añadido

- Integración `safe_store`: cifra con AES-256-GCM el campo `data` de cada config
  entry antes de escribir `core.config_entries`.
- Descifrado en caliente al arrancar, con recarga de las integraciones afectadas.
- Add-on `secrets_unlocker`: entrega la master key por HTTP local con token,
  desde un archivo simple o desde un `.env` cifrado con SOPS y age.
- Servicio `safe_store.dump` para volcar las credenciales en claro antes de
  desinstalar.
- Alta por config flow: la instalación no toca `configuration.yaml`.

### Notas

- El dominio `hassio` queda excluido: el Supervisor reescribe su `data`.
- Con el archivo cifrado y sin master key, la integración no escribe nada y las
  entradas quedan en `setup_retry`.

## [0.1.0] - 2026-11-26

### Añadido

- Cifrado AES-256-GCM del `data` de `core.config_entries` con descifrado al
  arrancar.
- Add-on `secrets_unlocker`.
- Servicio `safe_store.dump`.
- Exclusión del dominio `hassio`.
