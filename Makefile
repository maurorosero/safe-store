# SPDX-License-Identifier: MIT

PY ?= .venv/bin/python
RUFF ?= .venv/bin/ruff

.PHONY: check lint fmt test spdx assets version

check: lint fmt-check test spdx assets version

lint:
	$(RUFF) check custom_components tests

fmt-check:
	$(RUFF) format --check custom_components tests

fmt:
	$(RUFF) format custom_components tests

# PYTHONPATH suele venir heredado de otro intérprete y rompe las extensiones.
test:
	env -u PYTHONPATH $(PY) -m pytest -q tests

spdx:
	tools/hooks/spdx.sh

assets:
	env -u PYTHONPATH $(PY) tools/check_assets.py

# El Marketplace lee manifest.json y el Supervisor lee config.yaml: si no
# coinciden, el release publica dos versiones distintas.
version:
	@a=$$(grep -o '"version": "[^"]*"' custom_components/safe_store/manifest.json | cut -d'"' -f4); \
	b=$$(grep -o '^version: "[^"]*"' secrets_unlocker/config.yaml | cut -d'"' -f2); \
	[ "$$a" = "$$b" ] || { echo "versiones distintas: manifest $$a · config $$b"; exit 1; }; \
	echo "version $$a · manifest y config.yaml coinciden"
