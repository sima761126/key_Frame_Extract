"""
音视频处理模块
使用 FFmpeg 进行音频提取和切片
配合 Whisper 进行语音识别
"""

import subprocess
from pathlib import Path
from typing import List, Optional
import config


class AudioProcessor:
    """音视频处理：音频提取、切片、语音识别"""

    def __init__(self):
        self.audio_dir = config.BASE_DIR / "audio"
        self.ffmpeg_config = config.FFMPEG_CONFIG

    def _ensure_audio_dir(self) -> None:
        """确保音频目录存在"""
        self.audio_dir.mkdir(parents=True, exist_ok=True)

    def extract_audio(
        self,
        input_video: Path,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        从视频中提取音频并转换为16kHz单声道（Vosk要求）

        Args:
            input_video: 输入视频路径
            output_path: 输出音频路径，默认使用 audio/full_audio.wav

        Returns:
            提取的音频文件路径
        """
        if not input_video.exists():
            raise FileNotFoundError(f"视频文件不存在: {input_video}")

        self._ensure_audio_dir()

        if output_path is None:
            output_path = self.audio_dir / "full_audio.wav"

        # 使用 FFmpeg 提取音频并转换为 16kHz 单声道（Vosk 要求）
        cmd = [
            "ffmpeg",
            "-i", str(input_video),
            "-vn",  # 不处理视频
            "-acodec", "pcm_s16le",  # 音频编码器：16位有符号LE
            "-ar", "16000",  # 采样率：16kHz
             "-ac", "1",  # 单声道
            "-y",  # 覆盖输出
            str(output_path)
        ]

        print(f"正在提取音频（16kHz单声道）...")
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                raise RuntimeError(f"FFmpeg音频提取失败: {stderr}")

            print(f"音频已提取: {output_path}")
            return output_path

        except FileNotFoundError:
            raise EnvironmentError(
                "FFmpeg未安装或未添加到PATH"
            )

    def segment_audio(
        self,
        audio_path: Path,
        segment_duration: int = 60
    ) -> List[Path]:
        """
        将音频按指定时长切片

        Args:
            audio_path: 音频文件路径
            segment_duration: 每个切片时长（秒），默认60秒

        Returns:
            音频切片路径列表
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")

        self._ensure_audio_dir()

        # 清理旧的切片文件
        for f in self.audio_dir.glob("segment_*.wav"):
            f.unlink()

        # 使用 FFmpeg segment 分割音频
        output_pattern = str(self.audio_dir / "segment_%03d.wav")

        cmd = [
            "ffmpeg",
            "-i", str(audio_path),
            "-f", "segment",
            "-segment_time", str(segment_duration),
            "-c", "copy",  # 直接复制流，不重新编码
            "-y",
            output_pattern
        ]

        print(f"正在切片音频（每段{segment_duration}秒）...")
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                raise RuntimeError(f"FFmpeg音频切片失败: {stderr}")

        except FileNotFoundError:
            raise EnvironmentError("FFmpeg未安装或未添加到PATH")

        # 获取切片列表
        segments = sorted(self.audio_dir.glob("segment_*.wav"))
        print(f"已生成 {len(segments)} 个音频切片")
        return segments


def extract_and_segment_audio(video_path: str) -> List[Path]:
    """
    便捷函数：从视频提取音频并切片

    Args:
        video_path: 视频文件路径

    Returns:
        音频切片路径列表
    """
    processor = AudioProcessor()
    video = Path(video_path)

    # 提取音频
    audio_path = processor.extract_audio(video)

    # 切片（每分钟）
    segments = processor.segment_audio(audio_path, segment_duration=60)

    return segments


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        video_file = sys.argv[1]
        segments = extract_and_segment_audio(video_file)
        print(f"生成了 {len(segments)} 个切片")
    else:
        print("用法: python audio_processor.py <视频文件路径>")