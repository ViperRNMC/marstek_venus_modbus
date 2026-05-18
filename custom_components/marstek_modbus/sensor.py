"""
Marstek Venus Modbus sensor entities.

All sensors now derive their values from the shared coordinator data.
No separate async_update needed; coordinator handles polling.

SCALING NOTE: The coordinator applies scale via extract_typed_value() before
storing values in coordinator.data. Sensor entities must NOT apply scale again.
The definition's "scale" and "precision" fields are only used for display hints,
not for re-scaling already-scaled coordinator data.
"""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
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

    entities = []
    sensor_groups = (
        (MarstekSensor, coordinator.SENSOR_DEFINITIONS),
        (MarstekEfficiencySensor, coordinator.EFFICIENCY_SENSOR_DEFINITIONS),
        (MarstekStoredEnergySensor, coordinator.STORED_ENERGY_SENSOR_DEFINITIONS),
        (MarstekBatteryCycleSensor, coordinator.CYCLE_SENSOR_DEFINITIONS),
    )
    for entity_cls, definitions in sensor_groups:
        entities.extend(entity_cls(coordinator, definition) for definition in definitions)

    async_add_entities(entities)


class MarstekSensor(CoordinatorEntity, SensorEntity):
    """Generic Modbus sensor reading from the coordinator."""

    def __init__(self, coordinator: MarstekCoordinator, definition: dict):
        super().__init__(coordinator)

        self._key = definition["key"]
        self.definition = definition
        self.coordinator._entity_types[self._key] = self.entity_type

        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{self.definition['key']}"
        self._attr_has_entity_name = True
        self._attr_translation_key = definition["key"]

        self._attr_native_unit_of_measurement = definition.get("unit")
        self._attr_device_class = definition.get("device_class")
        self._attr_state_class = definition.get("state_class")

        if "category" in definition:
            self._attr_entity_category = EntityCategory(definition["category"])
        if "icon" in definition:
            self._attr_icon = definition["icon"]
        if definition.get("enabled_by_default") is False:
            self._attr_entity_registry_enabled_default = False

        self.states = definition.get("states")

    @property
    def entity_type(self) -> str:
        return "sensor"

    @property
    def available(self) -> bool:
        data = getattr(self.coordinator, "data", None)
        return isinstance(data, dict) and self._key in data

    @property
    def native_value(self):
        """
        Return the sensor value from coordinator data.

        IMPORTANT: coordinator.data already contains SCALED values.
        Do NOT multiply by scale here – that would double-scale everything.
        Only apply: states mapping, precision rounding, ems_version special case.
        """
        if self._key not in self.coordinator.data:
            return None

        value = self.coordinator.data[self._key]

        # Schedule sensor: return boolean enabled state
        if self.definition.get("data_type") == "schedule":
            data = getattr(self.coordinator, "data", {}) or {}
            attrs = data.get(f"{self._key}_attrs") or {}
            enabled = None
            if isinstance(attrs, dict) and "enabled" in attrs:
                try:
                    enabled = bool(int(attrs.get("enabled") or 0))
                except Exception:
                    enabled = bool(attrs.get("enabled"))
            else:
                raw = data.get(self._key)
                if isinstance(raw, (list, tuple)) and len(raw) >= 5:
                    try:
                        enabled = bool(int(raw[4]))
                    except Exception:
                        enabled = bool(raw[4])
            return enabled

        if isinstance(value, (int, float)):
            # Special case: EMS version encoding
            if self._key == "ems_version":
                try:
                    iv = int(value)
                    if iv >= 1000:
                        value = round(iv / 10.0, 1)
                    else:
                        value = int(iv)
                    if isinstance(value, float) and value.is_integer():
                        value = int(value)
                except Exception:
                    pass
            else:
                # Coordinator already applied scale. Only round to display precision.
                precision = int(self.definition.get("precision", 0) or 0)
                value = round(float(value), precision)
                if isinstance(value, float) and value.is_integer():
                    value = int(value)

        if self.states and value in self.states:
            return self.states[value]

        return value

    @property
    def suggested_display_precision(self) -> int | None:
        if self.states:
            return None
        return self.definition.get("precision")

    @property
    def suggested_display_unit(self) -> str | None:
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
        data = self.coordinator.data or {}
        attrs = data.get(f"{self._key}_attrs") or {}
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
                        if 0 <= t <= 2359 and (t % 100) < 60:
                            hh = t // 100
                            mm = t % 100
                        else:
                            hh = t // 60
                            mm = t % 60
                        return f"{hh:02d}:{mm:02d}"
                    except Exception:
                        return t

                days = attrs.get("days")
                try:
                    dmask = int(days) if days is not None else 0
                except Exception:
                    dmask = 0
                weekday_names_mon = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                selected_mon = [weekday_names_mon[i] for i in range(7) if (dmask >> i) & 1]
                display_order = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
                selected = [d for d in display_order if d in selected_mon]

                enriched = {
                    "days_list": selected,
                    "start_time": _fmt_time(attrs.get("start")),
                    "end_time": _fmt_time(attrs.get("end")),
                }

                mode_raw = attrs.get("mode")
                mode = None
                power = None
                try:
                    if mode_raw is not None:
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
                    pass

                enriched["mode"] = mode
                enriched["power"] = power
                enriched["enabled"] = bool(attrs.get("enabled"))
                return enriched

        return attrs or {}


