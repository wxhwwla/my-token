import network  # type: ignore  # MicroPython 特有模块，IDE 无法解析属正常


wlan = network.WLAN(network.STA_IF)
# 板子就是wlan这个对象，他作为STA模式，也就是请求端的接口，连接wifi

with open("hello.html", "rb") as f:
    hello = f.read()

