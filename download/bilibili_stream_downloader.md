# B站直播流下载与实时切片工具 - 使用文档

## 一、功能概述

本工具用于下载B站直播流并进行实时切片，主要功能包括：

1. **查看直播格式**：获取B站直播可用的视频格式列表
2. **边下载边切片**：
   - 使用yt-dlp或ffmpeg下载直播流到FLV文件
   - 独立线程定期用ffmpeg提取图片和音频
   - 图片：每N秒提取一帧关键帧，支持jpg/png格式
   - 音频：每N秒切片，支持aac/mp3格式
3. **仅下载**：只下载直播流，不进行切片，输出MP4格式

## 二、实现原理

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        主进程 (主线程)                           │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  1. 解析命令行参数                                         │  │
│  │  2. 验证URL有效性                                         │  │
│  │  3. 选择下载方式 (FLV / fmp4)                             │  │
│  │  4. 监控录制进度和时长                                     │  │
│  │  5. 达到时长后终止录制进程                                 │  │
│  │  6. 执行最终完整切片                                       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    录制子进程                              │  │
│  │  FLV格式: yt-dlp直接下载                                  │  │
│  │  fmp4格式: ffmpeg转码下载                                │  │
│  │  输出: stream.flv                                        │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    切片子线程                              │  │
│  │  定期读取stream.flv文件                                   │  │
│  │  提取帧: ffmpeg -ss {time} -i stream.flv -frames:v 1      │  │
│  │  提取音频: ffmpeg -ss {time} -i stream.flv -t {interval}  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 格式分类与处理策略

B站直播提供两种类型的流格式，本工具针对不同格式采用不同的处理策略：

| 格式类型 | 格式ID列表 | 处理方式 | 说明 |
|---------|-----------|---------|------|
| **FLV格式** | `ultra_high_res-0`, `ultra_high_res-4`, `ultra_high_res-5` | yt-dlp直接下载 | 无需转码，下载速度快 |
| **fmp4/m3u8格式** | `ultra_high_res-1`, `ultra_high_res-2`, `ultra_high_res-3`, `ultra_high_res-6`, `ultra_high_res-7` | yt-dlp获取流地址 + ffmpeg转码 | 需要先获取真实流地址，再转码为FLV |

**为什么需要区分格式？**

- FLV格式支持流式写入，可以边下载边读取
- fmp4/m3u8格式的文件扩展名不被yt-dlp支持（报"The extracted extension ('fmp4') is unusual"错误）
- 通过ffmpeg转码为FLV格式后，才能实现边下载边切片

### 2.3 切片机制

#### 实时切片 (`_streaming_slice_loop`)

切片线程在后台运行，定期检查已录制的视频文件，提取对应时间点的帧和音频：

1. **等待文件就绪**：等待文件大小超过500KB（确保有足够数据）
2. **计算期望切片索引**：根据当前录制时间计算应该提取的帧和音频索引
3. **提取视频帧**：使用ffmpeg在指定时间点提取单帧
4. **提取音频片段**：使用ffmpeg在指定时间点提取一段音频
5. **去重处理**：跳过已存在的切片文件

#### 最终切片 (`_final_slice`)

录制完成后，对整个视频文件进行完整切片：

1. **获取视频时长**：使用ffmpeg获取视频时长，若失败则使用实际录制时长
2. **检查已存在切片**：扫描已生成的切片文件，记录已覆盖的时间点
3. **补全缺失切片**：对未覆盖的时间点进行补全切片

### 2.4 进程管理

录制达到指定时长或用户中断时，需要终止录制进程及其子进程：

- **Windows**：使用 `taskkill /F /T /PID` 终止进程树
- **Linux/macOS**：使用 `os.killpg` 终止进程组

确保yt-dlp及其启动的ffmpeg子进程都被彻底终止。

## 三、调用接口

### 3.1 命令行接口

#### 查看直播格式

```bash
python bilibili_stream_downloader.py --list-formats "https://live.bilibili.com/123456"
```

