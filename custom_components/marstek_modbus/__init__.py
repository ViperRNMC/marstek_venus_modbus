"""
Main integration setup for Marstek Venus Modbus component.

Handles setting up and unloading config entries, initializing
the data coordinator, and forwarding setup to sensor and select platforms.
"""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

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
            legacy_map = {
                "v1/v2": next((s for s in SUPPORTED_VERSIONS if s.lower().startswith("e v1")), "E v1/v2"),
                "v3": next((s for s in SUPPORTED_VERSIONS if s.lower().startswith("e v3")), "E v3"),
            }
            # Also accept plain 'd' or 'D' and map to the canonical 'D'
            if normalized in legacy_map:
                new_version = legacy_map[normalized]
                if new_version != raw_version:
                    _LOGGER.info(
                        "Updating config entry %s device_version '%s' -> '%s'",
                        entry.entry_id,
                        raw_version,
                        new_version,
                    )
                    new_data = dict(entry.data)
                    new_data["device_version"] = new_version
                    hass.config_entries.async_update_entry(entry, data=new_data)
        # Create and initialize the coordinator for data management
        coordinator = MarstekCoordinator(hass, entry)
        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

        # Forward setup to all platforms defined in PLATFORMS
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

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