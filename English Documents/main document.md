# IDM Sensor Installation and Configuration Tutorial

#### Before starting, please ensure you are using Klipper with Python 3.6 or above

### Using this module requires some knowledge and experience with Klipper. Please ensure you have the ability to modify configurations yourself before using.

To ensure accuracy, please install the sensor with the coil board's top surface as low as possible below the bottom of the heater block.

## Do NOT do anything not mentioned in this tutorial (especially G28). Do everything that IS mentioned.

---

## Installation

Execute the following git command in the user directory to download the accompanying script:

```bash
git clone https://gitee.com/NBTP/IDM.git 
```

If you are unsure whether your pip source is a domestic mirror or can download new libraries properly, or if you don't know what pip is at all, it is recommended to set pip to the Tsinghua mirror with the following command:

```bash
~/klippy-env/bin/pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
```

Then execute the following command to install:

```bash
IDM/install.sh
```

---

## Configuration Example (New Version with [scanner])

Below is the configuration example to add to Klipper's printer.cfg:

```ini
[mcu idm]
serial:
#canbus_uuid:
# Path to the serial port for the idm device. Typically has the form
# /dev/serial/by-id/usb-idm_idm_...

[scanner]
mcu:idm
# MCU of IDM
speed: 40.
#   Z probing dive speed.
lift_speed: 5.
#   Z probing lift speed.
backlash_comp: 0.5
#   Backlash compensation distance for removing Z backlash before measuring
#   the sensor response.
x_offset: 0.
#   X offset of idm from the nozzle.
y_offset: 21.1
#   Y offset of idm from the nozzle.
trigger_distance: 2.
#   idm trigger distance for homing.
trigger_dive_threshold: 1.5
#   Threshold for range vs dive mode probing. Beyond `trigger_distance +
#   trigger_dive_threshold` a dive will be used.
trigger_hysteresis: 0.006
#   Hysteresis on trigger threshold for untriggering, as a percentage of the
#   trigger threshold.
cal_nozzle_z: 0.1
#   Expected nozzle offset after completing manual Z offset calibration.
cal_floor: 0.1
#   Minimum z bound on sensor response measurement.
cal_ceil:5.
#   Maximum z bound on sensor response measurement.
cal_speed: 1.0
#   Speed while measuring response curve.
cal_move_speed: 10.
#   Speed while moving to position for response curve measurement.
default_model_name: default
#   Name of default idm model to load.
mesh_main_direction: x
#   Primary travel direction during mesh measurement.
#mesh_overscan: -1
#   Distance to use for direction changes at mesh line ends. Omit this setting
#   and a default will be calculated from line spacing and available travel.
mesh_cluster_size: 1
#   Radius of mesh grid point clusters.
mesh_runs: 1
#   Number of passes to make during mesh scan.
calibration_method: touch
#   Calibration method setting. If you don't want to use touch, you can set it
#   to scan for backward compatibility with older version commands.
sensor: idm
#   Sensor name, set to idm or cartographer
scanner_touch_max_temp:180
#   Nozzle will cool down to this temperature when touching the bed
scanner_touch_speed:5
#   Descent speed when using touch, not recommended to set too high
scanner_touch_accel:100
#   Acceleration when using touch
```

---

## Configuration Example (Old Version with [idm])

Below is the old version configuration example before IDM TOUCH update:

```ini
[mcu idm]
serial:
#canbus_uuid:
# Path to the serial port for the idm device. Typically has the form
# /dev/serial/by-id/usb-idm_idm_...

