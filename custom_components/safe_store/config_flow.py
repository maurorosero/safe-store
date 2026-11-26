# SPDX-License-Identifier: GPL-3.0-or-later
"""Config flow: solo confirma la activación del shim."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN


class SafeStoreConfigFlow(ConfigFlow, domain=DOMAIN):
    """Alta única: la integración no tiene parámetros."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Crea la entrada y deja que setup_entry arme el shim."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        return self.async_create_entry(title="Safe Store", data={})
