"""Numbers for the Marstek Venus Modbus integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfPower, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import MarstekConfigEntry
from .entity import MarstekEntityDescription, MarstekWritableEntity, descriptions_for
from .venus import VenusA, VenusDevice


@dataclass(frozen=True, kw_only=True)
class MarstekNumberEntityDescription(MarstekEntityDescription, NumberEntityDescription):
    """Describe a Marstek number."""


NUMBERS: tuple[MarstekNumberEntityDescription, ...] = (
    MarstekNumberEntityDescription(
        key="set_charge_power",
        component="control",
        native_unit_of_measurement=UnitOfPower.WATT,
        native_min_value=0,
        native_max_value=2500,
        native_step=50,
        icon="mdi:battery-arrow-up-outline",
        entity_registry_enabled_default=False,
    ),
    MarstekNumberEntityDescription(
        key="set_discharge_power",
        component="control",
        native_unit_of_measurement=UnitOfPower.WATT,
        native_min_value=0,
        native_max_value=2500,
        native_step=50,
        icon="mdi:battery-arrow-down-outline",
        entity_registry_enabled_default=False,
    ),
    MarstekNumberEntityDescription(
        key="max_charge_power",
        component="control",
        native_unit_of_measurement=UnitOfPower.WATT,
        native_min_value=0,
        native_max_value=2500,
        native_step=50,
        icon="mdi:battery-arrow-up-outline",
        entity_registry_enabled_default=False,
    ),
    MarstekNumberEntityDescription(
        key="max_discharge_power",
        component="control",
        native_unit_of_measurement=UnitOfPower.WATT,
        native_min_value=0,
        native_max_value=2500,
        native_step=50,
        icon="mdi:battery-arrow-down-outline",
        entity_registry_enabled_default=False,
    ),
    MarstekNumberEntityDescription(
        key="charging_cutoff_capacity",
        component="control",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=80,
        native_max_value=100,
        native_step=1,
        icon="mdi:battery-arrow-up-outline",
        entity_registry_enabled_default=False,
    ),
    MarstekNumberEntityDescription(
        key="discharging_cutoff_capacity",
        component="control",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=12,
        native_max_value=30,
        native_step=1,
        icon="mdi:battery-arrow-down-outline",
        entity_registry_enabled_default=False,
    ),
    MarstekNumberEntityDescription(
        key="charge_to_soc",
        component="control",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=10,
        native_max_value=100,
        native_step=1,
        icon="mdi:battery-sync-outline",
        entity_registry_enabled_default=False,
    ),
    *(
        MarstekNumberEntityDescription(
            key=f"schedule_{index}_start",
            component=f"schedule_{index}",
            field="start",
            entity_category=EntityCategory.CONFIG,
            native_unit_of_measurement=UnitOfTime.MINUTES,
            native_min_value=0,
            native_max_value=2358,
            native_step=1,
            icon="mdi:clock-start",
            entity_registry_enabled_default=False,
        )
        for index in range(1, 7)
    ),
    *(
        MarstekNumberEntityDescription(
            key=f"schedule_{index}_end",
            component=f"schedule_{index}",
            field="end",
            entity_category=EntityCategory.CONFIG,
            native_unit_of_measurement=UnitOfTime.MINUTES,
            native_min_value=1,
            native_max_value=2359,
            native_step=1,
            icon="mdi:clock-end",
            entity_registry_enabled_default=False,
        )
        for index in range(1, 7)
    ),
    *(
        MarstekNumberEntityDescription(
            key=f"schedule_{index}_mode",
            component=f"schedule_{index}",
            field="mode",
            entity_category=EntityCategory.CONFIG,
            native_unit_of_measurement=UnitOfPower.WATT,
            native_min_value=-2500,
            native_max_value=2500,
            native_step=1,
            icon="mdi:cog",
            entity_registry_enabled_default=False,
        )
        for index in range(1, 7)
    ),
)

# The Venus A has a 1500 W inverter.
_VENUS_A_POWER = {"native_max_value": 1500}
_VENUS_A_SCHEDULE_POWER = {"native_min_value": -1500, "native_max_value": 1500}

OVERRIDES: dict[type[VenusDevice], dict[str, dict[str, Any]]] = {
    VenusA: {
        "set_charge_power": _VENUS_A_POWER,
        "set_discharge_power": _VENUS_A_POWER,
        "max_charge_power": _VENUS_A_POWER,
        "max_discharge_power": _VENUS_A_POWER,
        **{f"schedule_{index}_mode": _VENUS_A_SCHEDULE_POWER for index in range(1, 7)},
    },
}


def descriptions(device: VenusDevice) -> list[MarstekNumberEntityDescription]:
    """Return the numbers this device model has."""
    return descriptions_for(device, NUMBERS, OVERRIDES)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MarstekConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the numbers."""
    coordinator = entry.runtime_data
    async_add_entities(
        MarstekNumber(coordinator, description)
        for description in descriptions(coordinator.device)
    )


class MarstekNumber(MarstekWritableEntity, NumberEntity):
    """A writable setting."""

    entity_description: MarstekNumberEntityDescription

    @property
    def native_value(self) -> float | None:
        """Return the value."""
        return self.field_value

    async def async_set_native_value(self, value: float) -> None:
        """Write the value."""
        await self.async_write(value)
