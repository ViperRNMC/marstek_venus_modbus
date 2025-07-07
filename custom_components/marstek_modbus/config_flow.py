# Config flow for Marstek Venus Modbus integration.
# This module handles the user configuration steps for setting up the integration in Home Assistant.

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from .const import DOMAIN, DEFAULT_PORT

class MarstekConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Marstek Venus Modbus integration."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step where the user provides configuration."""
        errors = {}

        # If user_input is provided, create the config entry with the given data.
        if user_input is not None:
            # Create a new config entry with the title and user input data.
            return self.async_create_entry(title="Marstek Venus Modbus", data=user_input)

        # Show the form to the user to collect host and port information.
        # vol.Schema defines the expected fields and their types for the form.
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
            }),
            errors=errors
        )