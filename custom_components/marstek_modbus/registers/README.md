# Register Research Notes

This document captures findings from register scanning and testing across Marstek device models.
Registers documented here were investigated but not included in the integration (no added value,
unclear semantics, or duplicate/inferior alternatives exist).

Add a section per model following the structure below.

---

## Venus E Gen 3.0 (e_v3.yaml)

Hardware tested: Marstek Venus E v3, firmware V148.

| Register | Notes |
|----------|-------|
| 30000 | Alternative for `battery_voltage` (32100). scale 0.1 V, uint16. Less precise. |
| 30002 | Alternative for `internal_temperature` (35000). scale 0.1 °C, int16. Duplicate. |
| 30003 | Alternative for `internal_mos1_temperature` (35001). scale 0.1 °C, int16. Duplicate. |
| 30004 | Alternative for `inverter_voltage` (32200). scale 0.1 V, uint16. Duplicate. |
| 30005 | Alternative for `ac_offgrid_voltage` (32300). scale 0.1 V, uint16. Duplicate. |
| 30007 | Alternative for `ac_offgrid_power` (32302). scale 1 W, int16. Duplicate. |
| 30100 | Alternative for `battery_voltage` (32100). scale 0.01 V, uint16. Inferior. |
| 30102 | Alternative for `max_cell_voltage` (37007). scale 0.001 V. Inferior. |
| 30103 | Alternative for `min_cell_voltage` (37008). scale 0.001 V. Inferior. |
| 30104 | Alternative for `max_cell_temperature` (35010). scale 0.01 °C, uint16. Inferior. |
| 30105 | Alternative for `min_cell_temperature` (35011). scale 0.01 °C, uint16. Inferior. |
| 30107 | Alternative for `bms_temperature_1` (34011). scale 0.1 °C, int16. Duplicate. |
| 30108 | Alternative for `bms_temperature_2` (34012). scale 0.1 °C, int16. Duplicate. |
| 30210 | Alternative for `bms_code` (34004). uint16. Duplicate. |
| 30212 | Unknown. Constant value 5 in all tested modes. Static across mode changes. Adjacent to 30210. Possibly another sub-version or config index. |
| 32101 | Unknown. Internal EMS state indicator — does not map to `inverter_state` or `user_work_mode`. Small integers (4–42) = active app-controlled charge/discharge; 0x9999 (39321) = app idle/bypass; 0x9967 (39271) = RS485-controlled discharge. Sentinel values may encode control source. Observed values: UPS 300W=4, Manual 450W=7, Manual 2500W=42, Manual 2500W (SoC>=95%)=30, Manual 500W=8, Manual 300W=4, Bypass/Stop=39321, RS485 discharge 2500W=39271. |
| 32104 | Alternative for `battery_soc_int` (37005). scale 1 %, uint16. Duplicate. |
| 32106 | Possibly alternative for 35111. Unclear semantics. |
| 32107 | Possibly alternative for 35112. Unclear semantics. |
| 32108 | Alternative for `max_cell_temperature` (35010). scale 0.1 °C. Inferior. |
| 32109 | Alternative for `bms_online` (37000). uint16. Duplicate. |
| 32301 | Alternative for `ac_offgrid_current` (calculated). Returns same value as 32300 (voltage, not current) — unusable for current measurement. `ac_offgrid_current` is calculated as `ac_offgrid_power / ac_offgrid_voltage` instead. |
| 34000 | Alternative for `battery_voltage` (32100). scale 0.01 V, uint16. Inferior. |
| 34001 | Alternative for `battery_current` (30101). scale 0.1 A, int16. Duplicate. |
| 34005 | Alternative for `max_cell_voltage` (37007). scale 0.001 V. Inferior. |
| 34006 | Alternative for `min_cell_voltage` (37008). scale 0.001 V. Inferior. |
| 34010 | Alternative for `bms_version` (30204). uint16. Inferior. |
| 34017 | Alternative for `bms_status` (30106). uint16. Duplicate. |
| 35110 | Unknown. Value 576 in active charge modes (UPS/Manual), 0 in initial scan. Did not change between different charge modes. Purpose unclear. |
| 35111 | Unknown. Changes with mode AND SoC — not a live power setpoint (constant within a snapshot while actual power varied). Observed: Charge (all)=330, Discharge 2500W SoC~46%=1000, Discharge 2500W SoC~25%=330. 330x0.1=33A, possibly a BMS current limit. |
| 35112 | Unknown. Same behaviour as 35111. Observed: Charge (all)=1000, Discharge 2500W SoC~46%=750, Discharge 2500W SoC~25%=500. |
| 36000 | Unknown. uint32, count 2. Possibly alarm bitmask. Individual bit semantics unknown. |
| 36100 | Unknown. uint32, count 2. Possibly fault bitmask. Individual bit semantics unknown. |
| 37006 | Alternative for `cell_temperature_1` (34013). scale 0.1 °C, int16. Duplicate. |
| 37012 | Alternative for `bms_version` (30204). uint16. Inferior. |
| 37016 | Alternative for `ac_voltage` (36103). scale 0.1 V, uint16. Duplicate. |
| 45603 | Unknown. Value 9985 (0x2701). Adjacent to 45604/45605. Possibly WiFi channel, frequency, or AP info. Not confirmed. |
| 45604 | Unknown. Value 20599 (0x5077). Adjacent to 45603/45605. Possibly WiFi channel, frequency, or AP info. Not confirmed. |
| 45605 | Unknown. Constant value 74 in V148 scan. Adjacent to 45603/45604. |
| 47400 | Unknown. Value 43707 (0xAABB) in V148 scan. Alternating-nibble sentinel — same class as 0x9999, likely "not configured" / undefined. |
