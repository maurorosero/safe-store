#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Todo commit del rango tiene que llevar Signed-off-by.
set -eu
base="${1:-origin/main}"
falta=0
while read -r sha; do
  if ! git log -1 --format=%B "$sha" | grep -q "^Signed-off-by: "; then
    echo "sin Signed-off-by: $sha $(git log -1 --format=%s "$sha")"
    falta=1
  fi
done < <(git rev-list "$base"..HEAD)
exit "$falta"
