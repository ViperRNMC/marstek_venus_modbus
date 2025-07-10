# TODO List


- [ ] Fix icon display in HACS
- [ ] Improve HACS documentation and visibility
- [ ] Provide a Lovelace dashboard example in the integration folder
- [ ] fix reset button
- [ ] Implement bulk reading of grouped registers to improve polling efficiency
- [ ] Add dynamic polling interval adjustments per sensor group
- [ ] Refactor sensor update logic to handle bulk register reads
- [ ] Improve error handling and retry logic for Modbus communication
- [ ] Add support for user-configurable message wait time and timeout in UI
- [ ] Provide Lovelace dashboard example with key sensors and controls
- [ ] Add tests for new sensor types and bit flag decoding logic
- [x] Enable only key sensors (e.g. voltage, SOC, current, mode) by default
- [x] add fault / alarm sensor
- [x] add Round-Trip Efficiency
- [x] poll interval for single sensor
- [x] add sensors
- [x] Add all relevant Modbus sensors with `enabled_by_default: false`
- [x] Fix for int32/char handling 
- [x] Use device_name as device name in Home Assistant
- [x] Update documentation