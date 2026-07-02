"""
音频处理模块

使用 FFmpeg 进行音频提取和切片
针对 B 站直播源进行优化
支持格式：.mp4, .flv, .ts, .mkv
"""

import subprocess
import os
import sys
import re
import json
from pathlib import Path
from typing import List, Optional
from tqdm import tqdm

import config


class AudioProcessor:
    """音频处理：音频提取、切片、语音识别"""

    def __init__(self):
        self.audio_dir = config.AUDIO_DIR
        self.ffmpeg_config = config.FFMPEG_CONFIG

    def _ensure_audio_dir(self) -> None:
        """确保音频目录存在"""
        self.audio_dir.mkdir(parents=True, exist_ok=True)

    def _build_extract_command(
        self,
        input_video: Path,
        output_path: Path
    ) -> List[str]:
        """
        构建音频提取的FFmpeg命令

        Args:
            input_video: 输入视频路径
            output_path: 输出音频路径

        Returns:
            FFmpeg命令列表
        """
        cmd = [
            "ffmpeg",
            "-i", str(input_video),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            "-y",
            str(output_path)
        ]
        return cmd

    def _get_audio_duration(self, audio_path: Path) -> float:
        """获取音频总时长（秒）"""
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            str(audio_path)
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

    def _build_segment_command(
        self,
        audio_path: Path,
        output_pattern: str,
        segment_duration: int
    ) -> List[str]:
        """
        构建音频切片的FFmpeg命令

        Args:
            audio_path: 音频文件路径
            output_pattern: 输出文件名模式
            segment_duration: 每个切片时长（秒）

        Returns:
            FFmpeg命令列表
        """
        cmd = [
            "ffmpeg",
            "-i", str(audio_path),
            "-f", "segment",
            "-segment_time", str(segment_duration),
            "-reset_timestamps", "1",  # 重置每个切片的时间戳
            "-c", "copy",
            "-y",
            output_pattern
        ]
        return cmd

    def _clean_segment_files(self) -> None:
        """清理旧的切片文件"""
        for f in self.audio_dir.glob("audio_*_*.wav"):
            f.unlink()
        for f in self.audio_dir.glob("segment_*.wav"):
            f.unlink()

    def extract_audio(
        self,
        input_video: Path,
        force_reextract: bool = False,
        output_dir: Optional[Path] = None
    ) -> Path:
        """
        从视频中提取音频并转换为16kHz单声道（Vosk要求）

        Args:
            input_video: 输入视频路径
            force_reextract: 是否强制重新提取
            output_dir: 输出目录路径，如果为None则使用默认目录

        Returns:
            提取的音频文件路径
        """
        if not input_video.exists():
            raise FileNotFoundError(f"视频文件不存在: {input_video}")

        if input_video.suffix.lower() not in config.VIDEO_FORMATS:
            raise ValueError(
                f"不支持的视频格式: {input_video.suffix}，"
                f"支持格式: {config.VIDEO_FORMATS}"
            )

        if output_dir is not None:
            self.audio_dir = output_dir

        self._ensure_audio_dir()

        output_path = self.audio_dir / "full_audio.wav"

        if output_path.exists() and not force_reextract:
            print(f"✅ 发现已有音频文件，跳过提取")
            return output_path

        if force_reextract and output_path.exists():
            output_path.unlink()
            print("🗑️ 已清理旧音频文件")

        self._clean_segment_files()

        cmd = self._build_extract_command(input_video, output_path)

        print(f"🎵 正在处理: {input_video.name}")
        print(f"正在提取音频（16kHz单声道）...")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            pbar = tqdm(
                total=None,
                desc="提取音频",
                unit="s",
                bar_format="{desc}: [{bar}] {n:.1f}s [{elapsed}]",
                ncols=80
            )

            last_progress = 0
            current_time = 0

            while True:
                line = process.stderr.readline()
                if not line:
                    break

                try:
                    line_str = line.decode('utf-8', errors='ignore')
                except:
                    continue

                if "time=" in line_str:
                    try:
                        time_match = re.search(r'time=(\d+:\d+:\d+\.\d+)', line_str)
                        if time_match:
                            time_str = time_match.group(1)
                            parts = time_str.split(':')
                            if len(parts) == 3:
                                current_time = (
                                    int(parts[0]) * 3600 +
                                    int(parts[1]) * 60 +
                                    float(parts[2])
                                )
                            else:
                                current_time = float(time_str)

                            if current_time - last_progress >= 0.5:
                                pbar.update(current_time - last_progress)
                                last_progress = current_time
                    except:
                        pass

                if "progress=end" in line_str:
                    break

            process.wait()
            pbar.close()

            if process.returncode != 0:
                stderr = process.stderr.read() if process.stderr else b''
                error_msg = stderr.decode('utf-8', errors='ignore')
                raise RuntimeError(f"FFmpeg音频提取失败: {error_msg[:200]}")

        except FileNotFoundError:
            raise EnvironmentError(
                "❌ FFmpeg未安装或未添加到PATH，请先安装FFmpeg\n"
                "下载地址: https://ffmpeg.org/download.html"
            )
        except Exception as e:
            raise

        print(f"✅ 音频已提取: {output_path}")
        return output_path

    def segment_audio(
        self,
        audio_path: Path,
        segment_duration: int = 60,
        force_resegment: bool = False,
        output_dir: Optional[Path] = None
    ) -> List[Path]:
        """
        将音频按指定时长切片

        Args:
            audio_path: 音频文件路径
            segment_duration: 每个切片时长（秒），默认60秒
            force_resegment: 是否强制重新切片
            output_dir: 输出目录路径，如果为None则使用默认目录

        Returns:
            音频切片路径列表
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")

        if segment_duration <= 0:
            raise ValueError(f"切片时长必须大于0，当前值: {segment_duration}")

        if output_dir is not None:
            self.audio_dir = output_dir

        self._ensure_audio_dir()

        # 生成带时间戳的切片文件名
        audio_duration = self._get_audio_duration(audio_path)
        total_segments = int(audio_duration / segment_duration) + 1 if audio_duration else 1
        
        # 清理旧的切片文件
        if force_resegment:
            self._clean_segment_files()
            print("🗑️ 已清理旧切片文件")

        # 检查是否已有切片文件
        existing_segments = sorted(self.audio_dir.glob("audio_*_*.wav"))
        if existing_segments and not force_resegment:
            print(f"✅ 发现已有切片 {len(existing_segments)} 个，跳过切片")
            return existing_segments

        # 使用临时文件名进行切片，然后重命名
        temp_pattern = str(self.audio_dir / "temp_segment_%03d.wav")
        cmd = self._build_segment_command(audio_path, temp_pattern, segment_duration)

        print(f"正在切片音频（每段{segment_duration}秒）...")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            pbar = tqdm(
                total=None,
                desc="切片音频",
                unit="段",
                bar_format="{desc}: [{bar}] {n} 段 [{elapsed}]",
                ncols=80
            )

            segment_count = 0

            while True:
                line = process.stderr.readline()
                if not line:
                    break

                try:
                    line_str = line.decode('utf-8', errors='ignore')
                except:
                    continue

                if "segment_" in line_str and ".wav" in line_str:
                    segment_count += 1
                    pbar.update(1)

                if "progress=end" in line_str:
                    break

            process.wait()
            pbar.close()

            if process.returncode != 0:
                stderr = process.stderr.read() if process.stderr else b''
                error_msg = stderr.decode('utf-8', errors='ignore')
                raise RuntimeError(f"FFmpeg音频切片失败: {error_msg[:200]}")

        except FileNotFoundError:
            raise EnvironmentError(
                "❌ FFmpeg未安装或未添加到PATH，请先安装FFmpeg\n"
                "下载地址: https://ffmpeg.org/download.html"
            )
        except Exception as e:
            raise

        # 重命名切片文件为带时间戳的格式
        temp_segments = sorted(self.audio_dir.glob("temp_segment_*.wav"))
        renamed_segments = []
        
        for i, temp_seg in enumerate(temp_segments):
            start_time = i * segment_duration
            formatted_start = f"{start_time:04d}"  # 格式化为4位数字
            new_name = f"audio_{formatted_start}_{i+1:04d}.wav"
            new_path = self.audio_dir / new_name
            temp_seg.rename(new_path)
            renamed_segments.append(new_path)

        print(f"✅ 已生成 {len(renamed_segments)} 个音频切片")
        return renamed_segments

    def extract_and_segment_audio(
        self,
        input_video: Path,
        force_reextract: bool = False,
        segment_duration: int = 60,
        output_dir: Optional[Path] = None
    ) -> List[Path]:
        """
        从视频提取音频并切片（组合方法）

        Args:
            input_video: 输入视频路径
            force_reextract: 是否强制重新提取和切片
            segment_duration: 每个切片时长（秒）
            output_dir: 输出目录路径，如果为None则使用默认目录

        Returns:
            音频切片路径列表
        """
        audio_path = self.extract_audio(
            input_video,
            force_reextract=force_reextract,
            output_dir=output_dir
        )
        segments = self.segment_audio(
            audio_path,
            segment_duration=segment_duration,
            force_resegment=force_reextract,
            output_dir=output_dir
        )
        return segments

    def clear_audio_files(self) -> int:
        """
        清除所有音频文件

        Returns:
            清除的文件数量
        """
        count = 0
        for f in self.audio_dir.glob("*.wav"):
            f.unlink()
            count += 1
        return count

    def get_segment_count(self) -> int:
        """
        获取当前切片数量

        Returns:
            切片文件数量
        """
        return len(list(self.audio_dir.glob("audio_*_*.wav")))


def extract_audio_from_video(video_path: str, force: bool = False, output_dir: Optional[Path] = None) -> Path:
    """
    便捷函数：从视频提取音频

    Args:
        video_path: 视频文件路径
        force: 是否强制重新提取
        output_dir: 输出目录路径，如果为None则使用默认目录

    Returns:
        提取的音频文件路径
    """
    processor = AudioProcessor()
    return processor.extract_audio(Path(video_path), force_reextract=force, output_dir=output_dir)


def segment_audio_file(audio_path: str, segment_duration: int = 60, force: bool = False, output_dir: Optional[Path] = None) -> List[Path]:
    """
    便捷函数：将音频切片

    Args:
        audio_path: 音频文件路径
        segment_duration: 每个切片时长（秒）
        force: 是否强制重新切片
        output_dir: 输出目录路径，如果为None则使用默认目录

    Returns:
        音频切片路径列表
    """
    processor = AudioProcessor()
    return processor.segment_audio(Path(audio_path), segment_duration=segment_duration, force_resegment=force, output_dir=output_dir)


def extract_and_segment_audio(video_path: str, force: bool = False, segment_duration: int = 60, output_dir: Optional[Path] = None) -> List[Path]:
    """
    便捷函数：从视频提取音频并切片

    Args:
        video_path: 视频文件路径
        force: 是否强制重新提取和切片
        segment_duration: 每个切片时长（秒）
        output_dir: 输出目录路径，如果为None则使用默认目录

    Returns:
        音频切片路径列表
    """
    processor = AudioProcessor()
    return processor.extract_and_segment_audio(
        Path(video_path),
        force_reextract=force,
        segment_duration=segment_duration,
        output_dir=output_dir
    )


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description="从视频中提取音频并切片")
    parser.add_argument("video_path", help="视频文件路径")
    parser.add_argument("-f", "--force", action="store_true", help="强制重新提取")
    parser.add_argument("-i", "--segment-duration", type=int, default=60,
                        help="音频切片时长（秒），默认60秒")
    parser.add_argument("-o", "--output-dir", type=Path, help="输出目录路径，如果不指定则使用默认目录")
    args = parser.parse_args()

    try:
        segments = extract_and_segment_audio(args.video_path, force=args.force, segment_duration=args.segment_duration, output_dir=args.output_dir)
        print(f"生成了 {len(segments)} 个切片")
    except Exception as e:
        print(f"处理失败: {e}")
        sys.exit(1)