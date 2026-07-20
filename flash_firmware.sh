#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# IDM 交互式固件刷写脚本
# 支持 CAN / USB / DFU 三种方式
# 支持 STM32 / RP2040 两种硬件平台
# 自动检测 CanBoot / Katapult 版本
# ============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FW_DIR_IDM="${SCRIPT_DIR}/IDM固件(Main firmware)"
FW_DIR_CANBOOT="${SCRIPT_DIR}/Canboot通讯频率覆写用固件(canboot deployer firmware)"
FW_DIR_RP2040="${SCRIPT_DIR}/rp2040"

KLIPPER_ENV="${HOME}/klippy-env/bin/python"
KLIPPER_DIR="${HOME}/klipper"

CANBOOT_FLASH="${KLIPPER_DIR}/lib/canboot/flash_can.py"
KATAPULT_FLASH="${KLIPPER_DIR}/lib/katapult/flashtool.py"

print_banner() {
    echo -e "${CYAN}"
    echo "  ╔══════════════════════════════════════╗"
    echo "  ║       IDM 交互式固件刷写工具        ║"
    echo "  ╚══════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    echo -e "\n${BOLD}${GREEN}>>> $1${NC}"
}

print_info() {
    echo -e "${CYAN}  ● $1${NC}"
}

print_warn() {
    echo -e "${YELLOW}  ⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}  ✗ $1${NC}"
}

print_success() {
    echo -e "${GREEN}  ✓ $1${NC}"
}

# -----------------------------------------------------------
# 环境检测
# -----------------------------------------------------------
detect_environment() {
    print_step "检测运行环境"

    if [[ ! -f "${KLIPPER_ENV}" ]]; then
        print_warn "未找到 klippy-env Python: ${KLIPPER_ENV}"
        KLIPPER_ENV="python3"
    fi

    CAN_INTERFACE=$(ip -o link show 2>/dev/null | grep -oP 'can\d+' | head -1 || true)

    if [[ -f "${KATAPULT_FLASH}" ]]; then
        BOOTLOADER_TYPE="katapult"
        FLASH_TOOL="${KATAPULT_FLASH}"
        print_success "检测到 Katapult (新版)"
    elif [[ -f "${CANBOOT_FLASH}" ]]; then
        BOOTLOADER_TYPE="canboot"
        FLASH_TOOL="${CANBOOT_FLASH}"
        print_success "检测到 CanBoot (旧版)"
    else
        BOOTLOADER_TYPE=""
        print_warn "未检测到 CanBoot/Katapult 刷写工具，请确认 Klipper 已安装"
    fi

    if [[ -n "${CAN_INTERFACE}" ]]; then
        print_success "检测到 CAN 接口: ${CAN_INTERFACE}"
    else
        print_warn "未检测到 CAN 接口"
    fi
}

# -----------------------------------------------------------
# 选择刷写模式
# -----------------------------------------------------------
select_mode() {
    echo -e "\n${BOLD}请选择刷写模式:${NC}"
    echo "  1) CAN 模式 (通过 CAN 总线刷写)"
    echo "  2) USB 模式 (通过 USB 串口刷写)"
    echo "  3) DFU 模式 (通过 USB DFU 刷写)"
    echo "  4) 退出"
    echo ""
    while true; do
        read -r -p "请输入选项 [1-4]: " MODE
        case "${MODE}" in
            1) MODE_NAME="CAN"; break;;
            2) MODE_NAME="USB"; break;;
            3) MODE_NAME="DFU"; break;;
            4) echo "已退出"; exit 0;;
            *) print_error "无效选项，请输入 1-4";;
        esac
    done
    print_info "已选择: ${MODE_NAME} 模式"
}

# -----------------------------------------------------------
# 选择硬件平台
# -----------------------------------------------------------
select_hardware() {
    echo -e "\n${BOLD}请选择硬件平台:${NC}"
    echo "  1) STM32 (原版 IDM)"
    echo "  2) RP2040"
    echo ""
    while true; do
        read -r -p "请输入选项 [1-2]: " HW
        case "${HW}" in
            1) HW_PLATFORM="stm32"; break;;
            2) HW_PLATFORM="rp2040"; break;;
            *) print_error "无效选项，请输入 1-2";;
        esac
    done
    print_info "已选择: ${HW_PLATFORM}"
}

