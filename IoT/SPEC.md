# DeepSeek 用量 IoT 监控系统 — 规格说明 (SPEC)

## Problem Statement

DeepSeek API 用户在浏览器上查看每小时 token 用量不够直观，且无法在移动设备或非开发环境下便捷地实时监控。现有的数据导出方案需要手动在电脑上运行脚本，无法做到"随时看一眼"的体验。需要一个低功耗、常开机的设备来持续采集、处理和展示用量数据。

## Solution

构建一个以 **LILYGO T-Dongle-S3 (ESP32-S3)** 为核心的 IoT 监控系统，负责每小时从 DeepSeek 开放平台拉取 API 用量数据，生成可视化图表，并通过内网穿透对外提供 Web 访问。配套的电脑端脚本负责登录 DeepSeek 获取用户 token，通过保活机制维持 token 有效。

整体架构采用**发送端（ESP32）做轻量处理、预留未来迁移能力**的设计——当前 ESP32 承担下载、解析、展示职责，但模块化设计允许未来将计算密集部分迁移到树莓派或服务器。

开发流程优先级：
1. **基础设施** — WiFi 在线文件管理、UDP 广播发现、内网穿透（先铺路）
2. **数据管道** — ZIP 解析、CSV 计算、HTML 图表生成
3. **Token 管理** — 接收端发送 token、两段式校验、保活机制
4. **收尾** — 省电休眠、日志系统、月度归档

## User Stories

1. 作为 DeepSeek API 用户，我希望 ESP32 每小时自动下载最新的用量数据，避免手动操作
2. 作为 DeepSeek API 用户，我希望系统将 token 用量以柱状折线图展示，方便直观了解使用趋势
3. 作为 DeepSeek API 用户，我希望在外出时也能通过手机或电脑查看用量图表，不受局域网限制
4. 作为 DeepSeek API 用户，我希望系统在 WiFi 断开后自动恢复，减少维护工作量
5. 作为 DeepSeek API 用户，我希望系统能够重试失败的下载，提高数据采集的可靠性
6. 作为 DeepSeek API 用户，我希望每个月的旧数据能打包发送到电脑存档，节省 TF 卡空间
7. 作为 DeepSeek API 用户，我希望 Web 页面有基本的访问密码保护，防止他人查看用量数据
8. 作为 DeepSeek API 用户，我希望 ESP32 接收新 token 时自动验证其有效性，避免使用错误 token 导致任务失败
9. 作为 DeepSeek API 用户，我希望接收端发送 token 后能收到 ESP32 的确认，确保通信正常
10. 作为 DeepSeek API 用户，我希望系统提供详细的运行日志，方便排查下载或网络异常
11. 作为 DeepSeek API 用户，我希望 ESP32 在没有收到新 token 时自动进入省电轮询模式，降低功耗
12. 作为 DeepSeek API 用户，我希望系统架构支持未来迁移到树莓派等更强的硬件，不影响上层逻辑
13. 作为开发者，我希望能通过电脑端的自动化脚本完成 token 登录和发送，减少手动操作
14. **作为开发者，我希望通过浏览器直接管理 ESP32 上的文件**，实现无线代码更新，避免频繁插拔 USB（新增）
15. **作为开发者，我希望 ESP32 自动通过 UDP 广播它的访问地址**，让我在网络中发现设备，不必记 IP（新增）
16. **作为开发者，我希望文件列表能按类型分组显示**，让我快速定位 Python 代码、HTML 页面、配置文件（新增）
17. **作为开发者，我希望核心系统文件在 Web 页面中标记为受保护**，防止误删导致设备变砖（新增）
18. **作为开发者，我即使想删受保护文件也能通过修改白名单来实现**，不让功能成为障碍（新增）

## Implementation Decisions

### 0. 开发流程调整

原规划（SPEC v1）建议先做 ZIP 解析原型验证。实际开发中发现更高效的路径是**先铺基础设施，再做业务逻辑**：

```
Original:  烧录 → ZIP解析原型 → WiFi → Web → 穿透 → Token → 休眠
Revised:   烧录 → WiFi → Web(带文件管理) → UDP广播 → 穿透 → ZIP解析 → Token → 休眠
```

原因：WiFi + Web 文件管理打通后，后续所有代码修改都可以通过浏览器上传，开发效率大幅提升。

### 1. 双端架构（不变）

- **发送端（ESP32-S3）**：运行 MicroPython，负责数据下载、解析、Web 服务、保活确认
- **接收端（电脑）**：运行 Python 脚本（Playwright 自动化），负责 DeepSeek 登录获取 usertoken、每小时发送 token、接收保活确认

两端通过**局域网 UDP 广播 + 内网穿透域名**实现通信，数据流单向（接收端→发送端，仅传输 token）。

### 2. 固件与模块（已验证，修正）

