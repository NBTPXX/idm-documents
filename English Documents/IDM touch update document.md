#### Prerequisite Requirements
Update the bed_mesh configuration with the following item (to avoid errors):
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
```
