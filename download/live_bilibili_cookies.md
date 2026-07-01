# B站Cookies获取工具 - 使用文档

## 一、功能概述

本工具是一个基于Playwright的B站Cookies获取工具，支持以下两种模式：

| 模式 | 说明 | 默认输出文件 |
|------|------|-------------|
| **stream（直播）** | 获取B站直播页面Cookies | `live.bilibili.com_cookies.txt` |
| **video（视频）** | 获取B站视频页面Cookies | `www.bilibili.com_cookies.txt` |

**核心功能**：
1. 使用Playwright自动化浏览器访问B站
2. 过滤并提取B站域名的Cookies
3. 转换为Netscape HTTP Cookie File格式（yt-dlp/curl兼容）
4. 支持JSON格式导出
5. 提供文件预览功能

## 二、实现原理

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    B站Cookies获取器                          │
├─────────────────────────────────────────────────────────────┤
│  BilibiliCookiesFetcher                                    │
│  ├── BILIBILI_DOMAINS          # B站域名列表               │
│  ├── BILIBILI_LIVE_URL         # 直播页面URL               │
│  ├── BILIBILI_VIDEO_URL        # 视频页面URL               │
│  ├── _is_bilibili_cookie()     # 判断B站Cookie             │
│  ├── _format_cookies()         # 格式化Cookies              │
│  ├── _get_url()                # 获取当前模式URL            │
│  ├── _get_mode_name()          # 获取模式名称               │
│  ├── fetch_cookies()           # 获取Cookies               │
│  ├── convert_to_netscape()     # 转换为Netscape格式         │
│  ├── save_cookies_to_json()    # 保存为JSON                 │
│  └── show_preview()            # 显示文件预览               │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Cookie获取流程

1. **启动浏览器**：使用Playwright启动无头Chromium浏览器
2. **访问页面**：根据模式访问直播或视频页面
3. **获取Cookies**：从浏览器上下文获取所有Cookies
4. **过滤Cookies**：只保留B站域名相关的Cookies
5. **格式转换**：转换为Netscape HTTP Cookie File格式
6. **输出文件**：保存到指定的输出文件

### 2.3 域名过滤规则

**B站域名**：
- `.bilibili.com`
- `live.bilibili.com`
- `www.bilibili.com`
- `video.bilibili.com`

### 2.4 Netscape格式转换

转换为标准的Netscape HTTP Cookie File格式，每行包含7个字段，用Tab分隔：

| 字段 | 说明 | 示例 |
|------|------|------|
| domain | 域名 | `.bilibili.com` |
| flag | 是否包含子域 | `TRUE`/`FALSE` |
| path | 路径 | `/` |
| secure | 是否需要HTTPS | `TRUE`/`FALSE` |
| expires | 过期时间戳 | `1783132786` |
| name | Cookie名称 | `bili_ticket` |
| value | Cookie值 | `xxx...` |

## 三、调用接口

### 3.1 命令行接口

#### 基本用法

```bash
# 获取B站直播Cookies（默认）
python get_bilibili_cookies.py

# 获取B站视频Cookies
python get_bilibili_cookies.py --mode video
```

#### 参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--mode` | string | 否 | `stream` | 获取模式：`stream`（直播）或 `video`（视频） |
| `--output` | string | 否 | 自动 | 输出的Cookies文件名 |
| `--save-json` | flag | 否 | - | 同时保存JSON格式的Cookies文件 |

#### 默认输出文件名

| 模式 | 默认文件名 |
|------|-----------|
| stream（直播） | `live.bilibili.com_cookies.txt` |
| video（视频） | `www.bilibili.com_cookies.txt` |

#### 使用示例

```bash
# 获取B站直播Cookies
python get_bilibili_cookies.py

# 获取B站视频Cookies
python get_bilibili_cookies.py --mode video

# 获取Cookies并保存JSON
python get_bilibili_cookies.py --mode stream --save-json

# 获取Cookies并指定输出文件
python get_bilibili_cookies.py --mode video --output my_video_cookies.txt
```

### 3.2 Python API接口

#### 导入模块

