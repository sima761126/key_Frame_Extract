# 音频处理模块 (audio_processor.py)

## 概述

`audio_processor.py` 是一个音频处理工具，使用 FFmpeg 从视频中提取音频并进行切片处理。该模块针对 B 站直播源进行优化，支持常见的直播视频格式，适用于语音识别等后续处理场景。

## 功能特性

1. **音频提取** - 从视频中提取音频并转换为 16kHz 单声道（Vosk 语音识别要求）
2. **音频切片** - 将音频按指定时长分割为多个片段
3. **B 站直播源优化** - 针对 B 站直播常见格式（.mp4, .flv, .ts, .mkv）进行优化
4. **进度条显示** - 使用 tqdm 显示处理进度
5. **跳过已有文件** - 支持跳过已提取的音频文件和切片
6. **时间戳命名** - 音频切片文件名包含时间戳信息
7. **完善的异常处理** - 包含完整的错误处理和资源清理机制
8. **灵活的接口** - 提供类接口和便捷函数两种使用方式

## 安装依赖

```bash
pip install -r requirements.txt
```

需要确保系统已安装 FFmpeg 并添加到 PATH 环境变量中。

## 使用方法

### 1. 基本使用

#### 使用类方式

```python
from audio_processor import AudioProcessor
from pathlib import Path

processor = AudioProcessor()

audio_path = processor.extract_audio(Path("video.mp4"))
print(f"音频已提取: {audio_path}")

segments = processor.segment_audio(audio_path, segment_duration=60)
print(f"已生成 {len(segments)} 个音频切片")
```

#### 使用便捷函数

```python
from audio_processor import extract_and_segment_audio

segments = extract_and_segment_audio("video.mp4")
print(f"已生成 {len(segments)} 个音频切片")
```

### 2. 命令行使用

```bash
# 提取音频并切片
python audio_processor.py video.mp4

# 强制重新提取
python audio_processor.py video.mp4 -f

# 指定切片时长为30秒
python audio_processor.py video.mp4 -i 30

# 指定输出目录
python audio_processor.py video.mp4 -o ./my_audio

# 组合使用
python audio_processor.py video.mp4 -f -i 30 -o ./my_audio
```

## 切片命名规则

生成的音频切片按照以下命名规则保存：

```
audio_起始时间_序号.wav
```

- `audio_` - 固定前缀
- `起始时间` - 切片起始时间（秒），用4位数字表示，不足前面补0
- `_` - 分隔符
- `序号` - 切片序号，用4位数字表示，不足前面补0
- `.wav` - 固定扩展名

**示例：**
- `audio_0000_0001.wav` - 第一个音频切片（从第0秒开始）
- `audio_0060_0002.wav` - 第二个音频切片（从第60秒开始）
- `audio_0120_0003.wav` - 第三个音频切片（从第120秒开始）

## 参数说明

### Python API 参数

#### AudioProcessor 类初始化参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `audio_dir` | Path | config.AUDIO_DIR | 默认输出目录路径 |

#### extract_audio 方法参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `input_video` | Path | 必需 | 输入视频路径 |
| `force_reextract` | bool | False | 是否强制重新提取，跳过已有文件检查 |
| `output_dir` | Path | None | 输出目录路径，如果为None则使用默认目录 |

#### segment_audio 方法参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `audio_path` | Path | 必需 | 音频文件路径 |
| `segment_duration` | int | 60 | 每个切片时长（秒） |
| `force_resegment` | bool | False | 是否强制重新切片，跳过已有切片检查 |
| `output_dir` | Path | None | 输出目录路径，如果为None则使用默认目录 |

#### extract_and_segment_audio 方法参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `input_video` | Path | 必需 | 输入视频路径 |
| `force_reextract` | bool | False | 是否强制重新提取和切片 |
| `segment_duration` | int | 60 | 每个切片时长（秒） |
| `output_dir` | Path | None | 输出目录路径，如果为None则使用默认目录 |

### 便捷函数参数

#### extract_audio_from_video 函数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `video_path` | str | 必需 | 视频文件路径 |
| `force` | bool | False | 是否强制重新提取 |
| `output_dir` | Path | None | 输出目录路径，如果为None则使用默认目录 |

#### segment_audio_file 函数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `audio_path` | str | 必需 | 音频文件路径 |
| `segment_duration` | int | 60 | 每个切片时长（秒） |
| `force` | bool | False | 是否强制重新切片 |
| `output_dir` | Path | None | 输出目录路径，如果为None则使用默认目录 |

#### extract_and_segment_audio 函数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `video_path` | str | 必需 | 视频文件路径 |
| `force` | bool | False | 是否强制重新提取和切片 |
| `segment_duration` | int | 60 | 每个切片时长（秒） |
| `output_dir` | Path | None | 输出目录路径，如果为None则使用默认目录 |

