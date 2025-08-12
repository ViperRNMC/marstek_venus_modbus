"""
Module for creating number entities for Marstek Venus battery devices.
The number entities retrieve data by reading Modbus registers.
"""

import logging

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import NUMBER_DEFINITIONS, DOMAIN, MANUFACTURER, MODEL
from .coordinator import MarstekCoordinator

_LOGGER = logging.getLogger(__name__)


def get_entity_type(entity) -> str:
    """Determine entity type based on its class inheritance."""
    for base in entity.__class__.__mro__:
        if issubclass(base, Entity) and base.__name__.endswith("Entity"):
            return base.__name__.replace("Entity", "").lower()
    return "entity"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """
    Set up number entities when the config entry is loaded.

    Retrieves the coordinator instance,
    creates number entities from definitions,
    and registers them with Home Assistant.
    """
    # Retrieve coordinator for this config entry
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Refresh data to ensure coordinator data is available
    await coordinator.async_config_entry_first_refresh()

    # Create number entities for all definitions
    entities = [MarstekNumber(coordinator, definition) for definition in NUMBER_DEFINITIONS]

    # Register the created entities
    async_add_entities(entities)


class MarstekNumber(NumberEntity):
    """Representation of a Modbus number entity for Marstek Venus."""

    def __init__(self, coordinator: MarstekCoordinator, definition: dict):
        """
        Initialize the number entity.

        Args:
            coordinator: Data update coordinator instance.
            definition: Dictionary with number configuration.
        """
        self.coordinator = coordinator
        self.definition = definition

        # Set entity attributes from definition
        self._attr_name = self.definition["name"]
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{self.definition['key']}"
        self._attr_has_entity_name = True

        self._attr_native_unit_of_measurement = definition.get("unit")
        self._attr_native_min_value = definition.get("min")
        self._attr_native_max_value = definition.get("max")
        self._attr_native_step = definition.get("step")
        self._register = definition["register"]
        self._key = definition["key"]

        # Set entity category if defined
        if "category" in self.definition:
            try:
                self._attr_entity_category = EntityCategory(self.definition.get("category"))
            except ValueError:
                _LOGGER.warning(
                    "Unknown entity category %s for number %s",
                    self.definition.get("category"),
                    self._attr_name,
                )

        # Set icon if defined
        if "icon" in self.definition:
            self._attr_icon = self.definition.get("icon")

        # Disable entity by default if specified
        if definition.get("enabled_by_default") is False:
            self._attr_entity_registry_enabled_default = False

        # Initialize internal state variable
        self._state = None

    async def async_added_to_hass(self):
        """Called when entity is added to Home Assistant."""
        await self.async_update()
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return True if coordinator data update succeeded and state is set."""
        return self.coordinator.last_update_success and self._state is not None

    async def async_update(self):
        """
        Asynchronously update the sensor state.

        Reads register values via the coordinator's client and processes
        them based on the number's data type and configuration.
        """
        data_type = self.definition.get("data_type", "uint16")
        register = self._register
        count = self.definition.get("count", 1)

        try:
            # Request the register value asynchronously
            value = await self.coordinator.client.async_read_register(
                register=register,
                data_type=data_type,
                count=count,
                sensor_key=self._key,
            )
        except Exception as e:
            _LOGGER.error("Error reading register 0x%X: %s", register, e)
            self._state = None
            return

        # Process the received value
        if value is not None:
            if isinstance(value, (int, float)):
                # Apply scale and offset if specified, round to precision
                scaled = value * self.definition.get("scale", 1)
                scaled += self.definition.get("offset", 0)
                precision = self.definition.get("precision", 0)
                self._state = round(scaled, precision)
            else:
                # Fallback: just store value directly
                self._state = value

            # Update the coordinator data cache
            await self.coordinator.async_update_value(
                self._key,
                self._state,
                register=register,
                scale=self.definition.get("scale"),
                unit=self.definition.get("unit"),
                entity_type=get_entity_type(self),
            )
        else:
            self._state = None

    @property
    def native_value(self):
        """Return the current state value for Home Assistant."""
        if self.coordinator.data and isinstance(self.coordinator.data, dict):
            return self.coordinator.data.get(self._key)
        return None

    @property
    def device_info(self) -> dict:
        """
        Return device information for Home Assistant device registry.

        Groups entities under the same device in the UI.
        """
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": self.coordinator.config_entry.title,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "entry_type": "service",
        }

    async def async_set_native_value(self, value: float) -> None:
        """
        Write the value to the Modbus register.

        Converts scaled value back to raw before writing.
        """
        register = self._register
        data_type = self.definition.get("data_type", "uint16")
        scale = self.definition.get("scale", 1)
        offset = self.definition.get("offset", 0)

        # Convert scaled value back to raw register value
        raw_value = int((value - offset) / scale)

        success = await self.coordinator.async_write_value(
            register=register,
            value=raw_value,
            data_type=data_type,
            key=self._key,
            scale=scale,
            unit=self.definition.get("unit"),
            entity_type=get_entity_type(self),
        )

        if success:
            self._state = value
            self.async_write_ha_state()