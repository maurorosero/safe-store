#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
#
# Lo mismo que corre el CI, en un comando. Sin make.
#
#   tools/check.sh
#
# ruff, formato, tests, SPDX, assets y que las dos versiones coincidan.

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${RAIZ}"

PY=".venv/bin/python"
RUFF=".venv/bin/ruff"

echo "== ruff =="
"${RUFF}" check custom_components tests

echo "== formato =="
"${RUFF}" format --check custom_components tests

echo "== tests =="
# PYTHONPATH suele venir heredado de otro intérprete y rompe las extensiones.
env -u PYTHONPATH "${PY}" -m pytest -q tests

echo "== SPDX =="
tools/hooks/spdx.sh

echo "== assets =="
env -u PYTHONPATH "${PY}" tools/check_assets.py

# El Marketplace lee manifest.json y el Supervisor lee config.yaml: si no
# coinciden, el release publica dos versiones distintas.
echo "== versiones =="
a="$(grep -o '"version": "[^"]*"' custom_components/safe_store/manifest.json | cut -d'"' -f4)"
b="$(grep -o '^version: "[^"]*"' secrets_unlocker/config.yaml | cut -d'"' -f2)"
[ "${a}" = "${b}" ] || {
	echo "versiones distintas: manifest ${a} · config ${b}" >&2
	exit 1
}
echo "version ${a} · manifest y config.yaml coinciden"
