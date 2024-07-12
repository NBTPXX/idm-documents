### 本文档主要介绍当前开放的使用voron tap(限位开关也行)的自动z偏移方法
首先在[idm]的配置下添加以下新配置： 
```
tap_location:125,125
#进行自动z偏移测算时，喷嘴戳的坐标
calibration_method:voron_tap

z_offset:0
#触发高度相对于喷嘴的偏移,tap的话请自行测量
probe_speed:10
校准时z移动速度
probe_pin:
tap使用的限位引脚配置
```
配置好之后使用`idm_calibrate`时会默认使用该触发方式进行z归零之后自动开始校准，  
对z偏移进行校准请使用`probe_calibrate method=auto`