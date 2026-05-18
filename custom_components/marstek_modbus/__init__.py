"""
Main integration setup for Marstek Venus Modbus component.

Handles setting up and unloading config entries, initializing
the data coordinator, and forwarding setup to sensor and select platforms.
"""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import MarstekCoordinator
from .const import SUPPORTED_VERSIONS

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    "sensor",
    "switch",
    "select",
    "button",
    "number",
    "binary_sensor",
]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """General setup – called once when Home Assistant starts."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Set up a config entry.

    Order of operations:
    1. Load register YAML for the configured device version.
    2. Connect to the Modbus gateway (raises ConfigEntryNotReady on failure).
    3. Forward setup to all entity platforms so entities are created and
       added to HA (async_added_to_hass is complete for all of them).
    4. Query the entity registry for any user-enabled non-default entities
       and add them to the coordinator's polling groups dynamically.
    5. Run the first coordinator refresh so every entity has a value
       immediately (tick 1 polls all groups).
    """
    try:
        # Warn about unsupported device_version strings in existing entries
        raw_version = (entry.data.get("device_version") or "").strip()
        if raw_version:
            normalized = raw_version.lower()
            allowed = {s.lower() for s in SUPPORTED_VERSIONS}
            if normalized not in allowed:
                _LOGGER.warning(
                    "Config entry %s uses unsupported device_version '%s'. "
                    "Please remove and re-add the device. Supported: %s",
                    entry.entry_id, raw_version, ", ".join(SUPPORTED_VERSIONS),
                )

        coordinator = MarstekCoordinator(hass, entry)
        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

        # 1 – Load register definitions (blocking I/O runs in executor)
        try:
            await coordinator.async_load_registers(entry.data.get("device_version"))
        except Exception as err:
            _LOGGER.warning(
                "Failed loading register definitions for entry %s: %s",
                entry.entry_id, err,
            )

        # 2 – Connect to Modbus gateway.
        # ConfigEntryNotReady is intentionally NOT caught here – it must
        # propagate to HA so the built-in retry mechanism (exponential
        # backoff: 5 s → 10 s → 30 s → 60 s → …) kicks in automatically.
        # This handles temporary failures such as a disconnected LAN cable
        # or the device being in the middle of a reboot.
        await coordinator.async_init()

        # 3 – Create all entity platforms (async_added_to_hass runs here)
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        # 4 – Register user-enabled non-default entities for polling
        await coordinator.async_register_enabled_entities()

        # 5 – First refresh: tick 1 polls ALL groups so every entity has
        #     a value immediately without waiting for slow intervals.
        # ConfigEntryNotReady from here also propagates so HA retries.
        await coordinator.async_config_entry_first_refresh()

        return True
    except ConfigEntryNotReady:
        # Re-raise so HA schedules an automatic retry.
        # The platforms forwarded in step 3 are cleaned up by HA automatically.
        raise
    except Exception as err:
        _LOGGER.error("Error setting up entry %s: %s", entry.entry_id, err)
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and its associated platforms."""
    try:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

        if unload_ok:
            coordinator = hass.data[DOMAIN][entry.entry_id]
            await coordinator.async_close()
            hass.data[DOMAIN].pop(entry.entry_id, None)

        return unload_ok
    except Exception as err:
        _LOGGER.error("Error unloading entry %s: %s", entry.entry_id, err)
        return False
