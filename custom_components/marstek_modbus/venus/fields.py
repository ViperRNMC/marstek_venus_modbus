"""Register fields for encodings the stock field helpers do not cover."""

from __future__ import annotations

from modbus_connection.decode import decode_string
from modbus_connection.model import RegisterField, StringField


class AsciiField(StringField):
    """An ASCII string that ends at its first NUL byte.

    The device can leave stale bytes after the terminator, so stripping
    trailing NULs is not enough.
    """

    def decode(self, words: list[int], scale_exponent: int | None = None) -> str:
        return decode_string(words).split("\x00", 1)[0]


class MacField(RegisterField[str]):
    """A MAC address, as ``AA:BB:CC:DD:EE:FF``.

    The device stores it as 12 ASCII hex digits. Bytes that are not such a
    string are formatted as raw octets.
    """

    def decode(self, words: list[int], scale_exponent: int | None = None) -> str:
        raw = b"".join(word.to_bytes(2, "big") for word in words).split(b"\x00", 1)[0]
        try:
            text = raw.decode("ascii").strip()
        except UnicodeDecodeError:
            text = ""
        if len(text) == 12 and all(char in "0123456789abcdefABCDEF" for char in text):
            return ":".join(
                text[index : index + 2].upper() for index in range(0, 12, 2)
            )
        return ":".join(f"{byte:02X}" for byte in raw)


def ascii_string(address: int, length: int) -> AsciiField:
    """An ASCII string over ``length`` registers, ending at its first NUL."""
    return AsciiField(address, count=length)


def mac_address(address: int) -> MacField:
    """A MAC address over six registers."""
    return MacField(address, count=6)
