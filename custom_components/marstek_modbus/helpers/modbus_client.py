"""
Helper module for Modbus TCP communication using pymodbus.
Provides an abstraction for reading and writing registers from
a Marstek Venus battery system asynchronously.
"""

from pymodbus.client.tcp import AsyncModbusTcpClient
import asyncio
from typing import Optional

import logging

from ..const import DEFAULT_MESSAGE_WAIT_MS, DEFAULT_UNIT_ID

_LOGGER = logging.getLogger(__name__)


class MarstekModbusClient:
    """
    Wrapper for pymodbus AsyncModbusTcpClient with helper methods
    for async reading/writing and interpreting common data types.
    """

    def __init__(self, host: str, port: int, message_wait_ms: int = DEFAULT_MESSAGE_WAIT_MS, timeout: int = 3, unit_id: int = DEFAULT_UNIT_ID):
        """
        Initialize Modbus client with host, port, message wait time, timeout, and unit ID.

        Args:
            host (str): IP address or hostname of Modbus server.
            port (int): TCP port number.
            message_wait_ms (int): Delay in ms between Modbus messages.
            timeout (int): Connection timeout in seconds (default 3 for faster failure).
            unit_id (int): Modbus Unit ID (slave ID), default is 1.
        """
        self.host = host
        self.port = port
        self.timeout = timeout

        # Normalize and guard message_wait_ms so it is never None
        self.message_wait_ms = int(message_wait_ms) if message_wait_ms is not None else DEFAULT_MESSAGE_WAIT_MS

        # Precompute seconds sleep to avoid repeated float(None) errors
        try:
            self.message_wait_sec = max(0.0, float(self.message_wait_ms) / 1000.0)
        except (TypeError, ValueError):
            self.message_wait_sec = float(DEFAULT_MESSAGE_WAIT_MS) / 1000.0

        # Create pymodbus async TCP client instance
        self.client = AsyncModbusTcpClient(
            host=host,
            port=port,
            timeout=timeout,
        )

        # set message wait on client if supported
        try:
            self.client.message_wait_milliseconds = self.message_wait_ms
        except AttributeError:
            pass

        # Normalize and guard unit_id so it is never None
        try:
            self.unit_id = int(unit_id)
        except (TypeError, ValueError):
            self.unit_id = DEFAULT_UNIT_ID

        # Lock to serialize outgoing Modbus requests to avoid transaction id collisions
        self._request_lock = asyncio.Lock()

    async def async_connect(self) -> bool:
        """
        Connect asynchronously to the Modbus TCP server.

        Returns:
            bool: True if connection succeeded, False otherwise.
        """
        # If client was closed previously, recreate the AsyncModbusTcpClient
        if self.client is None:
            self.client = AsyncModbusTcpClient(
                host=self.host,
                port=self.port,
                timeout=self.timeout,
            )
            # restore configured properties
            try:
                self.client.message_wait_milliseconds = self.message_wait_ms
            except Exception:
                # some client implementations may not expose this attribute
                pass

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
        Close the Modbus TCP connection safely (sync or async) 
        and reset client reference.
        """
        if not self.client:
            return

        try:
            result = self.client.close()
            if asyncio.iscoroutine(result):
                await result
            _LOGGER.debug("Modbus client closed successfully")
        except Exception as e:
            _LOGGER.warning("Error closing Modbus client: %s", e)
        finally:
            self.client = None

    async def async_reconnect(self) -> bool:
        """Reconnect to the Modbus TCP server by closing and re-opening the connection."""
        async with self._request_lock:
            _LOGGER.info("Reconnecting to Modbus server at %s:%s", self.host, self.port)

            try:
                await self.async_close()
            except Exception as e:
                _LOGGER.debug("Error closing Modbus client during reconnect: %s", e)

            try:
                connected = await self.async_connect()
            except Exception as e:
                _LOGGER.warning(
                    "Exception while reconnecting to Modbus server at %s:%s: %s",
                    self.host,
                    self.port,
                    e,
                )
                return False

            if connected:
                _LOGGER.info("Reconnected to Modbus server at %s:%s", self.host, self.port)
            else:
                _LOGGER.warning("Reconnect failed to Modbus server at %s:%s", self.host, self.port)

            return connected

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
            # Guard against client being None (closed during unload)
            client_connected = False
            try:
                client_connected = bool(self.client and getattr(self.client, "connected", False))
            except Exception:
                client_connected = False

            if not client_connected:
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
                result = None
                # Serialize Modbus requests to avoid overlapping frames and transaction id mismatches
                async with self._request_lock:
                    try:
                        # Try multiple kwarg names for different pymodbus versions
                        read_method = getattr(self.client, "read_holding_registers")
                        for unit_kw in ("device_id", "unit", "slave"):
                            try:
                                result = await read_method(address=register, count=count, **{unit_kw: self.unit_id})
                                break
                            except TypeError:
                                result = None
                                continue
                    finally:
                        # Short spacing after each request to give the device time
                        try:
                            await asyncio.sleep(self.message_wait_sec)
                        except asyncio.CancelledError:
                            raise

                if result is None:
                    _LOGGER.error(
                        "No response object returned for register %d (0x%04X) on attempt %d",
                        register,
                        register,
                        attempt + 1,
                    )
                elif getattr(result, "isError", lambda: False)():
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
                        "Requesting register %d (0x%04X) from '%s' for sensor '%s' (type: %s, count: %s)",
                        register,
                        register,
                        sensor_key or 'unknown',
                        self.host,
                        data_type,
                        count,
                    )
                    _LOGGER.debug("Received data from '%s' for register %d (0x%04X): %s", self.host, register, register, regs)

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

            except asyncio.CancelledError:
                # Allow cancellation to propagate during Home Assistant shutdown
                raise
            except Exception as e:
                # If the underlying cause is a CancelledError (pymodbus wraps it),
                # propagate it so shutdown is not logged as an error.
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

        if not (0 <= value <= 0xFFFF):
            _LOGGER.error(
                "Invalid value for write: %d. Must be 0-65535.",
                value,
            )
            return False

        attempt = 0
        while attempt < max_retries:
            # Check client connection
            client_connected = False
            try:
                client_connected = bool(
                    self.client and getattr(self.client, "connected", False)
                )
            except Exception:
                client_connected = False

            if not client_connected:
                _LOGGER.warning(
                    "Modbus client not connected, attempting reconnect before write to register %d (0x%04X)",
                    register,
                    register,
                )
                connected = await self.async_connect()
                if not connected:
                    _LOGGER.error(
                        "Reconnect failed, skipping write to register %d (0x%04X)",
                        register,
                        register,
                    )
                    return False

            # Additional safety check
            if self.client is None:
                _LOGGER.error("Modbus Client became None unexpectedly")
                return False

            try:
                _LOGGER.debug(
                    "Writing to register %d (0x%04X), value=%d (0x%04X), attempt=%d",
                    register,
                    register,
                    value,
                    value,
                    attempt + 1,
                )

                result = None
                async with self._request_lock:
                    try:
                        # Try multiple kwarg names for compatibility
                        for unit_kw in ("device_id", "unit", "slave"):
                            try:
                                result = await self.client.write_register(
                                    address=register, value=value, **{unit_kw: self.unit_id}
                                )
                                break
                            except TypeError:
                                result = None
                                continue
                    finally:
                        # Spacing after write
                        try:
                            await asyncio.sleep(self.message_wait_sec)
                        except asyncio.CancelledError:
                            raise

                # Check result
                if result is None:
                    _LOGGER.warning(
                        "No response from write to register %d (0x%04X) on attempt %d",
                        register,
                        register,
                        attempt + 1,
                    )
                elif getattr(result, "isError", lambda: False)():
                    _LOGGER.warning(
                        "Modbus write error at register %d (0x%04X) on attempt %d",
                        register,
                        register,
                        attempt + 1,
                    )
                else:
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