**实测结果**（MicroPython v1.29.0-preview on ESP32-S3）：

| 模块 | 状态 | 说明 |
|------|------|------|
| `machine` | ✅ | 硬件控制 |
| `network` | ✅ | WiFi 连接 |
| `urequests` | ✅ | HTTP 请求 |
| `deflate` | ✅ | **替代 `uzlib`**（MicroPython v1.23+ 已改名） |
| `uos` | ✅ | 文件系统 |
| `json` | ✅ | JSON 解析 |
| `_thread` | ✅ | 双核多线程 |
| `socket` | ✅ | TCP/UDP 网络编程 |
| `esp32` | ✅ | 芯片特定功能 |
| `uzlib` | ❌ | 已废弃，被 `deflate` 取代 |

**变更**：ZIP 解析代码使用 `deflate.DeflateIO` 替代 `uzlib.DecompIO`。

- **芯片**：ESP32-S3（LILYGO T-Dongle-S3 Dual）
- **语言**：MicroPython（官方固件 v1.29+）
- **Flash**：16MB，已验证
- **RAM**：217KB 空闲
- **TF 卡**：FAT 文件系统，待验证

### 3. 文件管理与 OTA 更新（新增）

ESP32 的 Web 服务器扩展为**文件管理服务器**，提供以下 API：

| 路径 | 方法 | 功能 |
|------|------|------|
| `/` | GET | 文件管理首页（文件列表 + 上传表单） |
| `/filemanager` | GET | 文件管理页面（独立页，导航可切换） |
| `/upload` | POST | 上传文件到 ESP32 |
| `/delete` | POST | 删除指定文件 |
| `/dashboard` | GET | 用量看板（预留） |
| `/status` | GET | 系统状态页（预留） |
| `/settings` | GET | 设置页（预留） |

**文件列表展示方式**：
- 扁平列表，无嵌套目录树（MicroPython 文件系统天然扁平）
- 按文件类型分组显示：Python 模块、HTML 页面、配置文件、其他
- 每个文件显示：文件名、大小（字节）、类型标签

**文件保护机制（防误删）**：
- 基于文件名白名单。白名单内的文件在 Web 界面中不可删除（删除按钮灰掉或隐藏）
- 白名单文件在列表中用不同颜色标识（如绿色），一眼可辨
- 白名单由代码硬编码定义，包含核心系统文件：`boot.py`、`main.py`、`config.py`、`web_server.py`、`wifi_connect.py` 等
- 白名单不防"直接 upload 覆盖"——如果你上传同名文件，旧文件会被覆盖。这是合理行为：你要改代码就是重新上传
- 要删除白名单文件的流程：改代码移除白名单 → 上传更新 → 再删除。有意删的操作多一步，误删几乎不可能
- 白名单文件本身也可被自己的更新覆盖，不阻止正常开发

**上传实现要点**：
- 解析 `multipart/form-data` 格式的 POST body
- 文件名支持中英文
- 限制文件大小防止撑爆 RAM（每次 1-2KB 足够）
- 覆盖已有文件不影响当前运行中的程序（MicroPython 已 import 的模块不受影响——重启后才生效）
- 上传目标目录：当前为根目录 `/`，未来可扩展为下拉框选择子目录

### 4. WiFi 连接（已验证）

```python
# 已验证的伪代码
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)
# 轮询 wlan.isconnected() 直到超时
```

要点（保持）：
- 连接是异步的，需要轮询等待
- 设 10-15 秒超时
- 需断线检测 + 自动重连

### 5. UDP 广播（规划中）

ESP32 每分钟通过 UDP 广播自己的内网穿透域名（或内网 IP）。接收端收到后回复确认消息，确认后停止广播。

实现方式：
- 广播地址：`255.255.255.255` 或子网广播
- 端口：双方约定（如 8888）
- 消息格式：纯文本 JSON，包含设备名和域名/IP

### 6. 内网穿透（规划中）

使用 `esp32-tunnel` 库调用 localtunnel，重启后域名变化，通过 UDP 广播重新分发。

**待验证**：`esp32-tunnel` 库是否可通过 `mip` 安装，或需要手动从 GitHub 下载后放到 `lib/`。

### 7. Web 架构：导航布局（新增）

为支持多页面（文件管理、用量看板、系统状态、设置）且避免后续大改，Web UI 采用**固定侧边导航栏 + 右侧内容区**布局：

```
┌─────────┬─────────────────────────┐
│ 导航栏   │                         │
│          │   内容区                 │
│ 📁 文件   │   (当前页面内容)          │
│ 📊 看板   │                         │
│ ⚙ 状态   │                         │
│ 🔧 设置   │                         │
│          │                         │
│          │                         │
└─────────┴─────────────────────────┘
```

