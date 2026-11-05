"""Diagnostics for the Marstek Venus Modbus integration."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from modbus_connection import ModbusError

from .coordinator import MarstekConfigEntry

# Registers that identify the owner's battery: the serial number and the
# Bluetooth MAC address, where each model keeps them.
_PERSONAL_REGISTERS = (
    *range(31200, 31210),
    *range(30304, 30310),
    *range(30402, 30408),
)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: MarstekConfigEntry
) -> dict[str, Any]:
    """Return the raw register map and the state of the last poll."""
    coordinator = entry.runtime_data
    # A sub-system that failed its last read would fail this one too.
    names = [name for name in coordinator.polled if name not in coordinator.failed]
    try:
        registers: Any = await coordinator.device.async_read_raw(names)
    except ModbusError as err:
        registers = f"Error reading registers: {err}"
    else:
        for address in _PERSONAL_REGISTERS:
            registers.get("holding", {}).pop(address, None)
    return {
        "device_version": entry.data.get("device_version"),
        "last_update_success": coordinator.last_update_success,
        "failed": sorted(coordinator.failed),
        "registers": registers,
    }
