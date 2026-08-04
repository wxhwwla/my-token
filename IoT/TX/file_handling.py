import os
from boot import filemanager


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

