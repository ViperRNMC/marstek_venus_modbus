import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custom_components.marstek_modbus.helpers.modbus_client import MarstekModbusClient


class FakeClient:
    def __init__(self):
        self.read_calls = 0
        self.read_kwargs = None
        self.write_calls = 0
        self.write_kwargs = None
        self.message_spacing = None

    def set_message_spacing(self, seconds):
        self.message_spacing = seconds

    async def read_holding_registers(self, address, count, **kwargs):
        self.read_calls += 1
        self.read_kwargs = kwargs
        return [1] * count

    async def write_register(self, address, value, **kwargs):
        self.write_calls += 1
        self.write_kwargs = kwargs
        return None


@pytest.mark.asyncio
async def test_read_holding_registers_uses_shared_unit_return_value():
    fake_client = FakeClient()
    client = MarstekModbusClient(
        fake_client, "127.0.0.1", 502, message_wait_ms=0
    )

    result = await client.async_read_holding_registers(register=1, count=1, max_retries=1, retry_delay=0)

    assert result == [1]
    assert fake_client.read_calls == 1
    assert fake_client.read_kwargs == {}
    assert fake_client.message_spacing == 0


@pytest.mark.asyncio
async def test_write_register_uses_shared_unit_return_value():
    fake_client = FakeClient()
    client = MarstekModbusClient(
        fake_client, "127.0.0.1", 502, message_wait_ms=0
    )

    result = await client.async_write_register(register=1, value=10, max_retries=1, retry_delay=0)

    assert result is True
    assert fake_client.write_calls == 1
    assert fake_client.write_kwargs == {}
