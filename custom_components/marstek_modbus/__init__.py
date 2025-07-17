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

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    "sensor",
    "switch",
    "select",
    "button",
    "number",
]  # List of supported platforms for this integration


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
        # Create and initialize the coordinator for data management
        coordinator = MarstekCoordinator(hass, entry)
        await coordinator.async_init()

        # Store the coordinator in hass data for later reference
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][entry.entry_id] = coordinator

        # Forward setup to all platforms defined in PLATFORMS
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

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
            # Remove coordinator reference from hass data
            hass.data[DOMAIN].pop(entry.entry_id, None)

        return unload_ok
    except Exception as err:
        _LOGGER.error("Error unloading entry %s: %s", entry.entry_id, err)
        return False