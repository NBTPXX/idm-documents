### 本文档主要介绍使用touch以外的自动z偏移方法
首先在[scanner]的配置下添加以下新配置： 
```
calibration_method:second_probe

z_offset:0
#触发高度相对于喷嘴的偏移,tap的话请自行测量
probe_speed:10
校准时z移动速度
probe_pin:
tap使用的限位引脚配置
```
配置好之后使用`idm_touch calibrate=1`时会默认使用该触发方式进行z归零之后自动开始校准，  
对z偏移进行校准请使用`probe_calibrate method=auto`

由于可能TAP进行自动z偏移的过程中会产生挤压，需要自行测定固定z偏移 
使用网页上的偏移按钮后，使用SAVE_TOUCH_OFFSET将这个偏移量保存给自动z 