import asyncio
from boot import hello

"""
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
"""


async def read_small(reader, writer):
    """
    用来读取客户端请求的函数
    可以返回任何数据
    不接受上传文件等大数据
    """
    data = await reader.read(4096)
    # 读取客户端请求数据，最大读取4096字节
    segments = data.split(b"\r\n")
    # 将请求数据按行分割，得到一个字节串列表
    request_line = segments[0]
    # 取出请求行，也就是列表的第一个元素
    path = request_line.split(b" ")[1]
    # 将请求行按空格分割，取出第二个元素，也就是请求的路径

    response = (b"HTTP/1.1 200 OK\r\n"           # 状态行：版本 + 状态码 + 说明
                b"Content-Type: text/html\r\n"    # 响应头：告诉浏览器这是网页
                b"Connection: close\r\n"          # 处理完就关连接
                b"\r\n"                           # 空行
                + hello)                          # 正文

    writer.write(response)
    await writer.drain()
    # 返回数据，并且等待确认收到
    writer.close()
    await writer.wait_closed()
    # 关闭连接，等待关闭完成


async def main():
    server = await asyncio.start_server(read_small, "0.0.0.0", 80)
    print("服务器已启动，等待连接...")
    await server


asyncio.run(main())
# end of file





