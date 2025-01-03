#### 前置需求
请确保你更新固件到[touch版本](https://gitee.com/NBTP/idm-documents/tree/master/IDM%E5%9B%BA%E4%BB%B6(Main%20firmware))  
更新idm脚本至最新版并重新执行`install.sh`
#### 配置修改
对于新用户，请直接参照以下配置  
```
[mcu idm]
serial:
#canbus_uuid:
# Path to the serial port for the idm device. Typically has the form
# /dev/serial/by-id/usb-idm_idm_...

[scanner]
mcu:idm
# mcu of IDM
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
#    校准方法的设置，如果你不想使用touch可以设置为scan来直接兼容旧版本的命令ng. 
sensor: idm
#   传感器名称，idm/cartographer
scanner_touch_max_temp:180
#    戳床时喷嘴下降到该温度
```

对于从旧版本升级而来的老用户，你们可以直接在旧配置的基础上将所有''idm''修改为''scanner'',  请注意自动配置(位于配置文件最下方)中的[idm model xxx]也要改成[scanner model xxx]  
并在`[scanner]`项中添加下方几个项目
```
calibration_method: touch
#    leave this as touch unless you want to use scan only for everything. 
sensor: idm
#    this must be set as cartographer unless using IDM etc.
scanner_touch_z_offset: 0.05         
```
并在bed_mesh的配置中加入以下项目（如果不配置会有报错提示你添加该项）  
该点为自动z偏移时喷嘴戳的坐标
```
[bed_mesh]
zero_reference_position: 125, 125    
#    set this to the middle of your bed
```
#### 指令参考
`IDM_TOUCH METHOD=MANUAL`手动进行IDM的模型校准（通常用在未对touch进行校准的时候）  
`IDM_TOUCH CALIBRATE=1`自动进行IDM的模型校准（通常用在touch完成校准后）  
`IDM_THRESHOLD_SCAN MIN=500`对touch进行阈值校准（请归零后再执行）   
`PROBE_CALIBRATE METHOD=AUTO`对z偏移进行自动测算  
`SAVE_TOUCH_OFFSET`保存自动z偏移所用的固定z偏移  

#### 操作指导
首先使用`IDM_TOUCH METHOD=MANUAL`来进行初次校准  
校准后进行归零操作  
确保z轴完成归零后，执行`IDM_THRESHOLD_SCAN MIN=500`来对touch阈值进行校准  
由于可能touch进行自动z偏移的过程中会产生挤压，需要自行测定固定z偏移  
使用网页上的偏移按钮后，使用`SAVE_TOUCH_OFFSET`将这个偏移量保存给自动z  
使用PROBE_CALIBRATE METHOD=AUTO来进行z偏移测量
#### 开始打印gcode
加入  
```
PROBE_CALIBRATE METHOD=AUTO  
```