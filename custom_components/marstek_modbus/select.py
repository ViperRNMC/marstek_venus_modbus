"""Selects for the Marstek Venus Modbus integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import MarstekConfigEntry, MarstekCoordinator
from .entity import MarstekEntityDescription, MarstekWritableEntity, descriptions_for
from .venus import VenusDevice


@dataclass(frozen=True, kw_only=True)
class MarstekSelectEntityDescription(MarstekEntityDescription, SelectEntityDescription):
    """Describe a Marstek select."""

    # The register value of each option, in display order.
    options_map: dict[str, int]


_WEEKDAYS = {
    "sunday": 64,
    "monday": 1,
    "tuesday": 2,
    "wednesday": 4,
    "thursday": 8,
    "friday": 16,
    "saturday": 32,
}

SELECTS: tuple[MarstekSelectEntityDescription, ...] = (
    MarstekSelectEntityDescription(
        key="user_work_mode",
        component="control",
        options_map={"manual": 0, "anti_feed": 1, "trade_mode": 2},
    ),
    MarstekSelectEntityDescription(
        key="force_mode",
        component="control",
        options_map={"standby": 0, "charge": 1, "discharge": 2},
        entity_registry_enabled_default=False,
    ),
    MarstekSelectEntityDescription(
        key="grid_standard",
        component="control",
        options_map={
            "Auto": 0,
            "EN50549": 1,
            "Netherlands": 2,
            "Germany": 3,
            "Austria": 4,
            "United Kingdom": 5,
            "Spain": 6,
            "Poland": 7,
            "Italy": 8,
            "China": 9,
        },
    ),
    *(
        MarstekSelectEntityDescription(
            key=f"schedule_{index}_days",
            component=f"schedule_{index}",
            field="days",
            entity_category=EntityCategory.CONFIG,
            options_map=_WEEKDAYS,
            entity_registry_enabled_default=False,
        )
        for index in range(1, 7)
    ),
)


def descriptions(device: VenusDevice) -> list[MarstekSelectEntityDescription]:
    """Return the selects this device model has."""
    return descriptions_for(device, SELECTS)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MarstekConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the selects."""
    coordinator = entry.runtime_data
    async_add_entities(
        MarstekSelect(coordinator, description)
        for description in descriptions(coordinator.device)
    )


class MarstekSelect(MarstekWritableEntity, SelectEntity):
    """A register that holds one of a set of values."""

    entity_description: MarstekSelectEntityDescription

    def __init__(
        self,
        coordinator: MarstekCoordinator,
        description: MarstekSelectEntityDescription,
    ) -> None:
        super().__init__(coordinator, description)
        self._attr_options = list(description.options_map)
        # English entity ids whatever the language of the friendly name.
        self._attr_suggested_object_id = description.key

    @property
    def current_option(self) -> str | None:
        """Return the option the register holds."""
        value = self.field_value
        for option, option_value in self.entity_description.options_map.items():
            if option_value == value:
                return option
        return None

    async def async_select_option(self, option: str) -> None:
        """Write the option's value."""
        await self.async_write(self.entity_description.options_map[option])
