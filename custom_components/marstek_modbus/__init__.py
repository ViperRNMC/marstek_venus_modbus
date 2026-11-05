"""The Marstek Venus Modbus integration."""

from __future__ import annotations

from collections import defaultdict

from homeassistant.components.modbus import async_get_unit
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import entity_registry as er
from modbus_connection import ModbusTcpParams

from . import binary_sensor, button, number, select, sensor, switch
from .const import DEFAULT_UNIT_ID, DOMAIN, MODELS
from .coordinator import MarstekConfigEntry, MarstekCoordinator
from .entity import required_fields
from .venus import VenusDevice

PLATFORMS = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.BINARY_SENSOR,
]

_PLATFORM_DESCRIPTIONS = {
    Platform.BINARY_SENSOR: binary_sensor.descriptions,
    Platform.BUTTON: button.descriptions,
    Platform.NUMBER: number.descriptions,
    Platform.SELECT: select.descriptions,
    Platform.SENSOR: sensor.descriptions,
    Platform.SWITCH: switch.descriptions,
}


async def async_setup_entry(hass: HomeAssistant, entry: MarstekConfigEntry) -> bool:
    """Set up a Marstek Venus battery from a config entry."""
    unit = async_get_unit(
        hass,
        entry,
        ModbusTcpParams(host=entry.data["host"], port=entry.data["port"]),
        entry.data.get("unit_id", DEFAULT_UNIT_ID),
    )
    device = MODELS[model_name(entry.data.get("device_version"))](unit)
    if (spacing_ms := entry.data.get("message_wait_milliseconds")) is not None:
        unit.set_message_spacing(spacing_ms / 1000)

    polled = _async_restrict_to_enabled_entities(hass, entry, device)
    coordinator = MarstekCoordinator(
        hass,
        entry,
        device,
        fast=[name for name in device.FAST if name in polled],
        slow=[name for name in device.SLOW if name in polled],
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MarstekConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


def model_name(device_version: str | None) -> str:
    """Return the model for an entry's device version.

    Older entries name E v1/v2 and E v3 "v1/v2" and "v3". Entries without a
    version predate E v3 and are E v1/v2.

    Raises ``ConfigEntryError`` for a version the integration does not know.
    """
    version = (device_version or "").strip().lower() or "e v1/v2"
    version = {"v1/v2": "e v1/v2", "v3": "e v3"}.get(version, version)
    for name in MODELS:
        if version == name.lower():
            return name
    raise ConfigEntryError(
        f"Unsupported device version {device_version!r}. Remove and re-add the"
        f" device with one of: {', '.join(MODELS)}"
    )


def _async_restrict_to_enabled_entities(
    hass: HomeAssistant, entry: MarstekConfigEntry, device: VenusDevice
) -> set[str]:
    """Narrow each sub-system to the fields enabled entities read.

    A disabled entity's registers are not read. Enabling an entity reloads the
    entry, which reads them from then on. Returns the sub-systems left with
    fields to read.
    """
    registry = er.async_get(hass)
    needed: defaultdict[str, set[str]] = defaultdict(set)
    for platform, descriptions in _PLATFORM_DESCRIPTIONS.items():
        for description in descriptions(device):
            entity_id = registry.async_get_entity_id(
                platform, DOMAIN, f"{entry.entry_id}_{description.key}"
            )
            if entity_id is None:
                enabled = description.entity_registry_enabled_default
            else:
                enabled = not registry.entities[entity_id].disabled
            if enabled:
                for component, field in required_fields(description):
                    needed[component].add(field)
    for name in (*device.FAST, *device.SLOW):
        if (component := getattr(device, name)) is not None and name in needed:
            component.restrict_fields(needed[name])
    return set(needed)
