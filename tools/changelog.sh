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
      # Se inserta antes de la primera sección existente, no después de la cabecera.
      linea="$(grep -n '^## \[' CHANGELOG.md | head -1 | cut -d: -f1 || true)"
      if [ -n "${linea}" ]; then
        { head -n $((linea - 1)) CHANGELOG.md; cat "$archivo"; tail -n +"${linea}" CHANGELOG.md; } > CHANGELOG.new
      else
        { cat CHANGELOG.md; echo; cat "$archivo"; } > CHANGELOG.new
      fi
      mv CHANGELOG.new CHANGELOG.md
    else
      { echo "# Changelog"; echo; cat "$archivo"; } > CHANGELOG.md
    fi
    find .changes/unreleased -name '*.md' ! -name 'README.md' -delete
    echo "changelog: sección ${ver} creada y fragmentos archivados"
    ;;

  guard)
    # En un PR a main el CHANGELOG tiene que cambiar; en cualquier PR, un
    # fragmento visible exige que el mismo cambio toque documentación.
    base="${2:?falta la rama base}"
    fallo=0

    if [ "${base}" = "main" ] && git diff --quiet "origin/${base}...HEAD" -- CHANGELOG.md; then
      echo "docs: CHANGELOG.md no cambió respecto de ${base}" >&2
      fallo=1
    fi

    visibles=0
    sin_docs=""
    for f in $(find .changes/unreleased -maxdepth 1 -name '*.md' ! -name 'README.md' 2>/dev/null | sort); do
      tipo="$(basename "$f" | cut -d- -f1)"
      case "${tipo}" in
        added|changed|deprecated|removed)
          visibles=1
          grep -qi '^Docs: none' "$f" || sin_docs="${sin_docs} ${f}"
          ;;
      esac
    done

    if [ "${visibles}" -eq 1 ] && [ -n "${sin_docs}" ]; then
      tocados="$(git diff --name-only "origin/${base}...HEAD")"
      if ! printf '%s\n' "${tocados}" | grep -qE '^(README\.md|AGENTS\.md|CONTRIBUTING\.md|custom_components/safe_store/strings\.json|secrets_unlocker/config\.yaml)$'; then
        echo "docs: cambios visibles sin documentación que los acompañe:" >&2
        printf '%s\n' "${sin_docs# }" | sed 's/^/  /' >&2
        echo "docs: actualizá el documento que corresponda o agregá 'Docs: none' al fragmento" >&2
        fallo=1
      fi
    fi

    [ "${fallo}" -eq 0 ] && echo "docs: ok"
    exit "${fallo}"
    ;;

  *)
    echo "uso: $0 [check|guard <base>|prepare <version>]" >&2
    exit 2
    ;;
esac
