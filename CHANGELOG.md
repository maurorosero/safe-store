# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y
versionado [SemVer](https://semver.org/lang/es/).

## [0.2.17] - 2026-11-27

- Tests unitarios del shim: cifrado al guardar, descifrado al cargar, busqueda de la llave y volcado, sin levantar Home Assistant.

## [0.2.16] - 2026-11-27

- safe_store.dump queda verificado: vuelca las entradas en claro con permisos 600 mientras el archivo original sigue cifrado.

## [0.2.15] - 2026-11-27

- La tabla de estado del README recoge lo verificado de la interfaz: descarga del QR dentro de Home Assistant, restauracion subiendo el PNG y el aviso cuando la llave no tiene copia.

## [0.2.14] - 2026-11-27

- Despues de restaurar la llave el add-on se reinicia por el Supervisor, que es quien escribe la configuracion; antes terminaba el proceso y la opcion nueva no entraba en vigor.

## [0.2.13] - 2026-11-27

- La pagina del add-on apunta al QR con la ruta completa del Ingress, asi que la descarga entrega la imagen y no la pagina.

## [0.2.12] - 2026-11-27

- El add-on tiene interfaz web: muestra la huella de la llave, permite descargar el QR para guardarlo y restaura la llave subiendo ese PNG.
- El QR se puede bajar en cualquier momento, y la restauracion escribe la llave en la configuracion del add-on, que si viaja en los backups.

## [0.2.11] - 2026-11-27

- El README vuelve a mostrar los badges de CI, versión, licencia y HACS, y la tabla de estado dice qué está verificado y qué no.
- Un release ahora empieza por `tools/release-prep.sh`, y el CI falla si un cambio visible no trae su documentación.

## [0.2.10] - 2026-11-26

- Con el archivo cifrado, si el add-on no responde ya no se genera una clave local: la integracion queda en reintento

## [0.2.9] - 2026-11-26

- La integracion consulta el detalle del add-on para obtener su direccion, porque el listado no la incluye

## [0.2.8] - 2026-11-26

- La integracion le pregunta al Supervisor el hostname del add-on en vez de asumirlo

## [0.2.7] - 2026-11-26

- El add-on declara un hostname estable y la integracion lo usa, en vez del slug que lleva el hash del repositorio

## [0.2.6] - 2026-11-26

- La integracion crea el token compartido con el add-on si no existe, sin el cual caia siempre al archivo local

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