class MarstekCalculatedSensor(CoordinatorEntity, SensorEntity):
    """
    Base class for calculated sensors that depend on multiple coordinator keys.

    SCALING NOTE: dependency values are read directly from coordinator.data,
    which already contains scaled values. Do NOT multiply by scale again.
    """

    def __init__(self, coordinator: MarstekCoordinator, definition: dict):
        super().__init__(coordinator)

        self._key = definition["key"]
        self.definition = definition
        self.coordinator._entity_types[self._key] = self.entity_type

        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{self.definition['key']}"
        self._attr_has_entity_name = True
        self._attr_translation_key = definition["key"]

        self._attr_native_unit_of_measurement = definition.get("unit")
        self._attr_device_class = definition.get("device_class")
        self._attr_state_class = definition.get("state_class")

        if "category" in definition:
            self._attr_entity_category = EntityCategory(definition["category"])
        if "icon" in definition:
            self._attr_icon = definition["icon"]
        if definition.get("enabled_by_default") is False:
            self._attr_entity_registry_enabled_default = False

    def get_dependency_keys(self):
        return self.definition.get("dependency_keys", {})

    @property
    def entity_type(self) -> str:
        return "sensor"

    @property
    def device_info(self) -> dict:
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": self.coordinator.config_entry.title,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "entry_type": "service",
        }

    def _handle_coordinator_update(self) -> None:
        if not getattr(self.coordinator, "last_update_success", False):
            self._attr_native_value = None
            self.async_write_ha_state()
            return

        data = self.coordinator.data if isinstance(self.coordinator.data, dict) else {}
        self._calculate(data)
        self.async_write_ha_state()

    def _calculate(self, data: dict) -> None:
        """
        Check dependencies and calculate sensor value.

        Values in coordinator.data are already scaled – use them directly
        without multiplying by scale again.
        """
        dependency_keys = self.get_dependency_keys()
        dep_values = {}
        missing = []

        for alias, actual_key in dependency_keys.items():
            val = data.get(actual_key)
            if val is None:
                missing.append(alias)
            else:
                # coordinator.data already contains scaled values – no re-scaling
                dep_values[alias] = float(val)

        if missing:
            _LOGGER.warning(
                "%s missing required value(s): %s. Current data: %s. Cannot calculate value.",
                self._key,
                ", ".join(missing),
                {k: data.get(v) for k, v in dependency_keys.items()},
            )
            self._attr_native_value = None
            return

        try:
            value = self.calculate_value(dep_values)
            _LOGGER.debug(
                "Calculated value for %s: %s (input values: %s)",
                self._key, value, dep_values,
            )
            self._attr_native_value = value
        except Exception as ex:
            _LOGGER.warning("Error calculating value for sensor %s: %s", self._key, ex)
            self._attr_native_value = None

    def calculate_value(self, dep_values: dict):
        raise NotImplementedError


class MarstekStoredEnergySensor(MarstekCalculatedSensor):
    """Stored battery energy = SOC% × capacity (kWh)."""

    def calculate_value(self, dep_values: dict):
        soc = dep_values.get("soc")
        capacity = dep_values.get("capacity")
        if soc is None or capacity in (None, 0):
            return None
        return round((soc / 100) * capacity, 2)


class MarstekEfficiencySensor(MarstekCalculatedSensor):
    """Round-trip or conversion efficiency sensor."""

    def calculate_value(self, dep_values: dict):
        mode = self.definition.get("mode", "round_trip")

        if mode == "round_trip":
            charge = dep_values.get("charge")
            discharge = dep_values.get("discharge")
            if not charge:
                return None
            efficiency = (discharge / charge) * 100

        elif mode == "conversion":
            battery_power = dep_values.get("battery_power")
            ac_power = dep_values.get("ac_power")
            if battery_power is None or ac_power is None:
                return None
            if battery_power > 0:
                efficiency = abs(battery_power) / abs(ac_power) * 100 if ac_power else None
            else:
                efficiency = abs(ac_power) / abs(battery_power) * 100 if battery_power else 0.0
            if efficiency is None:
                return None

        else:
            _LOGGER.warning("%s unknown efficiency mode '%s'", self._key, mode)
            return None

        return round(min(efficiency, 100.0), 1)


class MarstekBatteryCycleSensor(MarstekCalculatedSensor):
    """Estimated battery cycles = total discharge ÷ capacity."""

    def calculate_value(self, dep_values: dict):
        discharge = dep_values.get("discharge")
        capacity = dep_values.get("capacity")
        if discharge is None or not capacity:
            return None
        return round(discharge / capacity, 2)
