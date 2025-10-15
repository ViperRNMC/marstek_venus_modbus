# Changelog

## [2025.9.5.b1] - 2025-09-23

### Added
- Config flow now asks for device version (v1/v2 or v3) during setup so the integration can load the correct register map at runtime.
- Per-version register modules: `registers_v12.py` (v1/v2) and `registers_v3.py` (v3). The integration selects the right definitions based on the chosen version.

### Changed
- General integration constants remain in `const.py`; large per-version register/entity definitions were moved to separate files for maintainability.

### Security / Stability
- Modbus client handling: added defensive checks and client recreation to avoid NoneType errors during unload/reconnect and to prevent request cancellations from leaving the coordinator in a bad state.

### Notes
- `registers_v3.py` was generated from a CSV mapping but the registers are UNTESTED for v3 devices. Manual verification on actual hardware is REQUIRED before using v3 definitions in production.
- Efficiency sensor calculations: added guards to skip calculations when denominators are zero or required inputs are missing (prevents division-by-zero errors and noisy tracebacks during shutdown or transient zero-values).

## [2025.9.4] - 2025-09-22

### Added
- Configurable scan intervals (high, medium, low, very_low) through integration options.
- Options flow with translated titles and descriptions.

### Changed
- Coordinator now dynamically adjusts polling interval based on the lowest configured scan interval.

### Fixed
- Corrected calculation of Actual Conversion Efficiency to properly handle charging vs discharging, avoiding efficiencies above 100%.
- Properly handle Modbus client closing when disabling the integration.
- Correctly apply updated polling intervals after options are changed.

## [2025.9.3] - 2025-09-16

### Added
- New `Actual Conversion Efficiency` calculated sensor to display the real-time charging/discharging efficiency as a percentage.  

### Fixed
- Fixed proper closing of Modbus connections when disabling and enabling entities, preventing multiple open sessions.
- Corrected state class for stored energy sensors to match energy device class requirements.
- Corrected calculation of Actual Conversion Efficiency to properly handle charging vs discharging, avoiding efficiencies above 100%.

## [2025.9.2] - 2025-09-07

### Fixed
- Corrected scaling for `Number` entities, ensuring `min`, `max`, and current values reflect the defined scale.
- Updated logging to include scale and unit when values are updated in Home Assistant.

## [2025.9.1] - 2025-09-05

### Fixed
- Switch writing fixed and now implemented with optimistic mode to handle delayed device response.
- Fixed PyModbus 3.x / Python 3.9 compatibility: replaced slave with device_id.

## [2025.9.0] - 2025-09-03

### Added
- Dependency keys registration so required values are always fetched even if disabled in Home Assistant.
- Polling now handled centrally via the DataUpdateCoordinator.
- Dynamic polling intervals based on sensor definitions and dependencies.

### Changed
- Calculated sensors (Round-Trip Efficiency Total, Round-Trip Efficiency Monthly, Stored Energy) with dependency handling
- Improved logging for dependency mapping, calculation, and skipping disabled entities.
- Cleaned up and refactored sensor calculation logic to be reusable and PEP8 compliant.

## [2025.8.1] - 2025-08-12

### Added
- New Min Cell Voltage sensor (register 35043) to monitor minimum battery cell voltage
- New Max Cell Voltage sensor (register 36943) to monitor maximum battery cell voltage
- New Reset Device button (register 41000) to allow resetting the battery management system via Home Assistant

### Changed
- Clean up code and improve overall code quality

## [2025.8.0] - 2025-08-09

### Fixed
- WiFi strength sensor now reports correct negative dBm values
- Corrected cell temperature reading after BMS firmware version 213

## [2025.7.1] - 2025-07-18

### Added
- New WiFi status sensor (register 30300): 0 = Disconnected, 1 = Connected
- New Cloud status sensor (register 30302): 0 = Disconnected, 1 = Connected
- New WiFi signal strength sensor (register 30303), value in dBm

## [2025.7.0] - 2025-07-17

### Added
- Fully asynchronous operation for optimal performance and responsiveness
- Background sensor update functionality temporarily disabled (to be resolved later)
- New `Charge to SOC` select entity  
- New `Discharge Limit Mode` sensor
- New 'Cutoff to SOC' number entities for charge and discharge

### Fixed
- Improved error handling for incorrect count of received bytes during Modbus communication
- Added validation to ensure the returned Modbus register matches the requested address and expected byte length

## [2025.6.4] - 2025-07-10

### Added
- New fault sensor combining grid fault bits from register 36100
- Grid Status sensor with decoded standard options from register 44100
- Support for `scan_interval` per sensor in `SENSOR_DEFINITIONS`
- Support for Modbus connection `timeout` and `message_wait_milliseconds` 
- Background polling for data needed by derived sensors (e.g. SOC, Energy)
- New efficiency sensors: Round-Trip Efficiency (monthly, total) and Stored Energy, calculated from other register values

### Changed
- Improved polling interval resolution using fastest required scan rate

## [2025.6.3] - 2025-07-08

### Added
- Entities now correctly register under a device in Home Assistant
- Select entity replaces Force Charge/Discharge Mode switches (42010)
- Improved error handling with specific Modbus connection error messages
- Universal handling of Modbus types (uint16, int32, char)
- All entity types now support `enabled_by_default` flag

### Fixed
- TypeError when writing to registers (fixed incorrect `register=` argument)
- Translation loading and fallback for config flow error messages

## [2025.6.2] - 2025-07-07
### Added
- `enabled_by_default: false` set for all sensors except key ones (e.g. voltage, current, SOC)
- Example Lovelace dashboard added to the integration folder
- Support for Modbus `int32` and `char` register types

### Changed
- Select, Number, and Switch entities now implement `async_update()` and reflect real device state
- Improved state mapping for sensors using `states` dictionary

### Fixed
- Correct mapping of 'Trade Mode' (value 2) in select register
- All switch and number entities now generate truly unique IDs per integration instance

## [2025.6.1] - 2025-07-07
### Added
- Combined alarm sensor decoding multiple alarm bits into one entity
- Support for `char` type registers with proper string decoding
- Improved sensor state mapping with `states` dictionary

### Fixed
- Fixed sensor registration to avoid duplicate unique IDs
- Corrected `read_register` to properly handle `int32` and `char` types

## [2025.6.0] - 2025-07-06
### Added
- Initial release with basic sensor and switch support
- Support for Modbus int16 and uint16 registers
- Basic configuration and polling

### Changed
- Updated documentation and improved code structure