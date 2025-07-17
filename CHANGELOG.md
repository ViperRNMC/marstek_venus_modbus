# Changelog

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