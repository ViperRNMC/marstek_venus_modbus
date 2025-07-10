"""
Helper module for Modbus TCP communication using pymodbus.
Provides an abstraction for reading and writing registers from a Marstek Venus battery system.
"""

from pymodbus.client import ModbusTcpClient
from typing import Optional

# Set up logging for debugging purposes
import logging
_LOGGER = logging.getLogger(__name__)


class MarstekModbusClient:
    """
    Wrapper class for pymodbus' ModbusTcpClient with helper methods
    to read/write registers and interpret common data types.
    """

    def __init__(self, host, port, message_wait_ms=35, timeout=5):
        # Initialize the Modbus client with host, port, and configurable timeouts
        self.client = ModbusTcpClient(
            host=host,
            port=port,
            timeout=timeout,  # timeout in seconds
        )
        self.client.message_wait_milliseconds = message_wait_ms
        self.unit_id = 1  # Default Modbus slave address (can be made configurable)

    def connect(self):
        """
        Establish connection to the Modbus server.
        Returns True if successful, False otherwise.
        """
        return self.client.connect()

    def close(self):
        """
        Closes the Modbus TCP connection.
        """
        self.client.close()

    def read_register(self, register, data_type="uint16", count=None, bit_index=None):
        """
        Reads one or more registers and interprets them as the specified data type.

        Args:
            register (int): Register address to read.
            data_type (str): Data type to interpret (e.g. 'int16', 'int32', 'char', 'bit').
            count (int): Number of registers to read (required for 'char' and 'int32').
            bit_index (int): Bit index to read (required for 'bit').

        Returns:
            Interpreted value: int, str, bool, or None on error.
        """
        if count is None:
            count = 2 if data_type in ["int32", "uint32"] else 1

        try:
            result = self.client.read_holding_registers(address=register, count=count, slave=self.unit_id)
            if result.isError():
                _LOGGER.error("Modbus read error at 0x%04X", register)
                return None
            regs = result.registers
        except Exception as e:
            _LOGGER.exception("Exception during modbus read: %s", e)
            return None

        if data_type == "int16":
            val = regs[0]
            return val - 0x10000 if val >= 0x8000 else val

        elif data_type == "uint16":
            return regs[0]

        elif data_type == "int32":
            val = (regs[0] << 16) | regs[1]  # big endian
            return val - 0x100000000 if val >= 0x80000000 else val

        elif data_type == "uint32":
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

    def write_register(self, register, value):
        """
        Writes a single value to a Modbus holding register.

        Args:
            register (int): Register address to write to.
            value (int): Value to write.

        Returns:
            bool: True if write was successful, False otherwise.
        """
        try:
            result = self.client.write_register(address=register, value=value, slave=self.unit_id)
            return not result.isError()
        except Exception as e:
            _LOGGER.exception("Exception during modbus write: %s", e)
            return False