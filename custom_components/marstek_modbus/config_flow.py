"""
Config flow for Marstek Venus Modbus integration.
"""

import socket
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers.translation import async_get_translations
from pymodbus.client import ModbusTcpClient
from .const import DOMAIN, DEFAULT_PORT

class MarstekConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """
    Handle a config flow for Marstek Venus Modbus integration.
    """
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """
        Handle the initial step where the user provides configuration.
        """
        errors = {}

        # Get the language from the context, default to English if not set
        language = self.context.get("language", "en")
        # Load translations for the config flow to provide localized error messages and titles
        translations = await async_get_translations(
            self.hass,
            language,
            category="config",
            integrations=DOMAIN
        )

        # If user input is provided, validate and process it
        if user_input is not None:
            host = user_input.get(CONF_HOST)
            try:
                # Validate the host by attempting to resolve its IP address
                socket.gethostbyname(host)
            except (socket.gaierror, TypeError):
                # If host is invalid, set an error message
                errors["base"] = "invalid_host" 
            else:
                # Check if the host is already configured to prevent duplicates
                for entry in self._async_current_entries():
                    if entry.data.get(CONF_HOST) == host:
                        return self.async_abort(reason="already_configured")

                # Retrieve the port from user input or use the default port
                port = user_input.get(CONF_PORT, DEFAULT_PORT)
                # Attempt to connect to the Modbus device using the provided host and port
                client = ModbusTcpClient(host=host, port=port)
                try:
                    if not client.connect():
                        raise ConnectionError("Unable to connect")
                except OSError as err:
                    err_msg = str(err).lower()
                    if "permission denied" in err_msg:
                        errors["base"] = "permission_denied""
                    elif "connection refused" in err_msg:
                        errors["base"] = "connection_refused"
                    elif "timed out" in err_msg:
                        errors["base"] = "timed_out"
                    else:
                        errors["base"] = "cannot_connect"
                    return self.async_show_form(
                        step_id="user",
                        data_schema=vol.Schema({
                            vol.Required(CONF_HOST): str,
                            vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                        }),
                        errors=errors
                    )
                finally:
                    client.close()

                # If no errors occurred, create the config entry
                if not errors:
                    title = translations.get("config.step.user.title", "Marstek Venus Modbus")
                    return self.async_create_entry(
                        title=title,
                        data=user_input
                    )

        # Show the form to the user to input host and port, including any errors
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
            }),
            errors=errors
        )