"""
modbus_client.py  –  Thin wrapper around tmodbus for marstek_modbus.

Drop this file into:
  custom_components/marstek_modbus/modbus_client.py

It replaces every direct use of pymodbus in coordinator.py and
provides the same helper interface that the rest of the integration
expects (read_registers, read_int16, read_int32, read_uint32,
read_string, write_register).
"""

from __future__ import annotations

import asyncio
import logging
import struct
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from tmodbus import create_async_tcp_client
from tmodbus.client import AsyncModbusClient
from tmodbus.exceptions import TModbusError, ModbusConnectionError

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

async def create_client(host: str, port: int, unit_id: int, timeout: float = 5.0) -> AsyncModbusClient:
    """Create and connect a tmodbus TCP client."""
    client = create_async_tcp_client(
        host,
        port,
        unit_id=unit_id,
        timeout=timeout,
        connect_timeout=timeout,
        auto_reconnect=True,          # tmodbus reconnects automatically
        wait_between_requests=0.05,   # 50 ms between requests – polite for RS485 gateways
    )
    await client.connect()
    _LOGGER.debug("tmodbus connected to %s:%s unit_id=%s", host, port, unit_id)
    return client


async def disconnect_client(client: AsyncModbusClient | None) -> None:
    """Gracefully disconnect a tmodbus client."""
    if client is not None:
        try:
            await client.disconnect()
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("Error while disconnecting tmodbus client: %s", exc)


# ---------------------------------------------------------------------------
# Low-level read helpers
# ---------------------------------------------------------------------------

async def read_registers(
    client: AsyncModbusClient,
    address: int,
    count: int,
) -> list[int]:
    """
    Read *count* holding registers starting at *address*.

    Returns a plain list[int] (unsigned 16-bit each), exactly as
    pymodbus's response.registers did.

    Raises HomeAssistantError-compatible exceptions on failure so the
    coordinator can catch them uniformly.
    """
    try:
        result = await client.read_holding_registers(
            start_address=address,
            quantity=count,
        )
        return result
    except ModbusConnectionError as exc:
        raise ConnectionError(f"Modbus connection error at reg {address}: {exc}") from exc
    except TModbusError as exc:
        raise OSError(f"Modbus error reading reg {address} (count={count}): {exc}") from exc


async def read_uint16(client: AsyncModbusClient, address: int) -> int:
    """Read one holding register as unsigned 16-bit integer (0…65535)."""
    regs = await read_registers(client, address, 1)
    return regs[0]


async def read_int16(client: AsyncModbusClient, address: int) -> int:
    """Read one holding register as signed 16-bit integer (-32768…32767)."""
    regs = await read_registers(client, address, 1)
    # Reinterpret unsigned 16-bit as signed
    return struct.unpack(">h", struct.pack(">H", regs[0]))[0]


async def read_uint32(client: AsyncModbusClient, address: int) -> int:
    """
    Read two consecutive holding registers as unsigned 32-bit integer.

    Byte order: big-endian word order (standard Modbus):
      register[0] = high word, register[1] = low word  →  (high << 16) | low
    """
    regs = await read_registers(client, address, 2)
    return (regs[0] << 16) | regs[1]


async def read_int32(client: AsyncModbusClient, address: int) -> int:
    """
    Read two consecutive holding registers as signed 32-bit integer.

    Same word order as read_uint32.
    """
    raw = (await read_registers(client, address, 2))
    unsigned = (raw[0] << 16) | raw[1]
    return struct.unpack(">i", struct.pack(">I", unsigned))[0]


async def read_string(client: AsyncModbusClient, address: int, num_registers: int) -> str:
    """
    Read *num_registers* holding registers and decode them as an ASCII string.

    Each register contains 2 bytes (big-endian), null-terminated.
    """
    regs = await read_registers(client, address, num_registers)
    raw_bytes = b"".join(struct.pack(">H", r) for r in regs)
    return raw_bytes.split(b"\x00")[0].decode("ascii", errors="replace").strip()


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------

async def write_register(
    client: AsyncModbusClient,
    address: int,
    value: int,
) -> None:
    """
    Write a single holding register (FC 06 – Write Single Register).

    Value must fit in uint16 (0…65535).
    """
    try:
        await client.write_single_register(address, value)
        _LOGGER.debug("Wrote reg %s = %s", address, value)
    except ModbusConnectionError as exc:
        raise ConnectionError(f"Modbus connection error writing reg {address}: {exc}") from exc
    except TModbusError as exc:
        raise OSError(f"Modbus error writing reg {address} = {value}: {exc}") from exc


async def write_registers(
    client: AsyncModbusClient,
    address: int,
    values: list[int],
) -> None:
    """
    Write multiple consecutive holding registers (FC 16).

    Each value must be uint16 (0…65535).
    """
    try:
        await client.write_multiple_registers(address, values)
        _LOGGER.debug("Wrote regs %s…%s = %s", address, address + len(values) - 1, values)
    except ModbusConnectionError as exc:
        raise ConnectionError(f"Modbus connection error writing regs at {address}: {exc}") from exc
    except TModbusError as exc:
        raise OSError(f"Modbus error writing regs at {address}: {exc}") from exc
