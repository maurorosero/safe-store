## [0.2.23] - 2026-11-27

- El panel de la llave ahora funciona: era un iframe contra una vista que exigia la cabecera de autorizacion, y el iframe no la manda, asi que HA respondia 401. El panel lleva un token propio en la URL, que solo recibe un administrador porque el panel es require_admin. El add-on deja de exponer Ingress: la interfaz vive en el componente. Probado en la VM: con token 200, sin token 403, QR 200/4059 bytes, 26 tests.

