#### Prerequisite Requirements
1. Please ensure you have updated the firmware to the touch version.
2. Update the IDM script to the latest version and re-run install.sh.

---

#### Configuration Modifications
For New Users:
Please follow the configuration below directly:
```
[mcu idm]
serial:
#canbus_uuid:
# Path to the serial port for the IDM device. Typically has the form
# /dev/serial/by-id/usb-idm_idm_...

[scanner]
#canbus_uuid: 0ca8d67388c2      
mcu: idm
# mcu of IDM
x_offset: 0                          
# Adjust for your cartographer's offset from the nozzle to the middle of the coil.
y_offset: 15                         
# Adjust for your cartographer's offset from the nozzle to the middle of the coil.
backlash_comp: 0.5
# Backlash compensation distance for removing Z backlash before measuring
# the sensor response.
#
# Offsets are measured from the center of your coil to the tip of your nozzle
# on a level axis. It is vital that this is accurate.
calibration_method: touch
# Leave this as "touch" unless you want to use "scan only" for everything.
sensor: idm
# This must be set to "cartographer" unless using IDM etc.
scanner_touch_z_offset: 0.05         
# This is the default and will be overwritten and added to the DO NOT SAVE area by using the UI to save Z offset.
mesh_runs: 1
# Number of passes to make during the mesh scan.
```
For Existing Users Upgrading from Older Versions:

If you are upgrading from an older version, you can modify your existing configuration by replacing all instances of 'idm' with 'scanner'. Additionally:
1. Update the auto-configuration section (located at the bottom of the configuration file) by renaming [idm model xxx] to [scanner model xxx].

2. Add the following entries under the [scanner] section:
```
calibration_method: touch
# Leave this as "touch" unless you want to use "scan only" for everything.
sensor: idm
# This must be set to "cartographer" unless using IDM etc.
scanner_touch_z_offset: 0.05
```

3. Update the bed_mesh configuration with the following item (to avoid errors):
```
[bed_mesh]
zero_reference_position: 125, 125    
# Set this to the middle of your bed.
```
---

#### Command References

Manual Model Calibration:  
`IDM_TOUCH METHOD=MANUAL`Used when touch calibration has not been performed.  
Automatic Model Calibration:  
`IDM_TOUCH CALIBRATE=1`Used after completing touch calibration.  
Threshold Calibration:  
`IDM_THRESHOLD_SCAN MIN=500`Perform threshold calibration for touch (ensure zeroing before execution).  
Automatic Z-Offset Measurement:  
`PROBE_CALIBRATE METHOD=AUTO`  
Save Fixed Z-Offset for Auto Z-Offset:  
`SAVE_TOUCH_OFFSET`  

---

#### Operational Guidance

1. Start with manual calibration using:

`IDM_TOUCH METHOD=MANUAL`

2. After calibration, run homing operation.

3. Ensure the Z-axis is fully zeroed, then run:
`IDM_THRESHOLD_SCAN MIN=500`to calibrate the touch threshold.

4. During automatic Z-offset adjustment, compression may occur. You will need to determine the fixed Z-offset manually:  
Use the offset adjustment button on the web interface.  
Then save the offset using:
`SAVE_TOUCH_OFFSET`

5. Perform Z-offset measurement using:
`PROBE_CALIBRATE METHOD=AUTO`

6. After measurement, reissue G28 Z to activate the offset.

---

#### Start Printing G-Code

Add the following lines to your G-code start sequence:
```
PROBE_CALIBRATE METHOD=AUTO  
G28 Z
```
