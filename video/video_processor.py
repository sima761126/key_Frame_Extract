# Name： 视频关键帧提取模块
# Author: simajinghua
# Version: 1.0.0

"""
功能：
1. 使用 FFmpeg 从视频中提取所有I帧（关键帧）
2. 支持时间间隔控制，减少提取的关键帧数量
3. 完善的异常处理和资源清理机制

使用示例：
    from video_processor import VideoProcessor, extract_video_frames

    # 使用类方式
    processor = VideoProcessor()
    frames = processor.extract_frames(Path("video.mp4"))

    # 使用便捷函数
    frames = extract_video_frames("video.mp4")
"""

import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Optional, List

# 获取当前脚本所在目录：D:\keyFrameExtract\video
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上一级目录（项目根目录）：D:\keyFrameExtract
project_root = os.path.dirname(current_dir)
# 添加到系统路径
sys.path.insert(0, project_root)  # 使用 insert(0) 确保优先级最高

import config
import json


class VideoProcessor:
    """视频关键帧提取处理器"""

    def __init__(self, pics_dir=None):
        """初始化视频处理器"""
        self.pics_dir = pics_dir if pics_dir is not None else config.PICS_DIR
        self.ffmpeg_config = config.FFMPEG_CONFIG
        self._ffmpeg_available = None

    def _ensure_output_dir(self, output_dir: Path) -> None:
        """确保输出目录存在"""
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            raise PermissionError(
                f"无法创建输出目录，请检查权限: {output_dir}"
            )

    def _ensure_pics_dir(self) -> None:
        """确保默认输出目录存在"""
        self._ensure_output_dir(self.pics_dir)

    def _clean_output_dir_in_path(self, output_dir: Path) -> None:
        """清理指定路径输出目录中的旧文件"""
        if not output_dir.exists():
            return

        deleted_count = 0
        for f in output_dir.glob("*.jpg"):
            try:
                f.unlink()
                deleted_count += 1
            except (PermissionError, FileNotFoundError):
                continue

        if deleted_count > 0:
            print(f"已清理 {deleted_count} 张旧帧图片")

    def _clean_output_dir(self) -> None:
        """清理默认输出目录中的旧文件"""
        self._clean_output_dir_in_path(self.pics_dir)

    def _get_video_duration(self, input_video: Path) -> float:
        """
        获取视频时长（秒）

        Args:
            input_video: 输入视频路径

        Returns:
            视频时长（秒）
        """
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "json",
            str(input_video)
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                duration = float(data['format']['duration'])
                return duration
            else:
                print(f"获取视频时长失败: {result.stderr}")
                return 0.0
        except Exception as e:
            print(f"获取视频时长异常: {e}")
            return 0.0

    def _validate_input_video(self, input_video: Path) -> None:
        """
        验证输入视频文件

        Args:
            input_video: 输入视频路径

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式不支持
            PermissionError: 文件无法读取
        """
        if not input_video.exists():
            raise FileNotFoundError(f"视频文件不存在: {input_video}")

        if not input_video.is_file():
            raise ValueError(f"路径不是文件: {input_video}")

        try:
            with open(input_video, "rb"):
                pass
        except PermissionError:
            raise PermissionError(
                f"无法读取视频文件，请检查权限: {input_video}"
            )

        if input_video.suffix.lower() not in config.VIDEO_FORMATS:
            raise ValueError(
                f"不支持的视频格式: {input_video.suffix}，"
                f"支持的格式: {config.VIDEO_FORMATS}"
            )

    def _build_ffmpeg_command(
        self,
        input_video: Path,
        output_dir: Path,
        frame_interval: float = 0.0
    ) -> List[str]:
        """
        构建FFmpeg命令 - 提取所有I帧（关键帧），支持时间间隔控制

        Args:
            input_video: 输入视频路径
            output_dir: 输出目录
            frame_interval: 帧提取时间间隔（秒），0表示不限制

        Returns:
            FFmpeg命令列表
        """
        output_pattern = self.ffmpeg_config["output_pattern"]
        vsync_mode = self.ffmpeg_config["vsync_mode"]

        output_path = output_dir / output_pattern

        if frame_interval > 0:
            fps_value = 1.0 / frame_interval
            vf_filter = f"select='eq(pict_type\\,I)',fps={fps_value:.6f}"
        else:
            vf_filter = "select='eq(pict_type\\,I)'"

        cmd = [
            "ffmpeg",
            "-i", str(input_video),
            "-vf", vf_filter,
            "-vsync", vsync_mode,
            "-q:v", "2",
            "-y",
            "-hide_banner",
            "-loglevel", "error",
            str(output_path)
        ]
        return cmd

    def _rename_frames_to_timestamp_format(self, frame_interval: float = 0.0, output_dir: Optional[Path] = None) -> List[Path]:
        """
        将提取的帧重命名为时间戳格式: frame_%04d_%04d.jpg (时间_序号)

        Args:
            frame_interval: 帧提取时间间隔（秒）
            output_dir: 输出目录路径，如果为None则使用默认目录

        Returns:
            重命名后的帧文件路径列表
        """
        # 使用指定的输出目录，否则使用默认目录
        target_dir = output_dir if output_dir is not None else self.pics_dir

        # 获取当前帧文件列表
        current_frames = sorted(target_dir.glob("*.jpg"))

        if not current_frames:
            return []

        renamed_frames = []
        time_counter = 0.0  # 时间计数器

        for idx, frame in enumerate(current_frames, 1):
            if frame_interval > 0:
                # 根据时间间隔计算时间戳
                timestamp = int(time_counter)
                time_counter += frame_interval
            else:
                # 如果没有时间间隔限制，可以根据索引估算时间（假设每帧间隔1秒）
                timestamp = idx - 1

            # 创建新文件名: frame_时间戳_序号.jpg
            new_filename = f"frame_{int(timestamp):04d}_{idx:04d}.jpg"
            new_path = target_dir / new_filename

            # 重命名文件
            frame.rename(new_path)
            renamed_frames.append(new_path)

        return renamed_frames

    def _is_ffmpeg_available(self) -> bool:
        """
        检查FFmpeg是否可用（结果缓存）

        Returns:
            bool: FFmpeg是否可用
        """
        if self._ffmpeg_available is None:
            try:
                result = subprocess.run(
                    ["ffmpeg", "-version"],
                    capture_output=True,
                    timeout=10
                )
                self._ffmpeg_available = result.returncode == 0
            except (FileNotFoundError, subprocess.TimeoutExpired):
                self._ffmpeg_available = False
        return self._ffmpeg_available

    def _kill_ffmpeg_process(self, process: subprocess.Popen) -> None:
        """
        终止FFmpeg进程及其子进程

        Args:
            process: FFmpeg进程对象
        """
        if process.poll() is None:
            try:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                        capture_output=True,
                        timeout=10,
                    )
                else:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass

    def extract_frames(
        self,
        input_video: Path,
        force_reextract: bool = False,
        frame_interval: float = 0.0,
        output_dir: Optional[Path] = None
    ) -> List[Path]:
        """
        从视频中提取关键帧，支持时间间隔控制

        Args:
            input_video: 输入视频路径
            force_reextract: 是否强制重新提取
            frame_interval: 帧提取时间间隔（秒），0表示不限制，提取所有I帧
            output_dir: 输出目录路径，如果为None则使用默认目录

        Returns:
            提取的图片路径列表

        Raises:
            FileNotFoundError: 视频文件不存在
            ValueError: 文件格式不支持或帧间隔参数无效
            EnvironmentError: FFmpeg未安装
            RuntimeError: FFmpeg执行失败
        """
        if frame_interval < 0:
            raise ValueError("帧间隔必须大于等于0")

        # 使用指定的输出目录，否则使用默认目录
        output_directory = output_dir if output_dir is not None else self.pics_dir

        # 验证输入文件
        self._validate_input_video(input_video)

        # 检查FFmpeg是否可用
        if not self._is_ffmpeg_available():
            raise EnvironmentError(
                "FFmpeg未安装或未添加到PATH，请先安装FFmpeg\n"
                "下载地址: https://ffmpeg.org/download.html"
            )

        # 确保输出目录存在
        self._ensure_output_dir(output_directory)

        # 检查是否已有提取结果
        existing_frames = sorted(output_directory.glob("*.jpg"))
        if existing_frames and not force_reextract:
            print(f"发现已有帧图片 {len(existing_frames)} 张，跳过提取")
            return existing_frames

        # 清理旧文件
        self._clean_output_dir_in_path(output_directory)

        # 执行FFmpeg命令
        interval_info = f"，时间间隔: {frame_interval}秒" if frame_interval > 0 else ""
        print(f"正在提取关键帧: {input_video.name}{interval_info}")
        cmd = self._build_ffmpeg_command(input_video, output_directory, frame_interval)

        process: Optional[subprocess.Popen] = None
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            stdout, stderr = process.communicate()

            if process.returncode != 0:
                error_msg = stderr.strip() if stderr else "未知错误"
                raise RuntimeError(f"FFmpeg执行失败: {error_msg}")

        except KeyboardInterrupt:
            print("\n用户中断，正在清理...")
            if process:
                self._kill_ffmpeg_process(process)
            self._clean_output_dir()
            raise

        except FileNotFoundError:
            raise EnvironmentError(
                "FFmpeg未安装或未添加到PATH，请先安装FFmpeg\n"
                "下载地址: https://ffmpeg.org/download.html"
            )

        except Exception as e:
            print(f"提取帧过程中发生错误: {e}")
            if process:
                self._kill_ffmpeg_process(process)
            self._clean_output_dir()
            raise

        # 获取提取的图片列表并重命名为时间戳格式
        frame_files = self._rename_frames_to_timestamp_format(frame_interval, output_directory)

        if not frame_files:
            print("警告: 未提取到任何关键帧，可能视频文件为空或损坏")

        print(f"成功提取 {len(frame_files)} 张关键帧")

        return frame_files

    def get_frame_list(self, pics_dir: Optional[Path] = None) -> List[Path]:
        """
        获取已提取的关键帧列表

        Args:
            pics_dir: 图片目录路径，如果为None则使用默认目录

        Returns:
            帧图片路径列表，如果目录不存在返回空列表
        """
        target_dir = pics_dir if pics_dir is not None else self.pics_dir
        if not target_dir.exists():
            return []
        return sorted(target_dir.glob("*.jpg"))

    def get_frame_count(self, pics_dir: Optional[Path] = None) -> int:
        """
        获取已提取的关键帧数量

        Args:
            pics_dir: 图片目录路径，如果为None则使用默认目录

        Returns:
            帧数量
        """
        return len(self.get_frame_list(pics_dir))

    def clear_frames(self, pics_dir: Optional[Path] = None) -> int:
        """
        清除所有已提取的帧图片

        Args:
            pics_dir: 图片目录路径，如果为None则使用默认目录

        Returns:
            清除的文件数量
        """
        target_dir = pics_dir if pics_dir is not None else self.pics_dir
        self._clean_output_dir_in_path(target_dir)
        return self.get_frame_count(target_dir)


