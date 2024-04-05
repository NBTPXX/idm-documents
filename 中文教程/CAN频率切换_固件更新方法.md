## CAN频率切换
首先连接上位机  
将与上位机直接连接的can通讯设备(U2C或者Can桥接)重新编译固件并频率设置为1M以与IDM通讯  
用下方命令查询IDM的uuid
```
~/klippy-env/bin/python ~/klipper/lib/canboot/flash_can.py -q
```
从网盘下载所需频率IDM固件和canboot覆盖固件
执行以下命令
```
~/klippy-env/bin/python ~/klipper/lib/canboot/flash_can.py -f <canboot更新固件存放路径> -u <查到的uuid>
```

上述”canboot更新固件存放路径”例如~/Canboot 1M.bin
等待执行完成后,之后输入:
```
~/klippy-env/bin/python ~/klipper/lib/canboot/flash_can.py -f <新频率的IDM固件存放路径> -u <查到的uuid>
```
上述”新频率的固件存放路径”例如~/IDM_CAN_8kib_offset_1M.bin
上述的内容填写自己的数据，记得删除”<>”括号  
如果想改成usb通讯，可以按上述方式刷入带USB字样的固件，并将idm背面的模式设置跳线改焊到usb的一侧。  

## 如果你当前使用的是USB的固件想要更新固件或者切换到CAN模式:
```
cd ~/klipper/scripts 
~/klippy-env/bin/python -c 'import flash_usb as u; u.enter_bootloader("<你的设备串口地址>")'
```
```
cd ~
~/klippy-env/bin/python ~/klipper/lib/canboot/flash_can.py -f <固件所在路径> -d <你的设备串口地址>
```
设备串口地址指的是/dev/serial/by-id/****这种格式的地址  
请注意第二次串口号应与第一次不同，请重新查询  
上述的内容填写自己的数据，记得删除`<>`括号  

#### 通过dfu上传固件
如果你通过短接boot0再上电的方式使得你的idm进入了dfu模式  
可以通过下方指令上传canboot  
如果你在试图刷入CAN通讯的canboot，请勿使用这个指令，请使用第二条指令刷入0x08002000地址，并重启设备  
```
sudo dfu-util -d ,0483:df11 -R -a 0 -s 0x8000000:leave -D <文件路径>
```
还可以通过下方指令上传主固件
```
sudo dfu-util -d ,0483:df11 -R -a 0 -s 0x8002000:leave -D <文件路径>
```
上述的内容填写自己的数据，记得删除`<>`括号，请注意两个指令是不一样的