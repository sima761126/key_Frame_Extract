"""
视频关键帧提取模块
使用 FFmpeg 从视频中提取所有I帧（关键帧）
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, List
from tqdm import tqdm
import config


class VideoProcessor:
    """视频关键帧提取处理器"""

    def __init__(self):
        self.pics_dir = config.PICS_DIR
        self.ffmpeg_config = config.FFMPEG_CONFIG

    def _ensure_pics_dir(self) -> None:
        """确保pics目录存在"""
        self.pics_dir.mkdir(parents=True, exist_ok=True)

    def _build_ffmpeg_command(
        self,
        input_video: Path,
        output_dir: Path
    ) -> List[str]:
        """
        构建FFmpeg命令 - 提取所有I帧（关键帧）

        Args:
            input_video: 输入视频路径
            output_dir: 输出目录

        Returns:
            FFmpeg命令列表
        """
        output_pattern = self.ffmpeg_config["output_pattern"]
        vsync_mode = self.ffmpeg_config["vsync_mode"]

        output_path = output_dir / output_pattern

        cmd = [
            "ffmpeg",
            "-i", str(input_video),
            "-vf", "select='eq(pict_type\\,I)'",
            "-vsync", vsync_mode,
            "-q:v", "2",  # 图片质量 (1-31, 越小越好)
            "-y",  # 覆盖输出文件
            str(output_path)
        ]
        return cmd

    def extract_frames(
        self,
        input_video: Path,
        force_reextract: bool = False
    ) -> List[Path]:
        """
        从视频中提取关键帧

        Args:
            input_video: 输入视频路径
            force_reextract: 是否强制重新提取

        Returns:
            提取的图片路径列表
        """
        # 验证输入文件
        if not input_video.exists():
            raise FileNotFoundError(f"视频文件不存在: {input_video}")

        # 检查文件格式
        if input_video.suffix.lower() not in config.VIDEO_FORMATS:
            raise ValueError(
                f"不支持的视频格式: {input_video.suffix}，"
                f"支持的格式: {config.VIDEO_FORMATS}"
            )

        # 确保输出目录存在
        self._ensure_pics_dir()

        # 检查是否已有提取结果
        existing_frames = sorted(self.pics_dir.glob("*.jpg"))
        if existing_frames and not force_reextract:
            print(f"发现已有帧图片 {len(existing_frames)} 张，跳过提取")
            return existing_frames

        # 清理旧文件
        if force_reextract:
            for f in existing_frames:
                f.unlink()
            print("已清理旧帧图片")

        # 执行FFmpeg命令
        print(f"正在提取关键帧: {input_video.name}")
        cmd = self._build_ffmpeg_command(input_video, self.pics_dir)

        try:
            # 隐藏FFmpeg输出，只显示进度
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # 等待完成
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                raise RuntimeError(f"FFmpeg执行失败: {stderr}")

        except FileNotFoundError:
            raise EnvironmentError(
                "FFmpeg未安装或未添加到PATH，请先安装FFmpeg\n"
                "下载地址: https://ffmpeg.org/download.html"
            )

        # 获取提取的图片列表
        frame_files = sorted(self.pics_dir.glob("*.jpg"))
        print(f"成功提取 {len(frame_files)} 张关键帧")

        return frame_files

    def get_frame_list(self) -> List[Path]:
        """获取已提取的关键帧列表"""
        if not self.pics_dir.exists():
            return []
        return sorted(self.pics_dir.glob("*.jpg"))


def extract_video_frames(video_path: str, force: bool = False) -> List[Path]:
    """
    便捷函数：从视频提取关键帧

    Args:
        video_path: 视频文件路径
        force: 是否强制重新提取

    Returns:
        帧图片路径列表
    """
    processor = VideoProcessor()
    return processor.extract_frames(Path(video_path), force_reextract=force)


if __name__ == "__main__":
    # 测试代码
    import sys
    if len(sys.argv) > 1:
        video_file = sys.argv[1]
        frames = extract_video_frames(video_file)
        print(f"提取了 {len(frames)} 帧")
    else:
        print("用法: python video_processor.py <视频文件路径>")
