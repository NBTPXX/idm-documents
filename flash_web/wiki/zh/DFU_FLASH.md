# DFU 模式刷写

DFU 模式使用 `dfu-util` 工具，适用于设备处于 USB DFU 模式时。

## 前置条件

- 安装 `dfu-util`：`sudo apt install -y dfu-util`
- 先尝试无 sudo 模式，失败后自动回退到 `sudo -n` 模式

## 选择 DFU 模式

在 Web 界面顶部点击 **DFU 模式** 选项卡。

DFU 模式下不显示 Enter BL / Exit BL 按钮（设备已通过物理方式进入 DFU）。

## Flash Address（刷写地址）

| 地址 | 说明 |
|------|------|
| `0x08002000` | 主固件 (Main Firmware) |
| `0x08000000` | Bootloader |

## 检测 DFU 设备

点击「检测 DFU」按钮执行 `dfu-util -l` 扫描 DFU 设备。

## 注意事项

- DFU 模式通常需要按住设备上的物理按钮（如 BOOT0）再上电
- 刷写完成后需要重新上电以退出 DFU 模式

## 刷写流程

1. 将设备置于 DFU 模式（按住 BOOT0 按钮上电）
2. 选择 DFU 模式
3. 选择正确的 Flash Address
4. 选择固件文件
5. 点击「检测 DFU」确认设备
6. 点击「开始刷写」
7. 刷写完成后重新上电
