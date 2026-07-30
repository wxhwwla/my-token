import network
import time
from config import wifi_name, wifi_password


wlan = network.WLAN(network.STA_IF)
# 板子就是wlan这个对象，他作为STA模式，也就是请求端的接口，连接wifi
wlan.active(True)
# 给板子WiFi通电
wlan.connect(wifi_name, wifi_password)
# 让板子去连接WiFi，参数是WiFi的名称和密码

timeout = 10  # 设置超时时间为10秒
while timeout > 0:
    if wlan.isconnected():
        break
    time.sleep(2)
    timeout -= 2
if not wlan.isconnected():
    print("WiFi连接失败！")
else:
    print("WiFi连接成功！")
    print("IP地址:", wlan.ifconfig()[0])