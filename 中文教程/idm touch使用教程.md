#### 前置需求
请确保你更新固件到[touch版本](https://gitee.com/NBTP/idm-documents/tree/master/IDM%E5%9B%BA%E4%BB%B6(Main%20firmware)/idm_touch)  
更新idm脚本至最新版并重新执行`install.sh`
#### 配置修改
对于新用户，请直接参照以下配置  
```
[scanner]
canbus_uuid: 0ca8d67388c2      
#serial：      
#    adjust to suit your scanner, if using usb change to serial.
#    serial: /dev/serial/by-id/usb-cartographer_cartographer_
x_offset: 0                          
#    adjust for your cartographers offset from nozzle to middle of coil
y_offset: 15                         
#    adjust for your cartographers offset from nozzle to middle of coil
backlash_comp: 0.5
#   Backlash compensation distance for removing Z backlash before measuring
#   the sensor response.
# 
#   Offsets are measured from the centre of your coil, to the tip of your nozzle 
#   on a level axis. It is vital that this is accurate. 
calibration_method: touch
#    leave this as touch unless you want to use scan only for everything. 
sensor: idm
#    this must be set as cartographer unless using IDM etc.
scanner_touch_z_offset: 0.05         
#    This is the default and will be overwritten and added to the DO NOT SAVE area by using UI to save z offset
mesh_runs: 2
#    Number of passes to make during mesh scan.
```

对于从旧版本升级而来的老用户，你们可以直接在旧配置的基础上将所有''idm''修改为''scanner'',  
并在`[scanner]`项中添加下方几个项目
```
calibration_method: touch
#    leave this as touch unless you want to use scan only for everything. 
sensor: idm
#    this must be set as cartographer unless using IDM etc.
scanner_touch_z_offset: 0.05         
```
并在bed_mesh的配置中加入以下项目（如果不配置会有报错提示你添加该项）
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
首先使用`IDM_TOUCH METHOD=MANAUL`来进行初次校准  
校准后进行归零操作  
确保z轴完成归零后，执行`IDM_THRESHOLD_SCAN MIN=500`来对touch阈值进行校准  
由于可能touch进行自动z偏移的过程中会产生挤压，需要自行测定固定z偏移  
使用网页上的偏移按钮后，使用`SAVE_TOUCH_OFFSET`将这个偏移量保存给自动z