# DeepSeek 用量 IoT 监控系统 — 规格说明 (SPEC)

## Problem Statement

DeepSeek API 用户在浏览器上查看每小时 token 用量不够直观，且无法在移动设备或非开发环境下便捷地实时监控。现有的数据导出方案需要手动在电脑上运行脚本，无法做到"随时看一眼"的体验。需要一个低功耗、常开机的设备来持续采集、处理和展示用量数据。

## Solution

构建一个以 **LILYGO T-Dongle-S3 (ESP32-S3)** 为核心的 IoT 监控系统，负责每小时从 DeepSeek 开放平台拉取 API 用量数据，生成可视化图表，并通过内网穿透对外提供 Web 访问。配套的电脑端脚本负责登录 DeepSeek 获取用户 token，通过保活机制维持 token 有效。

整体架构采用**发送端（ESP32）做轻量处理、预留未来迁移能力**的设计——当前 ESP32 承担下载、解析、展示职责，但模块化设计允许未来将计算密集部分迁移到树莓派或服务器。

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

## Implementation Decisions

### 1. 双端架构

- **发送端（ESP32-S3）**：运行 MicroPython，负责数据下载、解析、Web 服务、保活确认
- **接收端（电脑）**：运行 Python 脚本（Playwright 自动化），负责 DeepSeek 登录获取 usertoken、每小时发送 token、接收保活确认

两端通过**局域网 UDP 广播 + 内网穿透域名**实现通信，数据流单向（接收端→发送端，仅传输 token）。

### 2. 数据获取与处理

- **下载**：ESP32 通过 `urequests` 使用 usertoken 从 DeepSeek API 下载小时级别的用量 ZIP
- **ZIP 解析**：使用轻量 ZIP 解析器（手动解析 ZIP Local File Header + `uzlib.DecompIO`）提取 CSV — 小时 ZIP 预计 1-3KB，全量读入内存后再解析
- **CSV 解析**：从 CSV 尾部读取增量数据，计算该小时的 token 消耗量、使用方向和费用
- **存储**：原始 ZIP 暂存 TF 卡，每月由接收端打包归档一次

### 3. Token 管理

采用**两段式 Token 校验机制**防止意外锁死（来自 grilling session 的结论）：

- ESP32 维护两个 token 槽位：
  - `working_token`：当前生效的 token，用于 API 调用
  - `pending_token`：新收到的待验证 token
- 收到新 token → 存入 `pending_token` → 发一次 API 测试请求 → 若返回 200，替换 `working_token` → 若返回 401，丢弃 `pending_token` 并告警
- 接收端每小时发送一次 token，ESP32 需在 2 分钟内回复确认

### 4. 数据可视化

- ESP32 在本地拼接 HTML 字符串，内嵌 Chart.js 的 CDN 链接
- 页面包含：
  - 用户密码验证（HTTP Basic Auth 或查询参数 `?key=xxx`）
  - 每小时 token 使用量的柱状折线图（Chart.js）
- 每小时更新 HTML 文件，覆盖旧文件
- **安全增强**：在 localtunnel 域名基础上，访问路径加入固定密钥参数（如 `?key=<password>`），增加暴力扫描难度

### 5. 网络与通信

- **局域网发现**：ESP32 每分钟 UDP 广播自己的内网穿透域名，接收端收到后回复确认消息，确认后停止广播
- **内网穿透**：使用 `esp32-tunnel` 库调用 localtunnel，重启后域名变化，通过 UDP 广播重新分发
- **重启失联防护**：重启后重复广播流程，接收端脚本自动响应，无需人工介入

### 6. 省电与保活机制（来自 grilling session 的设计）

当 ESP32 连续一小时内未收到接收端发来的 token：

```
进入 Modem Sleep（轻睡眠）：
  → WiFi 关闭
  → CPU 暂停
  → RTC 定时器每 10 分钟唤醒一次
  
唤醒后：
  1. 打开 WiFi
  2. 检查 TF 卡上是否有新 token 标记文件
  3. 有 → 恢复正常运行，进入每小时循环
  4. 没有 → 继续 lightsleep(600_000)
```

