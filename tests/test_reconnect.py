import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custom_components.marstek_modbus.coordinator import (
    REQUEST_TIMEOUT,
    SINGLE_READ_TIMEOUT,
    MarstekCoordinator,
)
from custom_components.marstek_modbus.helpers.modbus_client import MarstekModbusClient


def make_coordinator(unit):
    coordinator = object.__new__(MarstekCoordinator)
    coordinator.unit = unit
    coordinator.host = "192.0.2.10"
    coordinator.port = 502
    return coordinator


async def test_recycling_drops_the_shared_link():
    unit = MagicMock()
    unit.disconnect = AsyncMock()
    await make_coordinator(unit)._async_recycle_connection("all reads failed")
    unit.disconnect.assert_awaited_once()


async def test_recycling_never_raises():
    unit = MagicMock()
    unit.disconnect = AsyncMock(side_effect=RuntimeError("teardown failed"))
    await make_coordinator(unit)._async_recycle_connection("repeated timeouts")
    unit.disconnect.assert_awaited_once()


async def test_recycling_is_skipped_for_a_unit_without_disconnect():
    unit = object()  # an older connection object without the method
    await make_coordinator(unit)._async_recycle_connection("all reads failed")


def test_the_client_attempts_fit_into_the_outer_read_timeout():
    # three attempts of the client, each up to REQUEST_TIMEOUT plus the retry delay
    assert 3 * (REQUEST_TIMEOUT + 0.1) < SINGLE_READ_TIMEOUT


async def test_a_dead_link_gives_up_after_the_attempts_not_after_the_outer_guard():
    unit = MagicMock()
    unit.read_holding_registers = AsyncMock(side_effect=TimeoutError("no answer"))
    client = MarstekModbusClient(unit, "192.0.2.10", 502)
    assert await client.async_read_holding_registers(register=32100, count=1) is None
    assert unit.read_holding_registers.await_count == 3
