# Marstek Venus Battery - Home Assistant Integration

[![GitHub Release](https://img.shields.io/github/v/release/ViperRNMC/marstek_venus_modbus)](https://github.com/ViperRNMC/marstek_venus_modbus/releases)
[![GitHub Issues](https://img.shields.io/github/issues/ViperRNMC/marstek_venus_modbus)](https://github.com/ViperRNMC/marstek_venus_modbus/issues)
[![Downloads](https://img.shields.io/github/downloads/ViperRNMC/marstek_venus_modbus/total)](https://github.com/ViperRNMC/marstek_venus_modbus/releases)

This is a custom HACS-compatible integration for the Marstek Venus E home battery system, using **Modbus TCP** via an **RS485-to-WiFi gateway**. No YAML required. The integration provides sensors, switches and number controls to monitor and manage the battery directly from Home Assistant.


### 🧩 Requirements

- A configured **Modbus RTU to Modbus TCP bridge** connected to the battery's RS485 port
- The IP address, port of the Modbus TCP (usually port 502) and Unit ID (also called Slave ID).
- Home Assistant Core 2025.9 or later
- HACS installed


### 🔧 Features

- Native Modbus TCP polling via `pymodbus`
- Polling is handled centrally via the DataUpdateCoordinator with dynamic intervals per entity type
- Configurable scan intervals via the integration options UI
- Dependency entities are always polled, even if the related entity is disabled
- Fully asynchronous operation for optimal performance and responsiveness
- Sensors for voltage, current, SOC, power, energy, and fault/alarm status (combined bits)
- Switches for force charge/discharge control
- Adjustable charge/discharge power (0–2500W)
- Entities grouped under a device in Home Assistant
- Select entity support for multi-state control (e.g., force mode)
- Select entity for control modes (e.g., force mode, grid standard)
- Backup mode control and charge/discharge to SOC included
- Includes calculated sensors: round-trip efficiency (total/monthly) and stored energy
- Reset button to allow manual reset of the battery management system via Home Assistant
- Some advanced sensors are disabled by default to keep the UI clean
- UI-based configuration (Config Flow)
- Fully local, no cloud required


## 🚀 Installation

1. Add this repository to HACS **Integrations → Custom repositories**
[![Add repository to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=ViperRNMC&repository=marstek_venus_modbus&category=integration)
2. Install the “Marstek Venus Modbus” integration
3. Restart Home Assistant
4. Add the integration via **Settings → Devices & Services**
[![Open your Home Assistant instance and show the integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=marstek_modbus)  
5. Enter the connection details:
   - IP address of your Modbus TCP gateway
   - Port (default: 502)
   - Unit ID / Slave ID (default: 1, valid range: 1-255)
   - Device version (v1/v2 or v3)


## ⚙️ Configuration

### Polling Intervals

The integration uses intelligent polling with configurable intervals per entity type to balance responsiveness and network load.

**Configurable via Options UI:**
- **High priority** (default: 5 seconds) - Critical sensors like power, voltage, current, SOC
- **Medium priority** (default: 30 seconds) - Temperature sensors, state sensors
- **Low priority** (default: 60 seconds) - Energy totals, efficiency calculations
- **Very low priority** (default: 300 seconds) - Device information, firmware versions


## ✅ Tested Devices for Modbus TCP

The Marstek Venus Modbus integration has been tested with the following hardware:
- Elfin EW11 WiFi to RS485 Converter
- PUSR DR134 Modbus Gateway
- Waveshare RS485 to RJ45 Ethernet Converter
- M5Stack RS485 + Atom S3 Lite [#25](https://github.com/ViperRNMC/marstek_venus_modbus/issues/25)
- A/D/E-v3 with ethernet cable (no adapter required) [#46](https://github.com/ViperRNMC/marstek_venus_modbus/issues/46#issuecomment-3631312782) [#106](https://github.com/ViperRNMC/marstek_venus_modbus/issues/106)


## ⚠️ Known Issues / Bugs

- **User Work Mode (AI Optimized) not reflected correctly**  
  Setting `User Work Mode` to `2 (Trade Mode)` in Home Assistant may not correctly show the updated state.  
  The Marstek app shows the correct mode, but Home Assistant may continue to display the previous state due to a discrepancy in the Modbus register response.  
  This is a known issue with the current Modbus firmware and integration handling.


## 📘 Modbus Registers Used

Register definitions live in `custom_components/marstek_modbus/registers/`.

Below is a per-key table showing descriptive fields and the register defined in each YAML file. Columns `Type`, `Bytes`, `Scale` and `Unit` are taken from the YAML definitions when present.

| Key / Name                        | Description                                | Type    | Bytes | Scale  | Unit | a     | d     | e_v12 | e_v3 |
|:----------------------------------|:-------------------------------------------|:--------|:-----:|:------:|:----:|:-----:|:-----:|:------:|:-----:|
| device_name                       | Device name (string)                       | char    | 20   | -      | -    | 31000 | 31000 | 31000 | 31000 |
| sn_code                           | Device serial / SN code                    | char    | 20   | -      | -    |       |       | 31200 |       |
| software_version                  | Device software version                    | uint16  | 2    | 0.01   | -    |       |       | 31100 |       |
| bms_version                       | BMS firmware version                       | uint16  | 2    | -      | -    | 30204 | 30204 | 31102 | 30204 |
| vms_version                       | VMS firmware version                       | uint16  | 2    | -      | -    | 30202 | 30202 |       | 30202 |
| ems_version                       | EMS firmware version (special formatting)  | uint16  | 2    | 1      | -    | 30200 | 30200 | 31101 | 30200 |
| mac_address                       | MAC address                                | char    | 12   | -      | -    | 30304 | 30304 | 30402 | 30304 |
| comm_module_firmware              | Communication module firmware              | char    | 12   | -      | -    | 30350 | 30350 | 30800 | 30350 |
| wifi_signal_strength              | WiFi RSSI                                  | uint16  | 2    | -1     | dBm  | 30303 | 30303 | 30303 | 30303 |
| bluetooth_status                  | Bluetooth connectivity/status              | uint16  | 2    | -      | -    | 30301 | 30301 | 30301 | 30301 |
| wifi_status (binary)              | WiFi connected (0/1)                       | uint16  | 2    | 1      | -    | 30300 | 30300 | 30300 | 30300 |
| cloud_status (binary)             | Cloud connected (0/1)                      | uint16  | 2    | 1      | -    | 30302 | 30302 | 30302 | 30302 |
| battery_soc                       | State of charge                            | uint16  | 2    | 0.1/1  | %    | 34002 | 34002 | 32104 | 34002 |
| battery_total_energy              | Total stored energy                        | uint16  | 2    | 0.001  | kWh  | 32105 | 32105 | 32105 | 32105 |
| battery_voltage                   | Battery voltage                            | uint16  | 2    | 0.01   | V    | 30100 | 30100 | 32100 | 30100 |
| battery_current                   | Battery current                            | int16   | 2    | 0.1/0.01| A   | 30101 | 30101 | 32101 | 30101 |
| battery_power                     | Battery power                              | int16/32| 2/4  | 1      | W    | 30001 | 30001 | 32102 | 30001 |
| total_charging_energy             | Total charging energy                      | uint32  | 4    | 0.01   | kWh  | 33000 | 33000 | 33000 | 33000 |
| total_discharging_energy          | Total discharging energy                   | int32   | 4    | 0.01   | kWh  | 33002 | 33002 | 33002 | 33002 |
| total_daily_charging_energy       | Total daily charging energy                | uint32  | 4    | 0.01   | kWh  | 33004 | 33004 | 33004 | 33004 |
| total_daily_discharging_energy    | Total daily discharging energy             | int32   | 4    | 0.01   | kWh  | 33006 | 33006 | 33006 | 33006 |
| total_monthly_charging_energy     | Total monthly charging energy              | uint32  | 4    | 0.01   | kWh  | 33008 | 33008 | 33008 | 33008 |
| total_monthly_discharging_energy  | Total monthly discharging energy           | int32   | 4    | 0.01   | kWh  | 33010 | 33010 | 33010 | 33010 |
| ac_voltage                        | AC voltage                                 | uint16  | 2    | 0.1    | V    | 32200 | 32200 | 32200 | 32200 |
| ac_current                        | AC current                                 | int16   | 2    | 0.004/0.01| A  | 37004 | 37004 | 32201 | 37004 |
| ac_power                          | AC power                                   | int16/32| 2/4  | 1      | W    | 30006 | 30006 | 32202 | 30006 |
| ac_frequency                      | AC frequency                               | int16   | 2    | 0.1/0.01| Hz  | 32204 | 32204 | 32204 | 32204 |
| ac_offgrid_voltage                | AC offgrid voltage                         | uint16  | 2    | 0.1    | V    | 32300 | 32300 | 32300 | 32300 |
| ac_offgrid_current                | AC offgrid current                         | uint16  | 2    | 0.01   | A    | 32301 | 32301 | 32301 | 32301 |
| ac_offgrid_power                  | AC offgrid power                           | int32   | 4    | 1      | W    | 32302 | 32302 | 32302 | 32302 |
| internal_temperature              | Internal device temperature                | int16   | 2    | 0.1    | °C   | 35000 | 35000 | 35000 | 35000 |
| internal_mos1_temperature         | MOS1 internal temperature                  | int16   | 2    | 0.1    | °C   | 35001 | 35001 | 35001 | 35001 |
| internal_mos2_temperature         | MOS2 internal temperature                  | int16   | 2    | 0.1    | °C   | 35002 | 35002 | 35002 | 35002 |
| max_cell_temperature              | Max cell temperature                       | int16   | 2    | 0.1/1  | °C   | 35010 | 35010 | 35010 | 35010 |
| max_cell_voltage                  | Max cell voltage                           | uint16  | 2    | 0.001  | V    | 37007 | 37007 | 37007 | 37007 |
| min_cell_voltage                  | Min cell voltage                           | uint16  | 2    | 0.001  | V    | 37008 | 37008 | 37008 | 37008 |
| cell_1_voltage                    | Cell 1 voltage                             | int16   | 2    | 0.001  | V    | 34018 | 34018 |       | 34018 |
| cell_2_voltage                    | Cell 2 voltage                             | int16   | 2    | 0.001  | V    | 34019 | 34019 |       | 34019 |
| cell_3_voltage                    | Cell 3 voltage                             | int16   | 2    | 0.001  | V    | 34020 | 34020 |       | 34020 |
| cell_4_voltage                    | Cell 4 voltage                             | int16   | 2    | 0.001  | V    | 34021 | 34021 |       | 34021 |
| cell_5_voltage                    | Cell 5 voltage                             | int16   | 2    | 0.001  | V    | 34022 | 34022 |       | 34022 |
| cell_6_voltage                    | Cell 6 voltage                             | int16   | 2    | 0.001  | V    | 34023 | 34023 |       | 34023 |
| cell_7_voltage                    | Cell 7 voltage                             | int16   | 2    | 0.001  | V    | 34024 | 34024 |       | 34024 |
| cell_8_voltage                    | Cell 8 voltage                             | int16   | 2    | 0.001  | V    | 34025 | 34025 |       | 34025 |
| cell_9_voltage                    | Cell 9 voltage                             | int16   | 2    | 0.001  | V    | 34026 | 34026 |       | 34026 |
| cell_10_voltage                   | Cell 10 voltage                            | int16   | 2    | 0.001  | V    | 34027 | 34027 |       | 34027 |
| cell_11_voltage                   | Cell 11 voltage                            | int16   | 2    | 0.001  | V    | 34028 | 34028 |       | 34028 |
| cell_12_voltage                   | Cell 12 voltage                            | int16   | 2    | 0.001  | V    | 34029 | 34029 |       | 34029 |
| cell_13_voltage                   | Cell 13 voltage                            | int16   | 2    | 0.001  | V    | 34030 | 34030 |       | 34030 |
| cell_14_voltage                   | Cell 14 voltage                            | int16   | 2    | 0.001  | V    |       | 34031 |       | 34031 |
| cell_15_voltage                   | Cell 15 voltage                            | int16   | 2    | 0.001  | V    |       | 34032 |       | 34032 |
| cell_16_voltage                   | Cell 16 voltage                            | int16   | 2    | 0.001  | V    |       | 34033 |       | 34033 |
| mppt1_voltage                     | MPPT1 array voltage                        | uint16  | 2    | 0.1    | V    | 30020 | 30020 |       |       |
| mppt1_current                     | MPPT1 array current                        | uint16  | 2    | 0.1    | A    | 30024 | 30024 |       |       |
| mppt1_power                       | MPPT1 array power                          | uint16  | 2    | 0.1    | W    | 30037 | 30037 |       |       |
| mppt2_voltage                     | MPPT2 array voltage                        | uint16  | 2    | 0.1    | V    | 30021 | 30021 |       |       |
| mppt2_current                     | MPPT2 array current                        | uint16  | 2    | 0.1    | A    | 30025 | 30025 |       |       |
| mppt2_power                       | MPPT2 array power                          | uint16  | 2    | 0.1    | W    | 30038 | 30038 |       |       |
| mppt3_voltage                     | MPPT3 array voltage                        | uint16  | 2    | 0.1    | V    | 30022 | 30022 |       |       |
| mppt3_current                     | MPPT3 array current                        | uint16  | 2    | 0.1    | A    | 30026 | 30026 |       |       |
| mppt3_power                       | MPPT3 array power                          | uint16  | 2    | 0.1    | W    | 30039 | 30039 |       |       |
| mppt4_voltage                     | MPPT4 array voltage                        | uint16  | 2    | 0.1    | V    | 30023 | 30023 |       |       |
| mppt4_current                     | MPPT4 array current                        | uint16  | 2    | 0.1    | A    | 30027 | 30027 |       |       |
| mppt4_power                       | MPPT4 array power                          | uint16  | 2    | 0.1    | W    | 30040 | 30040 |       |       |
| inverter_state                    | Inverter / device state                    | uint16  | 2    | 1      | -    | 35100 | 35100 | 35100 | 35100 |
| fault_status                      | Fault status bits                          | uint64  | 8    | -      | -    |       |       | 36100 |       |
| alarm_status                      | Alarm status bits                          | uint32  | 4    | -      | -    |       |       | 36000 |       |
| modbus_address                    | Modbus slave/unit id                       | uint16  | 2    | -      | -    | 41100 | 41100 | 41100 | 41100 |
| rs485_control_mode (switch)       | RS485 control mode (write commands)        | uint16  | 2    | -      | -    | 42000 | 42000 | 42000 | 42000 |
| backup_function (switch)          | Backup function control                    | uint16  | 2    | -      | -    | 41200 | 41200 | 41200 | 41200 |
| force_mode (select)               | Force mode (None/Charge/Discharge)         | uint16  | 2    | -      | -    | 42010 | 42010 | 42010 | 42010 |
| user_work_mode (select)           | User Work Mode (manual/anti_feed/trade)    | uint16  | 2    | -      | -    | 43000 | 43000 | 43000 | 43000 |
| discharge_limit_mode (binary)     | Discharge limit mode (diagnostic)          | uint16  | 2    | -      | -    |       |       | 41010 |       |
| grid_standard (select)            | Grid standard / region selection           | uint16  | 2    | -      | -    |       |       | 44100 |       |
| charge_to_soc (number)            | Charge/discharge to SOC (0-100%)           | uint16  | 2    | 1      | %    | 42011 | 42011 | 42011 | 42011 |
| set_charge_power (number)         | Forcible charge power setpoint             | uint16  | 2    | -      | W    | 42020 | 42020 | 42020 | 42020 |
| set_discharge_power (number)      | Forcible discharge power setpoint          | uint16  | 2    | -      | W    | 42021 | 42021 | 42021 | 42021 |
| max_charge_power (number)         | Max allowed charge power                   | uint16  | 2    | -      | W    | 44002 | 44002 | 44002 | 44002 |
| max_discharge_power (number)      | Max allowed discharge power                | uint16  | 2    | -      | W    | 44003 | 44003 | 44003 | 44003 |
| charging_cutoff_capacity (number) | Charging cutoff (percentage)               | uint16  | 2    | 0.1    | %    |       |       | 44000 |       |
| discharging_cutoff_capacity       | Discharging cutoff (percentage)            | uint16  | 2    | 0.1    | %    |       |       | 44001 |       |
| reset_device (button)             | Reset device command                       | uint16  | 2    | -      | -    | 41000 | 41000 | 41000 | 41000 |
| factory_reset (button)            | Factory reset command                      | uint16  | 2    | -      | -    | 41001 | 41001 | 41001 | 41001 |
| schedule_1_days                  | Schedule 1 days (bitmask)                   | bit      | 2    | -      | -    | 43100 | 43100 | 43100 | 43100 |
| schedule_1_start                 | Schedule 1 start (HHMM)                     | uint     | 2    | -      | min  | 43101 | 43101 | 43101 | 43101 |
| schedule_1_end                   | Schedule 1 end (HHMM)                       | uint     | 2    | -      | min  | 43102 | 43102 | 43102 | 43102 |
| schedule_1_mode                  | Schedule 1 mode (numeric)                   | int16    | 2    | -      | W    | 43103 | 43103 | 43103 | 43103 |
| schedule_1_enabled               | Schedule 1 enabled (0/1)                    | uint     | 2    | -      | -    | 43104 | 43104 | 43104 | 43104 |
| schedule_2_days                  | Schedule 2 days (bitmask)                   | bit      | 2    | -      | -    | 43105 | 43105 | 43105 | 43105 |
| schedule_2_start                 | Schedule 2 start (HHMM)                     | uint     | 2    | -      | min  | 43106 | 43106 | 43106 | 43106 |
| schedule_2_end                   | Schedule 2 end (HHMM)                       | uint     | 2    | -      | min  | 43107 | 43107 | 43107 | 43107 |
| schedule_2_mode                  | Schedule 2 mode (numeric)                   | int16    | 2    | -      | W    | 43108 | 43108 | 43108 | 43108 |
| schedule_2_enabled               | Schedule 2 enabled (0/1)                    | uint     | 2    | -      | -    | 43109 | 43109 | 43109 | 43109 |
| schedule_3_days                  | Schedule 3 days (bitmask)                   | bit      | 2    | -      | -    | 43110 | 43110 | 43110 | 43110 |
| schedule_3_start                 | Schedule 3 start (HHMM)                     | uint     | 2    | -      | min  | 43111 | 43111 | 43111 | 43111 |
| schedule_3_end                   | Schedule 3 end (HHMM)                       | uint     | 2    | -      | min  | 43112 | 43112 | 43112 | 43112 |
| schedule_3_mode                  | Schedule 3 mode (numeric)                   | int16    | 2    | -      | W    | 43113 | 43113 | 43113 | 43113 |
| schedule_3_enabled               | Schedule 3 enabled (0/1)                    | uint     | 2    | -      | -    | 43114 | 43114 | 43114 | 43114 |
| schedule_4_days                  | Schedule 4 days (bitmask)                   | bit      | 2    | -      | -    | 43115 | 43115 | 43115 | 43115 |
| schedule_4_start                 | Schedule 4 start (HHMM)                     | uint     | 2    | -      | min  | 43116 | 43116 | 43116 | 43116 |
| schedule_4_end                   | Schedule 4 end (HHMM)                       | uint     | 2    | -      | min  | 43117 | 43117 | 43117 | 43117 |
| schedule_4_mode                  | Schedule 4 mode (numeric)                   | int16    | 2    | -      | W    | 43118 | 43118 | 43118 | 43118 |
| schedule_4_enabled               | Schedule 4 enabled (0/1)                    | uint     | 2    | -      | -    | 43119 | 43119 | 43119 | 43119 |
| schedule_5_days                  | Schedule 5 days (bitmask)                   | bit      | 2    | -      | -    | 43120 | 43120 | 43120 | 43120 |
| schedule_5_start                 | Schedule 5 start (HHMM)                     | uint     | 2    | -      | min  | 43121 | 43121 | 43121 | 43121 |
| schedule_5_end                   | Schedule 5 end (HHMM)                       | uint     | 2    | -      | min  | 43122 | 43122 | 43122 | 43122 |
| schedule_5_mode                  | Schedule 5 mode (numeric)                   | int16    | 2    | -      | W    | 43123 | 43123 | 43123 | 43123 |
| schedule_5_enabled               | Schedule 5 enabled (0/1)                    | uint     | 2    | -      | -    | 43124 | 43124 | 43124 | 43124 |
| schedule_6_days                  | Schedule 6 days (bitmask)                   | bit      | 2    | -      | -    | 43125 | 43125 | 43125 | 43125 |
| schedule_6_start                 | Schedule 6 start (HHMM)                     | uint     | 2    | -      | min  | 43126 | 43126 | 43126 | 43126 |
| schedule_6_end                   | Schedule 6 end (HHMM)                       | uint     | 2    | -      | min  | 43127 | 43127 | 43127 | 43127 |
| schedule_6_mode                  | Schedule 6 mode (numeric)                   | int16    | 2    | -      | W    | 43128 | 43128 | 43128 | 43128 |
| schedule_6_enabled               | Schedule 6 enabled (0/1)                    | uint     | 2    | -      | -    | 43129 | 43129 | 43129 | 43129 |
| round_trip_efficiency_total       | Round-trip efficiency (total charge/discharge energies) | calculated | - | - | % |  |  |  |  |
| round_trip_efficiency_monthly     | Round-trip efficiency (monthly charge/discharge) | calculated | - | - | % |  |  |  |  |
| conversion_efficiency             | Conversion efficiency (battery ↔ AC)       | calculated | - | - | % |  |  |  |  |
| stored_energy                     | Stored battery energy (SOC × capacity)     | calculated | - | - | kWh |  |  |  |  |

_Notes:_
- Columns `a`, `d`, `e_v12` and `e_v3` correspond to the YAML files under `custom_components/marstek_modbus/registers/`.
- `Bytes` shows the typical byte size for the key (each Modbus register = 2 bytes).
- Blank cells mean that YAML does not define that key (or the value is calculated and has no direct Modbus register).
- The `rs485_control_mode` switch (register 42000) uses write commands (command_on=21930, command_off=21947) to trigger RS485 control operations; use with caution.
- For access to registers in the 42000–42999 range, the battery must be set to RS485 control mode.
- Schedule Time format: `start` and `end` are entered as HHMM 24-hour integers (for example `0830` = 08:30). Use values within the valid range shown in the YAML for each device; ensure `start` is earlier than `end` for a single active period.
- Schedule Day selection: the underlying `schedule_*_days` register uses a bitmask to represent multiple days, but the integration currently exposes it as a single-select option in Home Assistant. Due to this limitation you cannot select multiple days from the integration UI.
- Schedule Mode values: `schedule_*_mode` accepts the following ranges:
  - `-1` = Self consumption mode
  - `100` to `2500` = Charge power (W)
  - `-100` to `-2500` = Discharge power (W)
