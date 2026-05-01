"""
Marstek Venus Modbus sensor entities.

All sensors now derive their values from the shared coordinator data.
No separate async_update needed; coordinator handles polling.
"""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import MarstekCoordinator
from .const import DOMAIN, MANUFACTURER, MODEL

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up all Marstek sensors from definitions."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Create sensor entities from coordinator-provided definitions
    entities = []
    sensor_groups = (
        (MarstekSensor, coordinator.SENSOR_DEFINITIONS),
        (MarstekEfficiencySensor, coordinator.EFFICIENCY_SENSOR_DEFINITIONS),
        (MarstekStoredEnergySensor, coordinator.STORED_ENERGY_SENSOR_DEFINITIONS),
        (MarstekBatteryCycleSensor, coordinator.CYCLE_SENSOR_DEFINITIONS),
    )
    for entity_cls, definitions in sensor_groups:
        entities.extend(entity_cls(coordinator, definition) for definition in definitions)

    # Add all entities to Home Assistant
    async_add_entities(entities)


class MarstekSensor(CoordinatorEntity, SensorEntity):
    """Generic Modbus sensor reading from the coordinator."""

    def __init__(self, coordinator: MarstekCoordinator, definition: dict):
        super().__init__(coordinator)

        # Store the key and definition
        self._key = definition["key"]
        self.definition = definition     

        # Assign the entity type to the coordinator mapping
        self.coordinator._entity_types[self._key] = self.entity_type

        # Set entity attributes from definition
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{self.definition['key']}"
        self._attr_has_entity_name = True
        self._attr_translation_key = definition["key"]

        # Set basic attributes from definition
        self._attr_native_unit_of_measurement = definition.get("unit")
        self._attr_device_class = definition.get("device_class")
        self._attr_state_class = definition.get("state_class")

        # Optional: entity category and icon
        if "category" in definition:
            self._attr_entity_category = EntityCategory(definition["category"])
        if "icon" in definition:
            self._attr_icon = definition["icon"]
        if definition.get("enabled_by_default") is False:
            self._attr_entity_registry_enabled_default = False

        # Optional states mapping for int → label conversion
        self.states = definition.get("states")

    @property
    def entity_type(self) -> str:
        """
        Return the type of this entity for logging purposes.
        This allows the coordinator to show more descriptive messages.
        """
        return "sensor"

    @property
    def available(self) -> bool:
        """Return True if coordinator has valid data for this sensor."""
        # Consider the sensor available when coordinator has provided a value
        # for this key. This avoids sensors remaining 'unknown' when the
        # coordinator had transient update failures but still supplies data.
        data = getattr(self.coordinator, "data", None)
        return isinstance(data, dict) and self._key in data

    @property
    def native_value(self):
        """Return the value from coordinator data with scaling and states applied."""
        if self._key not in self.coordinator.data:
            return None
        value = self.coordinator.data[self._key]

        # Special handling for schedule data type: the sensor state should
        # represent whether the schedule is enabled (boolean). The raw
        # register list is exposed in attributes under `raw` and all decoding
        # / interpretation is performed in `extra_state_attributes`.
        if self.definition.get("data_type") == "schedule":
            data = getattr(self.coordinator, "data", {}) or {}
            # Prefer decoded attrs if coordinator provided them, otherwise
            # attempt to decode from the raw register list.
            attrs = data.get(f"{self._key}_attrs") or {}
            enabled = None

            if isinstance(attrs, dict) and "enabled" in attrs:
                try:
                    enabled = bool(int(attrs.get("enabled") or 0))
                except Exception:
                    enabled = bool(attrs.get("enabled"))
            else:
                # Try to decode from raw registers stored at data[self._key]
                raw = data.get(self._key)
                if isinstance(raw, (list, tuple)) and len(raw) >= 5:
                    try:
                        enabled = bool(int(raw[4]))
                    except Exception:
                        enabled = bool(raw[4])

            # If we couldn't determine enabled state, return None (unknown)
            if enabled is None:
                return None

            return enabled

        if isinstance(value, (int, float)):
            # Special-case: EMS version is encoded as an integer where
            # values with 4 digits encode a decimal in the last digit
            # (e.g. 1573 -> 157.3), while 3-digit values are whole numbers
            # (e.g. 158 -> 158). Handle that before applying generic scale.
            if self._key == "ems_version":
                try:
                    iv = int(value)
                except Exception:
                    iv = None

                if iv is not None:
                    if iv >= 1000:
                        # interpret last digit as decimal (tenths)
                        value = round(iv / 10.0, 1)
                    else:
                        value = int(iv)
                    # return early after mapping; skip generic scaling
                    if isinstance(value, float) and value.is_integer():
                        value = int(value)
                    # apply states mapping below
                else:
                    # fall back to generic handling if conversion fails
                    pass
            else:
                # Apply scaling/offset and round according to precision.
                scale = self.definition.get("scale", 1)
                offset = self.definition.get("offset", 0)
                precision = int(self.definition.get("precision", 0) or 0)

                value = float(value) * scale + offset
                value = round(value, precision)

                # If the rounded value has no fractional component, return int
                # so Home Assistant does not render an unnecessary trailing .0.
                if isinstance(value, float) and value.is_integer():
                    value = int(value)

        if self.states and value in self.states:
            return self.states[value]

        return value

    @property
    def suggested_display_precision(self) -> int | None:
        """Suggest display precision based on definition, but only if not a string or mapped state."""
        if self.states:
            return None
        return self.definition.get("precision")

    @property
    def suggested_display_unit(self) -> str | None:
        """Suggest display unit based on definition, but only if not a string or mapped state."""
        if self.states:
            return None
        return self.definition.get("unit")

    @property
    def device_info(self) -> dict:
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": self.coordinator.config_entry.title,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "entry_type": "service",
        }

    @property
    def extra_state_attributes(self) -> dict:
        """Return attributes for packed schedule sensors from coordinator data."""
        data = self.coordinator.data or {}
        attrs = data.get(f"{self._key}_attrs") or {}
        # For schedule types, enrich attributes with human-readable fields.
        # If `_attrs` is not present but the coordinator stored the raw
        # 5-register list in `data[key]`, decode that here so we don't
        # duplicate decoding in the coordinator.
        if self.definition.get("data_type") == "schedule":
            if not isinstance(attrs, dict) or not attrs:
                raw = data.get(self._key)
                if isinstance(raw, (list, tuple)) and len(raw) >= 5:
                    try:
                        attrs = {
                            "days": int(raw[0]),
                            "start": int(raw[1]),
                            "end": int(raw[2]),
                            "mode": int(raw[3]) - 0x10000 if int(raw[3]) >= 0x8000 else int(raw[3]),
                            "enabled": int(raw[4]),
                        }
                    except Exception:
                        attrs = {}

            if isinstance(attrs, dict) and attrs:
                def _fmt_time(t):
                    try:
                        t = int(t)
                        # Heuristic: device encodes times as HHMM (e.g. 200 -> 02:00,
                        # 610 -> 06:10) when the low two digits are < 60 and the
                        # value is within 0..2359. Otherwise treat value as
                        # minutes-since-midnight.
                        if 0 <= t <= 2359 and (t % 100) < 60:
                            hh = t // 100
                            mm = t % 100
                        else:
                            hh = t // 60
                            mm = t % 60
                        return f"{hh:02d}:{mm:02d}"
                    except Exception:
                        return t

                # Debug logging for raw schedule data from coordinator
                _LOGGER.warning(
                    "Raw schedule data for %s: value=%s attrs=%s",
                    self._key,
                    data.get(self._key),
                    attrs,
                )

                days = attrs.get("days")
                try:
                    dmask = int(days) if days is not None else 0
                except Exception:
                    dmask = 0
                # Bits are encoded with Monday at bit 0 (device ordering), but
                # display should start with Sunday. Compute set using Monday-first
                # mapping, then reorder to Sunday-first for presentation.
                weekday_names_mon = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                selected_mon = [weekday_names_mon[i] for i in range(7) if (dmask >> i) & 1]
                display_order = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
                selected = [d for d in display_order if d in selected_mon]

                # Build a minimal enriched dict — do not duplicate raw fields.
                enriched = {}
                enriched["days_list"] = selected
                enriched["start_time"] = _fmt_time(attrs.get("start"))
                enriched["end_time"] = _fmt_time(attrs.get("end"))

                # Interpret mode into a human-friendly type and a separate watt attribute.
                # NOTE: device uses signed mode where -1 == self consumption and
                # signed values represent magnitude. Empirically the device
                # uses negative -> charge and positive -> discharge (inverse
                # of earlier assumption), so map accordingly.
                mode_raw = attrs.get("mode")
                mode = None
                power = None
                try:
                    if mode_raw is None:
                        mode = None
                    else:
                        m = int(mode_raw)
                        if m == -1:
                            mode = "self consumption"
                        elif m < 0:
                            mode = "charge"
                            power = abs(m)
                        else:
                            mode = "discharge"
                            power = m
                except Exception:
                    mode = None
                    power = None

                enriched["mode"] = mode
                enriched["power"] = power
                enriched["enabled"] = bool(attrs.get("enabled"))
                return enriched

        return attrs or {}


