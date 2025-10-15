### This document describes an automatic Z-offset method that doesn’t rely on Touch.
First, add the following configuration under `[scanner]`:

```ini
calibration_method: second_probe

z_offset: 0
# The trigger height offset relative to the nozzle. For TAP, please measure manually.
probe_speed: 10
# Z-axis movement speed during calibration
probe_pin:
# Endstop pin configuration used for TAP

After configuration, when you run idm_touch calibrate=1,
the system will use this trigger method for Z homing and then automatically start calibration.
To calibrate the Z offset, use:

probe_calibrate method=auto

Since TAP may cause slight compression during automatic Z-offset calibration,
you should manually determine and fix the Z offset.
After adjusting the offset through the web interface,
run SAVE_TOUCH_OFFSET to save this offset for automatic Z calibration.