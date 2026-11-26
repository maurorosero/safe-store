# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y
versionado [SemVer](https://semver.org/lang/es/).

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
