# Name： B站视频下载与切片工具
# Author: simajinghua
# Version: 1.0.0

---

## 功能概述

B站视频下载与切片工具，支持三种处理模式：

1. **边下载边切片（streaming模式）**：使用yt-dlp下载视频到临时文件，独立线程定期用ffmpeg提取图片和音频
2. **先下载后切片（download模式）**：先使用yt-dlp完整下载视频，下载完成后对整个视频进行切片
3. **仅下载（download-only模式）**：只下载视频内容，不进行切片，输出MP4格式

---

## 环境依赖

- Python 3.8+
- yt-dlp（视频下载工具）
- ffmpeg（视频处理工具）
- requests（HTTP请求库）

安装依赖：
```bash
pip install yt-dlp
```

ffmpeg需单独安装：
- Windows：下载ffmpeg并添加到PATH
- macOS：`brew install ffmpeg`
- Linux：`sudo apt install ffmpeg`

---

## 使用方式

### 查看视频格式列表

```bash
python bilibili_video_downloader.py --list-formats "https://www.bilibili.com/video/BV1xx411c7mZ/"
```

### 先下载后切片（默认模式）

```bash
python bilibili_video_downloader.py --video "https://www.bilibili.com/video/BV1xx411c7mZ/"
```

### 边下载边切片

```bash
python bilibili_video_downloader.py --video "https://www.bilibili.com/video/BV1xx411c7mZ/" --mode streaming
```

### 仅下载视频（不切片）

```bash
python bilibili_video_downloader.py --video "https://www.bilibili.com/video/BV1xx411c7mZ/" --download-only
```

### 自定义参数

```bash
python bilibili_video_downloader.py --video "https://www.bilibili.com/video/BV1xx411c7mZ/" \
    --mode streaming \
    --format best \
    --interval 10 \
    --audio-interval 60 \
    --image-format jpg \
    --audio-format aac \
    --output my_video \
    --cookies www.bilibili.com_cookies.txt
```

---

## 参数说明

| 参数 | 缩写 | 类型 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--list-formats` | `-l` | str | - | 查看B站视频可用格式列表 |
| `--video` | `-d` | str | - | B站视频地址 |
| `--mode` | `-m` | str | download | 下载模式：`download`（先下载后切，默认）或 `streaming`（边下载边切） |
| `--download-only` | - | bool | false | 仅下载视频，不进行切片（输出MP4格式） |
| `--format` | `-f` | str | best | 指定视频格式ID |
| `--interval` | `-i` | int | 10 | 视频切片间隔（秒） |
| `--audio-interval` | `-a` | int | 60 | 音频切片间隔（秒） |
| `--image-format` | - | str | jpg | 图片格式：jpg/png |
| `--audio-format` | - | str | aac | 音频格式：aac/mp3 |
| `--output` | `-o` | str | 自动生成 | 输出目录名 |
| `--cookies` | - | str | www.bilibili.com_cookies.txt | cookies文件路径 |

---

## 处理流程

### Streaming模式（边下载边切片）

```
┌─────────────────────────────────────────────────────────────┐
│                    Streaming模式流程                        │
├─────────────────────────────────────────────────────────────┤
│  1. yt-dlp开始下载视频到临时文件                              │
│                    ↓                                        │
│  2. 切片线程启动，等待文件达到500KB                           │
│                    ↓                                        │
│  3. 每interval秒提取一帧图片                                  │
│     每audio_interval秒提取一段音频                            │
│                    ↓                                        │
│  4. yt-dlp下载完成                                          │
│                    ↓                                        │
│  5. 最终完整切片，补全缺失的帧和音频                          │
│                    ↓                                        │
│  6. 输出结果：frames目录（图片） + audio目录（音频）           │
└─────────────────────────────────────────────────────────────┘
```

### Download模式（先下载后切片）

```
┌─────────────────────────────────────────────────────────────┐
│                    Download模式流程                         │
├─────────────────────────────────────────────────────────────┤
│  1. yt-dlp完整下载视频到文件                                 │
│                    ↓                                        │
│  2. 下载完成后，对整个视频进行切片                            │
│     每interval秒提取一帧图片                                  │
│     每audio_interval秒提取一段音频                            │
│                    ↓                                        │
│  3. 输出结果：frames目录（图片） + audio目录（音频）           │
└─────────────────────────────────────────────────────────────┘
```

---

## 输出文件结构

### 切片模式（streaming/download）

```
video_downloads/
└── video_20240101_120000/
    ├── video.mp4                # 下载的视频文件
    ├── frames/                 # 图片目录
    │   ├── frame_0000_0001.jpg
    │   ├── frame_0010_0002.jpg
    │   ├── frame_0020_0003.jpg
    │   └── ...
    └── audio/                  # 音频目录
        ├── audio_0000_0001.aac
        ├── audio_0060_0002.aac
        ├── audio_0120_0003.aac
        └── ...
