import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custom_components.marstek_modbus.coordinator import MarstekCoordinator
from custom_components.marstek_modbus.sensor import MarstekSolarPowerSensor

SOLAR_TOTAL = {
    "key": "solar_power_total",
    "dependency_keys": {
        "mppt1": "mppt1_power",
        "mppt2": "mppt2_power",
        "mppt3": "mppt3_power",
        "mppt4": "mppt4_power",
    },
}


class FakeCoordinator:
    def __init__(self):
        self._scales = {f"mppt{n}_power": 0.1 for n in range(1, 5)}


def make_sensor():
    sensor = object.__new__(MarstekSolarPowerSensor)
    sensor._key = SOLAR_TOTAL["key"]
    sensor.definition = SOLAR_TOTAL
    sensor.coordinator = FakeCoordinator()
    return sensor


def test_solar_dependencies_are_fetched_like_the_other_calculated_sensors():
    coordinator = object.__new__(MarstekCoordinator)
    coordinator.EFFICIENCY_SENSOR_DEFINITIONS = [
        {"key": "round_trip_efficiency_total", "dependency_keys": {"charge": "total_charging_energy"}}
    ]
    coordinator.SOLAR_POWER_SENSOR_DEFINITIONS = [SOLAR_TOTAL]
    coordinator.VERSION_SENSOR_DEFINITIONS = []
    coordinator.STORED_ENERGY_SENSOR_DEFINITIONS = [
        {"key": "stored_energy", "dependency_keys": {"soc": "battery_soc", "none": None}}
    ]
    coordinator.CYCLE_SENSOR_DEFINITIONS = []

    assert coordinator._calculated_dependency_keys() == {
        "total_charging_energy",
        "mppt1_power",
        "mppt2_power",
        "mppt3_power",
        "mppt4_power",
        "battery_soc",
    }


def test_solar_total_is_the_sum_of_all_inputs():
    sensor = make_sensor()
    sensor._calculate({"mppt1_power": 303, "mppt2_power": 302, "mppt3_power": 0, "mppt4_power": 0})
    assert sensor._attr_native_value == 60.5


def test_missing_dependency_is_warned_once_until_it_is_back(caplog):
    sensor = make_sensor()
    partial = {"mppt1_power": 303, "mppt2_power": 302}
    complete = {**partial, "mppt3_power": 0, "mppt4_power": 0}

    def warnings():
        return [r for r in caplog.records if r.levelno == logging.WARNING]

    with caplog.at_level(logging.DEBUG):
        for _ in range(5):
            sensor._calculate(partial)
        assert sensor._attr_native_value is None
        assert len(warnings()) == 1
        assert "mppt3, mppt4" in warnings()[0].getMessage()

        sensor._calculate(complete)
        assert sensor._attr_native_value == 60.5
        assert len(warnings()) == 1

        sensor._calculate(partial)
        assert len(warnings()) == 2
