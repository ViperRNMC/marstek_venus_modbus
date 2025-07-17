"""
Config flow for Marstek Venus Modbus integration.
"""

import socket
import voluptuous as vol
import logging
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers.translation import async_get_translations
from pymodbus.client import ModbusTcpClient

from .const import DOMAIN, DEFAULT_PORT

_LOGGER = logging.getLogger(__name__)


class MarstekConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """
    Handle the configuration flow for the Marstek Venus Modbus integration.
    """

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """
        Handle the initial step of the config flow where the user inputs host and port.

        Validates user input and attempts connection to the Modbus device.
        """
        errors = {}

        # Determine user language, fallback to English
        language = self.context.get("language", "en")

        # Load translations for localized messages
        translations = await async_get_translations(
            self.hass,
            language,
            category="config",
            integrations=DOMAIN,
        )

        if user_input is not None:
            host = user_input.get(CONF_HOST)
            port = user_input.get(CONF_PORT, DEFAULT_PORT)

            # Validate port range
            if not (1 <= port <= 65535):
                errors["base"] = "invalid_port"
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema(
                        {
                            vol.Required(CONF_HOST): str,
                            vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                        }
                    ),
                    errors=errors,
                )

            # Validate the host by resolving it to an IP address
            try:
                socket.gethostbyname(host)
            except (socket.gaierror, TypeError):
                errors["base"] = "invalid_host"
            else:
                # Prevent duplicate entries for the same host
                for entry in self._async_current_entries():
                    if entry.data.get(CONF_HOST) == host:
                        return self.async_abort(reason="already_configured")

                # Log connection attempt at debug level
                _LOGGER.debug("Attempting to connect to Modbus server at %s:%d", host, port)

                # Create client with timeout (if supported by pymodbus version)
                client = ModbusTcpClient(host=host, port=port, timeout=3)

                try:
                    if not client.connect():
                        raise ConnectionError("Unable to connect")
                except OSError as err:
                    err_msg = str(err).lower()
                    if "permission denied" in err_msg:
                        errors["base"] = "permission_denied"
                    elif "connection refused" in err_msg:
                        errors["base"] = "connection_refused"
                    elif "timed out" in err_msg:
                        errors["base"] = "timed_out"
                    else:
                        errors["base"] = "cannot_connect"
                    _LOGGER.debug("Connection error during Modbus client connect: %s", err_msg)
                    return self.async_show_form(
                        step_id="user",
                        data_schema=vol.Schema(
                            {
                                vol.Required(CONF_HOST): str,
                                vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                            }
                        ),
                        errors=errors,
                    )
                except Exception as exc:
                    _LOGGER.error("Unexpected error connecting to Modbus server: %s", exc)
                    errors["base"] = "cannot_connect"
                    return self.async_show_form(
                        step_id="user",
                        data_schema=vol.Schema(
                            {
                                vol.Required(CONF_HOST): str,
                                vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                            }
                        ),
                        errors=errors,
                    )
                finally:
                    client.close()

                # If no errors, create the configuration entry
                if not errors:
                    title = translations.get("config.step.user.title", "Marstek Venus Modbus")
                    return self.async_create_entry(title=title, data=user_input)

        # Show the form for user input (host and port) with any errors
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                }
            ),
            errors=errors,
        )