```

### 仅下载模式（download-only）

```
video_downloads/
└── video_20240101_120000/
    └── video.mp4                # 下载的视频文件（MP4格式）
```

---

## 代码调用

### 示例代码

```python
from bilibili_video_downloader import BilibiliVideoDownloader

downloader = BilibiliVideoDownloader(cookies_file="www.bilibili.com_cookies.txt")

# 边下载边切片
output_dir = downloader.download_and_slice_streaming(
    url="https://www.bilibili.com/video/BV1xx411c7mZ/",
    interval=10,
    audio_interval=60,
    image_format="jpg",
    audio_format="aac",
    format_id="best",
    output_name="my_video"
)

# 先下载后切片
output_dir = downloader.download_and_slice_after(
    url="https://www.bilibili.com/video/BV1xx411c7mZ/",
    interval=10,
    audio_interval=60,
    image_format="jpg",
    audio_format="aac",
    format_id="best",
    output_name="my_video"
)

# 仅下载视频（不切片）
video_path = downloader.download_video_only(
    url="https://www.bilibili.com/video/BV1xx411c7mZ/",
    format_id="best",
    output_name="my_video"
)

# 查看格式列表
downloader.list_formats("https://www.bilibili.com/video/BV1xx411c7mZ/")
```

### API说明

#### `BilibiliVideoDownloader` 类

| 方法 | 说明 |
|------|------|
| `__init__(cookies_file)` | 初始化下载器，指定cookies文件 |
| `list_formats(url)` | 查看视频可用格式列表 |
| `download_and_slice_streaming(url, interval, audio_interval, image_format, audio_format, format_id, output_name)` | 边下载边切片 |
| `download_and_slice_after(url, interval, audio_interval, image_format, audio_format, format_id, output_name)` | 先下载后切片 |
| `download_video_only(url, format_id, output_name)` | 仅下载视频，不切片（输出MP4格式） |

---

## 支持的B站视频URL模式

```python
# 普通视频
https://www.bilibili.com/video/BV1xx411c7mZ/
http://www.bilibili.com/video/BV1xx411c7mZ/
https://bilibili.com/video/BV1xx411c7mZ/

# 番剧/剧集
https://www.bilibili.com/bangumi/play/ep123456/
https://www.bilibili.com/bangumi/play/ss12345/
```

---

## Cookies获取

登录B站后获取cookies，保存为 `www.bilibili.com_cookies.txt` 文件。

可使用 `get_bilibili_cookies.py` 工具获取：
```bash
python get_bilibili_cookies.py --mode video
```

---

## 注意事项

1. **网络要求**：需要稳定的网络连接，下载过程中如果网络中断会导致下载失败
2. **存储空间**：确保有足够的存储空间存放下载的视频和切片文件
3. **权限问题**：如果下载受限视频（如大会员专享），需要提供有效的cookies文件
4. **ffmpeg路径**：确保ffmpeg已正确安装并添加到系统PATH
5. **视频格式**：默认使用best格式，可通过 `--format` 参数指定具体格式ID
6. **切片间隔**：视频切片间隔建议10-30秒，音频切片间隔建议60-300秒
7. **中断处理**：按Ctrl+C可中断下载，工具会自动清理资源
8. **文件命名**：图片和音频文件命名格式为 `frame_起始时间_序号.格式` 和 `audio_起始时间_序号.格式`

---

## 故障排除

### 常见问题

| 问题 | 原因 | 解决方法 |
|------|------|----------|
| 下载失败 | 网络问题 | 检查网络连接，重试下载 |
| 获取格式失败 | URL错误或视频不存在 | 检查视频URL是否正确 |
| 切片失败 | ffmpeg未安装或路径错误 | 安装ffmpeg并添加到PATH |
| 权限错误 | 受限视频 | 提供有效的cookies文件 |
| 文件损坏 | 下载中断 | 重新下载 |

### 日志说明

- `[下载线程]`：下载进度日志
- `[切片线程]`：切片进度日志
- `[主线程]`：主流程日志

---

## 更新日志

### v1.0.1
- 新增仅下载模式（download-only），支持只下载视频不切片
- 仅下载模式输出MP4格式

### v1.0.0
- 初始版本
- 支持边下载边切片（streaming模式）
- 支持先下载后切片（download模式）
- 支持自定义切片间隔和输出格式
- 支持cookies认证
- 支持查看视频格式列表