# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y
versionado [SemVer](https://semver.org/lang/es/).

## [0.2.26] - 2026-11-27

- El README describia un producto que ya no existe: pedia pegar la master key a mano, mandaba al Ingress del add-on, afirmaba que /data entero queda fuera del backup (solo se excluye master.key) y decia que el panel no distingue administradores. Se reescribe con el flujo real (imagen publicada, llave generada en /data/master.key, panel del componente solo para admin) y se agrega arriba la advertencia de que el shim hookea un metodo privado y puede romperse con una actualizacion de HA.
- _data_to_save parte de super() y solo transforma el data, asi que los campos que agregue el core no se pierden; el fragmento opaco de orjson se convierte antes de tocarlo; si una entrada no se puede cifrar se aborta el guardado en vez de escribirla en claro; _clave_local se elimina, sin add-on no hay clave nueva; las recargas del puente van de a una y solo para las entradas afectadas.

## [0.2.25] - 2026-11-27

- El add-on no declaraba image, asi que el Supervisor compilaba en el equipo del usuario. Ahora apunta a ghcr.io/maurorosero/safe-store-unlocker, y el release publica tambien el tag sin la v (0.2.25), que es el que el Supervisor busca a partir de la version del config.

## [0.2.24] - 2026-11-27

- La restauracion escribia la llave en options.json, y las opciones si viajan en el backup: la llave terminaba copiada en cada backup. Ahora se escribe en /data/master.key con 600, se verifica que quedo, y recien despues se vacia la opcion. Al arrancar, una clave que haya llegado por las opciones se mueve al archivo. Cuatro pruebas con un directorio real.

## [0.2.23] - 2026-11-27

- El panel de la llave ahora funciona: era un iframe contra una vista que exigia la cabecera de autorizacion, y el iframe no la manda, asi que HA respondia 401. El panel lleva un token propio en la URL, que solo recibe un administrador porque el panel es require_admin. El add-on deja de exponer Ingress: la interfaz vive en el componente. Probado en la VM: con token 200, sin token 403, QR 200/4059 bytes, 26 tests.

## [0.2.22] - 2026-11-27

- La interfaz de la llave vuelve al add-on por Ingress, que es la que se certifico en la VM: se habia movido al componente y el panel no montaba.

## [0.2.21] - 2026-11-27

- La instalacion se documenta paso a paso y dice que el add-on va primero: instalar la integracion antes deja la llave en /config y el add-on ya no puede leer el archivo.
- El panel de la llave es un iframe: con panel custom Home Assistant lo registraba pero no montaba el elemento y la pagina quedaba en blanco.

## [0.2.20] - 2026-11-27

- Las llamadas al Supervisor usan aiohttp: con urllib Home Assistant aborta la peticion por bloquear el event loop.

## [0.2.19] - 2026-11-27

- La vista usa web.Response: HomeAssistantView no expone self.response, asi que pedir el QR devolvia 500.

## [0.2.18] - 2026-11-27

- La interfaz de la llave pasa al componente como panel lateral de Home Assistant, visible solo para administradores; el add-on queda solo custodiando la llave.

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
