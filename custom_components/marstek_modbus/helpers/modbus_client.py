"""
modbus_client.py  –  tmodbus wrapper for marstek_modbus.

Provides:
  - create_client / disconnect_client  (connection lifecycle)
  - batch_read()                       (block-optimised multi-register read)
  - extract_typed_value()              (decode raw register cache → Python value)
  - write_register / write_registers   (single + multi write)

Individual per-type read helpers (read_uint16 etc.) are kept for
backward-compatibility in case other files call them.

Drop into: custom_components/marstek_modbus/helpers/modbus_client.py
  (or wherever the integration currently places this file)
"""

from __future__ import annotations

import logging
import struct
from typing import Any

from tmodbus import create_async_tcp_client
from tmodbus.client import AsyncModbusClient
from tmodbus.exceptions import TModbusError, ModbusConnectionError

_LOGGER = logging.getLogger(__name__)

# ── Block-read tuning ────────────────────────────────────────────────────────
MAX_BLOCK_SIZE: int = 64   # max registers per single Modbus FC03 request
                            # (Modbus spec allows up to 125; 64 is a safe
                            # conservative value for RS-485 gateways)
MAX_GAP: int = 15           # bridge gaps of up to 15 registers between
                            # requested addresses – dramatically reduces the
                            # number of round-trips for sparse register maps
                            # (e.g. cell voltages at 34018-34033 + 34003 → 1
                            # request instead of 2)
# ────────────────────────────────────────────────────────────────────────────


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

async def create_client(
    host: str, port: int, unit_id: int, timeout: float = 5.0
) -> AsyncModbusClient:
    """Create and connect a tmodbus TCP client."""
    client = create_async_tcp_client(
        host,
        port,
        unit_id=unit_id,
        timeout=timeout,
        connect_timeout=timeout,
        auto_reconnect=True,
        wait_between_requests=0.05,   # 50 ms – safe for Elfin EW11 / RS485 gateways
    )
    await client.connect()
    _LOGGER.debug("tmodbus connected to %s:%s unit_id=%s", host, port, unit_id)
    return client


async def disconnect_client(client: AsyncModbusClient | None) -> None:
    """Gracefully disconnect."""
    if client is not None:
        try:
            await client.disconnect()
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("Error while disconnecting: %s", exc)


# ---------------------------------------------------------------------------
# Block builder
# ---------------------------------------------------------------------------

def _build_blocks(
    addresses: list[int],
    max_gap: int = MAX_GAP,
    max_size: int = MAX_BLOCK_SIZE,
    bad_gaps: set[tuple[int, int]] | None = None,
) -> list[tuple[int, int]]:
    """
    Group a list of register addresses into (start, count) read blocks.

    Rules:
    - Gaps ≤ max_gap between addresses are bridged (those registers are
      read but their values are simply available in the cache for free).
    - A block is split once it would exceed max_size registers.
    - Gaps listed in bad_gaps are never bridged regardless of size – they
      caused a block failure on a previous poll and the device rejected them.

    Returns a list of (start_address, count) tuples, sorted by address.
    """
    if not addresses:
        return []

    sorted_addrs = sorted(set(addresses))
    blocks: list[tuple[int, int]] = []
    block_start = sorted_addrs[0]
    prev_addr = sorted_addrs[0]

    for addr in sorted_addrs[1:]:
        gap = addr - prev_addr
        new_size = addr - block_start + 1
        gap_is_bad = bad_gaps is not None and (prev_addr, addr) in bad_gaps
        if gap <= max_gap and new_size <= max_size and not gap_is_bad:
            prev_addr = addr
        else:
            blocks.append((block_start, prev_addr - block_start + 1))
            block_start = addr
            prev_addr = addr

    blocks.append((block_start, prev_addr - block_start + 1))
    return blocks


# ---------------------------------------------------------------------------
# Batch read
# ---------------------------------------------------------------------------

