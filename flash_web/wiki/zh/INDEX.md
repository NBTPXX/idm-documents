# IDM Flash Web 使用手册

IDM Flash Web 是一个基于浏览器的固件刷写工具，用于给 IDM 3D 打印机传感器刷写固件。支持 CAN、USB 串口和 DFU 三种连接模式。

## 目录

- [安装指南](INSTALL.md)
- [CAN 模式刷写](CAN_FLASH.md)
- [USB 模式刷写](USB_FLASH.md)
- [DFU 模式刷写](DFU_FLASH.md)
- [Bootloader 管理](BOOTLOADER.md)
- [Moonraker 集成](MOONRAKER.md)

## 快速开始

1. 将打印机连接到上位机（CAN 或 USB）
2. 打开 Web 界面：`http://<打印机IP>:8888`
3. 选择连接模式（CAN / USB / DFU）
4. 选择要刷写的固件文件
5. 点击「开始刷写」

## 支持模式

| 模式 | 适用场景 | 通信方式 |
|------|---------|---------|
| CAN | CAN 总线连接的设备 | CAN socket |
| USB | USB 串口连接的设备 | Serial (Katapult) |
| DFU | USB DFU 模式设备 | dfu-util |
