# IDM Module – English Guide

## Prerequisites

- Ensure your Klipper installation is using **Python 3.6 or newer**.
- You should already have some familiarity with configuring Klipper. This guide assumes you can troubleshoot and modify configs independently.
- For best accuracy, install the sensor coil so that its top surface lies **just below** the bottom surface of your heated bed.

> **Warning**: Do **not** execute any commands or steps that are **not** explicitly described in this tutorial—especially `G28`. Only perform the steps mentioned.

---

## 1. Install the Supporting Scripts

In your home directory (e.g. `~/`), clone the IDM toolkit:

```bash
git clone https://gitee.com/NBTP/IDM.git
```

Make the install script executable:

```bash
chmod +x IDM/install.sh
```

If you're unsure whether your `pip` index is configured properly (or if pip itself is unfamiliar to you), it's recommended to use a mirror before installing:

```bash
~/klippy-env/bin/pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
```

Then run the install:

```bash
IDM/install.sh
```

---

## 2. Add IDM Configuration to `printer.cfg`

Below is a sample snippet you can add to your Klipper `printer.cfg`:

```ini
[mcu idm]
serial:
# canbus_uuid:

[idm]
mcu: idm
# speed: 40.       # Z probing dive speed
# lift_speed: 5    # Z probing lift speed
backlash_comp: 0.5
x_offset: 0.0
y_offset: 21.1
trigger_distance: 2.0
trigger_dive_threshold: 1.5
trigger_hysteresis: 0.006
cal_nozzle_z: 0.1
cal_floor: 0.1
cal_ceil: 5.0
cal_speed: 1.0
cal_move_speed: 10.0
default_model_name: default
mesh_main_direction: x
# mesh_overscan: -1
mesh_cluster_size: 1
mesh_runs: 1
calibration_method: touch
sensor: idm
scanner_touch_max_temp: 180
scanner_touch_speed: 5
scanner_touch_accel: 100
```

- Adjust `x_offset` and `y_offset` so that during calibration, the nozzle moves to the same XY position the coil originally occupied.
- If your IDM uses **CAN** instead of serial, replace `serial:` with `canbus_uuid:`. You can find the UUID with:

  ```bash
  ~/klippy-env/bin/python ~/klipper/lib/canboot/flash_can.py -q
  ```

- After specifying `canbus_uuid`, remove the `serial:` line.

Also add:

```ini
[force_move]
enable_force_move: true
```

If you previously used a `[probe]` module (e.g., `klicky`), remove it. Then in your Z-axis stepper config, change:

```ini
endstop_pin:
```

to:

```ini
endstop_pin: probe:z_virtual_endstop
```

You will also need:

```ini
[safe_z_home]
home_xy_position: <your X center>,<your Y center>
z_hop: 10
```

If `safe_z_home` or `homing_override` is already present, you may omit this.

---

## 3. Calibrate IDM

After restarting Klipper, **do not home Z immediately**—only home X and Y:

```gcode
G28 X Y
```

Then move the toolhead to the bed center and run:

```gcode
SET_KINEMATIC_POSITION Z=80
```

Lower the nozzle carefully to the bed (or use a sheet of paper to gauge a proper gap), and then:

```gcode
SET_KINEMATIC_POSITION Z=0
```

Finally, run:

```gcode
idm_calibrate
```

When prompted, use the control to reduce offset (e.g. `‑0.1`) to position the nozzle just touching, then confirm. The calibration sequence will run automatically.

If after calibration and rebooting your printer fails to zero Z or shows “no model,” that indicates a config formatting error—please correct your syntax.

---

## 4. Optional Macros & Advanced Configurations

### High-Power AC Heated Beds

For beds drawing over ~500 W, interference during scanning is common. Override the bed mesh macro to reduce interference:

```ini
[gcode_macro BED_MESH_CALIBRATE]
rename_existing: _BED_MESH_CALIBRATE
gcode:
  {% set TARGET_TEMP = printer.heater_bed.target %}
  M140 S0
  _BED_MESH_CALIBRATE {rawparams}
  M140 S{TARGET_TEMP}
```

### Multi-Z / Gantry Machines

For 4‑Z systems (like Voron 2.4):

```ini
[gcode_macro QUAD_GANTRY_LEVEL]
rename_existing: _QUAD_GANTRY_LEVEL
gcode:
  SAVE_GCODE_STATE NAME=STATE_QGL
  BED_MESH_CLEAR
  {% if not printer.quad_gantry_level.applied %}
    _QUAD_GANTRY_LEVEL horizontal_move_z=10 retry_tolerance=1
  {% endif %}
  _QUAD_GANTRY_LEVEL horizontal_move_z=2
  G28 Z
  RESTORE_GCODE_STATE NAME=STATE_QGL
```

For 3-fork Z systems (Voron Trident, etc.):

```ini
[gcode_macro Z_TILT_ADJUST]
rename_existing: _Z_TILT_ADJUST
gcode:
  SAVE_GCODE_STATE NAME=STATE_Z_TILT
  BED_MESH_CLEAR
  {% if not printer.z_tilt.applied %}
    _Z_TILT_ADJUST horizontal_move_z=10 retry_tolerance=1
  {% endif %}
  _Z_TILT_ADJUST horizontal_move_z=2
  G28 Z
  RESTORE_GCODE_STATE NAME=STATE_Z_TILT
```

---

## 5. Optional Accelerometer Support

If your hardware includes accelerometer support (e.g. LIS2DW or ADXL345), place this configuration **after** the `[idm]` section:

```ini
[lis2dw]
cs_pin: idm:PA3
spi_bus: spi1

[resonance_tester]
accel_chip: lis2dw
probe_points:
  125, 125, 20
```

---

## 6. Saving and Switching Calibration Profiles

To save your current calibration under a name:

```gcode
IDM_MODEL_SAVE NAME=<your_model_name>
```

Later, you can load it with:

```gcode
IDM_MODEL_SELECT NAME=<your_model_name>
```

List all saved models with:

```gcode
IDM_MODEL_LIST
```

Delete a named calibration with:

```gcode
IDM_MODEL_REMOVE NAME=<your_model_name>
```

---

## 7. Alternative Z-Probing Methods

- For touch (bed contact) based Z offset, see: *IDM touch update document*
- For tap-based or endstop-based Z probing, see: *second probe document*
- There is an option to use Klipper’s official eddy-current (capacitive) sensor support, but it’s **not recommended**—refer to the official config for details.