不使用深度睡眠（Deep Sleep），因为深度睡眠下无法被网络包唤醒，必须用 RTC 定时器自唤醒轮询。接收端发送 token 时写入本地标记，ESP32 醒来主动读取。

### 7. 日志系统

- 日志采用紧凑的**模块映射编码**，例如：模块 `100`（网络层）+ 状态码 `200`（正常）→ `100200`
- 每满 10-20 条批量写入 TF 卡一次，减少写入磨损
- 日志记录：网络状态、下载结果、解析状态、token 验证结果、异常堆栈

### 8. 月度数据归档

- 每月末（或月初），ESP32 将上月的 ZIP 文件夹打包发送到电脑
- 电脑接收到后决定保留或删除
- ESP32 本地清理已归档的数据

### 9. 固件与硬件资源

- **芯片**：ESP32-S3（LILYGO T-Dongle-S3 Dual）
- **语言**：MicroPython（官方固件）
- **Flash**：16MB，需确认官方固件包含 `uzlib`、`_thread`、`urequests`、`esp32-tunnel` 等模块
- **TF 卡**：FAT 文件系统，小时级写入，使用寿命充足
- 若 Flash 空间紧张，可自编译 MicroPython 固件，仅包含所需模块

## Testing Decisions

### 测试原则

- 优先在外层行为上测试，避免绑定实现细节
- 硬件项目测试分为三层：
  1. **模拟层**：在电脑上模拟 ESP32 逻辑（ZIP 解析、CSV 计算、HTML 生成）—— 最快、最可靠
  2. **硬件-in-the-loop**：在真实 ESP32 上运行，验证 TF 卡 IO、WiFi 连接、实际下载
  3. **端到端**：发送端+接收端联调，验证完整一小时周期

### 测试点

| 测试内容 | 层级 | 说明 |
|---------|------|------|
| ZIP Local File Header 解析 | 模拟层 | 验证解析逻辑是否正确提取 deflate 数据 |
| CSV 增量计算 | 模拟层 | 给定两份 CSV，验证差值计算正确 |
| HTML 图表生成 | 模拟层 | 验证生成的 HTML 包含正确的 Chart.js 配置 |
| token 两段式校验逻辑 | 模拟层 | 验证正确/错误 token 的处理分支 |
| TF 卡读写 | 硬件层 | 验证文件创建、写入、读取的稳定性 |
| WiFi 重连 | 硬件层 | 验证断网后自动恢复 |
| 端到端一小时循环 | E2E | 验证完整周期不崩溃 |
| 保活超时→休眠→恢复 | E2E | 验证休眠唤醒后能恢复工作 |

### 现有参考

项目已存在的脚本可复用为测试参考：
- [下载脚本](A1-get-zip.py) — 可用于生成测试用的真实 ZIP 数据
- [ZIP 转 CSV 脚本](A2-zip-to-csv.py) — 输出的 CSV 格式与 ESP32 处理的一致，可用于对比验证解析结果

## Out of Scope

- **异地网络**（接收端和发送端不在同一局域网）— 当前仅在家庭网络下工作，异地场景留待后续扩展
- **HTTPS** — localtunnel 免费层 HTTPS 支持有限，当前使用 HTTP + 密码保护
- **多用户/多设备** — 当前仅服务一个用户/一个接收端
- **短信/推送告警** — 不会主动推送用量告警，仅提供 Web 页面查看
- **电池供电优化** — 使用 USB 供电，不追求微安级功耗优化
- **OTA 更新** — 初次实现暂不包含远程固件更新

## Further Notes

- ZIP 解析是最大的技术未知数，建议先做**原型验证**：在电脑上用 MicroPython 兼容的方式写 ZIP 解析逻辑，确认方案可行后再移植到 ESP32
- localtunnel 的可靠性未经验证，如果生产使用应考虑更稳定的隧道方案（如 frp、Tailscale）
- ESP32 固件模块清单需要确认：`uzlib`、`_thread`、`urequests`、`machine`、`network` 是必需的，`esp32-tunnel` 可能需手动安装
- 项目初期单核处理即可满足性能需求，双核（`_thread`）是优化选项，非必需
- 建议在开发阶段保留电脑端的下载+解析脚本作为"参考实现"，ESP32 的输出可以与电脑输出做比对验证正确性
