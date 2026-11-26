#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
#
# Sincroniza los metadatos del repositorio remoto con los archivos del repo.
#
#   description.me  ->  el campo Description de GitHub (una línea, máx. 350)
#   about.me        ->  el bloque About: su última línea "Topics: ..." da los temas
#
# La regla es que el About **sale de about.me**: si cambia el archivo, se vuelve
# a correr esto y el repositorio remoto queda igual.
#
#   ./tools/repo-meta.sh --dry-run          muestra qué aplicaría
#   ./tools/repo-meta.sh                    aplica con gh (necesita sesión iniciada)
#   ./tools/repo-meta.sh --repo owner/name  apunta a otro repositorio

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SIMULAR=0
REPO=""

while [ $# -gt 0 ]; do
	case "$1" in
	--dry-run) SIMULAR=1; shift ;;
	--repo) REPO="${2:?falta owner/nombre}"; shift 2 ;;
	--repo=*) REPO="${1#*=}"; shift ;;
	-h | --help) sed -n '2,16p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
	*) echo "opción desconocida: $1" >&2; exit 1 ;;
	esac
done

DESCRIPCION="$(tr -s '[:space:]' ' ' <"${RAIZ}/description.me" | sed 's/^ //; s/ $//')"
if [ -z "${DESCRIPCION}" ]; then
	echo "description.me está vacío" >&2
	exit 1
fi
if [ "${#DESCRIPCION}" -gt 350 ]; then
	echo "description.me tiene ${#DESCRIPCION} caracteres: GitHub corta en 350" >&2
	exit 1
fi

TEMAS="$(grep -i '^Topics:' "${RAIZ}/about.me" | tail -1 | sed 's/^[Tt]opics:[[:space:]]*//' | tr -d ' ')"
if [ -z "${TEMAS}" ]; then
	echo "about.me no tiene una línea 'Topics:'" >&2
	exit 1
fi

echo "description (${#DESCRIPCION} caracteres):"
echo "  ${DESCRIPCION}"
echo "topics:"
echo "  ${TEMAS}"

if [ "${SIMULAR}" -eq 1 ]; then
	echo ""
	echo "[simulado] no se tocó el repositorio remoto"
	exit 0
fi

if ! command -v gh >/dev/null 2>&1; then
	echo "gh no está instalado: no puedo aplicar los metadatos" >&2
	exit 1
fi

args=(repo edit --description "${DESCRIPCION}" --add-topic "${TEMAS}")
if [ -n "${REPO}" ]; then
	args+=("${REPO}")
fi

gh "${args[@]}"
echo "repositorio actualizado"