def extract_video_frames(video_path: str, force: bool = False, frame_interval: float = 0.0, output_dir: Optional[Path] = None) -> List[Path]:
    """
    便捷函数：从视频中提取关键帧，支持时间间隔控制

    Args:
        video_path: 视频文件路径
        force: 是否强制重新提取
        frame_interval: 帧提取时间间隔（秒），0表示不限制，提取所有I帧
        output_dir: 输出目录路径，如果为None则使用默认目录

    Returns:
        帧图片路径列表
    """
    processor = VideoProcessor()
    return processor.extract_frames(Path(video_path), force_reextract=force, frame_interval=frame_interval, output_dir=output_dir)


if __name__ == "__main__":
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description="从视频中提取关键帧")
    parser.add_argument("video_path", help="视频文件路径")
    parser.add_argument("-f", "--force", action="store_true", help="强制重新提取")
    parser.add_argument("-i", "--frame-interval", type=float, default=0.0,
                        help="帧提取时间间隔（秒），0表示不限制，提取所有I帧")
    parser.add_argument("-o", "--output-dir", type=Path, help="输出目录路径，如果不指定则使用默认目录")
    args = parser.parse_args()

    try:
        frames = extract_video_frames(args.video_path, force=args.force, frame_interval=args.frame_interval, output_dir=args.output_dir)
        print(f"提取了 {len(frames)} 帧")
    except Exception as e:
        print(f"提取失败: {e}")
        sys.exit(1)