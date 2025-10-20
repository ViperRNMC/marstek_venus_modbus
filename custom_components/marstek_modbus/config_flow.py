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

from .const import DOMAIN, DEFAULT_PORT, DEFAULT_SCAN_INTERVALS, SUPPORTED_VERSIONS

CONF_CONF_VERSION = "conf_version"
CONF_DEVICE_VERSION = "device_version"

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
            device_version = user_input.get(CONF_DEVICE_VERSION, SUPPORTED_VERSIONS[0])
            
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

                # Test the Modbus connection using the helper function
                errors["base"] = await async_test_modbus_connection(host, port)

                # If no errors, create the configuration entry
                if not errors["base"]:
                        title = translations.get("config.step.user.title", "Marstek Venus Modbus")
                        # Ensure device_version is saved in the config entry data
                        data = {
                            CONF_HOST: host,
                            CONF_PORT: port,
                            CONF_DEVICE_VERSION: device_version,
                        }
                        return self.async_create_entry(title=title, data=data)

        # Show the form for user input (host, port and device version) with any errors
        # Version options are taken from SUPPORTED_VERSIONS and presented as a select
        # Provide friendly labels as description placeholders in case
        # translations are not yet loaded in the dev environment.
        description_placeholders = {
            "device_version_choices": ", ".join(
                [f"{v}: {translations.get(f'config.step.user.data.device_version|{v}', v)}" for v in SUPPORTED_VERSIONS]
            )
        }

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                    vol.Required(CONF_DEVICE_VERSION, default=SUPPORTED_VERSIONS[0]): vol.In(SUPPORTED_VERSIONS),
                }
            ),
            errors=errors,
            description_placeholders=description_placeholders,
        )
    
    @staticmethod
    # @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return MarstekOptionsFlow(config_entry)


class MarstekOptionsFlow(config_entries.OptionsFlow):
    """Handle Marstek Venus Modbus options flow."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}

        # Get language and translations for config flow
        language = self.hass.config.language
        translations = await async_get_translations(
            self.hass,
            language,
            category='config',
            integrations=DOMAIN
        )

        config = self._config_entry

        # Defaults: use options, then data, then DEFAULT_SCAN_INTERVALS
        defaults = {
            key: config.options.get(key, config.data.get(key, DEFAULT_SCAN_INTERVALS[key]))
            for key in ("high", "medium", "low", "very_low")
        }

        # Calculate the lowest scan interval for description placeholder
        lowest = min((user_input or defaults).values())

        if user_input is not None:
            # Update coordinator scan intervals if exists
            coordinator = self.hass.data.get(DOMAIN, {}).get(config.entry_id)
            if coordinator:
                coordinator._update_scan_intervals(user_input)

            # Do not set a custom title; let HA handle with translations
            return self.async_create_entry(data=user_input)

        # Schema for the form
        schema = vol.Schema(
            {
                vol.Required("high", default=defaults["high"]): vol.All(vol.Coerce(int), vol.Clamp(min=1, max=3600)),
                vol.Required("medium", default=defaults["medium"]): vol.All(vol.Coerce(int), vol.Clamp(min=1, max=3600)),
                vol.Required("low", default=defaults["low"]): vol.All(vol.Coerce(int), vol.Clamp(min=1, max=3600)),
                vol.Required("very_low", default=defaults["very_low"]): vol.All(vol.Coerce(int), vol.Clamp(min=1, max=3600)),
            }
        )

        # Use translations for form title and description, with placeholders
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
            description_placeholders={"lowest": str(lowest)},
        )


async def async_test_modbus_connection(host: str, port: int):
    """
    Attempt to connect to the Modbus server at the given host and port.
    Returns a string error key for the config flow errors dict, or None if successful.
    """
    import logging
    _LOGGER = logging.getLogger(__name__)
    # Log connection attempt at debug level
    _LOGGER.debug("Attempting to connect to Modbus server at %s:%d", host, port)

    client = ModbusTcpClient(host=host, port=port, timeout=3)
    try:
        if not client.connect():
            raise ConnectionError("Unable to connect")
    except OSError as err:
        err_msg = str(err).lower()
        if "permission denied" in err_msg:
            return "permission_denied"
        elif "connection refused" in err_msg:
            return "connection_refused"
        elif "timed out" in err_msg:
            return "timed_out"
        else:
            _LOGGER.debug("Connection error during Modbus client connect: %s", err_msg)
            return "cannot_connect"
    except Exception as exc:
        _LOGGER.error("Unexpected error connecting to Modbus server: %s", exc)
        return "cannot_connect"
    finally:
        client.close()
    return None