import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

PICS_DIR = BASE_DIR / "pics"

OUTPUT_FILES = {
    "havetext": BASE_DIR / "havetext.md",
    "info": BASE_DIR / "info.md",
    "result": BASE_DIR / "result.json"
}

FFMPEG_CONFIG = {
    "scene_threshold": 0.05,
    "output_pattern": "frame_%04d.jpg",
    "vsync_mode": "vfr"
}

OCR_CONFIG = {
    "confidence_threshold": 0.8,
    "image_resize": 600,
    "denoising_strength": 3
}

VIDEO_FORMATS = (".mp4", ".avi", ".flv", ".mkv", ".ts", ".mov", ".wmv")

SKIP_TEXT_PATTERNS = [
    "水印",
    "版权",
    "©",
    "logo",
    "默认",
    "提示",
    "请输入",
    "登录",
    "注册",
    "点击",
    "更多"
]