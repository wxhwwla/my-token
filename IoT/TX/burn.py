import esptool
import time
import os
import serial.tools.list_ports

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def flash_one_chip(port, firmware=None):
    """烧录单个芯片"""
    if firmware is None:
        firmware = os.path.join(BASE_DIR, "firmware.bin")

    if not os.path.isfile(firmware):
        print(f"❌ 固件文件不存在: {firmware}")
        return False

    print(f"开始烧录 {port} ...")

    baud_rates = [921600, 460800]
    last_error = None

    for baud in baud_rates:
        try:
            esptool.main([
                "--chip", "esp32s3",
                "--port", port,
                "--baud", str(baud),
                "write_flash",
                "--erase-all",
                "0x0", firmware
            ])
            print(f"✅ {port} 完成")
            return True
        except SystemExit as e:
            # esptool 成功 exit(0)，失败 exit(1)
            if e.code == 0:
                print(f"✅ {port} 完成")
                return True
            last_error = f"esptool 退出码 {e.code}"
            print(f"⚠️  {baud} 失败 ({last_error})，尝试降速..." if baud != baud_rates[-1] else f"❌ {baud} 失败 ({last_error})")
        except Exception as e:
            last_error = str(e)
            print(f"⚠️  {baud} 出错: {last_error}" if baud != baud_rates[-1] else f"❌ {baud} 出错: {last_error}")

    print(f"❌ {port} 烧录失败: {last_error}")
    return False

def main():
    # 1. 寻找串口
    ports = [
        p.device for p in serial.tools.list_ports.comports()
        if any(kw in p.description for kw in ["USB", "CH34", "CP210", "COM"])
    ]
    if len(ports) < 2:
        print("警告：只找到 {} 个端口，但 Dual 版本应有 2 个。".format(len(ports)))

    for idx, port in enumerate(ports):
        print(f"\n=== 开始烧录芯片 {idx+1} ({port}) ===")
        if flash_one_chip(port):
            print(f"芯片 {idx+1} 完成，等待 2 秒后继续...")
            time.sleep(2)
        else:
            print(f"芯片 {idx+1} 失败，请检查连接。")

if __name__ == "__main__":
    main()

    