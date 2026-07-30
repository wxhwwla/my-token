import network


wlan = network.WLAN(network.STA_IF)
# 板子就是wlan这个对象，他作为STA模式，也就是请求端的接口，连接wifi

with open("hello.html", "r") as f:
    hello = f.read()

    