#### 开始直播录制

```bash
python bilibili_stream_downloader.py --live "https://live.bilibili.com/123456"
```

#### 仅下载直播（不切片）

```bash
python bilibili_stream_downloader.py --live "https://live.bilibili.com/123456" --download-only
```

#### 完整参数示例

```bash
python bilibili_stream_downloader.py --live "https://live.bilibili.com/123456" \
    --format ultra_high_res-0 \
    --interval 10 \
    --audio-interval 60 \
    --duration 3600 \
    --image-format jpg \
    --audio-format aac \
    --output my_live \
    --cookies cookies.txt
```

#### 参数说明

| 参数 | 缩写 | 类型 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--list-formats` | `-l` | str | - | 查看B站直播可用格式列表 |
| `--live` | `-d` | str | - | B站直播地址 |
| `--download-only` | - | bool | false | 仅下载直播流，不进行切片（输出MP4格式） |
| `--format` | `-f` | str | best | 指定直播格式ID |
| `--interval` | `-i` | int | 10 | 视频切片间隔（秒） |
| `--audio-interval` | `-a` | int | 60 | 音频切片间隔（秒） |
| `--duration` | `-t` | int | 3600 | 录制时长（秒），默认60分钟 |
| `--image-format` | - | str | jpg | 图片格式，可选 jpg/png |
| `--audio-format` | - | str | aac | 音频格式，可选 aac/mp3 |
| `--output` | `-o` | str | 自动生成 | 输出目录名前缀 |
| `--cookies` | - | str | cookies.txt | cookies文件路径 |

### 3.2 Python API接口

#### 初始化下载器

```python
from bilibili_stream_downloader import BilibiliLiveStreamer

# 使用默认cookies文件
downloader = BilibiliLiveStreamer(cookies_file="cookies.txt")
```

#### 查看格式列表

```python
downloader.list_formats("https://live.bilibili.com/123456")
```

#### 开始录制

```python
output_dir = downloader.download_and_slice_live(
    url="https://live.bilibili.com/123456",
    interval=10,           # 视频切片间隔（秒）
    audio_interval=60,     # 音频切片间隔（秒）
    duration=3600,         # 录制时长（秒）
    image_format="jpg",    # 图片格式：jpg或png
    audio_format="aac",    # 音频格式：aac或mp3
    format_id="ultra_high_res-0",  # 指定格式ID
    output_name=None,      # 输出目录名，None则自动生成
)

if output_dir:
    print(f"录制完成，输出目录: {output_dir}")
```

#### 仅下载直播（不切片）

```python
video_path = downloader.download_live_only(
    url="https://live.bilibili.com/123456",
    duration=3600,         # 录制时长（秒）
    format_id="ultra_high_res-0",  # 指定格式ID
    output_name=None,      # 输出目录名，None则自动生成
)

if video_path:
    print(f"下载完成，视频文件: {video_path}")
```

#### 类方法说明

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `__init__` | `cookies_file: str` | - | 初始化下载器 |
| `list_formats` | `url: str` | `None` | 查看直播格式列表 |
| `download_and_slice_live` | `url, interval, audio_interval, duration, image_format, audio_format, format_id, output_name` | `Optional[Path]` | 开始录制并切片，返回输出目录 |
| `download_live_only` | `url, duration, format_id, output_name` | `Optional[Path]` | 仅下载直播流，不切片（输出MP4格式） |

#### 内部方法说明（供扩展使用）

| 方法 | 说明 |
|------|------|
| `_validate_url(url)` | 验证URL是否为B站直播地址 |
| `_run_command(cmd, verbose)` | 执行外部命令并返回结果 |
| `_kill_process_tree(proc)` | 终止进程及其所有子进程 |
| `_is_fmp4_format(format_id)` | 判断格式ID是否为fmp4格式 |
| `_get_stream_url(url, format_id)` | 获取直播流的实际URL |
| `_streaming_slice_loop(...)` | 切片线程循环 |
| `_final_slice(...)` | 录制完成后完整切片 |

## 四、输出文件结构

### 切片模式

录制完成后，输出目录结构如下：

```
live_downloads/
└── live_20260701_101034/          # 录制时间戳命名的目录
    ├── stream.flv                  # 完整直播视频文件
    ├── frames/                     # 视频帧目录
    │   ├── frame_0000_0001.jpg     # 第0秒的帧（第1个）
    │   ├── frame_0010_0002.jpg     # 第10秒的帧（第2个）
    │   ├── frame_0020_0003.jpg     # 第20秒的帧（第3个）
    │   └── ...
    └── audio/                      # 音频目录
        ├── audio_0000_0001.aac     # 第0秒开始的音频（第1个）
        ├── audio_0060_0002.aac     # 第60秒开始的音频（第2个）
        └── ...
