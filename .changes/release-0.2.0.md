## [0.2.0] - 2026-11-26

- Cifra con AES-256-GCM el campo data de cada config entry antes de escribir core.config_entries
- Descifra en caliente al arrancar y recarga las integraciones afectadas
- Añade el add-on secrets_unlocker, que entrega la master key por HTTP local con token
- Permite la master key desde un archivo simple o desde un env cifrado con SOPS y age
- Añade el servicio safe_store.dump para volcar las credenciales en claro antes de desinstalar
- Excluye el dominio hassio, cuyo data reescribe el Supervisor
- Valida en CI con hassfest, la acción de HACS, los assets y gitleaks

