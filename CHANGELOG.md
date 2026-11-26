# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).
Versionado [SemVer](https://semver.org/lang/es/).

## [0.1.0] - 2026-11-26

### Añadido

- Cifrado AES-256-GCM del `data` de `core.config_entries`, con descifrado en
  caliente al arrancar y recarga de las entradas afectadas.
- Add-on `secrets_unlocker`: entrega la master key por HTTP local con token,
  desde un archivo simple o desde un `.env` cifrado con SOPS y age.
- Servicio `safe_store.dump` para volcar las credenciales en claro antes de
  desinstalar.
- Exclusión del dominio `hassio`, cuyo `data` reescribe el Supervisor.
