"""Base entity for the Marstek Venus Modbus integration."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from time import monotonic
from typing import Any

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import MarstekCoordinator
from .venus import VenusDevice

# How long a written value is shown before reads count again. The device can
# report the old value for a moment after it accepts a write.
WRITE_SETTLE_SECONDS = 3.0


@dataclass(frozen=True, kw_only=True)
class MarstekEntityDescription(EntityDescription):
    """Describe an entity backed by fields of the device."""

    # The sub-system that holds the field, as named on the device object.
    component: str = ""
    # The field on that sub-system. Empty means the field is named like the key.
    field: str = ""
    # (component, field) pairs the entity reads. Empty means the one field above.
    requires: tuple[tuple[str, str], ...] = ()


def required_fields(
    description: MarstekEntityDescription,
) -> tuple[tuple[str, str], ...]:
    """Return the (component, field) pairs an entity reads."""
    return description.requires or (
        (description.component, description.field or description.key),
    )


def descriptions_for[D: MarstekEntityDescription](
    device: VenusDevice,
    descriptions: Iterable[D],
    overrides: Mapping[type[VenusDevice], Mapping[str, Mapping[str, Any]]] = {},
) -> list[D]:
    """Return the descriptions this device model has fields for, with its overrides."""
    model_overrides = overrides.get(type(device), {})
    result = []
    for description in descriptions:
        if changes := model_overrides.get(description.key):
            description = replace(description, **changes)
        if all(
            (component := getattr(device, component_name, None)) is not None
            and field in type(component).declared_fields
            for component_name, field in required_fields(description)
        ):
            result.append(description)
    return result


class MarstekEntity(CoordinatorEntity[MarstekCoordinator]):
    """An entity that reads fields of the device."""

    _attr_has_entity_name = True
    entity_description: MarstekEntityDescription

    def __init__(
        self, coordinator: MarstekCoordinator, description: MarstekEntityDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_translation_key = description.translation_key or description.key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def available(self) -> bool:
        """Unavailable while a sub-system this entity reads fails to answer."""
        return super().available and not any(
            component in self.coordinator.failed
            for component, _ in required_fields(self.entity_description)
        )

    @property
    def device(self) -> VenusDevice:
        """The device this entity belongs to."""
        return self.coordinator.device

    @property
    def field_value(self) -> Any:
        """The decoded value of the entity's field."""
        description = self.entity_description
        component = getattr(self.device, description.component)
        return getattr(component, description.field or description.key)


class MarstekWritableEntity(MarstekEntity):
    """An entity that writes its field, and shows the write until it settles."""

    _written_value: Any = None
    _written_at: float | None = None

    @property
    def field_value(self) -> Any:
        """The written value while it settles, then the decoded value."""
        if self._written_at is not None:
            return self._written_value
        return super().field_value

    async def async_write(self, value: Any) -> None:
        """Write a value to the entity's field."""
        description = self.entity_description
        await self.coordinator.async_write(
            description.component, description.field or description.key, value
        )
        self._written_value = value
        self._written_at = monotonic()
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        if (
            self._written_at is not None
            and monotonic() - self._written_at >= WRITE_SETTLE_SECONDS
        ):
            self._written_at = None
        super()._handle_coordinator_update()
