#!/usr/bin/env python3
"""
Simple script to read Modbus registers and display bits.
Usage: python3 modbus_read.py <host> <register> [count] [data_type]
Examples:
  python3 modbus_read.py 10.0.0.1 36000 2        # Read as uint16
  python3 modbus_read.py 10.0.0.1 31000 10 char  # Read as char
  python3 modbus_read.py 10.0.0.1 32102 2 int32  # Read as int32
"""

import sys
import asyncio
from pymodbus.client.tcp import AsyncModbusTcpClient

# Known register bit descriptions from registers_v12.py
REGISTER_DESCRIPTIONS = {
    # Fault Status (36100-36103)
    36100: {
        0: "Grid Overvoltage",
        1: "Grid Undervoltage",
        2: "Grid Overfrequency",
        3: "Grid Underfrequency",
        4: "Grid Peak Voltage",
        5: "Current Dcover",
        6: "Voltage Dcover",
        16: "BAT Overvoltage",
        17: "BAT Undervoltage",
        18: "BAT Overcurrent",
        19: "BAT low SOC",
        20: "BAT communication failure",
        21: "BMS protect",
        32: "Inverter soft start timeout",
        33: "self-checking failure",
        34: "eeprom failure",
        35: "other system failure",
        48: "Hardware Bus overvoltage",
        49: "Hardware Output overcurrent",
        50: "Hardware trans overcurrent",
        51: "Hardware battery overcurrent",
        52: "Hardware Protection",
        53: "Output Overcurrent",
        54: "High Voltage bus overvoltage",
        55: "High Voltage bus undervoltage",
        56: "Overpower Protection",
        57: "FSM abnormal",
        58: "Overtemperature Protection",
    },
    # Alarm Status (36000-36001)
    36000: {
        0: "PLL Abnormal Restart",
        1: "Overtemperature Limit",
        2: "Low Temperature Limit",
        3: "Fan Abnormal Warning",
        4: "Low Battery SOC Warning",
        5: "Output Overcurrent Warning",
        6: "Abnormal Line Sequence Detection",
        16: "WiFi Abnormal",
        17: "BLE Abnormal",
        18: "Network Abnormal",
        19: "CT Connection Abnormal",
    },
    # Inverter State (35100)
    35100: {
        0: "Sleep",
        1: "Standby",
        2: "Charge",
        3: "Discharge",
        4: "Backup Mode",
        5: "OTA Upgrade",
        6: "Bypass",
    },
}


def convert_value(registers, data_type):
    """Convert register value(s) based on data type."""
    if data_type == "char":
        # Convert registers to string
        chars = []
        for reg in registers:
            high = (reg >> 8) & 0xFF
            low = reg & 0xFF
            if high != 0:
                chars.append(chr(high))
            if low != 0:
                chars.append(chr(low))
        return ''.join(chars).strip('\x00')
    
    elif data_type == "uint16":
        return registers[0]
    
    elif data_type == "int16":
        # Convert to signed
        value = registers[0]
        if value > 32767:
            value -= 65536
        return value
    
    elif data_type == "uint32":
        # Combine two registers (big-endian)
        return (registers[0] << 16) | registers[1]
    
    elif data_type == "int32":
        # Combine two registers (big-endian) and convert to signed
        value = (registers[0] << 16) | registers[1]
        if value > 2147483647:
            value -= 4294967296
        return value
    
    return registers[0]


async def read_register(host: str, port: int, register: int, count: int = 1, data_type: str = "uint16"):
    """Read Modbus holding register and display bits."""
    client = AsyncModbusTcpClient(host=host, port=port, timeout=3)
    
    try:
        print(f"Connecting to {host}:{port}...")
        connected = await client.connect()
        
        if not connected:
            print("Failed to connect!")
            return
        
        print(f"Connected! Reading register {register} (count={count}, type={data_type})...")
        
        # Read holding registers (function code 3)
        result = await client.read_holding_registers(address=register, count=count)
        
        if result.isError():
            print(f"Error reading register: {result}")
            return
        
        print(f"\nRegister(s) starting at {register}:")
        print("-" * 80)
        
        # Try to convert the value
        try:
            converted = convert_value(result.registers, data_type)
            print(f"\nConverted as {data_type}: {converted}")
            if data_type == "char":
                print(f"  String: '{converted}'")
        except Exception as e:
            print(f"\nCould not convert as {data_type}: {e}")
        
        print()
        
        # Check if this register has known bit descriptions
        descriptions = REGISTER_DESCRIPTIONS.get(register, {})
        
        for i, value in enumerate(result.registers):
            reg_addr = register + i
            print(f"Register {reg_addr}: {value} (0x{value:04X})")
            print(f"  Binary: {value:016b}")
            
            # For state registers (single value states like inverter_state)
            if value in descriptions and count == 1:
                print(f"  State: {descriptions[value]}")
            else:
                bits_found = False
                for bit in range(16):
                    if value & (1 << bit):
                        bit_offset = i * 16 + bit
                        description = descriptions.get(bit_offset, None)
                        if description:
                            if not bits_found:
                                print(f"  Bits set:")
                                bits_found = True
                            print(f"    Bit {bit} (offset {bit_offset}): SET - {description}")
        
        # If reading 2 or more registers, show combined value
        if count >= 2:
            combined = 0
            for i, val in enumerate(result.registers):
                combined |= (val << (16 * (count - 1 - i)))
            
            bits = count * 16
            print(f"\nCombined {bits}-bit value: {combined} (0x{combined:0{count*4}X})")
            print(f"  Binary: {combined:0{bits}b}")
            
            bits_found = False
            for bit in range(bits):
                if combined & (1 << bit):
                    description = descriptions.get(bit, None)
                    if description:
                        if not bits_found:
                            print(f"  Bits set in {bits}-bit value:")
                            bits_found = True
                        print(f"    Bit {bit}: SET - {description}")
        
    finally:
        client.close()
        print("\nConnection closed.")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 test_modbus_read.py <host> <register> [count] [data_type]")
        print("Examples:")
        print("  python3 modbus_read.py 10.0.0.1 36000 2")
        print("  python3 modbus_read.py 10.0.0.1 31000 10 char")
        print("  python3 modbus_read.py 10.0.0.1 32102 2 int32")
        print("\nData types: uint16 (default), int16, uint32, int32, char")
        sys.exit(1)
    
    host = sys.argv[1]
    register = int(sys.argv[2])
    count = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    data_type = sys.argv[4] if len(sys.argv) > 4 else "uint16"
    port = 502  # Standard Modbus TCP port
    
    asyncio.run(read_register(host, port, register, count, data_type))