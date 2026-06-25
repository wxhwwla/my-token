# DeepSeek 用量数据导出工具

自动登录 DeepSeek 开放平台，下载每月 API 用量数据的 ZIP 文件。

## 功能

- 自动打开浏览器，登录 DeepSeek 开放平台
- 下载当前月份的用量数据（ZIP 格式）
- 加载时显示心跳提示，不干等
- 失败时自动截图 + 保存页面 HTML，方便排查

## 快速开始

### 1. 安装依赖

```bash
pip install playwright python-dotenv
playwright install chromium
```

### 2. 配置

复制 `.env.example` 为 `.env`，填写你的账号密码：

```env
USER_EMAIL = "your_email@example.com"
USER_PASSWORD = "your_password"
ZIP_SAVE_PATH = "./output-history/zip"
CSV_SAVE_PATH = "./output-history/csv"
ERROR_SAVE_PATH = "./output-history/error"
```

### 3. 运行

```bash
python get-zip.py
```

浏览器会自动弹出 → 登录 → 下载 → 保存到 `output-history/zip/`。

## 文件结构

```
├── get-zip.py               # 主程序
├── main.py                  # 入口（预留）
├── zip-to-csv.py            # ZIP 转 CSV（预留）
├── .env                     # 配置文件（不提交 Git）
├── .env.example             # 配置示例
├── requirements.txt         # Python 依赖
└── output-history/
    ├── zip/                 # 下载的 ZIP 文件
    ├── csv/                 # CSV 文件（预留）
    └── error/               # 运行失败时的截图和 HTML
```

## 注意

- 登录页面默认是验证码模式，脚本会自动切换到密码登录
- `.env` 文件包含你的账号密码，**不要提交到 Git**
- 首次运行需要安装 Chromium 浏览器（`playwright install chromium`）
