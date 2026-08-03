import asyncio
import os
from boot import hello, filemanager, success
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


def format_size(size):
    if size < 1024:
        return str(size) + " B"
    elif size < 1024 * 1024:
        return "%.1f KB" % (size / 1024)
    else:
        return "%.1f MB" % (size / (1024 * 1024))

def get_file():
    rows = []
    files = os.listdir()
    # 遍历当前目录下的所有文件和文件夹
    for f in files:
        size = os.stat(f)[6]
        # 获取文件大小，os.stat() 返回一个元组，索引6是文件大小
        rows.append(b"<tr><td>%s</td><td>%s</td><td>%d</td></tr>" 
                    % (f.encode(), format_size(size).encode(), size))
        # 生成一个表格行，包含文件名、格式化后的大小和原始大小
        print(f, size)
    page = filemanager.replace(b"__FILES__", b"".join(rows))
    # 将 filemanager.html 中的 __FILES__ 替换为生成的表格行
    return page


async def read_small(reader, writer):
    """
    用来读取客户端请求的函数
    可以返回任何数据files = os.listdir()
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


    if path == b"/":
        # 如果请求路径是根目录，就返回 hello 网页
        response = (b"HTTP/1.1 200 OK\r\n"            # 状态行：版本 + 状态码 + 说明
                    b"Content-Type: text/html\r\n"    # 响应头：告诉浏览器这是网页
                    b"Connection: close\r\n"          # 处理完就关连接
                    b"\r\n"                           # 空行
                    + hello)                          # 正文
    elif path == b"/filemanager":
        page = get_file()
        # 如果请求路径是 /filemanager，就返回 filemanager 网页
        response = (b"HTTP/1.1 200 OK\r\n"            # 状态行：版本 + 状态码 + 说明
                    b"Content-Type: text/html\r\n"    # 响应头：告诉浏览器这是网页
                    b"Connection: close\r\n"          # 处理完就关连接
                    b"\r\n"                           # 空行
                    + page)                           # 正文
    elif path == b"/upload":
        boundary = data.split(b"boundary=")[1].split(b"\r\n")[0]
        # 如果请求是上传文件的 POST 请求，boundary 是分隔符，用来分割上传的文件数据
        parts = data.split(b"--" + boundary)
        # 将请求数据按 boundary 分割，得到一个列表，每个元素是一个上传的文件数据块
        header = parts[1].split(b"\r\n\r\n")[0]
        # 取出上传文件数据块的头部，也就是列表的第一个元素，按两个换行符分割，取出第一个部分
        filename = header.split(b'filename="')[1].split(b'"')[0]
        # 取出上传文件的文件名，按 filename=" 分割，取出第二个部分，再按 " 分割，取出第一个部分
        content = parts[1].split(b"\r\n\r\n")[1]
        # 取出上传文件数据块的内容，也就是列表的第一个元素，按两个换行符分割，取出第二个部分
        content = content.split(b"\r\n--" + boundary)[0]
        # 取出上传文件数据块的内容，按 boundary 分割，取出第一个部分
        with open(filename, "wb") as f:
            f.write(content)
            
        response = (b"HTTP/1.1 200 OK\r\n"
                    b"Content-Type: text/html\r\n"
                    b"Connection: close\r\n"
                    b"\r\n"
                    + "<html><body><h1>上传成功: ".encode()
                    + filename
                    + b"</h1></body></html>")

        
    else:
        # 如果请求路径不是以上两种，就返回 404 网页
        response = (b"HTTP/1.1 404 Not Found\r\n"     # 状态行：版本 + 状态码 + 说明
                    b"Content-Type: text/html\r\n"    # 响应头：告诉浏览器这是网页
                    b"Connection: close\r\n"          # 处理完就关连接
                    b"\r\n"                           # 空行
                    + b"<html><body><h1>404 Not Found</h1></body></html>")  # 正文

        
    writer.write(response)
    await writer.drain()
    # 返回数据，并且等待确认收到
    writer.close()
    await writer.wait_closed()
    # 关闭连接，等待关闭完成


async def main():
    server = await asyncio.start_server(read_small, "0.0.0.0", 80)
    # start_server 协程只创建服务器就返回（实测确认），accept 任务在后台运行，
    # 所以 main 必须保持事件循环不结束，否则后台任务被一起停掉
    print("服务器已启动，等待连接...")
    while True:
        await asyncio.sleep(3600)   # 保持事件循环，让后台 accept 任务持续运行


asyncio.run(main())
# end of file





