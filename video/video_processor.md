# 视频关键帧提取模块 (video_processor.py)

## 概述

`video_processor.py` 是一个通用的视频关键帧提取工具，使用 FFmpeg 从视频中提取所有I帧（关键帧）。该模块支持时间间隔控制，可以减少提取的关键帧数量，适用于各种视频处理场景。

## 功能特性

1. **关键帧提取** - 从视频中提取所有I帧（关键帧）
2. **时间间隔控制** - 支持设置时间间隔，减少提取的帧数量
3. **通用视频格式支持** - 支持多种常见视频格式
4. **完善的异常处理** - 包含完整的错误处理和资源清理机制
5. **灵活的接口** - 提供类接口和便捷函数两种使用方式

## 安装依赖

```bash
pip install -r requirements.txt
```

需要确保系统已安装 FFmpeg 并添加到 PATH 环境变量中。

## 使用方法

### 1. 基本使用

#### 使用类方式
```python
from video_processor import VideoProcessor
from pathlib import Path

# 使用默认输出目录
processor = VideoProcessor()
frames = processor.extract_frames(Path("video.mp4"))
print(f"提取了 {len(frames)} 张关键帧")

# 指定输出目录
processor = VideoProcessor(pics_dir=Path("custom_output_dir"))
frames = processor.extract_frames(Path("video.mp4"))
print(f"提取了 {len(frames)} 张关键帧")

# 或者在提取时指定输出目录
frames = processor.extract_frames(Path("video.mp4"), output_dir=Path("another_output_dir"))
print(f"提取了 {len(frames)} 张关键帧")
```

#### 使用便捷函数
```python
from video_processor import extract_video_frames
from pathlib import Path

# 使用默认输出目录
frames = extract_video_frames("video.mp4")
print(f"提取了 {len(frames)} 张关键帧")

# 指定输出目录
frames = extract_video_frames("video.mp4", output_dir=Path("custom_output_dir"))
print(f"提取了 {len(frames)} 张关键帧")
```

### 2. 命令行使用

```bash
# 提取所有关键帧
python video_processor.py video.mp4

# 强制重新提取
python video_processor.py video.mp4 -f

# 设置时间间隔（例如每5秒提取一帧）
python video_processor.py video.mp4 -i 5

# 指定输出目录
python video_processor.py video.mp4 -o ./custom_output

# 强制重新提取并设置时间间隔
python video_processor.py video.mp4 -f -i 10

# 组合使用：指定输出目录并设置时间间隔
python video_processor.py video.mp4 -o ./custom_output -i 5 -f
```

### 3. 高级使用

```python
from video_processor import VideoProcessor
from pathlib import Path

# 使用默认输出目录
processor = VideoProcessor()

# 提取所有关键帧（无时间间隔限制）
frames = processor.extract_frames(
    input_video=Path("video.mp4"),
    force_reextract=True,
    frame_interval=0.0  # 0表示无限制
)

# 按时间间隔提取关键帧（例如每2秒提取一帧）
frames = processor.extract_frames(
    input_video=Path("video.mp4"),
    force_reextract=False,
    frame_interval=2.0,  # 每2秒提取一帧
    output_dir=Path("./custom_output")  # 指定输出目录
)

print(f"提取了 {len(frames)} 张关键帧")

# 初始化时指定默认输出目录
processor = VideoProcessor(pics_dir=Path("./default_output"))
frames = processor.extract_frames(
    input_video=Path("video.mp4"),
    force_reextract=True,
    frame_interval=5.0  # 每5秒提取一帧
)
```

## 图片命名规则

提取的关键帧图片按照以下命名规则保存：

```
frame_%04d_%04d.jpg
```

- 第一部分 `frame_` - 固定前缀
- 第二部分 `%04d` - 截取帧的时间（单位：秒），用4位数字表示，不足前面补0
- 第三部分 `_` - 分隔符
- 第四部分 `%04d` - 序号，用4位数字表示，不足前面补0
- 第五部分 `.jpg` - 固定扩展名