# -----------------------------------------------------------
# 选择频率（CAN模式）
# -----------------------------------------------------------
select_frequency() {
    echo -e "\n${BOLD}请选择 CAN 通讯频率:${NC}"
    echo "  1) 1M     (高速)"
    echo "  2) 500k   (中速)"
    echo "  3) 250k   (低速)"
    echo ""
    while true; do
        read -r -p "请输入选项 [1-3]: " FREQ
        case "${FREQ}" in
            1) FREQ_LABEL="1M"; break;;
            2) FREQ_LABEL="500k"; break;;
            3) FREQ_LABEL="250k"; break;;
            *) print_error "无效选项，请输入 1-3";;
        esac
    done
    print_info "已选择: ${FREQ_LABEL}"
}

# -----------------------------------------------------------
# 选择固件类型
# -----------------------------------------------------------
select_fw_type() {
    echo -e "\n${BOLD}请选择固件类型:${NC}"
    echo "  1) IDM 主固件 (Main firmware)"
    echo "  2) Bootloader 覆盖固件 (Deployer firmware)"
    echo ""
    while true; do
        read -r -p "请输入选项 [1-2]: " FW_TYPE
        case "${FW_TYPE}" in
            1) FW_CATEGORY="main"; break;;
            2) FW_CATEGORY="deployer"; break;;
            *) print_error "无效选项，请输入 1-2";;
        esac
    done
    print_info "已选择: ${FW_CATEGORY}"
}

# -----------------------------------------------------------
# 查找固件文件
# -----------------------------------------------------------
find_firmware() {
    local platform="$1"
    local category="$2"
    local freq="$3"

    if [[ "${platform}" == "rp2040" ]]; then
        FW_BASE_DIR="${FW_DIR_RP2040}"
    else
        if [[ "${category}" == "main" ]]; then
            FW_BASE_DIR="${FW_DIR_IDM}"
        else
            FW_BASE_DIR="${FW_DIR_CANBOOT}"
        fi
    fi

    if [[ ! -d "${FW_BASE_DIR}" ]]; then
        print_error "固件目录不存在: ${FW_BASE_DIR}"
        return 1
    fi

    local pattern=""
    local platform_str=""
    if [[ "${platform}" == "rp2040" ]]; then
        platform_str="rp2040"
    fi

    if [[ "${category}" == "main" ]]; then
        if [[ "${platform}" == "rp2040" ]]; then
            pattern="IDM_rp2040"
        else
            pattern="IDM_"
        fi
    else
        if [[ "${platform}" == "rp2040" ]]; then
            pattern="canboot_rp2040"
        else
            pattern="canboot_"
        fi
    fi

    if [[ -n "${freq}" ]]; then
        if [[ "${freq}" == "USB" ]]; then
            pattern="${pattern}*[Uu][Ss][Bb]*"
        else
            pattern="${pattern}*${freq}*"
        fi
    fi

    if [[ "${category}" == "main" ]]; then
        pattern="${pattern}*.bin"
    else
        if [[ "${platform}" == "rp2040" ]]; then
            pattern="${pattern}*deployer*.bin"
        else
            pattern="${pattern}*deployer*.bin"
        fi
    fi

    local matches
    matches=$(find "${FW_BASE_DIR}" -maxdepth 1 -type f -name "${pattern}" 2>/dev/null | grep -v '/old/' | sort)

    if [[ -z "${matches}" ]]; then
        print_error "未找到匹配的固件文件"
        print_info "搜索模式: ${pattern}"
        print_info "搜索目录: ${FW_BASE_DIR}"
        echo ""
        print_info "目录中的文件:"
        find "${FW_BASE_DIR}" -maxdepth 1 -type f -name "*.bin" ! -path "*/old/*" -exec basename {} \; 2>/dev/null | sort | while read -r f; do
            echo "      ${f}"
        done
        return 1
    fi

    FW_FILE=$(echo "${matches}" | head -1)
    print_success "找到固件: $(basename "${FW_FILE}")"
}

