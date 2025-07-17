"""
Main integration setup for Marstek Venus Modbus component.

Handles setting up and unloading config entries, initializing
the data coordinator, and forwarding setup to sensor platforms.
"""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import MarstekCoordinator

PLATFORMS = ["sensor"]
# Potential expansions: "switch", "number", "select", "button"


async def async_setup(hass: HomeAssistant, config):
    """
    General setup of the integration.

    Called once when Home Assistant starts.
    Does not perform any configuration and always returns True.
    """
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """
    Set up a config entry.

    Initializes the coordinator for this entry and stores it in hass.data.
    Also forwards the setup to platforms (e.g., sensor) used by this integration.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry being set up.

    Returns:
        bool: True if setup was successful.
    """
    coordinator = MarstekCoordinator(hass, entry)
    await coordinator.async_init()

    # Ensure there is a dict for this domain in hass.data
    hass.data.setdefault(DOMAIN, {})
    # Store the coordinator under this entry's ID
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Forward the entry to the platforms to initialize them
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """
    Unload a config entry and its associated platforms.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry being unloaded.

    Returns:
        bool: True if unload was successful.
    """
    # Unload the platforms (e.g., sensor) associated with this entry
    await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    # Remove the coordinator from hass.data
    hass.data[DOMAIN].pop(entry.entry_id)
    return True