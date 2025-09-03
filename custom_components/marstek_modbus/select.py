"""
This module defines a SelectEntity for setting and reading the user work mode
and force mode of a Marstek Venus battery via Modbus within Home Assistant.
"""

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import MarstekCoordinator
from .const import DOMAIN, MANUFACTURER, MODEL, SELECT_DEFINITIONS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """
    Set up select sensor entities when the config entry is loaded.

    This function retrieves the coordinator from hass.data,
    creates select entities based on SELECT_DEFINITIONS,
    and registers them with Home Assistant.

    Args:
        hass: Home Assistant instance.
        entry: Configuration entry.
        async_add_entities: Callback to add entities.
    """
    # Retrieve the coordinator instance from hass data and add entities
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [MarstekSelect(coordinator, definition) for definition in SELECT_DEFINITIONS]
    async_add_entities(entities)


class MarstekSelect(CoordinatorEntity, SelectEntity):
    """
    Representation of a Modbus select entity for Marstek Venus.

    Select state is read and write asynchronously via
    the coordinator communicating with the Modbus device.
    """

    def __init__(self, coordinator: MarstekCoordinator, definition: dict[str, Any]) -> None:
        """
        Initialize the select entity.

        Args:
            coordinator: The MarstekCoordinator instance managing data updates.
            definition: A dictionary defining the select entity's properties.
        """
        super().__init__(coordinator)

        # Store the key and definition
        self._key = definition["key"]
        self.definition = definition   

        # Assign the entity type to the coordinator mapping
        self.coordinator._entity_types[self._key] = self.entity_type

        # Set entity attributes from definition
        self._attr_name = definition["name"]
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{self._key}"
        self._attr_has_entity_name = True

        # Internal state variables
        self._state = None
        self._register = definition["register"]

        # set category if defined in the definition
        if "category" in self.definition:
            self._attr_entity_category = EntityCategory(self.definition.get("category"))

        # Set icon if defined in the button definition
        if "icon" in self.definition:
            self._attr_icon = self.definition.get("icon")

        # Optional: disable entity by default if specified in the definition
        if definition.get("enabled_by_default") is False:
            self._attr_entity_registry_enabled_default = False

    @property
    def entity_type(self) -> str:
        """
        Return the type of this entity for logging purposes.
        This allows the coordinator to show more descriptive messages.
        """
        return "select"

    @property
    def available(self) -> bool:
        """
        Return True if the coordinator has successfully fetched data.
        Used by Home Assistant to determine entity availability.
        """
        return self.coordinator.last_update_success

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

        The value is obtained from the coordinator's shared data dictionary.
        Maps the numeric register value back to the option string.
        """
        data = self.coordinator.data
        if data is None:
            return None

        value = data.get(self._key)
        if value is None:
            return None

        options_map = self.definition.get("options", {})
        # Reverse the mapping: {int_value: option_name}
        reversed_map = {int(v): k for k, v in options_map.items()}

        return reversed_map.get(int(value))

    async def async_select_option(self, option: str) -> None:
        """
        Change the selected option by writing to the device register.

        Args:
            option: The option string to select.
        """
        options_map = self.definition.get("options", {})
        if option not in options_map:
            _LOGGER.warning("Invalid option '%s' for %s", option, self._attr_name)
            return

        value = options_map[option]

        # Write the new value to the register via the coordinator
        success = await self.coordinator.async_write_value(
            register=self._register,
            value=value,
            data_type=self.definition.get("data_type", "uint16"),
            key=self._key,
            scale=self.definition.get("scale", 1),
            unit=self.definition.get("unit"),
            entity_type=self.entity_type,
        )

        if success:
            import asyncio

            # Wait briefly to allow the device to process the change
            await asyncio.sleep(0.5)
            # Request coordinator to refresh data
            await self.coordinator.async_request_refresh()

    @property
    def device_info(self) -> dict:
        """
        Return device information for Home Assistant's device registry.
        Includes identifiers, name, manufacturer, model, and entry type.
        """
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": self.coordinator.config_entry.title,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "entry_type": "service",
        }

    # def _update_state_from_coordinator(self) -> None:
    #     """
    #     Update the internal state from the coordinator's data.

    #     This method reads the register value, maps it to the option key,
    #     and updates the internal _state attribute.
    #     """
    #     data = self.coordinator.data
    #     if data is None:
    #         self._state = None
    #         return

    #     data_type = self.definition.get("data_type", "uint16")
    #     register = self.definition["register"]
    #     count = self.definition.get("count", 1)

    #     # The coordinator data structure should contain the register values
    #     # Here we assume coordinator.data is a dict with keys as register addresses
    #     # or keys, adjust if necessary.
    #     # For safety, we attempt to read by key first, then register.
    #     value = None
    #     if self._key in data:
    #         value = data[self._key]
    #     elif register in data:
    #         value = data[register]

    #     if value is None:
    #         self._state = None
    #         return

    #     options_map = self.definition.get("options", {})
    #     # Reverse the options map to map values back to keys (int values)
    #     reversed_map = {int(v): k for k, v in options_map.items()}

    #     try:
    #         int_value = int(value)
    #         self._state = reversed_map.get(int_value)
    #     except (ValueError, TypeError):
    #         self._state = None
    #         _LOGGER.warning(
    #             "Unable to convert value '%s' to int for select %s",
    #             value,
    #             self._attr_name,
    #         )

    #     if self._state is None:
    #         _LOGGER.warning(
    #             "Unknown register value %s for select %s (expected one of %s)",
    #             value,
    #             self._attr_name,
    #             list(reversed_map.keys()),
    #         )

    # @property
    # def extra_state_attributes(self) -> dict[str, Any]:
    #     """
    #     Return additional state attributes if needed.

    #     Returns:
    #         Dictionary of extra state attributes.
    #     """
    #     return {}

    # @property
    # def should_poll(self) -> bool:
    #     """
    #     Disable polling as updates are pushed via the coordinator.

    #     Returns:
    #         False, polling is not needed.
    #     """
    #     return False

    # @property
    # def native_value(self) -> str | None:
    #     """
    #     Return the current option value for the select entity.

    #     Returns:
    #         The current option string or None if unknown.
    #     """
    #     return self._state

    # @CoordinatorEntity._handle_coordinator_update
    # def _handle_coordinator_update(self) -> None:
    #     """
    #     Handle updated data from the coordinator.

    #     This method is called when the coordinator has new data.
    #     It updates the internal state and writes the state to Home Assistant.
    #     """
    #     self._update_state_from_coordinator()
    #     self.async_write_ha_state()