# -----------------------------------------------------------
# 手动指定固件文件
# -----------------------------------------------------------
manual_firmware_select() {
    echo -e "\n${BOLD}自动匹配失败，请手动选择固件文件:${NC}"
    local search_dir
    if [[ "${HW_PLATFORM}" == "rp2040" ]]; then
        search_dir="${FW_DIR_RP2040}"
    elif [[ "${FW_CATEGORY}" == "main" ]]; then
        search_dir="${FW_DIR_IDM}"
    else
        search_dir="${FW_DIR_CANBOOT}"
    fi

    local files
    mapfile -t files < <(find "${search_dir}" -maxdepth 1 -type f \( -name "*.bin" -o -name "*.uf2" \) ! -path "*/old/*" 2>/dev/null | sort)

    if [[ ${#files[@]} -eq 0 ]]; then
        print_error "目录 ${search_dir} 中没有固件文件"
        return 1
    fi

    local i=1
    for f in "${files[@]}"; do
        echo "  ${i}) $(basename "${f}")"
        ((i++))
    done
    echo "  ${i}) 手动输入路径"

    while true; do
        read -r -p "请选择文件 [1-${i}]: " FILE_IDX
        if [[ "${FILE_IDX}" =~ ^[0-9]+$ ]] && (( FILE_IDX >= 1 && FILE_IDX <= i )); then
            if (( FILE_IDX == i )); then
                read -r -p "请输入固件文件的完整路径: " FW_FILE
            else
                FW_FILE="${files[$((FILE_IDX - 1))]}"
            fi
            break
        else
            print_error "无效选项"
        fi
    done
    print_success "已选择: $(basename "${FW_FILE}")"
}

# -----------------------------------------------------------
# 查询 CAN 设备 UUID
# -----------------------------------------------------------
query_can_device() {
    print_step "查询 CAN 总线设备"

    if [[ -z "${CAN_INTERFACE}" ]]; then
        read -r -p "请输入 CAN 接口名称 (如 can0): " CAN_INTERFACE
    fi

    if [[ "${BOOTLOADER_TYPE}" == "katapult" ]]; then
        print_info "使用 Katapult flashtool 查询..."
        local output
        output=$("${KLIPPER_ENV}" "${FLASH_TOOL}" -i "${CAN_INTERFACE}" -q 2>&1) || true
        echo "${output}"
        CAN_UUIDS=$(echo "${output}" | grep -oP '[0-9a-f]{16,}' || true)
    else
        print_info "使用 CanBoot flash_can 查询..."
        local output
        output=$("${KLIPPER_ENV}" "${FLASH_TOOL}" -q 2>&1) || true
        echo "${output}"
        CAN_UUIDS=$(echo "${output}" | grep -oP '[0-9a-f]{16,}' || true)
    fi

    if [[ -z "${CAN_UUIDS}" ]]; then
        print_warn "未检测到 CAN 设备，请确认设备已连接且处于 Bootloader 模式"
        read -r -p "请输入设备 UUID (或按 Enter 跳过): " CAN_UUID
    else
        local uuid_count
        uuid_count=$(echo "${CAN_UUIDS}" | wc -l)
        if (( uuid_count == 1 )); then
            CAN_UUID="${CAN_UUIDS}"
            print_success "检测到设备: ${CAN_UUID}"
        else
            print_info "检测到 ${uuid_count} 个设备:"
            local idx=1
            local uuids_arr=()
            while IFS= read -r uid; do
                uuids_arr+=("${uid}")
                echo "  ${idx}) ${uid}"
                ((idx++))
            done <<< "${CAN_UUIDS}"
            read -r -p "请选择设备 [1-${uuid_count}]: " UUID_IDX
            CAN_UUID="${uuids_arr[$((UUID_IDX - 1))]}"
            print_success "已选择: ${CAN_UUID}"
        fi
    fi
}

# -----------------------------------------------------------
# 查询 USB 串口设备
# -----------------------------------------------------------
query_usb_device() {
    print_step "查询 USB 串口设备"

    print_info "系统中的串口设备:"
    local devices
    devices=$(ls /dev/serial/by-id/* 2>/dev/null || true)

    if [[ -z "${devices}" ]]; then
        print_warn "未找到 /dev/serial/by-id/ 下的设备"
        devices=$(ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || true)
        if [[ -z "${devices}" ]]; then
            print_error "未找到任何串口设备"
            read -r -p "请手动输入串口地址: " SERIAL_DEVICE
        else
            echo "${devices}" | while read -r d; do echo "  ${d}"; done
            read -r -p "请输入串口地址: " SERIAL_DEVICE
        fi
    else
        local idx=1
        local dev_arr=()
        while IFS= read -r d; do
            dev_arr+=("${d}")
            echo "  ${idx}) ${d}"
            ((idx++))
        done <<< "${devices}"
        echo "  ${idx}) 手动输入"
        read -r -p "请选择设备 [1-${idx}]: " DEV_IDX
        if [[ "${DEV_IDX}" =~ ^[0-9]+$ ]] && (( DEV_IDX >= 1 && DEV_IDX < idx )); then
            SERIAL_DEVICE="${dev_arr[$((DEV_IDX - 1))]}"
        else
            read -r -p "请输入串口地址: " SERIAL_DEVICE
        fi
    fi
    print_success "串口设备: ${SERIAL_DEVICE}"
}

# -----------------------------------------------------------
# CAN 模式刷写
# -----------------------------------------------------------
flash_can() {
    print_step "CAN 模式刷写"

    if [[ -z "${CAN_UUID:-}" ]]; then
        query_can_device
    fi

    if [[ -z "${CAN_UUID}" ]]; then
        print_error "无法继续，未获取到设备 UUID"
        return 1
    fi

    print_info "准备刷入: $(basename "${FW_FILE}")"
    print_info "目标设备: ${CAN_UUID}"

    echo ""
    read -r -p "确认开始刷写? [y/N]: " CONFIRM
    if [[ ! "${CONFIRM}" =~ ^[Yy]$ ]]; then
        print_info "已取消"
        return 0
    fi

    if [[ "${BOOTLOADER_TYPE}" == "katapult" ]]; then
        local cmd=("${KLIPPER_ENV}" "${FLASH_TOOL}" -i "${CAN_INTERFACE}" -f "${FW_FILE}" -u "${CAN_UUID}")
    else
        local cmd=("${KLIPPER_ENV}" "${FLASH_TOOL}" -f "${FW_FILE}" -u "${CAN_UUID}")
    fi

    print_info "执行命令: ${cmd[*]}"
    echo ""
    if "${cmd[@]}"; then
        print_success "固件刷写完成!"
    else
        print_error "刷写失败，请检查设备和连接"
        return 1
    fi
}

# -----------------------------------------------------------
# USB 模式刷写
# -----------------------------------------------------------
flash_usb() {
    print_step "USB 模式刷写"

    query_usb_device

    print_info "第 1 步: 进入 Bootloader 模式"
    local enter_cmd=("${KLIPPER_ENV}" -c "import flash_usb as u; u.enter_bootloader('${SERIAL_DEVICE}')")
    local workdir="${KLIPPER_DIR}/scripts"

    print_info "执行: cd ${workdir} && ${enter_cmd[*]}"
    if ! (cd "${workdir}" && "${enter_cmd[@]}" 2>&1); then
        print_warn "进入 Bootloader 可能失败，请检查设备连接"
    fi

    sleep 2

    print_info "第 2 步: 重新查询串口 (Bootloader 模式下的串口号不同)"
    echo ""
    local bootloader_devices
    bootloader_devices=$(ls /dev/serial/by-id/* 2>/dev/null || true)
    if [[ -n "${bootloader_devices}" ]]; then
        echo "${bootloader_devices}" | while read -r d; do echo "  ${d}"; done
    else
        ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || true
    fi
    echo ""
    read -r -p "请输入 Bootloader 模式下的串口地址: " BOOTLOADER_SERIAL

    print_info "准备刷入: $(basename "${FW_FILE}")"

    echo ""
    read -r -p "确认开始刷写? [y/N]: " CONFIRM
    if [[ ! "${CONFIRM}" =~ ^[Yy]$ ]]; then
        print_info "已取消"
        return 0
    fi

    if [[ "${BOOTLOADER_TYPE}" == "katapult" ]]; then
        local cmd=("${KLIPPER_ENV}" "${FLASH_TOOL}" -d "${BOOTLOADER_SERIAL}" -f "${FW_FILE}")
    else
        local cmd=("${KLIPPER_ENV}" "${FLASH_TOOL}" -f "${FW_FILE}" -d "${BOOTLOADER_SERIAL}")
    fi

    print_info "执行命令: ${cmd[*]}"
    echo ""
    if "${cmd[@]}"; then
        print_success "固件刷写完成!"
    else
        print_error "刷写失败，请检查设备和连接"
        return 1
    fi
}

# -----------------------------------------------------------
# DFU 模式刷写
# -----------------------------------------------------------
flash_dfu() {
    print_step "DFU 模式刷写"

    if ! command -v dfu-util &>/dev/null; then
        print_error "dfu-util 未安装，请执行: sudo apt install dfu-util"
        return 1
    fi

    print_info "请确保设备已进入 DFU 模式 (短接 BOOT0 后上电)"
    print_info "如果设备已连接，将列出 DFU 设备:"
    echo ""
    dfu-util -l 2>/dev/null || sudo -n dfu-util -l 2>/dev/null || true
    echo ""

    if [[ "${FW_CATEGORY}" == "main" ]]; then
        DFU_ADDR="0x8002000"
    else
        DFU_ADDR="0x8000000"
    fi

    print_info "目标地址: ${DFU_ADDR} ($([[ "${FW_CATEGORY}" == "main" ]] && echo "主固件" || echo "Bootloader"))"
    print_info "准备刷入: $(basename "${FW_FILE}")"

    echo ""
    read -r -p "确认开始刷写? [y/N]: " CONFIRM
    if [[ ! "${CONFIRM}" =~ ^[Yy]$ ]]; then
        print_info "已取消"
        return 0
    fi

    local dfu_args=(-d ,0483:df11 -R -a 0 -s "${DFU_ADDR}:leave" -D "${FW_FILE}")
    local cmd=(dfu-util "${dfu_args[@]}")
    local sudo_cmd=(sudo -n dfu-util "${dfu_args[@]}")

    print_info "执行命令: ${cmd[*]}"
    echo ""
    if "${cmd[@]}" 2>/dev/null; then
        print_success "固件刷写完成! 设备将自动重启"
    elif "${sudo_cmd[@]}"; then
        print_success "固件刷写完成! 设备将自动重启"
    else
        print_error "刷写失败"
        return 1
    fi
}

# -----------------------------------------------------------
# 仅查询设备信息
# -----------------------------------------------------------
query_devices_only() {
    print_step "设备查询"

    if [[ "${BOOTLOADER_TYPE}" == "katapult" ]]; then
        print_info "Katapult CAN 设备查询..."
        "${KLIPPER_ENV}" "${FLASH_TOOL}" -i "${CAN_INTERFACE:-can0}" -q 2>&1 || true
    elif [[ "${BOOTLOADER_TYPE}" == "canboot" ]]; then
        print_info "CanBoot CAN 设备查询..."
        "${KLIPPER_ENV}" "${FLASH_TOOL}" -q 2>&1 || true
    fi

    echo ""
    print_info "串口设备:"
    ls /dev/serial/by-id/* 2>/dev/null || echo "  (无)"

    echo ""
    print_info "DFU 设备:"
    dfu-util -l 2>/dev/null || sudo -n dfu-util -l 2>/dev/null || echo "  (无)"
}

# -----------------------------------------------------------
# 高级模式：一步到位刷写
# -----------------------------------------------------------
advanced_flash() {
    echo -e "\n${BOLD}高级模式 - 请依次完成以下配置:${NC}"

    select_hardware

    if [[ "${MODE_NAME}" == "DFU" ]]; then
        if [[ "${HW_PLATFORM}" == "rp2040" ]]; then
            print_error "DFU 模式仅支持 STM32 平台"
            return 1
        fi
    fi

    if [[ "${MODE_NAME}" == "DFU" ]]; then
        select_fw_type
        # DFU 需要找对应固件
        if [[ "${FW_CATEGORY}" == "main" ]]; then
            FW_FILE=$(find "${FW_DIR_IDM}" -maxdepth 1 -type f -name "*.bin" ! -path "*/old/*" | sort | head -1)
        else
            FW_FILE=$(find "${FW_DIR_CANBOOT}" -maxdepth 1 -type f -name "*.bin" ! -path "*/old/*" | sort | head -1)
        fi
        if [[ -z "${FW_FILE}" ]]; then
            manual_firmware_select
        else
            print_success "找到固件: $(basename "${FW_FILE}")"
        fi
        flash_dfu
        return
    fi

    if [[ "${MODE_NAME}" == "USB" ]]; then
        FREQ_LABEL=""
    else
        select_frequency
    fi
    select_fw_type

    if ! find_firmware "${HW_PLATFORM}" "${FW_CATEGORY}" "${FREQ_LABEL}"; then
        manual_firmware_select
    fi

    case "${MODE_NAME}" in
        CAN) flash_can;;
        USB) flash_usb;;
    esac
}

# -----------------------------------------------------------
# 简易模式：向导式一步步操作
# -----------------------------------------------------------
simple_flash() {
    echo -e "\n${BOLD}简易模式 - 将逐步引导你完成刷写${NC}"

    select_hardware

    if [[ "${HW_PLATFORM}" == "rp2040" ]]; then
        print_step "RP2040 固件刷写"
        print_info "RP2040 的 .uf2 文件请手动拖入开发板储存器"
        print_info "或使用 deployer .bin 文件通过 CAN/USB 远程刷写"

        echo -e "\n${BOLD}请选择操作:${NC}"
        echo "  1) 使用 deployer .bin 通过 CAN 远程刷写"
        echo "  2) 使用 deployer .bin 通过 USB 远程刷写"
        echo "  3) 返回主菜单"

        read -r -p "请选择 [1-3]: " RP_OP
        case "${RP_OP}" in
            1)
                MODE_NAME="CAN"
                FW_CATEGORY="deployer"
                select_frequency
                find_firmware "rp2040" "deployer" "${FREQ_LABEL}" || manual_firmware_select
                flash_can
                ;;
            2)
                MODE_NAME="USB"
                FW_CATEGORY="deployer"
                FW_FILE=$(find "${FW_DIR_RP2040}" -maxdepth 1 -type f -name "*deployer*.bin" ! -path "*/old/*" | sort | head -1)
                if [[ -z "${FW_FILE}" ]]; then
                    manual_firmware_select
                else
                    print_success "找到固件: $(basename "${FW_FILE}")"
                fi
                flash_usb
                ;;
            *) return;;
        esac
        return
    fi

    if [[ "${MODE_NAME}" == "DFU" ]]; then
        print_step "DFU 模式刷写 STM32"
        select_fw_type
        if [[ "${FW_CATEGORY}" == "main" ]]; then
            FW_FILE=$(find "${FW_DIR_IDM}" -maxdepth 1 -type f -name "*.bin" ! -path "*/old/*" | sort | head -1)
        else
            FW_FILE=$(find "${FW_DIR_CANBOOT}" -maxdepth 1 -type f -name "*.bin" ! -path "*/old/*" | sort | head -1)
        fi
        if [[ -z "${FW_FILE}" ]]; then
            manual_firmware_select
        else
            print_success "找到固件: $(basename "${FW_FILE}")"
        fi
        flash_dfu
        return
    fi

    if [[ "${MODE_NAME}" == "USB" ]]; then
        FREQ_LABEL=""
    else
        select_frequency
    fi
    select_fw_type

    if ! find_firmware "${HW_PLATFORM}" "${FW_CATEGORY}" "${FREQ_LABEL}"; then
        manual_firmware_select
    fi

    case "${MODE_NAME}" in
        CAN) flash_can;;
        USB) flash_usb;;
    esac
}

# -----------------------------------------------------------
# 主菜单
# -----------------------------------------------------------
main_menu() {
    print_banner
    detect_environment

    while true; do
        echo -e "\n${BOLD}════════ 主菜单 ════════${NC}"
        echo "  1) 简易模式 (向导式逐步引导)"
        echo "  2) 高级模式 (一步到位配置)"
        echo "  3) 仅查询已连接设备"
        echo "  4) 退出"
        echo ""

        read -r -p "请选择 [1-4]: " MAIN_CHOICE

        case "${MAIN_CHOICE}" in
            1)
                select_mode
                if [[ "${MODE_NAME}" == "DFU" ]]; then
                    simple_flash
                else
                    simple_flash
                fi
                ;;
            2)
                select_mode
                advanced_flash
                ;;
            3)
                query_devices_only
                ;;
            4)
                echo ""
                print_info "已退出"
                exit 0
                ;;
            *)
                print_error "无效选项"
                ;;
        esac
    done
}

main_menu
