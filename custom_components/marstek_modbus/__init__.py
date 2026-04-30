"""
Main integration setup for Marstek Venus Modbus component.

Handles setting up and unloading config entries, initializing
the data coordinator, and forwarding setup to sensor and select platforms.
"""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

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

# Sensor unique_id suffixes that no longer exist and must be removed from the
# entity registry on startup. Add entries here whenever a sensor key is renamed
# or removed so that stale entities are cleaned up automatically.
REMOVED_ENTITY_UNIQUE_ID_SUFFIXES = [
    # ac_frequency renamed to inverter_frequency (feat/inverter-ac-rename)
    "ac_frequency",
]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """
    General setup of the integration.

    This is called once when Home Assistant starts.
    It does not perform any configuration and always returns True.

    Args:
        hass: Home Assistant instance.
        config: Configuration dict.

    Returns:
        True always.
    """
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Set up a config entry.

    Initializes the coordinator for this entry and stores it in hass.data.
    Forwards setup to platforms (e.g., sensor, select) used by this integration.

    Args:
        hass: Home Assistant instance.
        entry: ConfigEntry to setup.

    Returns:
        True if setup successful, False otherwise.
    """
    try:
        # Migrate legacy device_version tokens in existing config entries to
        # the canonical SUPPORTED_VERSIONS strings. This handles older
        # installations that used tokens like 'v1/v2' or 'v3'.
        raw_version = (entry.data.get("device_version") or "").strip()
        if raw_version:
            normalized = raw_version.lower()
            # Consider anything not listed in SUPPORTED_VERSIONS as legacy/unsupported.
            allowed = {s.lower() for s in SUPPORTED_VERSIONS}
            if normalized not in allowed:
                _LOGGER.warning(
                    "Config entry %s uses unsupported device_version '%s'. Please remove and re-add the device with the correct device version. Supported versions: %s",
                    entry.entry_id,
                    raw_version,
                    ", ".join(SUPPORTED_VERSIONS),
                )
        # Create the coordinator for data management and attempt an initial
        # connection before forwarding platform setup so the client is ready.
        coordinator = MarstekCoordinator(hass, entry)
        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

        # Load register definitions off the event loop to avoid blocking
        try:
            await coordinator.async_load_registers(entry.data.get("device_version"))
        except Exception as err:
            _LOGGER.warning("Failed loading register definitions for entry %s: %s", entry.entry_id, err)

        # Establish the Modbus connection upfront so the first refresh does not
        # lazily reconnect on individual sensor reads, and failure is properly
        # tracked from the start.
        await coordinator.async_init()

        # Forward setup to all platforms defined in PLATFORMS
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        # Remove stale entities from previous versions
        ent_reg = er.async_get(hass)
        for suffix in REMOVED_ENTITY_UNIQUE_ID_SUFFIXES:
            unique_id = f"{entry.entry_id}_{suffix}"
            if entity_id := ent_reg.async_get_entity_id("sensor", DOMAIN, unique_id):
                _LOGGER.debug("Removing stale entity %s (unique_id: %s)", entity_id, unique_id)
                ent_reg.async_remove(entity_id)

        # Perform first refresh to ensure coordinator has up-to-date data
        await coordinator.async_config_entry_first_refresh()

        return True
    except Exception as err:
        _LOGGER.error("Error setting up entry %s: %s", entry.entry_id, err)
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Unload a config entry and its associated platforms.

    Args:
        hass: Home Assistant instance.
        entry: ConfigEntry to unload.

    Returns:
        True if unload successful, False otherwise.
    """
    try:
        # Unload all platforms for the entry
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

        if unload_ok:
            # Retrieve the coordinator and close it before removing
            coordinator = hass.data[DOMAIN][entry.entry_id]
            await coordinator.async_close()
            # Remove coordinator reference from hass data
            hass.data[DOMAIN].pop(entry.entry_id, None)

        return unload_ok
    except Exception as err:
        _LOGGER.error("Error unloading entry %s: %s", entry.entry_id, err)
        return False