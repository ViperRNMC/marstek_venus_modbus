"""Binary sensors for the Marstek Venus Modbus integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import MarstekConfigEntry
from .entity import MarstekEntity, MarstekEntityDescription, descriptions_for
from .venus import VenusDevice


@dataclass(frozen=True, kw_only=True)
class MarstekBinarySensorEntityDescription(
    MarstekEntityDescription, BinarySensorEntityDescription
):
    """Describe a Marstek binary sensor."""


BINARY_SENSORS: tuple[MarstekBinarySensorEntityDescription, ...] = (
    MarstekBinarySensorEntityDescription(
        key="wifi_status",
        component="network",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        icon="mdi:check-network-outline",
        entity_registry_enabled_default=False,
    ),
    MarstekBinarySensorEntityDescription(
        key="cloud_status",
        component="network",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        icon="mdi:cloud-outline",
        entity_registry_enabled_default=False,
    ),
    MarstekBinarySensorEntityDescription(
        key="discharge_limit_mode",
        component="control",
        icon="mdi:battery-arrow-down-outline",
        entity_registry_enabled_default=False,
    ),
)

CONNECTION = MarstekBinarySensorEntityDescription(
    key="modbus_connection",
    entity_category=EntityCategory.DIAGNOSTIC,
    device_class=BinarySensorDeviceClass.CONNECTIVITY,
)


def descriptions(device: VenusDevice) -> list[MarstekBinarySensorEntityDescription]:
    """Return the binary sensors this device model has."""
    return descriptions_for(device, BINARY_SENSORS)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MarstekConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            *(
                MarstekBinarySensor(coordinator, description)
                for description in descriptions(coordinator.device)
            ),
            MarstekConnectionBinarySensor(coordinator, CONNECTION),
        ]
    )


class MarstekBinarySensor(MarstekEntity, BinarySensorEntity):
    """A status register: any value but 0 is on."""

    @property
    def is_on(self) -> bool | None:
        """Return the state."""
        value = self.field_value
        return None if value is None else bool(value)


class MarstekConnectionBinarySensor(MarstekEntity, BinarySensorEntity):
    """Whether the last poll reached the battery."""

    @property
    def available(self) -> bool:
        """Always available, so a lost connection shows as off."""
        return True

    @property
    def is_on(self) -> bool:
        """Return the state."""
        return self.coordinator.last_update_success
