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

from .const import DOMAIN, DEFAULT_PORT, DEFAULT_SCAN_INTERVALS, SUPPORTED_VERSIONS, DEFAULT_UNIT_ID

CONF_CONF_VERSION = "conf_version"
CONF_DEVICE_VERSION = "device_version"
CONF_UNIT_ID = "unit_id"

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
            unit_id = user_input.get(CONF_UNIT_ID, DEFAULT_UNIT_ID)
            
            # Compact validation for port and unit_id
            if not (1 <= port <= 65535):
                errors["base"] = "invalid_port"
            elif not (1 <= unit_id <= 255):
                errors["base"] = "invalid_unit_id"

            if errors:
                # Re-show the form while preserving user input so fields are not cleared
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema(
                        {
                            vol.Required(CONF_HOST, default=host): str,
                            vol.Optional(CONF_PORT, default=port): int,
                            vol.Optional(CONF_UNIT_ID, default=unit_id): vol.Coerce(int),
                            vol.Required(CONF_DEVICE_VERSION, default=device_version): vol.In(SUPPORTED_VERSIONS),
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
                # Prevent duplicate entries for the same host and unit_id combination
                for entry in self._async_current_entries():
                    if (entry.data.get(CONF_HOST) == host and 
                        entry.data.get(CONF_UNIT_ID) == unit_id):
                        return self.async_abort(reason="already_configured")

                # Test the Modbus connection including unit_id validation
                errors["base"] = await async_test_modbus_connection(host, port, unit_id)

                # If no errors, create the configuration entry
                if not errors["base"]:
                        title = translations.get("config.step.user.title", "Marstek Venus Modbus")
                        # Ensure device_version and unit_id are saved in the config entry data
                        data = {
                            CONF_HOST: host,
                            CONF_PORT: port,
                            CONF_DEVICE_VERSION: device_version,
                            CONF_UNIT_ID: unit_id,
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

        # Preserve any previously entered values when re-displaying the form
        defaults = {
            CONF_HOST: (user_input.get(CONF_HOST) if user_input else None) or "",
            CONF_PORT: (user_input.get(CONF_PORT) if user_input else None) or DEFAULT_PORT,
            CONF_UNIT_ID: (user_input.get(CONF_UNIT_ID) if user_input else None) or DEFAULT_UNIT_ID,
            CONF_DEVICE_VERSION: (user_input.get(CONF_DEVICE_VERSION) if user_input else None) or SUPPORTED_VERSIONS[0],
        }

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=defaults[CONF_HOST]): str,
                    vol.Optional(CONF_PORT, default=defaults[CONF_PORT]): int,
                    vol.Required(CONF_UNIT_ID, default=defaults[CONF_UNIT_ID]): vol.Coerce(int),
                    vol.Required(CONF_DEVICE_VERSION, default=defaults[CONF_DEVICE_VERSION]): vol.In(SUPPORTED_VERSIONS),
                }
            ),
            errors=errors,
            description_placeholders=description_placeholders,
        )
    
    async def async_step_reauth(self, data=None):
        """
        Re-authentication step triggered when a config entry is missing required
        information (like device_version). This shows a popup asking the user to
        select the correct device version.
        """
        errors = {}

        # Load translations for the current language to present friendly labels
        language = self.context.get("language", self.hass.config.language)
        translations = await async_get_translations(
            self.hass, language, category="config", integrations=DOMAIN
        )

        if data is not None:
            # Persist the chosen device version into the existing config entry
            entry = self._async_current_entries()[0] if self._async_current_entries() else None
            if entry:
                try:
                    new_data = dict(entry.data)
                    new_data[CONF_DEVICE_VERSION] = data.get(CONF_DEVICE_VERSION)
                    await self.hass.config_entries.async_update_entry(entry, data=new_data)
                    return self.async_create_entry(title=entry.title or DOMAIN, data={})
                except Exception as exc:
                    _LOGGER.error("Failed to update config entry during reauth: %s", exc)
                    errors["base"] = "unknown"

        description_placeholders = {
            "device_version_choices": ", ".join(
                [f"{v}: {translations.get(f'config.step.user.data.device_version|{v}', v)}" for v in SUPPORTED_VERSIONS]
            )
        }

        return self.async_show_form(
            step_id="reauth",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_VERSION, default=SUPPORTED_VERSIONS[0]): vol.In(SUPPORTED_VERSIONS)
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
        
        # Default for unit_id
        default_unit_id = config.options.get(CONF_UNIT_ID, config.data.get(CONF_UNIT_ID, DEFAULT_UNIT_ID))

        # Calculate the lowest scan interval for description placeholder
        lowest = min((user_input or defaults).values())

        if user_input is not None:
            # Update coordinator scan intervals if exists
            coordinator = self.hass.data.get(DOMAIN, {}).get(config.entry_id)
            if coordinator:
                coordinator._update_scan_intervals(user_input)
                
                # Update unit_id if it has changed
                new_unit_id = user_input.get(CONF_UNIT_ID, default_unit_id)
                if new_unit_id != coordinator.client.unit_id:
                    coordinator.client.unit_id = new_unit_id
                    _LOGGER.info("Updated Modbus Unit ID to %d", new_unit_id)

            # Do not set a custom title; let HA handle with translations
            return self.async_create_entry(data=user_input)

        # Schema for the form
        schema = vol.Schema(
            {
                vol.Required("high", default=defaults["high"]): vol.All(vol.Coerce(int), vol.Clamp(min=1, max=3600)),
                vol.Required("medium", default=defaults["medium"]): vol.All(vol.Coerce(int), vol.Clamp(min=1, max=3600)),
                vol.Required("low", default=defaults["low"]): vol.All(vol.Coerce(int), vol.Clamp(min=1, max=3600)),
                vol.Required("very_low", default=defaults["very_low"]): vol.All(vol.Coerce(int), vol.Clamp(min=1, max=3600)),
                vol.Required(CONF_UNIT_ID, default=default_unit_id): vol.Coerce(int),
            }
        )

        # Use translations for form title and description, with placeholders
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
            description_placeholders={"lowest": str(lowest)},
        )