class MarstekCalculatedSensor(CoordinatorEntity, SensorEntity):
    """
    Base class for calculated sensors that depend on multiple coordinator keys.

    Handles registration of dependency keys and provides update handling.
    """

    def __init__(self, coordinator: MarstekCoordinator, definition: dict):
        """Initialize the calculated sensor and register dependencies."""
        super().__init__(coordinator)

        # Store the key and definition
        self._key = definition["key"]
        self.definition = definition

        # Assign the entity type to the coordinator mapping
        self.coordinator._entity_types[self._key] = self.entity_type

        # Set entity attributes from definition
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{self.definition['key']}"
        self._attr_has_entity_name = True
        self._attr_translation_key = definition["key"]

        # Set basic attributes from definition
        self._attr_native_unit_of_measurement = definition.get("unit")
        self._attr_device_class = definition.get("device_class")
        self._attr_state_class = definition.get("state_class")

        # Optional: entity category and icon
        if "category" in definition:
            self._attr_entity_category = EntityCategory(definition["category"])
        if "icon" in definition:
            self._attr_icon = definition["icon"]
        if definition.get("enabled_by_default") is False:
            self._attr_entity_registry_enabled_default = False

        # Register dependency keys in coordinator and set scales
        for alias, dep_key in self.get_dependency_keys().items():
            if not dep_key:
                continue

            self.coordinator._entity_types[dep_key] = "sensor"

            # Combine all definitions for iteration using coordinator-provided lists
            if not hasattr(self, "_all_definitions"):
                self._all_definitions = (
                    self.coordinator.SENSOR_DEFINITIONS + self.coordinator.BINARY_SENSOR_DEFINITIONS
                )
            all_definitions = self._all_definitions

            # Get scale from all definitions or fallback to current sensor dependency_defs
            scale = next((d.get("scale", 1) for d in all_definitions if d.get("key") == dep_key), None)
            scale = scale or self.definition.get("dependency_defs", {}).get(alias, 1)

            self.coordinator._scales[dep_key] = scale

    def get_dependency_keys(self):
        """Return the keys this sensor depends on."""
        return self.definition.get("dependency_keys", {})

    @property
    def entity_type(self) -> str:
        """
        Return the type of this entity for logging purposes.
        This allows the coordinator to show more descriptive messages.
        """
        return "sensor"

    @property
    def device_info(self) -> dict:
        """Return device info so sensor is linked to the integration/device."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": self.coordinator.config_entry.title,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "entry_type": "service",
        }

    def _handle_coordinator_update(self) -> None:
        """
        Handle coordinator update by recalculating the sensor value.

        Calls the subclass's calculate_value method and updates state.
        """
        if not getattr(self.coordinator, "last_update_success", False):
            self._attr_native_value = None
            self.async_write_ha_state()
            return

        data = self.coordinator.data if isinstance(self.coordinator.data, dict) else {}

        self._calculate(data)
        self.async_write_ha_state()

    def _calculate(self, data: dict) -> None:
        """
        Centralized method to check dependencies, log missing values,
        calculate value, and update native_value attribute.
        """
        dependency_keys = self.get_dependency_keys()
        dep_values = {}
        missing = []

        # dependency_keys is a dict alias -> actual key
        for alias, actual_key in dependency_keys.items():
            val = data.get(actual_key)
            scale = self.coordinator._scales.get(actual_key, 1)
            if val is None:
                missing.append(alias)
            else:
                dep_values[alias] = float(val) * scale

        if missing:
            _LOGGER.warning(
                "%s missing required value(s): %s. Current data: %s. Cannot calculate value.",
                self._key, ", ".join(missing), {k: data.get(v) for k, v in dependency_keys.items()},
            )
            self._attr_native_value = None
            return

        try:
            value = self.calculate_value(dep_values)
            _LOGGER.debug(
                "Calculated value for %s: %s (input values: %s)",
                self._key,
                value,
                dep_values
            )
            self._attr_native_value = value
        except Exception as ex:
            _LOGGER.warning(
                "Error calculating value for sensor %s: %s", self._key, ex
            )
            self._attr_native_value = None

    def calculate_value(self, dep_values: dict):
        """
        Calculate the sensor value from scaled dependency values.

        Must be implemented by subclasses.
        """
        raise NotImplementedError


class MarstekStoredEnergySensor(MarstekCalculatedSensor):
    """
    Sensor calculating stored battery energy (kWh).

    Uses SOC (%) and battery total energy (kWh) from coordinator data.
    """
    def calculate_value(self, dep_values: dict):
        """Calculate stored energy based on SOC and capacity dynamically."""
        soc = dep_values.get("soc")
        capacity = dep_values.get("capacity")
        stored_energy = round((soc / 100) * capacity, 2)
        self._attr_native_value = stored_energy
        return stored_energy


class MarstekEfficiencySensor(MarstekCalculatedSensor):
    """
    Calculate either Round Trip Efficiency (RTE) or Actual Conversion Efficiency.

    Mode is determined by 'mode' in the sensor definition:
    - "round_trip": uses charge / discharge energy
    - "conversion": uses battery_power / ac_power
    """
    def calculate_value(self, dep_values: dict):
        mode = self.definition.get("mode", "round_trip")
        if mode == "round_trip":
            charge = dep_values.get("charge")
            discharge = dep_values.get("discharge")
            if charge in (None, 0):
                return None
            efficiency = (discharge / charge) * 100

        elif mode == "conversion":
            battery_power = dep_values.get("battery_power")
            ac_power = dep_values.get("ac_power")
            if battery_power is None or ac_power is None:
                return None
            if battery_power > 0:
                if ac_power == 0:
                    return None
                efficiency = abs(battery_power) / abs(ac_power) * 100
            else:
                if battery_power == 0:
                    return None
                efficiency = abs(ac_power) / abs(battery_power) * 100

        else:
            _LOGGER.warning("%s unknown efficiency mode '%s'", self._key, mode)
            return None

        efficiency_rounded = round(min(efficiency, 100.0), 1)
        self._attr_native_value = efficiency_rounded
        return efficiency_rounded


class MarstekBatteryCycleSensor(MarstekCalculatedSensor):
    """Calculate estimated battery cycles from discharge energy and capacity."""

    def calculate_value(self, dep_values: dict):
        discharge = dep_values.get("discharge")
        capacity = dep_values.get("capacity")
        if discharge is None or capacity in (None, 0):
            return None

        cycles = round(discharge / capacity, 2)
        self._attr_native_value = cycles
        return cycles