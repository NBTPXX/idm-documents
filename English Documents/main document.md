### Notice
##### First of all:make sure you are using klipper based on python3.6 or above
Using this module requires a certain level of knowledge and experience with Klipper. Ensure that you have the ability to configure and modify it before installation.

To maintain accuracy, install the sensor coil board with its top surface as low as possible below the bottom surface of the heater block.

## Important Instructions
- Follow the tutorial strictly, especially regarding commands like G28. Only perform the mentioned steps.
- Execute the following git command in the user directory to download the accompanying script:
  ```bash
  git clone https://gitee.com/NBTP/IDM.git
  ```
- Run `chmod +x IDM/install.sh` after downloading.
  Then install with:
  ```bash
  IDM/install.sh
  ```

### Configuration Example for printer.cfg
```ini
[idm]
serial:
#canbus_uuid:
# Path to the serial port for the idm device. Typically has the form
# /dev/serial/by-id/usb-idm_idm_...
speed: 40.
# Z probing dive speed.
lift_speed: 5.
# Z probing lift speed.
backlash_comp: 0.5
# Backlash compensation distance for removing Z backlash before measuring
# the sensor response.
x_offset: 0.
# X offset of idm from the nozzle.
y_offset: 21.1
# Y offset of idm from the nozzle.
trigger_distance: 2.
# idm trigger distance for homing.
trigger_dive_threshold: 1.5
# Threshold for range vs dive mode probing. Beyond `trigger_distance +
# trigger_dive_threshold` a dive will be used.
trigger_hysteresis: 0.006
# Hysteresis on trigger threshold for untriggering, as a percentage of the
# trigger threshold.
cal_nozzle_z: 0.1
# Expected nozzle offset after completing manual Z offset calibration.
cal_floor: 0.1
# Minimum z bound on sensor response measurement.
cal_ceil:5.
# Maximum z bound on sensor response measurement.
cal_speed: 1.0
# Speed while measuring response curve.
cal_move_speed: 10.
# Speed while moving to position for response curve measurement.
default_model_name: default
# Name of the default idm model to load.
mesh_main_direction: x
# Primary travel direction during mesh measurement.
#mesh_overscan: -1
# Distance to use for direction changes at mesh line ends. Omit this setting
# and a default will be calculated from line spacing and available travel.
mesh_cluster_size: 1
# Radius of mesh grid point clusters.
mesh_runs: 1
# Number of passes to make during mesh scan.
```

Adjust the x and y direction offsets in the configuration. Ensure that during calibration, the nozzle moves the coils to the original xy position of the nozzle.

Add this configuration to printer.cfg and modify serial to your IDM's serial number. To find the IDM serial, use the command:
```bash
ls /dev/serial/by-id/*
```

### For CAN Version
Replace serial with canbus_uuid.

Use the following command to search for the CAN UUID and fill it in:
```bash
~/klippy-env/bin/python ~/klipper/lib/canboot/flash_can.py -q
```

Note: After adding the UUID, remove serial.

-------------------------------------------------

Include the following in the configuration (necessary for following operations.):
```ini
[force_move]
enable_force_move: true
```

### Remove the [probe] Module
Remove the [probe] module from your configuration.

If you've used Klicky, remove references to its scripts. Modify z limit (after stepper_z's endstop_pin:) to probe:z_virtual_endstop.

Also, set:
```ini
[safe_z_home]
home_xy_position: <your_x_axis_center_coordinate>,<your_y_axis_center_coordinate>
z_hop: 10
```
If you've configured safe_z_home or homing_override, you can skip this step.

#### Don't forget to set up [bed_mesh] to avoid errors.
Omit the zero_reference_position in bed_mesh.

After restarting, home x and y (g28 x y, don't home z), and move the nozzle to the center of the bed. Then enter `SET_KINEMATIC_POSITION z=80.`  
Now, you can control the z-axis movement and bring the nozzle close to the bed (or place an A4 paper for the right gap). Enter `SET_KINEMATIC_POSITION z=0`   
(note that it's different from the previous command).  
Execute `idm_calibrate`. In the offset control box, click -0.1 for offset and confirm. It will automatically calibrate.

If, after calibration, you encounter issues like not zeroing after a restart or reporting "no model,"   
there might be a format error in your configuration file's auto-generated configuration. Correct the format.
#### If you are using high power AC heater pad(over 500W)
you had better add this macro to avoid AC interference  
```
[gcode_macro BED_MESH_CALIBRATE]
rename_existing: _BED_MESH_CALIBRATE
gcode:
    {% set TARGET_TEMP = printer.heater_bed.target %}
    M140 S0
    _BED_MESH_CALIBRATE {rawparams}
    M140 S{TARGET_TEMP}
```
For 4Z machines like VORON2.4, add the following configuration to the file:
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

For 3Z machines like VORON Trident, add the following configuration:
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

It's recommended to add the following configuration to the moonraker.conf file for easy script updates:
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

For versions with a lis2dw accelerometer, add the following to enable it:  
dont put it before the config of `[IDM]`
```ini
[lis2dw]
cs_pin: idm:PA3
spi_bus: spi1

[resonance_tester]
accel_chip: lis2dw
probe_points:
    125, 125, 20  #set your prefered calibrating position
```
For versions with a adxl345 accelerometer, add the following to enable it:  
dont put it before the config of `[IDM]`
```ini
[adxl345]
cs_pin: idm:PA3
spi_bus: spi1

[resonance_tester]
accel_chip: adxl345
probe_points:
    125, 125, 20  #set your prefered calibrating position
Configure and use shaper_calibrate for resonance testing.

Adjust the z offset before printing. The z offset is saved in the model_offset variable.

### Note
Before adjusting the z offset, ensure to disable the bed mesh, complete mechanical leveling, and zero once again.

#### We also recommend using [[axis_twist_compesation]](https://www.klipper3d.org/Config_Reference.html?h=axis#axis_twist_compensation) to ensure the effectiveness of the mesh bed compensation