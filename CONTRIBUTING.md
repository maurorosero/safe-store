# Contribuir

## Ciclo

```
tema/<algo>  →  devs  →  main  →  tag vX.Y.Z
```

1. Rama `tema/<algo>` desde `devs`.
2. Un fragmento por cambio en `.changes/unreleased/<algo>.md`, una línea en
   imperativo.
3. Pull request a `devs`. El CI valida ruff, pytest, hassfest, el Marketplace,
   el add-on y los secretos.
4. Cuando `devs` está estable: PR a `main` y merge con `--no-ff`.
5. Release: `tools/changelog.sh prepare X.Y.Z`, subir la versión en
   `manifest.json` **y** en `secrets_unlocker/config.yaml`, commit, merge a
   `main`, tag `vX.Y.Z` sobre ese merge.

## Versión en dos lugares

`manifest.json` y el `config.yaml` del add-on son fuentes de versión distintas
—una para el Marketplace, otra para el Supervisor— y el release aborta si no
coinciden.

## Commits

Firmados con `git commit -s` (DCO). El CI rechaza commits sin `Signed-off-by`.

## Qué valida el CI, y por qué

| Job | Qué comprueba |
|---|---|
| `calidad` | ruff, pytest, SPDX, versión del manifest |
| `hassfest` | contrato de integración de Home Assistant |
| `marketplace` | que el repo sea instalable desde el Marketplace |
| `addon` | que la imagen del add-on construya |
| `secretos` | gitleaks sobre todo el historial |
| `dco` | `Signed-off-by` en los commits del PR |
| `changelog` | que los cambios traigan su fragmento |

No hay compilación de binarios. La distribución de una integración es el tag;
la del add-on, su imagen.
