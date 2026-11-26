# Contribuir

## Ciclo

1. Rama `tema/<algo>` desde `devs`.
2. Un fragmento en `.changes/unreleased/<algo>.md` con una línea en imperativo.
3. Pull request a `devs`: el CI valida ruff, pytest, hassfest, el Marketplace, el
   add-on y los secretos.
4. Cuando `devs` está estable, PR a `main` y merge con `--no-ff`.
5. El release es un tag `vX.Y.Z` sobre ese merge. `manifest.json` y el `config.yaml`
   del add-on tienen que decir la misma versión, o el workflow no publica.

## Commits

Firmados con `git commit -s` (DCO). El CI rechaza commits sin `Signed-off-by`.

## Qué valida el CI, y por qué

- **ruff y pytest**: calidad del código Python.
- **hassfest**: que la integración cumpla el contrato de Home Assistant.
- **hacs/action**: que el repositorio sea instalable desde el Marketplace.
- **docker build**: que la imagen del add-on construya.
- **gitleaks**: que no haya credenciales en el historial.

No hay compilación de binarios: la distribución de una integración es el tag, y
la del add-on es su imagen.
