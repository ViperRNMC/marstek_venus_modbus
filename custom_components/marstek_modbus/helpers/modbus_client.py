"""
Helper module for Modbus communication through Home Assistant's shared unit.
Provides an abstraction for reading and writing registers from
a Marstek Venus battery system asynchronously.
"""

import asyncio
from typing import Optional

import logging

from ..const import DEFAULT_MESSAGE_WAIT_MS, DEFAULT_UNIT_ID

_LOGGER = logging.getLogger(__name__)


class MarstekModbusClient:
    """
    Wrapper for a Home Assistant ModbusUnit with helper methods
    for async reading/writing and interpreting common data types.
    """

    def __init__(self, unit, host: str, port: int, message_wait_ms: int = DEFAULT_MESSAGE_WAIT_MS, unit_id: int = DEFAULT_UNIT_ID):
        """
        Initialize the unit wrapper with connection metadata and request pacing.

        Args:
            host (str): IP address or hostname of Modbus server.
            port (int): TCP port number.
            message_wait_ms (int): Delay in ms between Modbus messages.
            unit_id (int): Modbus Unit ID (slave ID), default is 1.
        """
        self.client = unit
        self.host = host
        self.port = port

        # Normalize and guard message_wait_ms so it is never None
        self.message_wait_ms = int(message_wait_ms) if message_wait_ms is not None else DEFAULT_MESSAGE_WAIT_MS

        # Precompute seconds sleep to avoid repeated float(None) errors
        try:
            self.message_wait_sec = max(0.0, float(self.message_wait_ms) / 1000.0)
        except (TypeError, ValueError):
            self.message_wait_sec = float(DEFAULT_MESSAGE_WAIT_MS) / 1000.0
        unit.set_message_spacing(self.message_wait_sec)

        # Normalize and guard unit_id so it is never None
        try:
            self.unit_id = int(unit_id)
        except (TypeError, ValueError):
            self.unit_id = DEFAULT_UNIT_ID

    @staticmethod
    def _default_count_for_data_type(data_type: str) -> int:
        """Return the default register count for a given data type."""
        if data_type in {"int32", "uint32"}:
            return 2
        if data_type == "schedule":
            return 5
        return 1

    def _decode_registers(
        self,
        register: int,
        regs: list[int],
        data_type: str = "uint16",
        bit_index: Optional[int] = None,
    ):
        """Decode raw holding registers into the requested data type."""
        if data_type == "int16":
            val = regs[0]
            return val - 0x10000 if val >= 0x8000 else val

        if data_type == "uint16":
            return regs[0]

        if data_type == "int32":
            if len(regs) < 2:
                _LOGGER.warning(
                    "Expected 2 registers for int32 at register %d (0x%04X), got %s",
                    register,
                    register,
                    len(regs),
                )
                return None
            val = (regs[0] << 16) | regs[1]
            return val - 0x100000000 if val >= 0x80000000 else val

        if data_type == "uint32":
            if len(regs) < 2:
                _LOGGER.warning(
                    "Expected 2 registers for uint32 at register %d (0x%04X), got %s",
                    register,
                    register,
                    len(regs),
                )
                return None
            return (regs[0] << 16) | regs[1]

        if data_type == "char":
            byte_array = bytearray()
            for reg in regs:
                byte_array.append((reg >> 8) & 0xFF)
                byte_array.append(reg & 0xFF)
            null_pos = byte_array.find(0)
            if null_pos >= 0:
                byte_array = byte_array[:null_pos]
            return byte_array.decode("ascii", errors="ignore")

        if data_type == "mac":
            byte_array = bytearray()
            for reg in regs:
                byte_array.append((reg >> 8) & 0xFF)
                byte_array.append(reg & 0xFF)

            null_pos = byte_array.find(0)
            if null_pos >= 0:
                byte_array = byte_array[:null_pos]

            try:
                ascii_value = byte_array.decode("ascii", errors="strict").strip()
            except UnicodeDecodeError:
                ascii_value = ""

            if len(ascii_value) == 12 and all(ch in "0123456789abcdefABCDEF" for ch in ascii_value):
                return ":".join(
                    ascii_value[index:index + 2].upper()
                    for index in range(0, 12, 2)
                )

            return ":".join(f"{byte:02X}" for byte in byte_array)

        if data_type == "schedule":
            if len(regs) < 5:
                _LOGGER.warning(
                    "Expected 5 registers for schedule at %d (0x%04X), got %s",
                    register,
                    register,
                    len(regs),
                )
                return None
            mode_raw = int(regs[3])
            mode_signed = mode_raw - 0x10000 if mode_raw >= 0x8000 else mode_raw
            return {
                "days": int(regs[0]),
                "start": int(regs[1]),
                "end": int(regs[2]),
                "mode": mode_signed,
                "enabled": int(regs[4]),
            }

        if data_type == "bit":
            if bit_index is None or not (0 <= bit_index < 16):
                raise ValueError("bit_index must be between 0 and 15 for bit data_type")
            reg_val = regs[0]
            return bool((reg_val >> bit_index) & 1)

        raise ValueError(f"Unsupported data_type: {data_type}")

    async def async_read_holding_registers(
        self,
        register: int,
        count: int,
        sensor_key: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 0.1,
    ) -> list[int] | None:
        """Read raw holding registers asynchronously with retries."""
        if not (0 <= register <= 0xFFFF):
            _LOGGER.error(
                "Invalid register address: %d (0x%04X). Must be 0-65535.",
                register,
                register,
            )
            return None

        if not (1 <= count <= 125):
            _LOGGER.error(
                "Invalid register count: %d. Must be between 1 and 125.",
                count,
            )
            return None

        attempt = 0
        while attempt < max_retries:
            try:
                result = await self.client.read_holding_registers(
                    address=register, count=count
                )

                if result is None:
                    _LOGGER.error(
                        "No response object returned for register %d (0x%04X) on attempt %d",
                        register,
                        register,
                        attempt + 1,
                    )
                elif not isinstance(result, list) or len(result) < count:
                    _LOGGER.warning(
                        "Incomplete data received at register %d (0x%04X) on attempt %d: expected %d registers, got %s",
                        register,
                        register,
                        attempt + 1,
                        count,
                        len(result) if isinstance(result, list) else 0,
                    )
                else:
                    regs = result
                    if count == 1:
                        _LOGGER.debug(
                            "Requesting single register %d (0x%04X) from '%s' for key '%s'",
                            register,
                            register,
                            self.host,
                            sensor_key or "unknown",
                        )
                        _LOGGER.debug(
                            "Received single register data from '%s' for register %d (0x%04X): %s",
                            self.host,
                            register,
                            register,
                            regs,
                        )
                    else:
                        _LOGGER.debug(
                            "Requesting register block %d-%d (0x%04X-0x%04X) from '%s' for keys '%s' (count: %s)",
                            register,
                            register + count - 1,
                            register,
                            register + count - 1,
                            self.host,
                            sensor_key or "unknown",
                            count,
                        )
                        _LOGGER.debug(
                            "Received block data from '%s' for registers %d-%d (0x%04X-0x%04X): %s",
                            self.host,
                            register,
                            register + count - 1,
                            register,
                            register + count - 1,
                            regs,
                        )
                    return regs
            except asyncio.CancelledError:
                raise
            except Exception as e:
                cause = getattr(e, "__cause__", None)
                if isinstance(cause, asyncio.CancelledError):
                    raise cause

                _LOGGER.exception(
                    "Exception during Modbus read at register %d (0x%04X) on attempt %d: %s",
                    register,
                    register,
                    attempt + 1,
                    e,
                )

            attempt += 1
            if attempt < max_retries:
                await asyncio.sleep(retry_delay)

        _LOGGER.error(
            "Failed to read register %d (0x%04X) after %d attempts",
            register,
            register,
            max_retries,
        )
        return None

    async def async_read_register(
        self,
        register: int,
        data_type: str = "uint16",
        count: Optional[int] = None,
        bit_index: Optional[int] = None,
        sensor_key: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 0.1,
    ):
        """
        Robustly read registers and interpret the data asynchronously with retries.

        Args:
            register (int): Register address to read from.
            data_type (str): Data type for interpretation, e.g. 'int16', 'int32', 'char', 'bit'.
            count (Optional[int]): Number of registers to read (default depends on data_type).
            bit_index (Optional[int]): Bit position for 'bit' data type (0-15).
            sensor_key (Optional[str]): Sensor key for logging.
            max_retries (int): Maximum number of read attempts.
            retry_delay (float): Delay in seconds between retries.

        Returns:
            int, str, bool, or None: Interpreted value or None on error.
        """
        if count is None:
            count = self._default_count_for_data_type(data_type)

        regs = await self.async_read_holding_registers(
            register=register,
            count=count,
            sensor_key=sensor_key,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )
        if regs is None:
            return None

        return self._decode_registers(
            register=register,
            regs=regs,
            data_type=data_type,
            bit_index=bit_index,
        )

    async def async_write_register(
        self,
        register: int,
        value: int,
        max_retries: int = 3,
        retry_delay: float = 0.2,
    ) -> bool:
        """
        Write a single value to a Modbus holding register asynchronously with retries.

        Args:
            register (int): Register address to write to.
            value (int): Value to write.
            max_retries (int): Maximum number of write attempts.
            retry_delay (float): Delay in seconds between retries.

        Returns:
            bool: True if write was successful, False otherwise.
        """
        # Input validation
        if not (0 <= register <= 0xFFFF):
            _LOGGER.error(
                "Invalid register address for write: %d (0x%04X). Must be 0-65535.",
                register,
                register,
            )
            return False

        # Expect caller to supply an already validated/converted 16-bit unsigned value.
        if not isinstance(value, int):
            _LOGGER.error("Invalid value type for write: %s. Must be int.", type(value))
            return False

        if not (0 <= value <= 0xFFFF):
            _LOGGER.error(
                "Invalid value for write: %d. Must be 0-65535.",
                value,
            )
            return False
        value_to_send = value

        attempt = 0
        while attempt < max_retries:
            try:
                _LOGGER.debug(
                    "Writing to register %d (0x%04X), value=%d (0x%04X), attempt=%d",
                    register,
                    register,
                    value,
                    value,
                    attempt + 1,
                )

                await self.client.write_register(address=register, value=value)
                _LOGGER.debug(
                    "Write confirmed for register %d (0x%04X), value=%d",
                    register,
                    register,
                    value,
                )
                return True

            except asyncio.CancelledError:
                # Allow cancellation to propagate during shutdown
                raise

            except Exception as e:
                # If underlying cause is CancelledError, propagate it
                cause = getattr(e, "__cause__", None)
                if isinstance(cause, asyncio.CancelledError):
                    raise cause

                _LOGGER.exception(
                    "Exception during Modbus write at register %d (0x%04X) on attempt %d: %s",
                    register,
                    register,
                    attempt + 1,
                    e,
                )

            attempt += 1
            if attempt < max_retries:
                await asyncio.sleep(retry_delay)

        _LOGGER.error(
            "Failed to write to register %d (0x%04X) after %d attempts",
            register,
            register,
            max_retries,
        )
        return False