**示例：**
- `frame_0000_0001.jpg` - 第0秒处的第一个帧
- `frame_0005_0002.jpg` - 第5秒处的第二个帧
- `frame_0010_0003.jpg` - 第10秒处的第三个帧

## 参数说明

### 命令行参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `video_path` | string | 必需 | 视频文件路径 |
| `-f, --force` | flag | False | 强制重新提取，清除已有的帧图片 |
| `-i, --frame-interval` | float | 0.0 | 帧提取时间间隔（秒），0表示不限制，提取所有I帧 |
| `-o, --output-dir` | Path | 默认目录 | 输出目录路径，如果不指定则使用默认目录 |

### Python API 参数

#### VideoProcessor 类初始化参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `pics_dir` | Path | config.PICS_DIR | 默认输出目录路径 |

#### extract_frames 方法参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `input_video` | Path | 必需 | 输入视频路径 |
| `force_reextract` | bool | False | 是否强制重新提取 |
| `frame_interval` | float | 0.0 | 帧提取时间间隔（秒），0表示不限制，提取所有I帧 |
| `output_dir` | Path | None | 输出目录路径，如果为None则使用默认目录 |

#### extract_video_frames 便捷函数参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `video_path` | str | 必需 | 视频文件路径 |
| `force` | bool | False | 是否强制重新提取 |
| `frame_interval` | float | 0.0 | 帧提取时间间隔（秒），0表示不限制，提取所有I帧 |
| `output_dir` | Path | None | 输出目录路径，如果为None则使用默认目录 |

## 输出目录结构

```
project_root/
├── pics/                           # 关键帧输出目录
│   ├── frame_0000_0001.jpg        # 第0秒处的第一帧
│   ├── frame_0005_0002.jpg        # 第5秒处的第二帧
│   ├── frame_0010_0003.jpg        # 第10秒处的第三帧
│   ├── frame_0015_0004.jpg        # 第15秒处的第四帧
│   └── ...                        # 更多帧图片
└── video_processor.py              # 主程序文件
```

## 配置文件

模块使用 `config.py` 中的配置：

```python
# FFmpeg 视频帧提取配置
FFMPEG_CONFIG = {
    "output_pattern": "frame_%04d_%04d.jpg",  # 输出图片命名模式
    "vsync_mode": "vfr"                       # 变帧率模式
}
```

## 异常处理

模块包含完整的异常处理机制：

- `FileNotFoundError` - 视频文件不存在
- `ValueError` - 文件格式不支持或帧间隔参数无效
- `EnvironmentError` - FFmpeg未安装
- `RuntimeError` - FFmpeg执行失败

## 性能优化

- **FFmpeg可用性缓存** - 避免重复检查FFmpeg是否可用
- **进程管理** - 正确终止FFmpeg进程及其子进程
- **资源清理** - 自动清理临时文件和错误状态

## 示例

### 提取视频关键帧
```python
from video_processor import extract_video_frames

# 提取所有关键帧
frames = extract_video_frames("sample_video.mp4")
print(f"总共提取了 {len(frames)} 张关键帧")

# 每5秒提取一帧
frames = extract_video_frames("sample_video.mp4", frame_interval=5.0)
print(f"按5秒间隔提取了 {len(frames)} 张关键帧")
```

### 使用自定义时间间隔
```python
from video_processor import VideoProcessor
from pathlib import Path

processor = VideoProcessor()

# 每10秒提取一帧，强制重新提取
frames = processor.extract_frames(
    input_video=Path("long_video.mp4"),
    force_reextract=True,
    frame_interval=10.0
)

print(f"按10秒间隔提取了 {len(frames)} 张关键帧")
```

## 注意事项

1. 确保系统已安装 FFmpeg 并添加到 PATH 环境变量
2. 视频文件必须存在且可读
3. 输出目录需要有写入权限
4. 时间间隔设置过大会导致关键帧数量显著减少
5. 对于长时间视频，建议使用时间间隔控制以减少输出文件数量