# Config flow for Marstek Venus Modbus integration.
# This module handles the user configuration steps for setting up the integration in Home Assistant.

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.helpers.translation import async_get_translations
from homeassistant.helpers.selector import selector
from .const import DOMAIN, DEFAULT_PORT, SCAN_INTERVAL

class MarstekConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Marstek Venus Modbus integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step where the user provides configuration."""
        errors = {}

        translations = await async_get_translations(self.hass, self.language)
        localize = translations.async_gettext

        # If user_input is provided, create the config entry with the given data.
        if user_input is not None:
            # Create a new config entry with the title and user input data.
            return self.async_create_entry(title=localize("config.step.user.title"), data=user_input)

        # Show the form to the user to collect host, port, and scan interval information.
        # vol.Schema defines the expected fields and their types for the form.
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
            }),
            description_placeholders={},
            errors=errors
        )