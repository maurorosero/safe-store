#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Fragmentos de changelog por cambio, sección por release.
#   check          informa fragmentos pendientes (no bloquea)
#   prepare <ver>  arma la sección en CHANGELOG.md y archiva los fragmentos
set -eu
cmd="${1:-check}"

fragmentos() {
  find .changes/unreleased -name '*.md' ! -name 'README.md' 2>/dev/null | sort
}

case "$cmd" in
  check)
    lista="$(fragmentos)"
    if [ -z "$lista" ]; then
      echo "changelog: sin fragmentos pendientes"
    else
      echo "changelog: fragmentos pendientes"
      echo "$lista" | sed 's/^/  /'
    fi
    ;;

  prepare)
    ver="${2:?falta la versión}"
    archivo=".changes/release-${ver}.md"
    { echo "## [${ver}] - $(date +%Y-%m-%d)"; echo; } > "$archivo"
    while IFS= read -r f; do
      [ -n "$f" ] || continue
      sed 's/^/- /' "$f" >> "$archivo"
    done < <(fragmentos)
    echo >> "$archivo"

    if [ -f CHANGELOG.md ]; then
      { head -n 3 CHANGELOG.md; cat "$archivo"; tail -n +4 CHANGELOG.md; } > CHANGELOG.new
      mv CHANGELOG.new CHANGELOG.md
    else
      { echo "# Changelog"; echo; cat "$archivo"; } > CHANGELOG.md
    fi
    find .changes/unreleased -name '*.md' ! -name 'README.md' -delete
    echo "changelog: sección ${ver} creada y fragmentos archivados"
    ;;

  *)
    echo "uso: $0 [check|prepare <version>]" >&2
    exit 2
    ;;
esac
