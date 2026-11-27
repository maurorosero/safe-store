# Expediente de release 0.2.11

Generado: 2026-11-27T03:09:40-05:00
Base: v0.2.8
Commits: 5

## 1. Fragmentos pendientes

(ninguno: todos los cambios fueron internos)
## 2. Commits desde v0.2.8

- b7ee2f6 fix: nunca generar una clave nueva sobre un archivo cifrado
- 3e8fd19 docs: pasos de instalacion verificados y estado real
- 210a657 fix: la direccion del add-on se lee de su detalle

## 3. Archivos tocados

 .changes/release-0.2.10.md                 |  4 ++
 .changes/release-0.2.9.md                  |  4 ++
 CHANGELOG.md                               |  8 +++
 README.md                                  | 21 ++++++--
 custom_components/safe_store/__init__.py   | 85 +++++++++++++++++++++---------
 custom_components/safe_store/const.py      |  3 ++
 custom_components/safe_store/manifest.json |  2 +-
 secrets_unlocker/config.yaml               |  2 +-
 8 files changed, 97 insertions(+), 32 deletions(-)

## 4. Documentos que suelen necesitar actualización

| Documento | Revisar si… |
|---|---|
| `README.md` | cambió qué cifra, cómo se instala, cómo se configura, los badges o la tabla de estado |
| `AGENTS.md` | cambió el proceso de desarrollo, el flujo de ramas o una regla |
| `CONTRIBUTING.md` | cambió el proceso de contribución |
| `custom_components/safe_store/strings.json` | cambió un texto que ve quien usa la integración |
| `secrets_unlocker/config.yaml` | cambió una opción, un puerto o un requisito del add-on |

## 5. Qué se espera de vos

1. Escribir la sección de `CHANGELOG.md` en prosa, desde el punto de vista de quien usa
   Home Assistant: qué puede hacer ahora que antes no, o qué dejó de romperse. Sin jerga
   interna, sin números de commit, sin inventar nada que no esté en los fragmentos o en
   el diff. Una línea por cambio; dos como máximo si hace falta contexto.
2. Actualizar sólo los documentos del punto 4 que de verdad cambiaron. Si el fragmento
   describe algo visible y ningún documento cambió, el fragmento lleva una línea
   `Docs: none` que explica por qué no aplica.
3. Revisar la tabla de estado del README: cada fila dice verificado o no, y una fila
   nueva sin evidencia no se escribe.
4. `tools/changelog.sh prepare v0.2.11` para ensamblar la sección.
5. `make check`, commit firmado.
