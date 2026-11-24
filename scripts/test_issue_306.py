"""Read and optionally exercise the control registers involved in issue 306."""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from modbus_connection import ModbusTcpParams
from modbus_connection.pymodbus import ModbusConnection


READ_FIELDS = {
    "rs485_control_mode": 42000,
    "force_mode": 42010,
    "charge_power": 42020,
    "discharge_power": 42021,
    "user_work_mode": 43000,
}

WRITE_SEQUENCE = (
    (42010, 3, "force mode: standby"),
    (42020, 0, "charge power: 0"),
    (42021, 0, "discharge power: 0"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect or exercise Marstek register behavior from issue 306",
    )
    parser.add_argument("host", help="Battery IP address")
    parser.add_argument("--port", type=int, default=502)
    parser.add_argument("--unit", type=int, default=1)
    parser.add_argument("--execute", action="store_true", help="Write the test sequence")
    parser.add_argument("--delay", type=float, default=3.5, help="Readback delay in seconds")
    parser.add_argument("--debug-log", type=Path, help="Write timestamped Modbus debug logs")
    return parser.parse_args()


async def read_registers(unit, label: str) -> None:
    print(f"\n{label}")
    for name, address in READ_FIELDS.items():
        try:
            result = await unit.read(address=address, count=1)
            print(f"  {name:20} 0x{address:X} ({address}) = {result[0]}")
        except Exception as exc:
            print(f"  {name:20} 0x{address:X} ({address}) = ERROR: {exc}")


def configure_logging(log_path: Path | None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_path is not None:
        handlers.append(logging.FileHandler(log_path, encoding="utf-8"))

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=handlers,
    )
    logging.getLogger("tmodbus").setLevel(logging.DEBUG)
    logging.getLogger("modbus_connection").setLevel(logging.DEBUG)


async def main() -> None:
    args = parse_args()
    configure_logging(args.debug_log)
    connection = ModbusConnection(
        ModbusTcpParams(host=args.host, port=args.port),
        timeout=10,
    )
    unit = connection.for_unit(args.unit)
    await connection.connect()
    try:
        await read_registers(unit, "Before")
        if not args.execute:
            print("\nRead-only mode. Use --execute to write the register sequence.")
            return

        print("\nWriting sequence")
        for address, value, description in WRITE_SEQUENCE:
            await unit.write_register(address=address, value=value)
            print(f"  {description}: write 0x{address:X} = {value}")

        await asyncio.sleep(args.delay)
        await read_registers(unit, "Readback")
    finally:
        await connection.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
