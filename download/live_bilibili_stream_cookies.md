# B站Cookies获取工具 - 使用文档

## 一、功能概述

本工具用于获取B站（bilibili）网站的Cookies并转换为Netscape HTTP Cookie File格式，主要功能包括：

1. **Cookies获取**：使用Playwright自动化浏览器访问B站直播页面获取Cookies
2. **格式转换**：将Cookies转换为Netscape格式，可直接用于yt-dlp/curl等工具
3. **文件输出**：输出到指定的Cookies文件，默认文件名 `live.bilibili.com_cookies.txt`

## 二、实现原理

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        主进程                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  1. 解析命令行参数                                         │  │
│  │  2. 初始化Cookies获取器                                   │  │
│  │  3. 调用Playwright获取Cookies                             │  │
│  │  4. 过滤B站相关Cookies                                   │  │
│  │  5. 转换为Netscape格式                                    │  │
│  │  6. 保存到文件并显示预览                                   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Playwright子进程                        │  │
│  │  1. 启动无头Chromium浏览器                                │  │
│  │  2. 创建浏览器上下文                                      │  │
│  │  3. 访问B站直播页面                                       │  │
│  │  4. 获取页面所有Cookies                                   │  │
│  │  5. 返回Cookies列表                                       │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Cookie获取流程

工具通过以下步骤获取B站Cookies：

1. **启动浏览器**：使用Playwright启动无头Chromium浏览器
2. **访问B站**：导航到B站直播页面 `https://live.bilibili.com/`
3. **等待加载**：等待网络空闲（`networkidle`），确保页面完全加载
4. **获取Cookies**：从浏览器上下文获取所有Cookies
5. **过滤筛选**：只保留B站域名相关的Cookies（`.bilibili.com`, `live.bilibili.com`, `www.bilibili.com`）
6. **格式转换**：转换为Netscape HTTP Cookie File格式
7. **保存文件**：输出到指定文件

### 2.3 Cookie域名过滤

工具只保留以下B站域名的Cookies：

| 域名模式 | 说明 |
|---------|------|
| `.bilibili.com` | B站主域名（包含所有子域名） |
| `live.bilibili.com` | B站直播子域名 |
| `www.bilibili.com` | B站官网子域名 |

这种过滤机制确保只获取与B站相关的Cookies，避免混入其他网站的Cookies。

### 2.4 Netscape格式转换

Netscape HTTP Cookie File是yt-dlp和curl使用的标准Cookies格式，每行包含7个字段，用tab分隔：

| 字段 | 说明 | 示例 |
|------|------|------|
| domain | 域名 | `.bilibili.com` |
| flag | 是否包含子域 | `TRUE` |
| path | 路径 | `/` |
| secure | 是否需要HTTPS | `FALSE` |
| expiration | 过期时间戳（0表示会话Cookie） | `1783132786` |
| name | Cookie名称 | `bili_ticket` |
| value | Cookie值 | `eyJhbGciOiJIUzI1NiIs...` |

转换逻辑：
- 域名以`.`开头时，`flag`设为`TRUE`（包含子域）
- 否则`flag`设为`FALSE`
- `secure`字段根据原始Cookie的secure属性设置
- 过期时间优先使用`expires`字段，其次使用`expiry`字段，都不存在则设为0

## 三、调用接口

### 3.1 命令行接口

#### 基本使用

```bash
# 获取B站Cookies（默认输出到 live.bilibili.com_cookies.txt）
python get_bilibili_cookies.py
```

#### 指定输出文件

```bash
python get_bilibili_cookies.py --output my_cookies.txt
```

#### 同时保存JSON格式

```bash
python get_bilibili_cookies.py --save-json
```

#### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--output` | str | `live.bilibili.com_cookies.txt` | 输出的Cookies文件名（Netscape格式） |
| `--save-json` | bool | False | 是否同时保存JSON格式的Cookies文件 |

### 3.2 Python API接口

#### 初始化获取器

```python
from get_bilibili_cookies import BilibiliCookiesFetcher

# 使用默认输出文件
fetcher = BilibiliCookiesFetcher(output_file="live.bilibili.com_cookies.txt")
```

#### 获取Cookies

```python
cookies = fetcher.fetch_cookies()
if cookies:
    print(f"获取到 {len(cookies)} 个B站Cookies")
```

#### 转换为Netscape格式

```python
result_file = fetcher.convert_to_netscape(cookies)
if result_file:
    print(f"Cookies已保存到: {result_file}")
```

#### 保存为JSON

```python
json_file = fetcher.save_cookies_to_json(cookies)
if json_file:
    print(f"Cookies已保存到JSON: {json_file}")
```

#### 显示预览

