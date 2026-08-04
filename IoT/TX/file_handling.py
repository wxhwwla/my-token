import os
from boot import filemanager

try:
    import protected_files_names
    # 这里尝试导入 protected_files_names 模块
    # 如果存在，就可以使用其中的 names 列表来保护文件不被删除
except ImportError:
    protected_files_names = None


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


def upload(data):
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
    return(filename)


def delete(data):
    body = data.split(b"\r\n\r\n")[1]
    # 取出请求体，也就是列表的第二个元素，按两个换行符分割，取出第二个部分
    filenames = body.split(b"=")[1]
    # 取出请求体中的文件名，按 = 分割，取出第二个部分
    filename = filenames.split(b" ")
    # 将文件名按空格分割，得到一个列表，每个元素是一个文件名

    results = []
    for i in filename:
        name = i.decode()
        if name not in os.listdir():
            results.append(i + " 文件不存在".encode())
        elif protected_files_names and i in protected_files_names.names:
            results.append(i + " 受保护，拒绝删除".encode())
        else:
            os.remove(name)
            results.append(i + " 已删除".encode())

    return b"<br>".join(results)


    