**实现方式**（不使用 JavaScript/SPA）：
- 每个页面由 Python 函数生成完整 HTML，包含侧边栏
- 导航栏 HTML 由公共函数生成，所有页面共用同一份代码
- 切换导航项 → 浏览器请求新 URL → ESP32 返回嵌有同一导航栏的完整页面
- 纯 HTTP，无前端路由，无 JavaScript

**导航项**：

| 项 | 路由 | 状态 |
|----|------|------|
| 文件管理 | `/filemanager` | 即将实现 |
| 用量看板 | `/dashboard` | 预留 |
| 系统状态 | `/status` | 预留 |
| 设置 | `/settings` | 预留 |

### 8. Web 服务器实现（更新）

当前实现：基于 `socket` 的简易 HTTP 服务器，单线程循环接受连接。

**请求路由逻辑**：
```
收到请求 → 解析 GET/POST + 路径
  ├─ GET /           → 发送文件管理器首页
  ├─ GET /filemanager → 文件管理页
  ├─ POST /upload    → 接收文件并保存
  ├─ POST /delete    → 删除文件（白名单检查）
  ├─ GET /dashboard  → [预留] 用量看板
  ├─ GET /status     → [预留] 系统状态
  ├─ GET /settings   → [预留] 设置
  ├─ GET /{filename} → 查找本地文件，存在则返回
  └─ 其他            → 404
```

演进路径：
1. 当前：单页面 Hello World ✅（已演进为 asyncio 多路由版）
2. 短期：文件管理服务器（上传/删除/文件列表）← 进行中（文件列表 ✅，上传/删除未做）
3. 中期：嵌入 DeepSeek 用量图表
4. 长期：密码保护、文件缓存优化

**asyncio 实测修正（重要）**：
- MicroPython v1.29 的 `asyncio.start_server` 协程**只创建服务器就返回**（不挂起），返回的 `Server` 对象**不可 await**（`await server` 报 `TypeError: 'Server' object isn't iterable`）
- 正确模式：`server = await asyncio.start_server(handler, host, port)` + `while True: await asyncio.sleep(3600)` 保持事件循环（accept 任务由 start_server 内部创建，main 只是"看门人"）
- `serve_forever` 不存在于 MicroPython 的 Server；官方讨论 #12219 的 `gather(server, other_tasks)` 写法要求 other_tasks 永久挂起，否则 main 结束后事件循环停止、后台任务被杀

### 9. 数据获取与处理（未开始）

- **下载**：ESP32 通过 `urequests` 使用 usertoken 从 DeepSeek API 下载小时级别的用量 ZIP
- **ZIP 解析**：使用 `deflate.DeflateIO`（替代 `uzlib.DecompIO`）+ 轻量 ZIP Local File Header 解析
- **CSV 解析**：从 CSV 尾部读取增量数据，计算该小时的 token 消耗量、使用方向和费用
- **存储**：原始 ZIP 暂存 TF 卡，每月由接收端打包归档一次

### 10. Token 管理（未开始）

采用**两段式 Token 校验机制**（不变）：
- `working_token`：当前生效的 token
- `pending_token`：新收到的待验证 token
- 收到新 token → 存入 `pending_token` → 发一次 API 测试请求 → 若返回 200，替换 `working_token`
- 接收端每小时发送一次 token，ESP32 需在 2 分钟内回复确认

### 11. 省电与保活机制（未开始）

同原 SPEC，使用 Modem Sleep（轻睡眠），WiFi 关闭，RTC 每 10 分钟唤醒检查。

### 12. 模块化文件结构（已确定）

```
TX/
├── boot.py              # [系统] 上电启动：WiFi + 服务器自启动
├── main.py              # [系统] 主循环（逐步填充业务逻辑）
├── config.py            # 配置：WiFi 密码、API key 等
├── wifi_connect.py      # WiFi 连接 + 断线重连
├── web_server.py        # HTTP 服务器 + 文件管理 + 静态文件服务
├── udp_broadcast.py     # UDP 广播模块（待建）
├── tunnel.py            # 内网穿透模块（待建）
├── deepseek_api.py      # DeepSeek API 客户端（待建）
├── zip_parser.py        # ZIP/CSV 解析（待建）
├── html_builder.py      # HTML 图表生成（待建）
├── logger.py            # 日志模块（待建）
├── index.html           # Web 首页
└── lib/                 # 第三方库
    └── esp32_tunnel.py  # esp32-tunnel（待安装）
```

### 13. 硬件特性确认（勘误）

**LILYGO T-Dongle-S3 Dual 只有一个物理按钮（BOOT 键），没有独立的 RESET 键。**

进入下载模式的正确操作：
1. 拔掉 USB
2. 按住 BOOT 按钮
3. 插回 USB
4. 等 2 秒松开

### 13.5 SD 卡挂载（实测确认 2026-08）

