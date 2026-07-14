# CAN 频率切换与固件更新方法

> **版本兼容说明：** 新版 Klipper 已将 `CanBoot` 替换为 `Katapult`，刷写工具路径和用法有所不同。如果你的 Klipper 使用 Katapult，请参考下方 **Katapult（新版）** 命令；如仍使用旧版 CanBoot，使用 **CanBoot（旧版）** 命令。不确定的话，执行以下命令检测：
>
> ```bash
> # 检测使用哪个版本
> test -f ~/klipper/lib/katapult/flashtool.py && echo "Katapult（新版）" || echo "CanBoot（旧版）"
> ```

## 一、CAN 频率切换

### 准备工作

1. 将直接连接上位机的 CAN 通讯设备（U2C 或 CAN 桥接）固件重新编译并设置频率为 1M，以与 IDM 正常通讯
2. 从网盘下载所需频率的 IDM 固件和 Bootloader 覆盖固件

### 步骤 1：查询 UUID

**CanBoot（旧版）：**

```bash
~/klippy-env/bin/python ~/klipper/lib/canboot/flash_can.py -q
```

**Katapult（新版）：**

```bash
~/klippy-env/bin/python ~/klipper/lib/katapult/flashtool.py -i can0 -q
```

### 步骤 2：刷入 Bootloader 覆盖固件

**CanBoot（旧版）：**

```bash
~/klippy-env/bin/python ~/klipper/lib/canboot/flash_can.py -f <canboot固件路径> -u <UUID>
```

**Katapult（新版）：**

```bash
~/klippy-env/bin/python ~/klipper/lib/katapult/flashtool.py -i can0 -f <katapult固件路径> -u <UUID>
```

例如：

```bash
# CanBoot 旧版
~/klippy-env/bin/python ~/klipper/lib/canboot/flash_can.py -f ~/Canboot_1M.bin -u <UUID>

# Katapult 新版
~/klippy-env/bin/python ~/klipper/lib/katapult/flashtool.py -i can0 -f ~/Katapult_1M.bin -u <UUID>
```

### 步骤 3：刷入新频率的 IDM 主固件

**CanBoot（旧版）：**

```bash
~/klippy-env/bin/python ~/klipper/lib/canboot/flash_can.py -f <IDM固件路径> -u <UUID>
```

**Katapult（新版）：**

```bash
~/klippy-env/bin/python ~/klipper/lib/katapult/flashtool.py -i can0 -f <IDM固件路径> -u <UUID>
```

例如：

```bash
# CanBoot 旧版
~/klippy-env/bin/python ~/klipper/lib/canboot/flash_can.py -f ~/IDM_CAN_8kib_offset_1M.bin -u <UUID>

# Katapult 新版
~/klippy-env/bin/python ~/klipper/lib/katapult/flashtool.py -i can0 -f ~/IDM_CAN_8kib_offset_1M.bin -u <UUID>
```

> **注意：** 以上命令中的 `<>` 括号表示你需要替换为实际值，使用时请删除 `<>` 符号。

### 切换到 USB 通讯

如需从 CAN 切换为 USB 通讯，按上述方式刷入带 "USB" 字样的固件，并将 IDM 背面的模式选择跳线改焊到 USB 一侧。

---

## 二、USB 固件更新或切换到 CAN 模式

### 步骤 1：进入 Bootloader

```bash
cd ~/klipper/scripts
~/klippy-env/bin/python -c 'import flash_usb as u; u.enter_bootloader("<设备串口地址>")'
```

### 步骤 2：刷入固件

```bash
cd ~
```

**CanBoot（旧版）：**

```bash
~/klippy-env/bin/python ~/klipper/lib/canboot/flash_can.py -f <固件路径> -d <设备串口地址>
```

**Katapult（新版）：**

```bash
~/klippy-env/bin/python ~/klipper/lib/katapult/flashtool.py -d <设备串口地址> -f <固件路径>
```

设备串口地址指的是 `/dev/serial/by-id/xxx` 格式的地址。

> **注意：**
> - 第二次刷入时的串口号与进入 Bootloader 时的串口号不同，请重新查询
> - 以上命令中的 `<>` 括号表示你需要替换为实际值，使用时请删除 `<>` 符号

---

## 三、通过 DFU 上传固件

### 进入 DFU 模式

通过短接 BOOT0 再上电的方式使 IDM 进入 DFU 模式。

### 刷入 Bootloader

```bash
sudo dfu-util -d ,0483:df11 -R -a 0 -s 0x8000000:leave -D <文件路径>
```

### 刷入主固件

```bash
sudo dfu-util -d ,0483:df11 -R -a 0 -s 0x8002000:leave -D <文件路径>
```

> **注意：**
> - 如果要刷入 CAN 通讯的 Bootloader，请使用第二条指令（刷入 `0x08002000` 地址），刷完后重启设备
> - 两条指令的地址参数不同，请确认使用正确
> - `<>` 括号表示你需要替换为实际值，使用时请删除 `<>` 符号

---

## 常见问题

**Q：刷入固件后设备无响应？**

A：检查固件与硬件版本是否匹配，确认刷入地址是否正确。如仍无法解决，尝试通过 DFU 模式重新刷入。

**Q：刷入 CAN 固件后 UUID 变化？**

A：Bootloader 刷入后 UUID 可能会出现变化，请重新查询并更新配置文件。

**Q：CanBoot 和 Katapult 有什么区别？**

A：Katapult 是 CanBoot 的后继项目。新版 Klipper 已在 `lib/katapult/` 目录中内置了 Katapult，无需额外安装。如果该目录存在则可使用新版命令，否则仍使用旧版 CanBoot 命令。
