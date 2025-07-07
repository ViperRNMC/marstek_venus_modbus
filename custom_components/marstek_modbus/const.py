DOMAIN = "marstek_modbus"

DEFAULT_HOST = "192.168.1.100"
DEFAULT_PORT = 502

SCAN_INTERVAL = 10

SENSOR_DEFINITIONS = [
    {
        "name": "Battery SOC",
        "address": 32104,
        "scale": 1,
        "unit": "%",
        "device_class": None,
        "state_class": "measurement",
        "key": "battery_soc",
        "data_type": "uint16",
        "precision": 1
    },    
    {
        "name": "Battery Voltage",
        "address": 32100,
        "scale": 0.01,
        "unit": "V",
        "device_class": "voltage",
        "state_class": "measurement",
        "key": "battery_voltage",
        "data_type": "uint16",
        "precision": 1
    },
    {
        "name": "Battery Current",
        "address": 32101,
        "scale": 0.01,
        "unit": "A",
        "device_class": "current",
        "state_class": "measurement",
        "key": "battery_current",
        "data_type": "int16",
        "precision": 1
    },
    {
        "name": "Battery Power",
        "address": 32102,
        "scale": 1,
        "unit": "W",
        "device_class": "power",
        "state_class": "measurement",
        "key": "battery_power",
        "data_type": "int32",
        "precision": 1
    },
    {
        "name": "Battery Temperature",
        "address": 35000,
        "scale": 0.1,
        "unit": "°C",
        "device_class": "temperature",
        "state_class": "measurement",
        "key": "battery_temperature",
        "data_type": "int16",
        "precision": 2
    },
    {
        "name": "Battery AC Voltage",
        "address": 32200,
        "scale": 0.1,
        "unit": "V",
        "device_class": "voltage",
        "state_class": "measurement",
        "key": "ac_voltage",
        "data_type": "uint16",
        "precision": 1
    },
    {
        "name": "Battery AC Current",
        "address": 32201,
        "scale": 0.01,
        "unit": "A",
        "device_class": "current",
        "state_class": "measurement",
        "key": "ac_current",
        "data_type": "int16",
        "precision": 1
    },
    {
        "name": "Battery AC Power",
        "address": 32202,
        "scale": 1,
        "unit": "W",
        "device_class": "power",
        "state_class": "measurement",
        "key": "ac_power",
        "data_type": "int32",
        "precision": 0
    },
    {
        "name": "Battery AC Frequency",
        "address": 32204,
        "scale": 0.01,
        "unit": "Hz",
        "device_class": "frequency",
        "state_class": "measurement",
        "key": "ac_frequency",
        "data_type": "int32",
        "precision": 2
    },





    {
        "name": "Total Charging Energy",
        "address": 33000,
        "scale": 0.01,
        "unit": "kWh",
        "device_class": "energy",
        "state_class": "total_increasing",
        "key": "total_charging_energy",
        "data_type": "uint32",
        "precision": 2
    },
    {
        "name": "Total Discharging Energy",
        "address": 33002,
        "scale": 0.01,
        "unit": "kWh",
        "device_class": "energy",
        "state_class": "total_increasing",
        "key": "total_discharging_energy",
        "data_type": "uint32",
        "precision": 2
    },    




    {
        "name": "Inverter State",
        "address": 35100,
        "scale": 1,
        "unit": None,
        "device_class": None,
        "state_class": "measurement",
        "key": "inverter_state",
        "data_type": "uint16",
        "precision": 0
        # "states": {
        #     0: "Sleep",
        #     1: "Standby",
        #     2: "Charge",
        #     3: "Discharge",
        #     4: "Backup Mode",
        #     5: "OTA Upgrade"
        # }
    }
]

SWITCH_DEFINITIONS = [
    {
        "name": "RS485 Control Mode",
        "address": 42000,
        "command_on": 21930,  # 0x55AA in decimal
        "command_off": 21947,  # 0x55BB in decimal
        "write_type": "holding",
        "key": "rs485_control_mode"
    },    
    {
        "name": "Force Charge Mode",
        "address": 42010,
        "command_on": 1,
        "command_off": 0,
        "write_type": "holding",
        "key": "force_charge_mode"
    },
    {
        "name": "Force Discharge Mode",
        "address": 42010,
        "command_on": 2,
        "command_off": 0,
        "write_type": "holding",
        "key": "force_discharge_mode"
    }
]