```python
from get_bilibili_cookies import BilibiliCookiesFetcher
```

#### 使用直播模式

```python
# 创建直播模式获取器
fetcher = BilibiliCookiesFetcher(
    output_file="live.bilibili.com_cookies.txt",
    mode="stream"
)

# 获取Cookies
cookies = fetcher.fetch_cookies()

# 转换为Netscape格式
fetcher.convert_to_netscape(cookies)

# 显示预览
fetcher.show_preview()

# 保存JSON
fetcher.save_cookies_to_json(cookies)
```

#### 使用视频模式

```python
# 创建视频模式获取器
fetcher = BilibiliCookiesFetcher(
    output_file="www.bilibili.com_cookies.txt",
    mode="video"
)

# 获取Cookies
cookies = fetcher.fetch_cookies()

# 转换并保存
fetcher.convert_to_netscape(cookies)
```

## 四、输出文件格式

### 4.1 Netscape格式（默认）

文件名：根据模式自动命名

```
# Netscape HTTP Cookie File
# This file is generated automatically. Do not edit.

.bilibili.com	TRUE	/	FALSE	1814416037	buvid3	xxx...
.bilibili.com	TRUE	/	FALSE	1783139238	bili_ticket	xxx...
www.bilibili.com	FALSE	/	FALSE	0	session_only	xxx...
```

### 4.2 JSON格式（可选）

文件名：`bilibili_{模式}_cookies.json`

```json
[
  {
    "name": "buvid3",
    "value": "xxx...",
    "domain": ".bilibili.com",
    "path": "/",
    "expires": 1814416037,
    "secure": false,
    "httpOnly": false
  }
]
```

## 五、注意事项

### 5.1 依赖安装

```bash
# 安装Playwright
pip install playwright

# 安装Chromium浏览器
playwright install chromium
```

### 5.2 Cookie有效期

- 获取的Cookies有效期取决于网站设置
- 会话Cookie（expires=0）在浏览器关闭后失效
- 建议定期重新获取Cookies

### 5.3 常见问题

**Q1: 获取不到Cookies或Cookies无效？**

A: 确保你已经在浏览器中登录过B站。Playwright启动的是全新的浏览器上下文，不会共享已登录状态。

**Q2: 提示playwright未安装？**

A: 运行以下命令安装：
```bash
pip install playwright
playwright install chromium
```

**Q3: 输出文件被覆盖？**

A: 默认会覆盖同名文件，请使用`--output`参数指定不同的文件名。

### 5.4 与其他工具配合使用

**与直播下载工具配合**：
```bash
# 获取直播Cookies
python get_bilibili_cookies.py --mode stream

# 使用直播下载工具
python live_bilibili_stream_downloader.py --live "https://live.bilibili.com/xxx"
```

**与yt-dlp配合**：
```bash
# B站直播
yt-dlp --cookies live.bilibili.com_cookies.txt "https://live.bilibili.com/xxx"

# B站视频
yt-dlp --cookies www.bilibili.com_cookies.txt "https://www.bilibili.com/video/BV1xx411c7mZ/"
```

**与curl配合**：
```bash
curl --cookie live.bilibili.com_cookies.txt "https://live.bilibili.com/xxx"
```

### 5.5 安全提示

- **切勿分享**：Cookies包含个人登录信息，切勿分享给他人
- **定期更新**：定期重新获取Cookies以确保安全性
- **合法使用**：仅用于合法用途，请遵守网站使用条款

## 六、版本历史

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| v2.0.0 | 2026-07-01 | 合并直播和视频模式，支持--mode参数切换 |
| v1.0.0 | - | 初始版本，仅支持直播模式 |

## 七、相关文件

| 文件 | 说明 |
|------|------|
| `get_bilibili_cookies.py` | B站Cookies获取器主程序 |
| `test_get_bilibili_cookies.py` | 单元测试文件 |
| `live.bilibili.com_cookies.txt` | B站直播Cookies（默认输出） |
| `www.bilibili.com_cookies.txt` | B站视频Cookies（默认输出） |
| `live_bilibili_stream_downloader.py` | B站直播流下载工具（配合使用） |
