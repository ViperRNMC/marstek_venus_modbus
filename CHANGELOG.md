# Changelog

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