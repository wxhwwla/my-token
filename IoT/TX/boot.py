import os  # type: ignore  # MicroPython 特有模块，IDE 无法解析属正常
import network  # type: ignore  # MicroPython 特有模块，IDE 无法解析属正常
from machine import SDCard  # type: ignore  # MicroPython 特有模块，IDE 无法解析属正常


try:
    if "sd" not in os.listdir("/"):      # 还没挂载才挂
        sd = SDCard(slot=0, sck=12, cmd=16, data=(14, 17, 21, 18), width=4)
        os.mount(sd, "/sd")
        print("SD 卡已挂载到 /sd")
    else:
        print("SD 卡已在 /sd")
except Exception as e:
    print("SD 卡挂载失败:", e)

wlan = network.WLAN(network.STA_IF)
# 板子就是wlan这个对象，他作为STA模式，也就是请求端的接口，连接wifi

with open("hello.html", "rb") as f:
    hello = f.read()

with open("filemanager.html", "rb") as f:
    filemanager = f.read()

    