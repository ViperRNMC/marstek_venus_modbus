"""
Helper module for Modbus TCP communication using pymodbus.
Provides an abstraction for reading and writing registers from
a Marstek Venus battery system asynchronously.
"""

from pymodbus.client.tcp import AsyncModbusTcpClient
import asyncio
from typing import Optional

import logging

_LOGGER = logging.getLogger(__name__)


class MarstekModbusClient:
    """
    Wrapper for pymodbus AsyncModbusTcpClient with helper methods
    for async reading/writing and interpreting common data types.
    """

    def __init__(self, host: str, port: int, message_wait_ms: int = 50, timeout: int = 5):
        """
        Initialize Modbus client with host, port, message wait time, and timeout.

        Args:
            host (str): IP address or hostname of Modbus server.
            port (int): TCP port number.
            message_wait_ms (int): Delay in ms between Modbus messages.
            timeout (int): Connection timeout in seconds.
        """
        self.host = host
        self.port = port

        # Create pymodbus async TCP client instance
        self.client = AsyncModbusTcpClient(
            host=host,
            port=port,
            timeout=timeout,
        )

        self.client.message_wait_milliseconds = message_wait_ms
        self.unit_id = 1  # Default Unit ID

    async def async_connect(self) -> bool:
        """
        Connect asynchronously to the Modbus TCP server.

        Returns:
            bool: True if connection succeeded, False otherwise.
        """
        connected = await self.client.connect()

        if connected:
            # Wait briefly to ensure connection stability
            await asyncio.sleep(0.2)
            _LOGGER.info(
                "Connected to Modbus server at %s:%s with unit %s",
                self.host,
                self.port,
                self.unit_id,
            )
        else:
            _LOGGER.warning(
                "Failed to connect to Modbus server at %s:%s with unit %s",
                self.host,
                self.port,
                self.unit_id,
            )

        return connected

    async def async_close(self) -> None:
        """
        Close the Modbus TCP connection asynchronously.
        """
        await self.client.close()

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
            count = 2 if data_type in ["int32", "uint32"] else 1

        if not (0 <= register <= 0xFFFF):
            _LOGGER.error(
                "Invalid register address: %d (0x%04X). Must be 0-65535.",
                register,
                register,
            )
            return None

        if not (1 <= count <= 125):  # Modbus spec limit
            _LOGGER.error(
                "Invalid register count: %d. Must be between 1 and 125.",
                count,
            )
            return None

        attempt = 0
        while attempt < max_retries:
            if not self.client.connected:
                _LOGGER.warning(
                    "Modbus client not connected, attempting reconnect before register %d (0x%04X)",
                    register,
                    register,
                )
                connected = await self.async_connect()
                if not connected:
                    _LOGGER.error(
                        "Reconnect failed, skipping register %d (0x%04X)",
                        register,
                        register,
                    )
                    return None

            try:
                result = await self.client.read_holding_registers(
                    address=register, count=count, device_id=self.unit_id
                )
                if result.isError():
                    _LOGGER.error(
                        "Modbus read error at register %d (0x%04X) on attempt %d",
                        register,
                        register,
                        attempt + 1,
                    )
                elif not hasattr(result, "registers") or result.registers is None or len(result.registers) < count:
                    _LOGGER.warning(
                        "Incomplete data received at register %d (0x%04X) on attempt %d: expected %d registers, got %s",
                        register,
                        register,
                        attempt + 1,
                        count,
                        len(result.registers) if result.registers else 0,
                    )
                else:
                    regs = result.registers
                    _LOGGER.debug(
                        "Requesting register %d (0x%04X) for sensor '%s' (type: %s, count: %s)",
                        register,
                        register,
                        sensor_key or 'unknown',
                        data_type,
                        count,
                    )
                    _LOGGER.debug("Received data from register %d (0x%04X): %s", register, register, regs)

                    if data_type == "int16":
                        val = regs[0]
                        return val - 0x10000 if val >= 0x8000 else val

                    elif data_type == "uint16":
                        return regs[0]

                    elif data_type == "int32":
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

                    elif data_type == "uint32":
                        if len(regs) < 2:
                            _LOGGER.warning(
                                "Expected 2 registers for uint32 at register %d (0x%04X), got %s",
                                register,
                                register,
                                len(regs),
                            )
                            return None
                        return (regs[0] << 16) | regs[1]

                    elif data_type == "char":
                        byte_array = bytearray()
                        for reg in regs:
                            byte_array.append((reg >> 8) & 0xFF)
                            byte_array.append(reg & 0xFF)
                        return byte_array.decode("ascii", errors="ignore").rstrip('\x00')

                    elif data_type == "bit":
                        if bit_index is None or not (0 <= bit_index < 16):
                            raise ValueError("bit_index must be between 0 and 15 for bit data_type")
                        reg_val = regs[0]
                        return bool((reg_val >> bit_index) & 1)

                    else:
                        raise ValueError(f"Unsupported data_type: {data_type}")

            except Exception as e:
                _LOGGER.exception("Exception during Modbus read at register %d (0x%04X) on attempt %d: %s", register, register, attempt + 1, e)

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

    async def async_write_register(self, register: int, value: int) -> bool:
        """
        Write a single value to a Modbus holding register asynchronously.

        Args:
            register (int): Register address to write to.
            value (int): Value to write.

        Returns:
            bool: True if write was successful, False otherwise.
        """
        try:
            result = await self.client.write_register(
                address=register, value=value, device_id=self.unit_id
            )
            return not result.isError()

        except Exception as e:
            _LOGGER.exception("Exception during modbus write: %s", e)
            return False