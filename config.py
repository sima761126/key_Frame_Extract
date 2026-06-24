import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# 输出目录配置
PICS_DIR = BASE_DIR / "pics"

# 输出文件配置
OUTPUT_FILES = {
    "havetext": BASE_DIR / "havetext.md",   # 包含文字的图片列表
    "info": BASE_DIR / "info.md",            # OCR识别结果
    "voice": BASE_DIR / "voice.md",          # 语音识别结果
    "result": BASE_DIR / "result.json",       # 结构化JSON结果
    "summary": BASE_DIR / "summary.md"  # md文档
}

# FFmpeg 视频帧提取配置
FFMPEG_CONFIG = {
    "output_pattern": "frame_%04d.jpg",  # 输出图片命名模式
    "vsync_mode": "vfr"          # 变帧率模式
}

# PaddleOCR 配置
OCR_CONFIG = {
    "use_angle_cls": True,        # 是否使用方向分类器
    "lang": "ch",                 # 语言：ch(中文)、en(英文)、japan(日语)、korean(韩语)
    "confidence_threshold": 0.8,  # 置信度阈值
    "image_resize": 600,         # 图片预处理resize尺寸
    "denoising_strength": 3      # 去噪强度
}

# 视频格式支持
VIDEO_FORMATS = (".mp4", ".avi", ".flv", ".mkv", ".ts", ".mov", ".wmv", ".m4v", ".webm")

# 文本相似度比较配置
SIMILARITY_CONFIG = {
    "similarity_threshold": 0.6,  # 相似度阈值，超过此值进行比较
}

# 跳过文本模式（用于过滤水印、版权信息等无价值文本）
SKIP_TEXT_PATTERNS = [
    "水印", "版权", "©", "logo", "默认", "提示",
    "请输入", "登录", "注册", "点击", "更多",
    "弹幕", "B站", "bilibili", "视频加载", "网络异常",
]

# 图像预处理配置
IMAGE_PREPROCESS = {
    "enable_gray": True,         # 启用灰度化
    "enable_denoise": True,      # 启用去噪
    "enable_threshold": False,   # 启用二值化（光线暗时启用）
    "threshold_value": 127       # 二值化阈值
}
