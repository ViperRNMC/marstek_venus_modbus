from pymodbus.client import ModbusTcpClient
import logging

_LOGGER = logging.getLogger(__name__)

class MarstekModbusClient:
    def __init__(self, host, port):
        self.client = ModbusTcpClient(host=host, port=port)
        self.unit_id = 1

    def connect(self):
        return self.client.connect()

    def close(self):
        self.client.close()

    def read_register(self, address, count=1):
        try:
            result = self.client.read_holding_registers(address=address, count=count, slave=self.unit_id)
            if result.isError():
                _LOGGER.error("Modbus read error at 0x%04X", address)
                return None
            return result.registers
        except Exception as e:
            _LOGGER.exception("Exception during modbus read: %s", e)
            return None

    def write_register(self, address, value):
        try:
            result = self.client.write_register(address=address, value=value, slave=self.unit_id)
            return not result.isError()
        except Exception as e:
            _LOGGER.exception("Exception during modbus write: %s", e)
            return False