[idm]
mcu:idm
# MCU of IDM
speed: 40.
#   Z probing dive speed.
lift_speed: 5.
#   Z probing lift speed.
backlash_comp: 0.5
#   Backlash compensation distance for removing Z backlash before measuring
#   the sensor response.
x_offset: 0.
#   X offset of idm from the nozzle.
y_offset: 21.1
#   Y offset of idm from the nozzle.
trigger_distance: 2.
#   idm trigger distance for homing.
trigger_dive_threshold: 1.5
#   Threshold for range vs dive mode probing. Beyond `trigger_distance +
#   trigger_dive_threshold` a dive will be used.
trigger_hysteresis: 0.006
#   Hysteresis on trigger threshold for untriggering, as a percentage of the
#   trigger threshold.
cal_nozzle_z: 0.1
#   Expected nozzle offset after completing manual Z offset calibration.
cal_floor: 0.1
#   Minimum z bound on sensor response measurement.
cal_ceil:5.
#   Maximum z bound on sensor response measurement.
cal_speed: 1.0
#   Speed while measuring response curve.
cal_move_speed: 10.
#   Speed while moving to position for response curve measurement.
default_model_name: default
#   Name of default idm model to load.
mesh_main_direction: x
#   Primary travel direction during mesh measurement.
#mesh_overscan: -1
#   Distance to use for direction changes at mesh line ends. Omit this setting
#   and a default will be calculated from line spacing and available travel.
mesh_cluster_size: 1
#   Radius of mesh grid
mesh_runs: 1
#   Number of passes to make during mesh scan.
```

---

## Important Notes

Please adjust the X and Y offset values in the configuration. Ensure that during calibration, the printhead will move the coil to the XY position where the nozzle was previously located.

Add this configuration to printer.cfg and change the serial to your IDM's serial port number. Query command:

```bash
ls /dev/serial/by-id/*
```

### For CAN Version

For CAN version, use canbus_uuid instead of serial. Use the following command to search for the CAN UUID:

**CanBoot (legacy):**

```bash
~/klippy-env/bin/python ~/klipper/lib/canboot/flash_can.py -q
```

**Katapult (new):**

```bash
~/klippy-env/bin/python ~/klipper/lib/katapult/flashtool.py -i can0 -q
```

**Note:** After filling in the UUID, please delete the `serial:` line.

---

## Required Configuration

Add the following to your configuration (you'll have problems if you don't):

```ini
[force_move]
enable_force_move: true
```

---

## Additional Steps

1. **Remove the [probe] module**
2. If you previously used Klicky, remember to remove its related script references
3. Change the Z endstop (`endstop_pin:` in `stepper_z`) to `probe:z_virtual_endstop`
4. Set up safe_z_home:

```ini
[safe_z_home]
home_xy_position: <your_x_center_coordinate>,<your_y_center_coordinate>
z_hop: 10
```

If you have already configured `safe_z_home` or `homing_override`, you can skip this step.

#### Remember to set up [bed_mesh] or you will get errors

---

## Calibration Procedure

After restarting:

1. Home X and Y only (`G28 X Y`, do NOT home Z)
2. Move the printhead to the center of the bed
3. Enter `SET_KINEMATIC_POSITION z=80`
4. Now you can control Z movement. Lower the nozzle to touch the platform (you can also use A4 paper to ensure proper gap)
5. Enter `SET_KINEMATIC_POSITION z=0` (note: this is different from the previous command)

Then execute the command `idm_calibrate` to calibrate. 

> If you are using touch mode (i.e., you set `calibration_method: touch`), please use `idm_touch method=manual` to calibrate.

In the offset control dialog that pops up, lower the printhead until the nozzle touches the bed, then click -0.1 offset and confirm. Calibration will proceed automatically.

**If after calibration and restart you cannot home and get a "no model" error, then your configuration file's auto-generated configuration format is incorrect. Please fix the format.**

---

## For High-Power AC Heated Beds (500W+)

It's best to configure the following macro to avoid bed interference with bed scanning:

```ini
[gcode_macro BED_MESH_CALIBRATE]
rename_existing: _BED_MESH_CALIBRATE
gcode:
    {% set TARGET_TEMP = printer.heater_bed.target %}
    M140 S0
    _BED_MESH_CALIBRATE {rawparams}
    M140 S{TARGET_TEMP}
```

---

## For VORON 2.4 (4Z Machines)

Add the following configuration:

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
    RESTORE_GCODE_STATE NAME=STATE_QGL
```

---

## For VORON Trident (3Z Machines)

Add the following configuration:

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
    RESTORE_GCODE_STATE NAME=STATE_Z_TILT
```

---

## Moonraker Auto-Update Configuration

It is recommended to add the following to moonraker.conf for automatic IDM script updates:

```ini
[update_manager idm]
type: git_repo
channel: dev
path: ~/IDM
origin: https://gitee.com/NBTP/IDM.git
env: ~/klippy-env/bin/python
requirements: requirements.txt
install_script: install.sh
is_system_service: False
managed_services: klipper
info_tags:
  desc=idm
```

---

## Accelerometer Configuration

### For lis2dw (Square Chip)

For versions with lis2dw accelerometer, add the following to enable the accelerometer.

> **Note:** The accelerometer configuration must be placed AFTER the IDM configuration.

```ini
[lis2dw]
cs_pin: idm:PA3
spi_bus: spi1

[resonance_tester]
accel_chip: lis2dw
probe_points:
    125, 125, 20  # Set this to the coordinates where the printhead will be during resonance measurement
```

### For adxl345 (Rectangular Chip)

If your accelerometer uses adxl345, use the following configuration.

> **Note:** The accelerometer configuration must be placed AFTER the IDM configuration.

```ini
[adxl345]
cs_pin: idm:PA3
spi_bus: spi1

[resonance_tester]
accel_chip: adxl345
probe_points:
    125, 125, 20  # Set this to the coordinates where the printhead will be during resonance measurement
```

After configuration, use `shaper_calibrate` for resonance measurement.

---

## Final Steps

After preparation is complete, adjust the Z offset before printing. The Z offset is saved in the `model_offset` variable.

### Before adjusting Z offset, please ensure bed mesh is disabled and mechanical leveling is complete. After leveling, home again.

#### It is recommended to use [[axis_twist_compensation]] to ensure bed mesh effectiveness

---

## Managing Multiple Calibration Results (for Different PEI Plates)

| Action | Command |
|--------|---------|
| Save current calibration | `IDM_MODEL_SAVE NAME=<your_desired_name>` |
| Load saved calibration | `IDM_MODEL_SELECT NAME=<your_previously_set_name>` |
| List all calibrations | `IDM_MODEL_LIST` |
| Delete a calibration | `IDM_MODEL_REMOVE NAME=<name_to_delete>` |

---

## Additional References

- For automatic Z offset using touch, refer to "idm touch usage tutorial.md"
- For automatic Z offset using tap or standard endstop, refer to "automatic z offset.md"
- If you want to use Klipper's official eddy current sensor functionality (not recommended), refer to "Klipper official eddy current sensor configuration.md"
