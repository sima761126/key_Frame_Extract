"""
音频处理器测试代码

测试内容：
1. 输入验证（文件不存在、格式不支持）
2. FFmpeg命令构建
3. B站直播格式特定处理（.mp4, .flv, .ts, .mkv）
4. 音频提取功能（模拟测试，含进度条）
5. 音频切片功能（模拟测试）
6. 跳过已有文件测试
7. 辅助方法测试（清除音频文件、获取切片数量）
"""

import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))
from audio_processor import AudioProcessor, extract_audio_from_video, segment_audio_file, extract_and_segment_audio


class TestAudioProcessor(unittest.TestCase):
    """测试音频处理器"""

    def setUp(self):
        """测试前准备"""
        self.processor = AudioProcessor()
        self.test_dir = Path(__file__).parent / "test_output_audio"
        self.test_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        """测试后清理"""
        if self.test_dir.exists():
            for item in self.test_dir.rglob("*"):
                if item.is_file():
                    try:
                        item.unlink()
                    except Exception:
                        pass
            for item in sorted(self.test_dir.rglob("*"), reverse=True):
                if item.is_dir():
                    try:
                        item.rmdir()
                    except Exception:
                        pass
            try:
                self.test_dir.rmdir()
            except Exception:
                pass

    def test_init(self):
        """测试初始化"""
        self.assertIsNotNone(self.processor.audio_dir)
        self.assertIsNotNone(self.processor.ffmpeg_config)

    def test_ensure_audio_dir(self):
        """测试确保输出目录存在"""
        temp_dir = self.test_dir / "temp_audio"
        self.processor.audio_dir = temp_dir
        self.processor._ensure_audio_dir()
        self.assertTrue(temp_dir.exists())

    def test_build_extract_command(self):
        """测试构建音频提取命令"""
        test_file = self.test_dir / "test.mp4"
        test_file.write_text("test")
        output_path = self.test_dir / "output.wav"

        cmd = self.processor._build_extract_command(test_file, output_path)

        self.assertIsInstance(cmd, list)
        self.assertIn("ffmpeg", cmd)
        self.assertIn("-i", cmd)
        self.assertIn(str(test_file), cmd)
        self.assertIn("-vn", cmd)
        self.assertIn("-acodec", cmd)
        self.assertIn("pcm_s16le", cmd)
        self.assertIn("-ar", cmd)
        self.assertIn("16000", cmd)
        self.assertIn("-ac", cmd)
        self.assertIn("1", cmd)
        self.assertIn(str(output_path), cmd)

    def test_build_segment_command(self):
        """测试构建音频切片命令"""
        audio_file = self.test_dir / "audio.wav"
        audio_file.write_text("test")
        output_pattern = str(self.test_dir / "segment_%03d.wav")
        segment_duration = 60

        cmd = self.processor._build_segment_command(audio_file, output_pattern, segment_duration)

        self.assertIsInstance(cmd, list)
        self.assertIn("ffmpeg", cmd)
        self.assertIn("-i", cmd)
        self.assertIn(str(audio_file), cmd)
        self.assertIn("-f", cmd)
        self.assertIn("segment", cmd)
        self.assertIn("-segment_time", cmd)
        self.assertIn("60", cmd)
        self.assertIn("-c", cmd)
        self.assertIn("copy", cmd)
        self.assertIn(output_pattern, cmd)

    def test_clean_segment_files(self):
        """测试清理切片文件"""
        temp_dir = self.test_dir / "clean_test"
        temp_dir.mkdir(exist_ok=True)

        for i in range(3):
            (temp_dir / f"segment_{i:03d}.wav").write_text("test")

        self.processor.audio_dir = temp_dir
        self.processor._clean_segment_files()

        self.assertEqual(len(list(temp_dir.glob("segment_*.wav"))), 0)

    def test_extract_audio_file_not_found(self):
        """测试文件不存在"""
        non_existent = Path("nonexistent_file.mp4")
        with self.assertRaises(FileNotFoundError):
            self.processor.extract_audio(non_existent)

    def test_extract_audio_format_not_supported(self):
        """测试不支持的视频格式"""
        unsupported_file = self.test_dir / "test.txt"
        unsupported_file.write_text("test")
        try:
            with self.assertRaises(ValueError):
                self.processor.extract_audio(unsupported_file)
        finally:
            unsupported_file.unlink()

    def test_extract_audio_bilibili_format(self):
        """测试B站直播推荐格式"""
        for fmt in [".mp4", ".flv", ".ts", ".mkv"]:
            test_file = self.test_dir / f"test{fmt}"
            test_file.write_text("test")
            try:
                with patch("subprocess.Popen") as mock_popen:
                    mock_process = MagicMock()
                    mock_process.stderr.readline.return_value = b''
                    mock_process.returncode = 0
                    mock_popen.return_value = mock_process

                    temp_audio = self.test_dir / f"audio_{fmt}"
                    temp_audio.mkdir(exist_ok=True)
                    self.processor.audio_dir = temp_audio

                    self.processor.extract_audio(test_file)
            finally:
                test_file.unlink()

    def test_extract_audio_skip_if_exists(self):
        """测试已有音频文件时跳过提取"""
        temp_audio = self.test_dir / "skip_audio"
        temp_audio.mkdir(exist_ok=True)
        (temp_audio / "full_audio.wav").write_text("test")

        self.processor.audio_dir = temp_audio

        test_file = self.test_dir / "test.mp4"
        test_file.write_text("test")

        audio_path = self.processor.extract_audio(test_file, force_reextract=False)
        self.assertEqual(audio_path, temp_audio / "full_audio.wav")

    def test_extract_audio_force_reextract(self):
        """测试强制重新提取"""
        temp_audio = self.test_dir / "force_audio"
        temp_audio.mkdir(exist_ok=True)
        (temp_audio / "full_audio.wav").write_text("old")

        self.processor.audio_dir = temp_audio

        test_file = self.test_dir / "test.mp4"
        test_file.write_text("test")

        def create_file_after_clean(*args, **kwargs):
            (temp_audio / "full_audio.wav").write_text("new")
            mock_process = MagicMock()
            mock_process.stderr.readline.return_value = b''
            mock_process.returncode = 0
            return mock_process

        with patch("subprocess.Popen", side_effect=create_file_after_clean) as mock_popen:
            audio_path = self.processor.extract_audio(test_file, force_reextract=True)
            self.assertTrue(audio_path.exists())

    def test_extract_audio_ffmpeg_error(self):
        """测试FFmpeg执行失败"""
        test_file = self.test_dir / "test.mp4"
        test_file.write_text("test")

        temp_audio = self.test_dir / "ffmpeg_error_audio"
        temp_audio.mkdir(exist_ok=True)
        self.processor.audio_dir = temp_audio

        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.stderr.readline.return_value = b''
            mock_process.returncode = 1
            mock_process.stderr.read.return_value = b"Error"
            mock_popen.return_value = mock_process

            with self.assertRaises(RuntimeError):
                self.processor.extract_audio(test_file)

    def test_extract_audio_ffmpeg_not_found(self):
        """测试FFmpeg未安装"""
        test_file = self.test_dir / "test.mp4"
        test_file.write_text("test")

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.side_effect = FileNotFoundError()

            with self.assertRaises(EnvironmentError):
                self.processor.extract_audio(test_file)

    def test_segment_audio_file_not_found(self):
        """测试音频文件不存在"""
        non_existent = Path("nonexistent_audio.wav")
        with self.assertRaises(FileNotFoundError):
            self.processor.segment_audio(non_existent)

    def test_segment_audio_invalid_duration(self):
        """测试无效的切片时长"""
        audio_file = self.test_dir / "test.wav"
        audio_file.write_text("test")

        with self.assertRaises(ValueError):
            self.processor.segment_audio(audio_file, segment_duration=0)

        with self.assertRaises(ValueError):
            self.processor.segment_audio(audio_file, segment_duration=-1)

    def test_segment_audio_skip_if_exists(self):
        """测试已有切片文件时跳过切片"""
        temp_audio = self.test_dir / "skip_segment"
        temp_audio.mkdir(exist_ok=True)

        for i in range(3):
            (temp_audio / f"segment_{i + 1:03d}.wav").write_text("test")

        self.processor.audio_dir = temp_audio

        audio_file = temp_audio / "full_audio.wav"
        audio_file.write_text("test")

        segments = self.processor.segment_audio(audio_file, force_resegment=False)
        self.assertEqual(len(segments), 3)

    def test_segment_audio_force_resegment(self):
        """测试强制重新切片"""
        temp_audio = self.test_dir / "force_segment"
        temp_audio.mkdir(exist_ok=True)

        for i in range(3):
            (temp_audio / f"segment_{i + 1:03d}.wav").write_text("old")

        self.processor.audio_dir = temp_audio

        audio_file = temp_audio / "full_audio.wav"
        audio_file.write_text("test")

        def create_segments_after_clean(*args, **kwargs):
            for i in range(5):
                (temp_audio / f"segment_{i + 1:03d}.wav").write_text("new")
            mock_process = MagicMock()
            mock_process.stderr.readline.return_value = b''
            mock_process.returncode = 0
            return mock_process

        with patch("subprocess.Popen", side_effect=create_segments_after_clean) as mock_popen:
            segments = self.processor.segment_audio(audio_file, force_resegment=True)
            self.assertEqual(len(segments), 5)

    def test_segment_audio_ffmpeg_error(self):
        """测试FFmpeg执行失败"""
        temp_audio = self.test_dir / "segment_error_audio"
        temp_audio.mkdir(exist_ok=True)
        audio_file = temp_audio / "full_audio.wav"
        audio_file.write_text("test")

        self.processor.audio_dir = temp_audio

        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.stderr.readline.return_value = b''
            mock_process.returncode = 1
            mock_process.stderr.read.return_value = b"Error"
            mock_popen.return_value = mock_process

            with self.assertRaises(RuntimeError):
                self.processor.segment_audio(audio_file)

    def test_segment_audio_ffmpeg_not_found(self):
        """测试FFmpeg未安装"""
        audio_file = self.test_dir / "test.wav"
        audio_file.write_text("test")

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.side_effect = FileNotFoundError()

            with self.assertRaises(EnvironmentError):
                self.processor.segment_audio(audio_file)

    def test_extract_and_segment_audio(self):
        """测试组合方法"""
        test_file = self.test_dir / "combo.mp4"
        test_file.write_text("test")

        temp_audio = self.test_dir / "combo_audio"
        temp_audio.mkdir(exist_ok=True)

        self.processor.audio_dir = temp_audio

        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.stderr.readline.return_value = b''
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            (temp_audio / "full_audio.wav").write_text("test")
            for i in range(3):
                (temp_audio / f"segment_{i + 1:03d}.wav").write_text("test")

            segments = self.processor.extract_and_segment_audio(test_file)
            self.assertEqual(len(segments), 3)

    def test_clear_audio_files(self):
        """测试清除所有音频文件"""
        temp_dir = self.test_dir / "clear_test"
        temp_dir.mkdir(exist_ok=True)

        for i in range(5):
            (temp_dir / f"audio_{i}.wav").write_text("test")

        self.processor.audio_dir = temp_dir
        count = self.processor.clear_audio_files()

        self.assertEqual(count, 5)
        self.assertEqual(len(list(temp_dir.glob("*.wav"))), 0)

    def test_get_segment_count(self):
        """测试获取切片数量"""
        self.processor.audio_dir = self.test_dir
        count = self.processor.get_segment_count()
        self.assertEqual(count, 0)

    def test_get_segment_count_with_segments(self):
        """测试获取已有切片数量"""
        temp_dir = self.test_dir / "count_test"
        temp_dir.mkdir(exist_ok=True)

        for i in range(3):
            (temp_dir / f"segment_{i:03d}.wav").write_text("test")

        self.processor.audio_dir = temp_dir
        count = self.processor.get_segment_count()
        self.assertEqual(count, 3)

    def test_extract_audio_from_video_convenience(self):
        """测试便捷函数 extract_audio_from_video"""
        test_file = self.test_dir / "conv_extract.mp4"
        test_file.write_text("test")

        temp_audio = self.test_dir / "conv_audio"
        temp_audio.mkdir(exist_ok=True)
        (temp_audio / "full_audio.wav").write_text("test")

        with patch("audio_processor.AudioProcessor.extract_audio") as mock_extract:
            mock_extract.return_value = temp_audio / "full_audio.wav"

            audio_path = extract_audio_from_video(str(test_file))
            self.assertEqual(audio_path, temp_audio / "full_audio.wav")

    def test_segment_audio_file_convenience(self):
        """测试便捷函数 segment_audio_file"""
        test_file = self.test_dir / "conv_segment.wav"
        test_file.write_text("test")

        temp_audio = self.test_dir / "conv_segment_audio"
        temp_audio.mkdir(exist_ok=True)
        for i in range(3):
            (temp_audio / f"segment_{i + 1:03d}.wav").write_text("test")

        with patch("audio_processor.AudioProcessor.segment_audio") as mock_segment:
            mock_segment.return_value = list(temp_audio.glob("segment_*.wav"))

            segments = segment_audio_file(str(test_file))
            self.assertEqual(len(segments), 3)

    def test_extract_and_segment_audio_convenience(self):
        """测试便捷函数 extract_and_segment_audio"""
        test_file = self.test_dir / "convenience.mp4"
        test_file.write_text("test")

        temp_audio = self.test_dir / "pics_conv"
        temp_audio.mkdir(exist_ok=True)
        for i in range(3):
            (temp_audio / f"segment_{i + 1:03d}.wav").write_text("test")

        with patch("audio_processor.AudioProcessor.extract_and_segment_audio") as mock_combo:
            mock_combo.return_value = list(temp_audio.glob("segment_*.wav"))

            segments = extract_and_segment_audio(str(test_file))
            self.assertEqual(len(segments), 3)


if __name__ == "__main__":
    print("=" * 60)
    print("运行音频处理器测试")
    print("=" * 60)
    unittest.main(verbosity=2)