async def batch_read(
    client: AsyncModbusClient,
    addresses: list[int],
    max_gap: int = MAX_GAP,
    max_size: int = MAX_BLOCK_SIZE,
    bad_gaps: set[tuple[int, int]] | None = None,
    good_gaps: set[tuple[int, int]] | None = None,
) -> dict[int, int]:
    """
    Read all *addresses* using the fewest possible Modbus requests.

    Returns {register_address: raw_uint16_value} for every address that
    was read (including gap-bridging registers).

    bad_gaps:  mutable set of (left, right) gap pairs that caused block
               failures in a previous poll.  _build_blocks avoids bridging
               these so the device is never asked about unsupported ranges.

    good_gaps: mutable set of (left, right) gap pairs that were bridged
               successfully at least once.  A gap already in good_gaps is
               NEVER added to bad_gaps – this protects block optimisations
               from being destroyed by a temporary TCP outage (where every
               block fails, not just the ones with unsupported registers).

    Both sets are mutated in place; pass coordinator._bad_gaps /
    coordinator._good_gaps to enable self-healing gap avoidance.

    Raises ConnectionError / OSError on Modbus failure.
    """
    if not addresses:
        return {}

    blocks = _build_blocks(addresses, max_gap, max_size, bad_gaps)

    _LOGGER.debug(
        "batch_read: %d unique addresses → %d block(s): %s",
        len(set(addresses)),
        len(blocks),
        [(s, s + c - 1) for s, c in blocks],
    )

    cache: dict[int, int] = {}
    needed = set(addresses)  # only addresses we actually need (not gap fillers)

    for start, count in blocks:
        try:
            regs = await client.read_holding_registers(
                start_address=start, quantity=count
            )
            for i, val in enumerate(regs):
                cache[start + i] = val

            # Block succeeded – record every gap bridged within it as good.
            # This protects these gaps from being poisoned as bad during a
            # future TCP outage where all blocks fail simultaneously.
            if good_gaps is not None:
                block_needed = sorted(
                    addr for addr in needed if start <= addr < start + count
                )
                for i in range(len(block_needed) - 1):
                    left, right = block_needed[i], block_needed[i + 1]
                    if right - left > 1 and (left, right) not in good_gaps:
                        good_gaps.add((left, right))
                        _LOGGER.debug(
                            "Confirmed good gap %d → %d (gap=%d): "
                            "protected from bad-gap poisoning on TCP outages.",
                            left, right, right - left,
                        )

        except Exception as exc:  # noqa: BLE001
            # One block failed (timeout, illegal address, connection drop…).
            # Log and skip – do NOT abort the whole poll.
            # The missing registers will simply stay absent from the cache.
            _LOGGER.debug(
                "Block %d–%d failed (%s: %s) – skipping",
                start, start + count - 1, type(exc).__name__, exc,
            )

            # Record the gaps between consecutive needed addresses inside
            # this failed block as bad – UNLESS the gap was already confirmed
            # good (i.e. succeeded before).  A confirmed-good gap failing now
            # means a TCP outage, not an unsupported register range.
            if bad_gaps is not None:
                block_needed = sorted(
                    addr for addr in needed if start <= addr < start + count
                )
                for i in range(len(block_needed) - 1):
                    left, right = block_needed[i], block_needed[i + 1]
                    if right - left > 1:
                        already_good = good_gaps is not None and (left, right) in good_gaps
                        already_bad = (left, right) in bad_gaps
                        if not already_good and not already_bad:
                            bad_gaps.add((left, right))
                            _LOGGER.info(
                                "Recorded bad gap %d → %d (gap=%d): "
                                "will not bridge this range in future requests.",
                                left, right, right - left,
                            )

            # Try each needed address in this block individually as fallback.
            # Use quantity=1 so a single bad register can't poison the rest.
            for addr in range(start, start + count):
                if addr not in needed:
                    continue
                try:
                    single = await client.read_holding_registers(
                        start_address=addr, quantity=1
                    )
                    cache[addr] = single[0]
                except Exception:  # noqa: BLE001
                    pass  # register truly not available – leave absent

    return cache


# ---------------------------------------------------------------------------
# Value extraction
# ---------------------------------------------------------------------------

def extract_typed_value(
    cache: dict[int, int],
    address: int,
    data_type: str,
    count: int,
    scale: float,
) -> int | float | str | None:
    """
    Extract and scale a value from a batch_read cache dict.

    Returns None if any required address is missing from the cache.

    data_type:  uint16 | int16 | uint32 | int32 | char
    count:      number of registers (1 for 16-bit, 2 for 32-bit, N for char)
    scale:      multiply raw integer result (not applied to char)
    """
    # Check all required addresses are present
    needed = range(address, address + count)
    if any(a not in cache for a in needed):
        return None

    raw = cache[address]

    if data_type == "uint16":
        value: int | float | str = raw

    elif data_type == "int16":
        value = struct.unpack(">h", struct.pack(">H", raw))[0]

    elif data_type == "uint32":
        value = (cache[address] << 16) | cache[address + 1]

    elif data_type == "int32":
        unsigned = (cache[address] << 16) | cache[address + 1]
        value = struct.unpack(">i", struct.pack(">I", unsigned))[0]

    elif data_type == "char":
        raw_bytes = b"".join(
            struct.pack(">H", cache[address + i]) for i in range(count)
        )
        return raw_bytes.split(b"\x00")[0].decode("ascii", errors="replace").strip()

    else:
        _LOGGER.warning("Unknown data_type '%s' at address %s", data_type, address)
        return None

    # Apply scale
    if scale == 1.0 or scale == 1:
        return int(value)
    return round(float(value) * scale, 6)


