"""
This module defines a SelectEntity for setting and reading the user work mode
and force mode of a Marstek Venus battery via Modbus within Home Assistant.
"""

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import MarstekCoordinator
from .const import DOMAIN, MANUFACTURER, MODEL, SELECT_DEFINITIONS

_LOGGER = logging.getLogger(__name__)


def get_entity_type(entity: Entity) -> str:
    """
    Determine the entity type from the class inheritance hierarchy.

    Args:
        entity: The entity instance to check.

    Returns:
        A lowercase string representing the entity type, derived from the class name.
    """
    for base in entity.__class__.__mro__:
        if issubclass(base, Entity) and base.__name__.endswith("Entity"):
            return base.__name__.replace("Entity", "").lower()
    return "entity"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """
    Set up select entities when the config entry is loaded.

    This function retrieves the coordinator from hass.data,
    creates select entities based on the SELECT_DEFINITIONS,
    and registers them with Home Assistant.

    Args:
        hass: The HomeAssistant instance.
        entry: The configuration entry.
        async_add_entities: Function to add entities to Home Assistant.
    """
    # Get the coordinator instance from hass.data
    coordinator: MarstekCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Await the first data refresh so coordinator.data is populated before use
    await coordinator.async_config_entry_first_refresh()

    entities = []

    # Create select entities defined in SELECT_DEFINITIONS
    for definition in SELECT_DEFINITIONS:
        entities.append(MarstekSelect(coordinator, definition))

    # Register all created select entities with Home Assistant
    async_add_entities(entities)


class MarstekSelect(SelectEntity):
    """
    Representation of a Modbus select entity for Marstek Venus.

    This entity allows selecting and reading options corresponding to
    specific registers via the Modbus protocol.
    """

    def __init__(self, coordinator: MarstekCoordinator, definition: dict[str, Any]) -> None:
        """
        Initialize the select entity.

        Args:
            coordinator: The MarstekCoordinator instance managing data updates.
            definition: A dictionary defining the select entity's properties.
        """
        self.coordinator = coordinator
        self.definition = definition

        # Set entity attributes from definition
        self._attr_name = f"{definition['name']}"
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{definition['key']}"
        self._attr_has_entity_name = True

        # Internal state and configuration
        self._state: str | None = None
        self._key: str = definition["key"]
        self._register: int = definition["register"]

        # Set icon if defined in the button definition
        if "icon" in self.definition:
            self._attr_icon = self.definition.get("icon")

        # Optional: disable entity by default if specified in the definition
        if definition.get("enabled_by_default") is False:
            self._attr_entity_registry_enabled_default = False

    async def async_added_to_hass(self) -> None:
        """
        Called when entity is added to Home Assistant.

        Triggers an initial update and writes the state.
        """
        await self.async_update()
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """
        Return True if coordinator data update was successful and state is known.

        Returns:
            bool: Availability status.
        """
        return self.coordinator.last_update_success and (self._state is not None)

    @property
    def options(self) -> list[str]:
        """
        Return a list of available options for selection.

        Returns:
            List of option strings.
        """
        return list(self.definition.get("options", {}).keys())

    @property
    def current_option(self) -> str | None:
        """
        Return the currently selected option.

        Returns:
            The current option string or None if unknown.
        """
        return self._state

    async def async_update(self) -> None:
        """
        Fetch the latest state from the coordinator's data.

        Reads the register value asynchronously and updates the internal state.
        """
        data_type = self.definition.get("data_type", "uint16")
        register = self.definition["register"]
        count = self.definition.get("count", 1)

        try:
            # Request the register value asynchronously
            value = await self.coordinator.client.async_read_register(
                register=register,
                data_type=data_type,
                count=count,
                sensor_key=self.definition.get("key", self.definition.get("name", "unknown")),
            )
        except Exception as e:
            _LOGGER.error("Error reading register 0x%X: %s", register, e)
            return

        if value is not None:
            options_map = self.definition.get("options", {})
            # Reverse the options map to map values back to keys
            reversed_map = {int(v): k for k, v in options_map.items()}
            try:
                int_value = int(value)
                self._state = reversed_map.get(int_value)
            except (ValueError, TypeError):
                self._state = None
                _LOGGER.warning(
                    "Unable to convert value '%s' to int for select %s",
                    value,
                    self._attr_name,
                )

            if self._state is None:
                _LOGGER.warning(
                    "Unknown register value %s for select %s (expected one of %s)",
                    value,
                    self._attr_name,
                    list(reversed_map.keys()),
                )
        else:
            self._state = None

        # Update the coordinator with the new value
        await self.coordinator.async_update_value(
            self.definition["key"],
            self._state,
            register=self.definition.get("register"),
            scale=self.definition.get("scale"),
            unit=self.definition.get("unit"),
            entity_type=get_entity_type(self),
        )

    async def async_select_option(self, option: str) -> None:
        """
        Change the selected option.

        Args:
            option: The option string to select.
        """
        options_map = self.definition.get("options", {})
        if option not in options_map:
            _LOGGER.warning("Invalid option '%s' for %s", option, self._attr_name)
            return

        value = options_map[option]

        # Write the new value to the register
        success = await self.coordinator.async_write_value(
            register=self._register,
            value=value,
            data_type=self.definition.get("data_type", "uint16"),
            key=self._key,
            scale=self.definition.get("scale", 1),
            unit=self.definition.get("unit"),
            entity_type=get_entity_type(self),
        )

        if success:
            import asyncio

            # Wait briefly to allow the device to process the change
            await asyncio.sleep(0.5)
            # Refresh the state after writing
            await self.async_update()

    @property
    def device_info(self) -> dict[str, Any]:
        """
        Return device info for device registry grouping.

        Returns:
            Dictionary containing device information.
        """
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": self.coordinator.config_entry.title,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "entry_type": "service",
        }