## 输出目录结构

```
project_root/
├── audio/                          # 音频输出目录
│   ├── full_audio.wav              # 完整音频文件
│   ├── audio_0000_0001.wav         # 第一个音频切片（从第0秒开始）
│   ├── audio_0060_0002.wav         # 第二个音频切片（从第60秒开始）
│   ├── audio_0120_0003.wav         # 第三个音频切片（从第120秒开始）
│   └── ...                         # 更多切片文件
└── audio_processor.py              # 主程序文件
```

## 配置文件

模块使用 `config.py` 中的配置：

```python
# 输出目录配置
AUDIO_DIR = BASE_DIR / "audio"

# FFmpeg 配置
FFMPEG_CONFIG = {
    "output_pattern": "temp_frame_%04d.jpg",
    "vsync_mode": "vfr"
}

# 视频格式支持
VIDEO_FORMATS = (".mp4", ".avi", ".flv", ".mkv", ".ts", ".mov", ".wmv", ".m4v", ".webm")
```

## 异常处理

模块包含完整的异常处理机制：

| 异常类型 | 触发条件 |
|----------|----------|
| `FileNotFoundError` | 视频或音频文件不存在 |
| `ValueError` | 文件格式不支持或切片时长参数无效 |
| `EnvironmentError` | FFmpeg 未安装或未添加到 PATH |
| `RuntimeError` | FFmpeg 执行失败 |

## 支持的视频格式

针对 B 站直播源优化，支持以下格式：

- `.mp4` - 常用封装格式
- `.flv` - 直播常见格式
- `.ts` - 直播流格式
- `.mkv` - 容器格式
- `.avi` - 传统格式
- `.mov` - QuickTime 格式
- `.wmv` - Windows 格式
- `.m4v` - Apple 格式
- `.webm` - Web 格式

## FFmpeg 命令构建

模块提供两个命令构建方法：

### _build_extract_command

构建音频提取命令：

```python
cmd = processor._build_extract_command(input_video, output_path)
# 命令组成：
# ffmpeg -i <input_video> -vn -acodec pcm_s16le -ar 16000 -ac 1 -y <output_path>
```

### _build_segment_command

构建音频切片命令：

```python
cmd = processor._build_segment_command(audio_path, output_pattern, segment_duration)
# 命令组成：
# ffmpeg -i <audio_path> -f segment -segment_time <duration> -reset_timestamps 1 -c copy -y <output_pattern>
```

## 性能优化

- **进度条显示** - 使用 tqdm 实时显示处理进度
- **跳过已有文件** - 避免重复处理，提高效率
- **时间戳命名** - 便于追踪音频切片的时间位置
- **错误处理** - 捕获并处理 FFmpeg 执行错误

## 示例

### 提取音频并切片

```python
from audio_processor import AudioProcessor
from pathlib import Path

processor = AudioProcessor()

audio_path = processor.extract_audio(Path("bilibili_live.mp4"))
print(f"音频已提取到: {audio_path}")

segments = processor.segment_audio(audio_path, segment_duration=60)
print(f"已生成 {len(segments)} 个切片，用于后续语音识别")

for idx, seg in enumerate(segments, 1):
    print(f"  切片 {idx}: {seg}")
```

### 使用便捷函数

```python
from audio_processor import extract_and_segment_audio

segments = extract_and_segment_audio("live_stream.flv")
print(f"处理完成，共生成 {len(segments)} 个音频切片")

for idx, seg in enumerate(segments, 1):
    print(f"  切片 {idx}: {seg}")
```

### 强制重新处理

```python
from audio_processor import AudioProcessor
from pathlib import Path

processor = AudioProcessor()

audio_path = processor.extract_audio(Path("video.mp4"), force_reextract=True)

segments = processor.segment_audio(audio_path, segment_duration=60, force_resegment=True)
print(f"强制重新生成了 {len(segments)} 个切片")
```

### 使用组合方法

```python
from audio_processor import AudioProcessor
from pathlib import Path

processor = AudioProcessor()

segments = processor.extract_and_segment_audio(
    Path("video.mp4"),
    force_reextract=True,
    segment_duration=60
)
print(f"完成音频提取和切片，共 {len(segments)} 个切片")
```

## 注意事项

1. 确保系统已安装 FFmpeg 并添加到 PATH 环境变量
2. 视频文件必须存在且可读
3. 输出目录需要有写入权限
4. 切片时长必须大于 0
5. 对于长时间视频，建议使用合理的切片时长以控制输出文件数量
6. 提取的音频格式为 16kHz 单声道 PCM，适用于 Vosk 等语音识别引擎
7. 使用 `force_reextract=True` 可以强制重新提取音频，忽略已有的音频文件
8. 音频切片文件名包含时间戳信息，便于追踪音频内容的时间位置