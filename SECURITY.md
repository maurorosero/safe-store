# Seguridad

## Qué protege y qué no

Safe Store cifra **el archivo** `core.config_entries` en disco. Protege de:

- otros usuarios del host que puedan leer `/config`;
- copias sueltas del archivo (foros, tickets, repositorios);
- backups filtrados, **solo si la master key no viaja en ellos**.

No protege de un proceso comprometido con acceso a la master key, ni de root
en la máquina. Una integración necesita el secreto en claro para autenticarse
contra un tercero: eso no lo cambia ningún cifrado en el mismo host.

## Reportar

Abrí un issue privado en <https://github.com/maurorosero/safe-store/security/advisories/new>.
No publiques detalles de una vulnerabilidad en un issue público.
