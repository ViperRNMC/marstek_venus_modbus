"""Buttons for the Marstek Venus Modbus integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import MarstekConfigEntry
from .entity import MarstekEntity, MarstekEntityDescription, descriptions_for
from .venus import VenusDevice


@dataclass(frozen=True, kw_only=True)
class MarstekButtonEntityDescription(MarstekEntityDescription, ButtonEntityDescription):
    """Describe a Marstek button."""

    # The value written to the command register.
    command: int


BUTTONS: tuple[MarstekButtonEntityDescription, ...] = (
    MarstekButtonEntityDescription(
        key="reset_device",
        component="commands",
        entity_category=EntityCategory.DIAGNOSTIC,
        command=21930,
        icon="mdi:restart",
        entity_registry_enabled_default=False,
    ),
    MarstekButtonEntityDescription(
        key="factory_reset",
        component="commands",
        entity_category=EntityCategory.DIAGNOSTIC,
        command=21930,
        icon="mdi:factory",
        entity_registry_enabled_default=False,
    ),
)


def descriptions(device: VenusDevice) -> list[MarstekButtonEntityDescription]:
    """Return the buttons this device model has."""
    return descriptions_for(device, BUTTONS)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MarstekConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the buttons."""
    coordinator = entry.runtime_data
    async_add_entities(
        MarstekButton(coordinator, description)
        for description in descriptions(coordinator.device)
    )


class MarstekButton(MarstekEntity, ButtonEntity):
    """A button that writes a command."""

    entity_description: MarstekButtonEntityDescription

    async def async_press(self) -> None:
        """Write the command, then refresh."""
        description = self.entity_description
        await self.coordinator.async_write(
            description.component, description.key, description.command
        )
        await self.coordinator.async_request_refresh()
