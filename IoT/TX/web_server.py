import socket
from boot import hello
def start_server():
    addr = ("0.0.0.0", 80)
    # 默认监听所有可用的网络接口，端口号为80
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # AF_INET — 使用 IPv4 地址，SOCK_STREAM — TCP 协议
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # 告诉系统：如果这个端口刚被用过，允许立刻重用
    # 否则 ESP32 重启后要等几分钟才能再次启动服务器
    server.bind(addr)
    # 绑定地址和端口
    server.listen(1)
    # 开始监听，参数是最大连接数，这里设置为1
    
    print("服务器已启动，等待连接...")
    
    while True:
        conn, addr = server.accept()
        # 等客户端链接，然后得到链接的通道对象和客户端的ip地址端口号
        # 分别是 conn 和 addr
        print("收到连接:", addr)
        request = conn.recv(1024)
        print("收到请求:", request)
        
        response = ("HTTP/1.1 200 OK\r\n"
                    "Content-Type: text/html\r\n"
                    "Connection: close\r\n"
                    "\r\n" 
                    + hello)
        conn.send(response.encode())
        conn.close()

start_server()
