"""
B站直播视频关键帧提取器测试代码

测试内容：
1. 输入验证（文件不存在、路径不是文件、权限问题、格式不支持）
2. FFmpeg可用性检查
3. B站直播格式特定处理
4. 帧提取功能（模拟测试）
5. 异常处理和资源清理
6. 辅助方法测试（获取帧列表、数量、清除帧）
"""

import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))
from video_processor import VideoProcessor, extract_video_frames


class TestVideoProcessor(unittest.TestCase):
    """测试视频关键帧提取处理器"""

    def setUp(self):
        """测试前准备"""
        self.processor = VideoProcessor()
        self.test_dir = Path(__file__).parent / "test_output"
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
        self.assertIsNotNone(self.processor.pics_dir)
        self.assertIsNotNone(self.processor.ffmpeg_config)

    def test_ensure_pics_dir(self):
        """测试确保输出目录存在"""
        temp_dir = self.test_dir / "temp_pics"
        self.processor.pics_dir = temp_dir
        self.processor._ensure_pics_dir()
        self.assertTrue(temp_dir.exists())

    @patch("pathlib.Path.mkdir")
    def test_ensure_pics_dir_permission_error(self, mock_mkdir):
        """测试目录创建权限错误"""
        mock_mkdir.side_effect = PermissionError("Permission denied")

        temp_dir = self.test_dir / "no_permission"
        self.processor.pics_dir = temp_dir

        with self.assertRaises(PermissionError):
            self.processor._ensure_pics_dir()

        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_clean_output_dir(self):
        """测试清理输出目录"""
        temp_dir = self.test_dir / "clean_test"
        temp_dir.mkdir(exist_ok=True)

        for i in range(3):
            (temp_dir / f"frame_{i:04d}.jpg").write_text("test")

        self.processor.pics_dir = temp_dir
        self.processor._clean_output_dir()

        self.assertEqual(len(list(temp_dir.glob("*.jpg"))), 0)

    def test_clean_output_dir_not_exists(self):
        """测试清理不存在的目录"""
        temp_dir = self.test_dir / "not_exists"
        self.processor.pics_dir = temp_dir
        self.processor._clean_output_dir()

    def test_validate_input_video_not_exists(self):
        """测试验证不存在的文件"""
        non_existent = Path("nonexistent_file.mp4")
        with self.assertRaises(FileNotFoundError):
            self.processor._validate_input_video(non_existent)

    def test_validate_input_video_not_file(self):
        """测试验证路径不是文件"""
        with self.assertRaises(ValueError):
            self.processor._validate_input_video(self.test_dir)

    def test_validate_input_video_format_not_supported(self):
        """测试验证不支持的格式"""
        unsupported_file = self.test_dir / "test.txt"
        unsupported_file.write_text("test")
        try:
            with self.assertRaises(ValueError):
                self.processor._validate_input_video(unsupported_file)
        finally:
            unsupported_file.unlink()

    def test_validate_input_video_bilibili_format(self):
        """测试验证B站直播推荐格式"""
        for fmt in [".mp4", ".flv", ".ts", ".mkv"]:
            test_file = self.test_dir / f"test{fmt}"
            test_file.write_text("test")
            try:
                self.processor._validate_input_video(test_file)
            finally:
                test_file.unlink()

    def test_is_ffmpeg_available(self):
        """测试FFmpeg可用性检查"""
        result = self.processor._is_ffmpeg_available()
        self.assertIsInstance(result, bool)

    @patch("subprocess.run")
    def test_is_ffmpeg_available_true(self, mock_run):
        """测试FFmpeg可用"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = self.processor._is_ffmpeg_available()
        self.assertTrue(result)

    @patch("subprocess.run")
    def test_is_ffmpeg_available_false(self, mock_run):
        """测试FFmpeg不可用"""
        mock_run.side_effect = FileNotFoundError()

        result = self.processor._is_ffmpeg_available()
        self.assertFalse(result)

    def test_kill_process_tree_already_terminated(self):
        """测试终止已终止的进程"""
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 0

        self.processor._kill_ffmpeg_process(mock_proc)

    @patch("subprocess.run")
    def test_kill_process_tree_windows(self, mock_run):
        """测试Windows环境下进程终止"""
        with patch("os.name", "nt"):
            mock_proc = MagicMock()
            mock_proc.poll.return_value = None
            mock_proc.pid = 99999

            self.processor._kill_ffmpeg_process(mock_proc)
            mock_run.assert_called_once()

    def test_get_frame_list_empty(self):
        """测试获取空帧列表"""
        self.processor.pics_dir = self.test_dir
        frames = self.processor.get_frame_list()
        self.assertEqual(len(frames), 0)

    def test_get_frame_count(self):
        """测试获取帧数量"""
        self.processor.pics_dir = self.test_dir
        count = self.processor.get_frame_count()
        self.assertEqual(count, 0)

    def test_clear_frames(self):
        """测试清除帧图片"""
        temp_dir = self.test_dir / "clear_test"
        temp_dir.mkdir(exist_ok=True)

        for i in range(5):
            (temp_dir / f"frame_{i:04d}.jpg").write_text("test")

        self.processor.pics_dir = temp_dir
        result = self.processor.clear_frames()
        self.assertEqual(result, 0)
        self.assertEqual(len(list(temp_dir.glob("*.jpg"))), 0)

    @patch("video_processor.VideoProcessor._is_ffmpeg_available")
    @patch("subprocess.Popen")
    def test_extract_frames_success(self, mock_popen, mock_available):
        """测试提取帧成功（模拟）"""
        mock_available.return_value = True

        test_file = self.test_dir / "test.mp4"
        test_file.write_text("test")

        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        temp_pics = self.test_dir / "pics"
        temp_pics.mkdir(exist_ok=True)
        for i in range(10):
            (temp_pics / f"frame_{i + 1:04d}.jpg").write_text("test")

        self.processor.pics_dir = temp_pics

        frames = self.processor.extract_frames(test_file)
        self.assertEqual(len(frames), 10)

    @patch("video_processor.VideoProcessor._is_ffmpeg_available")
    def test_extract_frames_ffmpeg_not_available(self, mock_available):
        """测试FFmpeg不可用"""
        mock_available.return_value = False

        test_file = self.test_dir / "test.mp4"
        test_file.write_text("test")

        with self.assertRaises(EnvironmentError):
            self.processor.extract_frames(test_file)

    def test_extract_frames_file_not_found(self):
        """测试文件不存在"""
        non_existent = Path("nonexistent_file.mp4")
        with self.assertRaises(FileNotFoundError):
            self.processor.extract_frames(non_existent)

    @patch("video_processor.VideoProcessor._is_ffmpeg_available")
    @patch("subprocess.Popen")
    def test_extract_frames_ffmpeg_error(self, mock_popen, mock_available):
        """测试FFmpeg执行失败"""
        mock_available.return_value = True

        test_file = self.test_dir / "test.mp4"
        test_file.write_text("test")

        temp_pics = self.test_dir / "ffmpeg_error_pics"
        temp_pics.mkdir(exist_ok=True)
        self.processor.pics_dir = temp_pics

        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "Error message")
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        with self.assertRaises(RuntimeError):
            self.processor.extract_frames(test_file)

    def test_extract_video_frames_convenience(self):
        """测试便捷函数"""
        test_file = self.test_dir / "convenience.mp4"
        test_file.write_text("test")

        temp_pics = self.test_dir / "pics_conv"
        temp_pics.mkdir(exist_ok=True)
        for i in range(5):
            (temp_pics / f"frame_{i + 1:04d}.jpg").write_text("test")

        with patch("video_processor.VideoProcessor.extract_frames") as mock_extract:
            mock_extract.return_value = list(temp_pics.glob("*.jpg"))

            frames = extract_video_frames(str(test_file))
            self.assertEqual(len(frames), 5)

    @patch("video_processor.VideoProcessor._is_ffmpeg_available")
    def test_extract_frames_existing_frames_skip(self, mock_available):
        """测试已有帧图片时跳过提取"""
        mock_available.return_value = True

        temp_pics = self.test_dir / "existing_frames"
        temp_pics.mkdir(exist_ok=True)
        for i in range(3):
            (temp_pics / f"frame_{i + 1:04d}.jpg").write_text("test")

        self.processor.pics_dir = temp_pics

        test_file = self.test_dir / "test.mp4"
        test_file.write_text("test")

        frames = self.processor.extract_frames(test_file, force_reextract=False)
        self.assertEqual(len(frames), 3)

    @patch("video_processor.VideoProcessor._is_ffmpeg_available")
    @patch("subprocess.Popen")
    def test_extract_frames_force_reextract(self, mock_popen, mock_available):
        """测试强制重新提取"""
        mock_available.return_value = True

        temp_pics = self.test_dir / "force_reextract"
        temp_pics.mkdir(exist_ok=True)
        for i in range(3):
            (temp_pics / f"frame_{i + 1:04d}.jpg").write_text("old")

        self.processor.pics_dir = temp_pics

        test_file = self.test_dir / "test.mp4"
        test_file.write_text("test")

        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        frames = self.processor.extract_frames(test_file, force_reextract=True)
        self.assertEqual(len(frames), 0)

    def test_extract_frames_invalid_frame_interval(self):
        """测试无效的帧间隔参数"""
        test_file = self.test_dir / "test.mp4"
        test_file.write_text("test")

        with self.assertRaises(ValueError):
            self.processor.extract_frames(test_file, frame_interval=-1)

    @patch("video_processor.VideoProcessor._is_ffmpeg_available")
    @patch("subprocess.Popen")
    def test_extract_frames_with_interval(self, mock_popen, mock_available):
        """测试带时间间隔的帧提取"""
        mock_available.return_value = True

        test_file = self.test_dir / "test.mp4"
        test_file.write_text("test")

        temp_pics = self.test_dir / "interval_pics"
        temp_pics.mkdir(exist_ok=True)
        for i in range(5):
            (temp_pics / f"frame_{i + 1:04d}.jpg").write_text("test")

        self.processor.pics_dir = temp_pics

        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        frames = self.processor.extract_frames(test_file, frame_interval=5.0)
        self.assertEqual(len(frames), 5)

    @patch("video_processor.VideoProcessor._is_ffmpeg_available")
    @patch("subprocess.Popen")
    def test_extract_frames_with_zero_interval(self, mock_popen, mock_available):
        """测试帧间隔为0（不限制）"""
        mock_available.return_value = True

        test_file = self.test_dir / "test.mp4"
        test_file.write_text("test")

        temp_pics = self.test_dir / "zero_interval_pics"
        temp_pics.mkdir(exist_ok=True)
        for i in range(10):
            (temp_pics / f"frame_{i + 1:04d}.jpg").write_text("test")

        self.processor.pics_dir = temp_pics

        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        frames = self.processor.extract_frames(test_file, frame_interval=0.0)
        self.assertEqual(len(frames), 10)


if __name__ == "__main__":
    print("=" * 60)
    print("运行B站直播视频关键帧提取器测试")
    print("=" * 60)
    unittest.main(verbosity=2)