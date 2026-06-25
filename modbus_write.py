#!/usr/bin/env python3
"""
Simple script to write Modbus registers.
Usage: python3 modbus_write.py <host> <register> <value> [data_type] [port]
Examples:
  python3 modbus_write.py 10.0.0.1 36000 1 uint16
  python3 modbus_write.py 10.0.0.1 36010 hello char
  python3 modbus_write.py 10.0.0.1 32102 123456789 uint32
"""

import sys
import asyncio

try:
    from pymodbus.client.tcp import AsyncModbusTcpClient
except ImportError:
    print("Missing dependency: pymodbus is not installed.")
    print("Install it with: pip install pymodbus")
    print("Or install all dependencies: pip install -r requirements.txt")
    sys.exit(1)


def prepare_registers(value_str: str, data_type: str):
    """Convert a value string into a list of 16-bit register integers."""
    if data_type == "char":
        s = value_str
        # Ensure even length
        if len(s) % 2 == 1:
            s += "\x00"
        regs = []
        for i in range(0, len(s), 2):
            high = ord(s[i])
            low = ord(s[i+1])
            regs.append((high << 8) | low)
        return regs

    if data_type in ("uint16", "int16"):
        v = int(value_str)
        if data_type == "uint16":
            v &= 0xFFFF
        else:
            if v < 0:
                v = (v + (1 << 16)) & 0xFFFF
        return [v]

    if data_type in ("uint32", "int32"):
        v = int(value_str)
        if data_type == "uint32":
            v &= 0xFFFFFFFF
        else:
            if v < 0:
                v = (v + (1 << 32)) & 0xFFFFFFFF
        hi = (v >> 16) & 0xFFFF
        lo = v & 0xFFFF
        return [hi, lo]

    # default: treat as uint16
    return [int(value_str) & 0xFFFF]


async def write_register(host: str, port: int, register: int, registers):
    client = AsyncModbusTcpClient(host=host, port=port, timeout=3)
    try:
        print(f"Connecting to {host}:{port}...")
        connected = await client.connect()
        if not connected:
            print("Failed to connect!")
            return

        print(f"Connected! Writing to register {register} -> {registers}")

        # Use write_registers for both single and multiple writes
        result = await client.write_registers(address=register, values=registers)

        if hasattr(result, "isError") and result.isError():
            print(f"Error writing registers: {result}")
        else:
            print("Write successful.")

    finally:
        client.close()
        print("Connection closed.")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python3 modbus_write.py <host> <register> <value> [data_type] [port]")
        print("Examples:")
        print("  python3 modbus_write.py 10.0.0.1 36000 1 uint16")
        print("  python3 modbus_write.py 10.0.0.1 36010 hello char")
        sys.exit(1)

    host = sys.argv[1]
    register = int(sys.argv[2])
    value = sys.argv[3]
    data_type = sys.argv[4] if len(sys.argv) > 4 else "uint16"
    port = int(sys.argv[5]) if len(sys.argv) > 5 else 502

    regs = prepare_registers(value, data_type)
    asyncio.run(write_register(host, port, register, regs))