```python
fetcher.show_preview(lines_count=15)
```

#### 完整示例

```python
from get_bilibili_cookies import BilibiliCookiesFetcher

# 初始化获取器
fetcher = BilibiliCookiesFetcher(output_file="live.bilibili.com_cookies.txt")

# 获取Cookies
cookies = fetcher.fetch_cookies()
if not cookies:
    print("未获取到Cookies")
    exit()

# 转换并保存
result_file = fetcher.convert_to_netscape(cookies)
if result_file:
    fetcher.show_preview()

# 可选：保存JSON格式
fetcher.save_cookies_to_json(cookies)
```

#### 类方法说明

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `__init__` | `output_file: str` | - | 初始化Cookies获取器 |
| `fetch_cookies` | - | `Optional[List[Dict]]` | 获取B站Cookies列表 |
| `convert_to_netscape` | `cookies: List[Dict]` | `Optional[Path]` | 转换为Netscape格式并保存 |
| `save_cookies_to_json` | `cookies: List[Dict]` | `Optional[Path]` | 保存为JSON格式 |
| `show_preview` | `lines_count: int = 15` | `None` | 显示Netscape格式文件预览 |

#### 内部方法说明（供扩展使用）

| 方法 | 说明 |
|------|------|
| `_is_bilibili_cookie(cookie)` | 判断Cookie是否属于B站域名 |
| `_format_cookies(cookies)` | 格式化Cookies列表，只保留B站相关的Cookies |

## 四、输出文件格式

### 4.1 Netscape格式（主输出）

文件名：`live.bilibili.com_cookies.txt`（默认）

```
# Netscape HTTP Cookie File
# This file is generated automatically. Do not edit.

.bilibili.com	TRUE	/	FALSE	1817433586	PVID	1
.bilibili.com	TRUE	/	FALSE	1783132786	bili_ticket	eyJhbGciOiJIUzI1NiIs...
.bilibili.com	TRUE	/	FALSE	1817433586	LIVE_BUVID	AUTO5517828735885796
live.bilibili.com	FALSE	/	FALSE	0	theme_style	light
```

### 4.2 JSON格式（可选）

文件名：`bilibili_cookies.json`

```json
[
  {
    "name": "bili_ticket",
    "value": "eyJhbGciOiJIUzI1NiIs...",
    "domain": ".bilibili.com",
    "path": "/",
    "expires": 1783132786,
    "secure": false,
    "httpOnly": false
  }
]
```

## 五、注意事项

### 5.1 依赖安装

确保已安装以下依赖：

```bash
# 安装Playwright
pip install playwright

# 安装Chromium浏览器
playwright install chromium
```

### 5.2 Cookie有效期

- **会话Cookie**：过期时间为0，关闭浏览器后失效
- **持久Cookie**：有明确的过期时间，在过期前一直有效
- 获取的Cookies有效期取决于B站服务器设置，通常为几天到几周

### 5.3 常见问题

**Q1: 获取不到Cookies或Cookies数量很少**

A: 请确保你已经在浏览器中登录过B站。Playwright启动的是一个全新的无头浏览器实例，不会共享你已登录的浏览器会话。

**Q2: Playwright安装失败**

A: 请确保网络连接正常，并使用管理员权限运行安装命令：

```bash
pip install playwright
playwright install chromium
```

**Q3: Cookies文件无法被yt-dlp识别**

A: 请检查文件格式是否正确。Netscape格式要求每行7个字段，用tab分隔。工具生成的文件应该是正确的格式。

**Q4: 获取的Cookies包含其他网站的Cookie**

A: 工具会自动过滤，只保留B站域名的Cookies。如果发现其他网站的Cookie，请检查B站页面是否嵌入了第三方服务。

### 5.4 与直播下载工具配合使用

本工具生成的Cookies文件可直接用于 `live_bilibili_stream_downloader.py`：

```bash
# 获取Cookies
python get_bilibili_cookies.py

# 开始录制直播（自动读取 live.bilibili.com_cookies.txt）
python live_bilibili_stream_downloader.py --live "https://live.bilibili.com/123456"
```

两个工具使用相同的默认Cookies文件名，无需额外配置即可配合使用。

### 5.5 安全提示

- **Cookies包含登录凭证**：获取的Cookies可能包含B站账号的登录信息，请妥善保管
- **不要提交到公共仓库**：不要将包含Cookies的代码或文件提交到公共代码仓库
- **仅用于合法用途**：获取和使用Cookies应遵守B站的使用条款和相关法律法规
- **定期更新Cookies**：Cookies会过期，需要定期重新获取

## 六、版本历史

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| 1.0.0 | 2026-07-01 | 初始版本，支持Playwright获取Cookies，转换为Netscape格式 |
