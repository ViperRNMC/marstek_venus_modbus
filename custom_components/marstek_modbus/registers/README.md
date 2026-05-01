# Register Research Notes — Venus E v3 (e_v3.yaml)

This document captures findings from register scanning and testing on the Marstek Venus E v3.
Registers documented here were investigated but not included in the integration (no added value,
unclear semantics, or duplicate/inferior alternatives exist).

Hardware tested: Marstek Venus E v3, firmware V148 (updated 2026-04-12).

---

## Alternative registers (_alt)

These registers were found during scanning and compared against the registers used in e_v3.yaml.
The primary register is preferred; _alt variants are kept here for reference.

| Name | Register | Notes |
|------|----------|-------|
| `battery_voltage_alt` | 34000 | scale 0.01 V, uint16. Inferior to primary (32100). |
| `battery_voltage_alt_2` | 30100 | scale 0.01 V, uint16. Inferior to primary (32100). |
| `battery_voltage_rounded` | 30000 | scale 0.1 V, uint16. Less precise than primary. |
| `battery_current_alt` | 34001 | scale 0.1 A, int16. Duplicate of primary (30101). |
| `internal_temperature_alt` | 30002 | scale 0.1 °C, int16. Duplicate of primary (35000). |
| `internal_mos1_temperature_alt` | 30003 | scale 0.1 °C, int16. Duplicate of primary (35001). |
| `inverter_voltage_alt` | 30004 | scale 0.1 V, uint16. Duplicate of primary (32200). |
| `ac_offgrid_voltage_alt` (1) | 30005 | scale 0.1 V, uint16. Duplicate of primary (32300). |
| `ac_offgrid_voltage_alt` (2) | 32301 | Returns same value as 32300 (duplicate voltage, not current). Used in app as `ac_offgrid_current` but incorrect — calculated sensor used instead. |
| `ac_offgrid_power_alt` | 30007 | scale 1 W, int16. Duplicate of primary (32302). |
| `battery_soc_int_alt` | 32104 | scale 1 %, uint16. Duplicate of primary (37005). |
| `max_cell_voltage_alt` | 30102 | scale 0.001 V. Inferior to primary (37007). |
| `min_cell_voltage_alt` | 30103 | scale 0.001 V. Inferior to primary (37008). |
| `max_cell_temperature_alt` | 32108 | scale 0.1 °C. Inferior to primary (35010). |
| `max_cell_temperature_alt_2` | 30104 | scale 0.01 °C, uint16. Inferior to primary (35010). |
| `min_cell_temperature_alt_2` | 30105 | scale 0.01 °C, uint16. Inferior to primary (35011). |
| `max_cell_voltage_alt_2` | 34005 | scale 0.001 V. Inferior to primary (37007). |
| `min_cell_voltage_alt_2` | 34006 | scale 0.001 V. Inferior to primary (37008). |
| `bms_temperature_1_alt` | 30107 | scale 0.1 °C, int16. Duplicate of primary (34011). |
| `bms_temperature_2_alt` | 30108 | scale 0.1 °C, int16. Duplicate of primary (34012). |
| `cell_temperature_1_alt` | 37006 | scale 0.1 °C, int16. Duplicate of primary (34013). |
| `bms_version_alt` | 34010 | uint16. Inferior to primary (30204). |
| `bms_version_alt_2` | 37012 | uint16. Inferior to primary (30204). |
| `ac_voltage_alt` | 37016 | scale 0.1 V, uint16. Duplicate of primary (36103). |
| `setpoint_a_alt` | 32106 | Unclear semantics. See `setpoint_a` section below. |
| `setpoint_b_alt` | 32107 | Unclear semantics. See `setpoint_b` section below. |
| `bms_online_alt` | 32109 | uint16. Duplicate of primary (37000). |
| `bms_code_alt` | 30210 | uint16. After firmware V148: single-digit value (3). Duplicate of primary (34004). |
| `bms_status_alt` | 34017 | uint16. Duplicate of primary (30106). |

---

## Unknown registers

These registers were found during a full register scan (V148, 2026-04-12) but their semantics
are unclear or only partially understood.

### `unknown_32101` (register 32101)

Internal EMS state indicator. Does **not** map to `inverter_state` or `user_work_mode`.

Measurements (2026-04-11):

| Mode | Value |
|------|-------|
| UPS mode 300W charge | 4 |
| Manual schedule 450W | 7 |
| Eigenverbrauch / Bypass / Stop | 39321 (0x9999) |
| Manual schedule 2500W | 42 |
| Manual 2500W (SoC 95%+) | 30 |
| Manual 500W | 8 |
| Manual 300W | 4 |
| Manual Stop (Bypass) | 39321 (0x9999) |
| RS485 discharge 2500W | 39271 (0x9967) |

Pattern: small integers (4–42) = active app-controlled charge/discharge; 0x9999 = app idle/bypass;
0x9967 = RS485-controlled discharge. Sentinel values may encode control source.

### `unknown_35110` (register 35110)

Value 576 in active charge modes (UPS/Manual), was 0 in initial scan.
Did not change between different charge modes (2026-04-11). Purpose unclear.

### `unknown_47400` (register 47400)

Value 43707 (0xAABB) in V148 scan (2026-04-12). Alternating-nibble sentinel — same class as
0x9999, likely "not configured" / undefined.

### `unknown_45605` (register 45605)

Value 74 in V148 scan (2026-04-12), constant. Adjacent to unknown_45603/45604.

### `unknown_45603` / `unknown_45604` (registers 45603, 45604)

Values: 45603 = 9985 (0x2701), 45604 = 20599 (0x5077). Adjacent to unknown_45605.
Possibly WiFi channel, frequency, or AP info. Not confirmed.

### `unknown_30212` (register 30212)

Constant value 5 in all tested modes (2026-04-11). Static across mode changes.
Adjacent to bms_code_alt (30210). Possibly another sub-version or config index.

---

## `setpoint_a` / `setpoint_b` (registers 35111, 35112)

Values change with mode AND SoC (2026-04-11). NOT a live EMS setpoint (constant within a
snapshot while actual power varied 262W–1742W). Values appear SoC-dependent, not only
mode-dependent.

| Mode | setpoint_a | setpoint_b |
|------|-----------|-----------|
| Charge (UPS/Manual, all sessions) | 330 | 1000 |
| Discharge 2500W (RS485, SoC ~46%) | 1000 | 750 |
| Discharge 2500W (RS485, SoC ~25%) | 330 | 500 |

330 × 0.1 = 33A — plausible BMS current limit; may encode per-mode, SoC-adjusted limits.
The observed 1800W cap during charge was BMS CV-phase (chemistry), not this register.

---

## `bms_status` (register 30106)

Semantics currently unknown.
- Pre-firmware-update (2026-04-11): values observed as 2052 / 2564.
- After firmware update to V148 (2026-04-12): single-digit value (e.g. 4).

Do not map to state labels until validated.

---

## `bms_code` (register 34004)

Semantics currently unknown.
- After firmware update to V148 (2026-04-12): single-digit value (3).

Do not map to state labels until validated.

---

## `ac_offgrid_current` — why it is calculated, not register-based

Register 32301 was expected to return AC off-grid current in amperes (as implied by the CSV
register map). Testing confirmed it returns a duplicate of the voltage value from register 32300.
The register is therefore unusable for current measurement.

`ac_offgrid_current` is instead calculated as `ac_offgrid_power / ac_offgrid_voltage`.