# ---------------------------------------------------------------------------
# Backward-compatible individual read helpers
# (kept so that any existing callers outside coordinator.py still work)
# ---------------------------------------------------------------------------

async def read_registers(
    client: AsyncModbusClient, address: int, count: int
) -> list[int]:
    """Read *count* holding registers; return raw list[int]."""
    cache = await batch_read(client, list(range(address, address + count)),
                              max_gap=0, max_size=MAX_BLOCK_SIZE)
    return [cache[address + i] for i in range(count)]


async def read_uint16(client: AsyncModbusClient, address: int) -> int:
    regs = await read_registers(client, address, 1)
    return regs[0]


async def read_int16(client: AsyncModbusClient, address: int) -> int:
    regs = await read_registers(client, address, 1)
    return struct.unpack(">h", struct.pack(">H", regs[0]))[0]


async def read_uint32(client: AsyncModbusClient, address: int) -> int:
    regs = await read_registers(client, address, 2)
    return (regs[0] << 16) | regs[1]


async def read_int32(client: AsyncModbusClient, address: int) -> int:
    regs = await read_registers(client, address, 2)
    unsigned = (regs[0] << 16) | regs[1]
    return struct.unpack(">i", struct.pack(">I", unsigned))[0]


async def read_string(client: AsyncModbusClient, address: int, num_registers: int) -> str:
    regs = await read_registers(client, address, num_registers)
    raw_bytes = b"".join(struct.pack(">H", r) for r in regs)
    return raw_bytes.split(b"\x00")[0].decode("ascii", errors="replace").strip()


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------

async def write_register(
    client: AsyncModbusClient, address: int, value: int
) -> None:
    """Write a single holding register (FC 06)."""
    try:
        await client.write_single_register(address, value)
        _LOGGER.debug("write_register %s = %s", address, value)
    except ModbusConnectionError as exc:
        raise ConnectionError(
            f"Modbus connection error writing reg {address}: {exc}"
        ) from exc
    except TModbusError as exc:
        raise OSError(f"Modbus error writing reg {address} = {value}: {exc}") from exc


async def write_registers(
    client: AsyncModbusClient, address: int, values: list[int]
) -> None:
    """Write multiple consecutive holding registers (FC 16)."""
    try:
        await client.write_multiple_registers(address, values)
        _LOGGER.debug(
            "write_registers %s…%s = %s",
            address, address + len(values) - 1, values,
        )
    except ModbusConnectionError as exc:
        raise ConnectionError(
            f"Modbus connection error writing regs at {address}: {exc}"
        ) from exc
    except TModbusError as exc:
        raise OSError(f"Modbus error writing regs at {address}: {exc}") from exc


# ---------------------------------------------------------------------------
# MarstekModbusClient  –  Compatibility wrapper for config_flow.py
# ---------------------------------------------------------------------------

class MarstekModbusClient:
    """
    High-level Modbus client wrapper used by config_flow.py.

    Provides an async connect / close / read interface on top of tmodbus
    so that config_flow.py does not need to know about tmodbus internals.
    """

    def __init__(
        self,
        host: str,
        port: int,
        *,
        message_wait_ms: int | None = None,
        timeout: float = 5.0,
        unit_id: int = 1,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.unit_id = unit_id
        self._wait_s = (message_wait_ms or 80) / 1000.0
        self._client: AsyncModbusClient | None = None

    async def async_connect(self) -> bool:
        """Open the Modbus TCP connection. Returns True on success."""
        try:
            self._client = await create_client(
                self.host, self.port, self.unit_id, timeout=self.timeout
            )
            return True
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("MarstekModbusClient.async_connect failed: %s", exc)
            return False

    async def async_close(self) -> None:
        """Close the Modbus TCP connection."""
        await disconnect_client(self._client)
        self._client = None

    async def async_read_register(
        self,
        register: int,
        data_type: str,
        count: int,
        sensor_key: str = "",
        scale: float = 1.0,
    ) -> int | float | str | None:
        """
        Read one register (or a multi-register value) and return the decoded value.

        Returns None on any Modbus error so callers can treat it as
        "no response" without raising exceptions.
        """
        if self._client is None:
            return None
        try:
            addresses = list(range(register, register + count))
            cache = await batch_read(self._client, addresses, max_gap=0)
            return extract_typed_value(cache, register, data_type, count, scale)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug(
                "MarstekModbusClient.async_read_register(%s, %s) failed: %s",
                register, sensor_key, exc,
            )
            return None