```

### 仅下载模式（download-only）

```
live_downloads/
└── live_20260701_101034/          # 录制时间戳命名的目录
    └── stream.mp4                  # 完整直播视频文件（MP4格式）
```

### 文件命名规则

| 文件类型 | 命名格式 | 示例 |
|---------|---------|------|
| 视频帧 | `frame_{起始时间}_{序号}.{格式}` | `frame_0010_0002.jpg` |
| 音频片段 | `audio_{起始时间}_{序号}.{格式}` | `audio_0060_0002.aac` |

## 五、注意事项

### 5.1 依赖安装

确保已安装以下依赖：

```bash
# 安装Python依赖
pip install yt-dlp

# 安装ffmpeg（用于转码和切片）
# Windows: 下载ffmpeg并添加到PATH
# Ubuntu/Debian: sudo apt install ffmpeg
# macOS: brew install ffmpeg
```

### 5.2 Cookies配置

对于需要登录才能观看的直播，需要提供cookies文件：

1. 使用 `get_bilibili_cookies.py` 获取cookies
2. 将cookies保存为 `live.bilibili.com_cookies.txt`（Netscape格式）
3. 使用 `--cookies` 参数指定cookies文件路径

### 5.3 格式选择建议

| 场景 | 推荐格式 | 说明 |
|------|---------|------|
| 快速录制 | `ultra_high_res-0` | FLV格式，无需转码 |
| 高质量录制 | `ultra_high_res-1` | fmp4格式，需要转码 |
| 最高质量 | `ultra_high_res-2` | fmp4格式，最高分辨率 |

### 5.4 常见问题

**Q1: 录制时出现"The extracted extension ('fmp4') is unusual"错误**

A: 这是因为选择了fmp4格式但代码未能正确识别。请确保使用最新版本的代码，或切换到FLV格式（`ultra_high_res-0`）。

**Q2: 切片文件数量与预期不符**

A: 切片数量取决于录制时长和切片间隔。最终切片会补全所有缺失的切片，确保完整性。

**Q3: 录制达到时长后进程未终止**

A: 代码使用进程树终止机制，确保所有子进程都被终止。如果问题持续存在，请检查系统权限。

**Q4: 直播流中断后无法恢复**

A: 当前版本不支持断点续传，如果直播流中断，需要重新开始录制。

### 5.5 性能优化建议

1. **减少切片频率**：较大的切片间隔可以减少CPU和IO负载
2. **选择合适格式**：FLV格式无需转码，性能更好
3. **使用SSD存储**：切片操作频繁读写文件，SSD可以显著提升性能
4. **合理设置duration**：避免录制过长时间导致文件过大

### 5.6 安全提示

- 仅用于合法用途，遵守B站使用条款
- Cookies文件包含登录凭证，请妥善保管
- 不要将包含cookies的代码提交到公共仓库

## 六、版本历史

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| 1.0.1 | 2026-07-02 | 新增仅下载模式（download-only），支持只下载直播流不切片，输出MP4格式；文件名改为bilibili_stream_downloader |
| 1.0.0 | 2026-07-01 | 初始版本，支持FLV和fmp4格式，实时切片 |
