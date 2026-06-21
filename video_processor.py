"""
视频关键帧提取模块
使用 FFmpeg 从视频中提取所有I帧（关键帧）
"""

import os
import subprocess
import sys
import re
import json
from pathlib import Path
from typing import Optional, List
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

    def _get_video_duration(self, video_path: Path) -> float:
        """获取视频总时长（秒）"""
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            str(video_path)
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return float(data['format']['duration'])
        except:
            pass

        return None  # 如果获取失败返回None

    def _format_time(self, seconds: float) -> str:
        """格式化时间显示"""
        if seconds is None or seconds < 0:
            return "??:??:??"

        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"

    def _update_progress(self, current: float, total: float, frame_count: int = 0):
        """更新单行进度显示"""
        if total is None or total <= 0:
            # 没有总时长信息，只显示已处理时间
            progress_text = f"⏳ 处理中: {self._format_time(current)}"
            if frame_count > 0:
                progress_text += f" | 已提取: {frame_count} 帧"
            sys.stdout.write(f"\r{progress_text}")
        else:
            # 计算百分比
            percentage = min(100, (current / total) * 100)
            bar_length = 40
            filled_length = int(bar_length * percentage / 100)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)

            progress_text = (
                f"\r⏳ 提取关键帧: [{bar}] "
                f"{percentage:5.1f}% | "
                f"{self._format_time(current)} / {self._format_time(total)}"
            )
            if frame_count > 0:
                progress_text += f" | 已提取: {frame_count} 帧"

            sys.stdout.write(progress_text)

        sys.stdout.flush()

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
            print(f"✅ 发现已有帧图片 {len(existing_frames)} 张，跳过提取")
            return existing_frames

        # 清理旧文件
        if force_reextract:
            for f in existing_frames:
                f.unlink()
            print("🗑️ 已清理旧帧图片")

        # 执行FFmpeg命令 - 使用二进制模式
        print(f"📹 正在处理: {input_video.name}")
        cmd = self._build_ffmpeg_command(input_video, self.pics_dir)

        # 获取视频总时长（用于进度显示）
        total_duration = self._get_video_duration(input_video)

        try:
            # 启动进程 - 使用二进制模式避免编码问题
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=1
            )

            # 记录已提取的帧数（从输出文件名判断）
            frame_count = 0
            last_progress = 0

            # 显示初始进度
            self._update_progress(0, total_duration, frame_count)

            # 读取stderr获取进度信息（FFmpeg默认输出进度到stderr）
            while True:
                line = process.stderr.readline()
                if not line:
                    break

                try:
                    line_str = line.decode('utf-8', errors='ignore')
                except:
                    continue

                # 解析时间进度
                if "time=" in line_str:
                    try:
                        # 提取时间: time=00:01:23.45
                        time_match = re.search(r'time=(\d+:\d+:\d+\.\d+)', line_str)
                        if time_match:
                            time_str = time_match.group(1)
                            # 解析时间
                            parts = time_str.split(':')
                            if len(parts) == 3:
                                current_time = (
                                    int(parts[0]) * 3600 +
                                    int(parts[1]) * 60 +
                                    float(parts[2])
                                )
                            else:
                                current_time = float(time_str)

                            # 更新进度（每隔0.5秒更新一次，减少刷新频率）
                            if current_time - last_progress >= 0.5:
                                self._update_progress(current_time, total_duration, frame_count)
                                last_progress = current_time
                    except:
                        pass

                # 解析帧数（提取的关键帧数量）
                if "frame=" in line_str and "I" in line_str:
                    try:
                        # 有时FFmpeg会输出 "frame=  123 I"
                        frame_match = re.search(r'frame=\s*(\d+)', line_str)
                        if frame_match:
                            frame_count = int(frame_match.group(1))
                    except:
                        pass

            # 等待进程结束
            process.wait()

            # 完成进度 - 使用最后状态
            self._update_progress(
                total_duration if total_duration else 1,
                total_duration,
                frame_count
            )
            print()  # 换行

            if process.returncode != 0:
                # 读取错误信息
                stderr = process.stderr.read() if process.stderr else b''
                error_msg = stderr.decode('utf-8', errors='ignore')
                raise RuntimeError(f"FFmpeg执行失败: {error_msg[:200]}")

        except FileNotFoundError:
            print()  # 换行
            raise EnvironmentError(
                "❌ FFmpeg未安装或未添加到PATH，请先安装FFmpeg\n"
                "下载地址: https://ffmpeg.org/download.html"
            )
        except Exception as e:
            print()  # 换行
            raise

        # 获取提取的图片列表
        frame_files = sorted(self.pics_dir.glob("*.jpg"))

        # 最终统计信息
        print(f"✅ 成功提取 {len(frame_files)} 张关键帧")

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