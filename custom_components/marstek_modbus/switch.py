"""Switches for the Marstek Venus Modbus integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import MarstekConfigEntry
from .entity import MarstekEntityDescription, MarstekWritableEntity, descriptions_for
from .venus import VenusDevice


@dataclass(frozen=True, kw_only=True)
class MarstekSwitchEntityDescription(MarstekEntityDescription, SwitchEntityDescription):
    """Describe a Marstek switch."""

    command_on: int
    command_off: int


SWITCHES: tuple[MarstekSwitchEntityDescription, ...] = (
    MarstekSwitchEntityDescription(
        key="backup_function",
        component="control",
        command_on=0,
        command_off=1,
    ),
    MarstekSwitchEntityDescription(
        key="rs485_control_mode",
        component="control",
        command_on=21930,
        command_off=21947,
        entity_registry_enabled_default=False,
    ),
    *(
        MarstekSwitchEntityDescription(
            key=f"schedule_{index}_enabled",
            component=f"schedule_{index}",
            field="enabled",
            entity_category=EntityCategory.CONFIG,
            command_on=1,
            command_off=0,
            icon="mdi:power",
            entity_registry_enabled_default=False,
        )
        for index in range(1, 7)
    ),
)


def descriptions(device: VenusDevice) -> list[MarstekSwitchEntityDescription]:
    """Return the switches this device model has."""
    return descriptions_for(device, SWITCHES)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MarstekConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the switches."""
    coordinator = entry.runtime_data
    async_add_entities(
        MarstekSwitch(coordinator, description)
        for description in descriptions(coordinator.device)
    )


class MarstekSwitch(MarstekWritableEntity, SwitchEntity):
    """A register that holds one of two commands."""

    entity_description: MarstekSwitchEntityDescription

    @property
    def is_on(self) -> bool | None:
        """Return the state."""
        value = self.field_value
        return None if value is None else value == self.entity_description.command_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Write the on command."""
        await self.async_write(self.entity_description.command_on)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Write the off command."""
        await self.async_write(self.entity_description.command_off)