**T-Dongle-S3 的 TF 卡槽是 SDMMC 4-bit 模式，必须显式指定引脚**（官方默认配置无效）：

```python
from machine import SDCard
import os
sd = SDCard(slot=0, sck=12, cmd=16, data=(14, 17, 21, 18), width=4)
os.mount(sd, "/sd")
```

- 引脚：SCK=GPIO12、CMD=GPIO16、DATA0-3=GPIO14/17/21/18（来源：LILYGO T-Dongle-S3 issue #11）
- `SDCard()` 默认参数（SDMMC slot 2）对象能创建但 mount 报 `OSError: 16 (ENODEV)`——引脚不对
- 本固件的 SDCard 不支持 SPI 模式参数（`slot=None` 报 TypeError，SPI 引脚报 ValueError）
- **MicroPython 的 soft reset 保留 VFS 挂载**——boot.py 每次启动重复挂载已挂载的 `/sd` 报 `EPERM`，挂载前应检查：`if "sd" not in os.listdir("/")`
- 挂载代码放 boot.py（`try/except` 兜底，没插卡不崩溃），已实测：用户 32GB FAT 卡挂载成功，含 `System Volume Information` + 数据文件
- 文件列表页 `os.stat()` 对目录返回大小 0（sd 显示 0 属正常）

## Testing Decisions

### 测试原则（不变）

- 优先在外层行为上测试，避免绑定实现细节
- 硬件项目测试分为三层：
  1. **模拟层**：在电脑上模拟 ESP32 逻辑（ZIP 解析、CSV 计算、HTML 生成）
  2. **硬件-in-the-loop**：在真实 ESP32 上运行，验证 TF 卡 IO、WiFi 连接、实际下载
  3. **端到端**：发送端+接收端联调，验证完整一小时周期

### 测试点

| 测试内容 | 层级 | 说明 |
|---------|------|------|
| ZIP Local File Header 解析 | 模拟层 | 验证解析逻辑是否正确提取 deflate 数据 |
| CSV 增量计算 | 模拟层 | 给定两份 CSV，验证差值计算正确 |
| HTML 图表生成 | 模拟层 | 验证生成的 HTML 包含正确的 Chart.js 配置 |
| token 两段式校验逻辑 | 模拟层 | 验证正确/错误 token 的处理分支 |
| **文件上传功能** | **硬件层** | 上传 .py 文件，验证 ESP32 文件系统上确实多出了文件 |
| **文件名白名单保护** | **硬件层** | 尝试通过 Web 删除受保护文件，验证被拒绝 |
| **非白名单文件删除** | **硬件层** | 删除上传的测试文件，验证成功 |
| **文件列表正确性** | **硬件层** | ✅ 已完成（/filemanager 实测：文件列表 + 大小 + sd 挂载点显示正常） |
| **UDP 广播收发** | **硬件层** | **验证设备发现功能（新增）** |
| TF 卡读写 | 硬件层 | 验证文件创建、写入、读取的稳定性 |
| WiFi 重连 | 硬件层 | 验证断网后自动恢复 |
| 端到端一小时循环 | E2E | 验证完整周期不崩溃 |
| 保活超时→休眠→恢复 | E2E | 验证休眠唤醒后能恢复工作 |
| **localtunnel 内网穿透** | **硬件层** | **验证外网可访问（新增）** |

### 现有参考

- [下载脚本](A1-get-zip.py) — 可用于生成测试用的真实 ZIP 数据
- [ZIP 转 CSV 脚本](A2-zip-to-csv.py) — 输出的 CSV 格式与 ESP32 处理的一致，可用于对比验证解析结果

## Out of Scope（保持）

- **异地网络**（接收端和发送端不在同一局域网）— 当前仅在家庭网络下工作
- **HTTPS** — localtunnel 免费层 HTTPS 支持有限，当前使用 HTTP + 密码保护
- **多用户/多设备** — 当前仅服务一个用户/一个接收端
- **短信/推送告警** — 不会主动推送用量告警，仅提供 Web 页面查看
- **电池供电优化** — 使用 USB 供电
- **OTA 固件更新** — 指远程更新 MicroPython 固件本身（区别于在线管理应用文件）

## Further Notes

- `uzlib` → `deflate` 模块改名已确认。之前的 SPEC 引用 `uzlib.DecompIO`，实际应使用 `deflate.DeflateIO`
- T-Dongle-S3 Dual 的 CH342 芯片提供双串口：COM3 (SERIAL-A) 用于烧录和 REPL，COM6 (SERIAL-B) 备用
- 烧录按键操作已更正：只有一个 BOOT 键，无 RESET 键
- 开发初期建议在电脑本地保持文件副本，ESP32 文件系统可能因意外断电损坏
- 建议在 `boot.py` 稳定后再放入自启动代码——开发阶段建议手动启动
