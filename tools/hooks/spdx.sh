#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Exige la cabecera SPDX en los archivos de código y configuración propios.
set -u
falta=0
while IFS= read -r f; do
  grep -q "SPDX-License-Identifier" "$f" || { echo "sin SPDX: $f"; falta=1; }
done < <(find custom_components secrets_unlocker tests tools -type f \
           \( -name "*.py" -o -name "*.sh" -o -name "*.yaml" -o -name "*.yml" \) 2>/dev/null)
for f in Makefile .github/workflows/*.yml requirements_test.txt .gitignore .editorconfig; do
  [ -f "$f" ] || continue
  grep -q "SPDX-License-Identifier" "$f" || { echo "sin SPDX: $f"; falta=1; }
done
exit "$falta"
