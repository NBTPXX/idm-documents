**Optimizing Temperature Compensation Parameters Tutorial**

This tutorial aims to optimize temperature compensation parameters to reduce temperature drift. The optimization process is time-consuming (over 1 hour). If your printer's temperature compensation meets your requirements, this operation may not be necessary.

**Step 1:** Paste the following macro into your configuration file:
```ini
[gcode_macro DATA_SAMPLE]
gcode:
  {% set bed_temp = params.BED_TEMP|default(90)|int %}
  {% set nozzle_temp = params.NOZZLE_TEMP|default(250)|int %}
  {% set min_temp = params.MIN_TEMP|default(40)|int %}
  {% set max_temp = params.MAX_TEMP|default(70)|int %}
  M106 S255
  TEMPERATURE_WAIT SENSOR='temperature_sensor IDM_coil' MAXIMUM={min_temp}
  M106 S0
  G28
  G0 Z1
  M104 S{nozzle_temp}
  M140 S{bed_temp}
  TEMPERATURE_WAIT SENSOR='temperature_sensor IDM_coil' MINIMUM={min_temp}
  IDM_STREAM FILENAME=data1
  TEMPERATURE_WAIT SENSOR='temperature_sensor IDM_coil' MINIMUM={max_temp}
  IDM_STREAM FILENAME=data1
  M104 S0
  M140 S0
  M106 S255
  G0 Z80
  TEMPERATURE_WAIT SENSOR='temperature_sensor IDM_coil' MAXIMUM={min_temp}
  M106 S0
  G28 Z0
  G0 Z2
  M104 S{nozzle_temp}
  M140 S{bed_temp}
  G4 P1000
  IDM_STREAM FILENAME=data2
  TEMPERATURE_WAIT SENSOR='temperature_sensor IDM_coil' MINIMUM={max_temp}
  IDM_STREAM FILENAME=data2
  M104 S0
  M140 S0
  M106 S255
  G0 Z80
  TEMPERATURE_WAIT SENSOR='temperature_sensor IDM_coil' MAXIMUM={min_temp}
  M106 S0
  G28 Z0
  G0 Z3
  M104 S{nozzle_temp}
  M140 S{bed_temp}
  G4 P1000
  IDM_STREAM FILENAME=data3
  TEMPERATURE_WAIT SENSOR='temperature_sensor IDM_coil' MINIMUM={max_temp}
  IDM_STREAM FILENAME=data3
  M104 S0
  M140 S0
```

**Step 2:** Execute `DATA_SAMPLE BED_TMEP=<target bed temperature> NOZZLE_TEMP=<target nozzle temperature> MIN_TEMP=<minimum temperature of sampling range> MAX_TEMP=<maximum temperature of samping range>`  
if you dont input any parameter,it will run with default parameters(BED_TEMP=90 NOZZLE_TEMP=250 MIN_TEMP=40 MAX_TEMP=70).  
This will generate 3 files (data1, data2, data3) in the klipper folder. This process takes a long time.  

**Step 3:** Move the 3 generated files to the IDM folder in your user directory.

**Step 4:** Execute the following commands:
```bash
cd ~/IDM
~/klippy-env/bin/python arg_fit.py
```
(Ensure that you are using the latest script package before running. If not, git clone again.)

This will generate three parameters and an image named fit_result.png in the IDM folder. Note that this process requires significant computational power and time.

**Step 5:** Check the fit_result.png image for the fitting result. The first row shows the original data, and the second row shows the data after temperature compensation. Ensure that the fit is effective, and the offsets are controlled within a reasonable range.

**Step 6:** Copy the generated parameters to the [IDM] block in your configuration file. See the example below:

![Example](/imgs/example.jpg)