async def async_test_modbus_connection(host: str, port: int, unit_id: int = 1):
    """
    Attempt to connect to the Modbus server at the given host, port and unit_id.
    Tests both TCP connection and actual Modbus communication with the specific unit_id.
    Returns a string error key for the config flow errors dict, or None if successful.
    """
    import asyncio
    import logging
    _LOGGER = logging.getLogger(__name__)
    # Log connection attempt at debug level
    _LOGGER.debug("Attempting to connect to Modbus server at %s:%d with unit_id %d", host, port, unit_id)

    client = ModbusTcpClient(host=host, port=port, timeout=3)
    try:
        # First test TCP connection
        if not client.connect():
            raise ConnectionError("Unable to connect")
        
        # Small delay to ensure connection is stable
        await asyncio.sleep(0.1)
            
        # Test actual Modbus communication with the specified unit_id
        try:
            # Try to read a known register - use register 32104 (Battery SOC) which should exist
            # We run the sync operation in an executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: client.read_holding_registers(address=32104, count=1, slave=unit_id)
            )
            
            # Check if we got any response (even an error response indicates unit_id communication)
            if result is None:
                return "unit_id_no_response"
            elif hasattr(result, 'isError') and result.isError():
                # Some Modbus errors are OK - they indicate the unit_id responds but register doesn't exist
                error_code = getattr(result, 'exception_code', None)
                if error_code in [1, 2, 3, 4]:  # Common Modbus exception codes for valid unit but invalid register
                    _LOGGER.debug("Unit ID %d responds (got expected Modbus exception %s)", unit_id, error_code)
                    return None  # This is actually success - unit_id responds
                else:
                    _LOGGER.debug("Unit ID %d error: %s", unit_id, result)
                    return "unit_id_no_response"
            else:
                # Got valid data - unit_id is definitely correct
                _LOGGER.debug("Unit ID %d test successful", unit_id)
                return None
                
        except asyncio.TimeoutError:
            _LOGGER.debug("Timeout testing unit_id %d - may be incorrect", unit_id)
            return "unit_id_no_response"
        except Exception as e:
            _LOGGER.debug("Error testing unit_id %d: %s", unit_id, e)
            # Don't fail on unit_id test - just warn and continue
            _LOGGER.warning("Could not verify unit_id %d, but continuing anyway: %s", unit_id, e)
            return None  # Allow connection even if unit_id test fails
            
    except OSError as err:
        err_msg = str(err).lower()
        if "permission denied" in err_msg:
            return "permission_denied"
        elif "connection refused" in err_msg:
            return "connection_refused"
        elif "timed out" in err_msg or "timeout" in err_msg:
            return "timed_out"
        else:
            _LOGGER.debug("Connection error during Modbus client connect: %s", err_msg)
            return "cannot_connect"
    except Exception as exc:
        _LOGGER.error("Unexpected error connecting to Modbus server: %s", exc)
        return "cannot_connect"
    finally:
        try:
            client.close()
        except Exception:
            pass  # Ignore errors during cleanup
    return None