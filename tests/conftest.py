"""Fixtures for the Marstek Venus Modbus tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import patch

import pytest
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from modbus_connection.mock import MockModbusConnection, MockModbusUnit
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.marstek_modbus.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Generator[None]:
    """Let Home Assistant load this custom integration."""
    yield


@pytest.fixture(name="unit")
def unit_fixture() -> MockModbusUnit:
    """An in-memory Venus E v3 on unit 1."""
    unit = MockModbusConnection().for_unit(1)
    unit.holding[30001] = 0xFF38  # battery power -200 W
    unit.holding[30006] = 0xFF42  # ac power -190 W
    unit.holding[30100] = 5312  # battery voltage 53.12 V
    unit.holding[30200] = [1476, 0, 117, 0, 112]  # EMS, VMS, BMS versions
    unit.holding[31000] = [0x5645, 0x4E55, 0x5300]  # "VENUS"
    unit.holding[32105] = 5120  # 5.12 kWh
    unit.holding[33000] = [0x0001, 0xD4C0, 0x0001, 0x86A0]  # 1200.00, 1000.00 kWh
    unit.holding[34002] = 550  # 55.0 %
    unit.holding[35100] = 2  # charging
    unit.holding[43000] = 1  # anti-feed
    unit.holding[41200] = 0  # backup on
    return unit


@pytest.fixture(name="device_version")
def device_version_fixture() -> str:
    """The model the entry was set up for."""
    return "E v3"


@pytest.fixture(name="config_entry")
def config_entry_fixture(hass: HomeAssistant, device_version: str) -> MockConfigEntry:
    """A config entry for a battery at 192.168.1.50."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Marstek",
        data={
            CONF_HOST: "192.168.1.50",
            CONF_PORT: 502,
            "unit_id": 1,
            "device_version": device_version,
        },
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture(name="mock_get_unit")
def mock_get_unit_fixture(unit: MockModbusUnit) -> Generator[None]:
    """Hand the integration the in-memory unit."""
    with patch("custom_components.marstek_modbus.async_get_unit", return_value=unit):
        yield


@pytest.fixture(name="setup_integration")
async def setup_integration_fixture(
    hass: HomeAssistant, config_entry: MockConfigEntry, mock_get_unit: None
) -> MockConfigEntry:
    """Set the entry up over the in-memory unit."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry
