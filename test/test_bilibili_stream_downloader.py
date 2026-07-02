"""
B站直播流下载器测试代码

测试内容：
1. URL验证
2. 格式ID判断（fmp4格式）
3. 命令执行
4. 目录创建
5. 进程终止
"""

import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent))
from download.bilibili_stream_downloader import BilibiliLiveStreamer


class TestBilibiliLiveStreamer(unittest.TestCase):
    """测试B站直播流下载器类"""

    def setUp(self):
        """测试前准备"""
        self.streamer = BilibiliLiveStreamer(cookies_file="test_cookies.txt")

    def test_validate_url_valid_bilibili(self):
        """测试验证有效B站直播URL"""
        valid_urls = [
            "https://live.bilibili.com/1914112349",
            "http://live.bilibili.com/1914112349",
            "https://live.bilibili.com/123",
        ]
        for url in valid_urls:
            self.assertTrue(self.streamer._validate_url(url), f"URL '{url}' 应该被识别为有效B站直播地址")

    def test_validate_url_invalid(self):
        """测试验证无效URL"""
        invalid_urls = [
            "https://www.baidu.com",
            "https://live.douyin.com/123456",
            "https://www.youtube.com/watch?v=abc",
            "ftp://live.bilibili.com/123",
            "invalid_url",
        ]
        for url in invalid_urls:
            self.assertFalse(self.streamer._validate_url(url), f"URL '{url}' 应该被识别为无效B站直播地址")

    def test_is_fmp4_format_true(self):
        """测试判断fmp4格式ID返回True"""
        fmp4_formats = ["ultra_high_res-0", "ultra_high_res-1", "ultra_high_res-2", "ultra_high_res-3",
                        "ultra_high_res-6", "ultra_high_res-7"]
        for fmt in fmp4_formats:
            self.assertTrue(self.streamer._is_fmp4_format(fmt), f"格式 '{fmt}' 应该被识别为fmp4格式")

    def test_is_fmp4_format_false(self):
        """测试判断非fmp4格式ID返回False"""
        flv_formats = ["ultra_high_res-4", "ultra_high_res-5"]
        for fmt in flv_formats:
            self.assertFalse(self.streamer._is_fmp4_format(fmt), f"格式 '{fmt}' 不应该被识别为fmp4格式")

    def test_is_fmp4_format_none(self):
        """测试判断None格式ID返回False"""
        self.assertFalse(self.streamer._is_fmp4_format(None))

    def test_is_fmp4_format_empty(self):
        """测试判断空字符串格式ID返回False"""
        self.assertFalse(self.streamer._is_fmp4_format(""))

    def test_run_command_success(self):
        """测试执行命令成功"""
        if os.name == "nt":
            result = self.streamer._run_command(["cmd", "/c", "echo hello"], verbose=False)
        else:
            result = self.streamer._run_command(["echo", "hello"], verbose=False)
        self.assertIsNotNone(result)
        self.assertTrue("hello" in result)

    def test_run_command_failure(self):
        """测试执行命令失败"""
        result = self.streamer._run_command(["nonexistent_command_xyz123"], verbose=False)
        self.assertIsNone(result)

    def test_default_format_id(self):
        """测试默认格式ID"""
        self.assertEqual(self.streamer.DEFAULT_FORMAT_ID, "ultra_high_res-0")

    def test_bilibili_url_patterns(self):
        """测试B站URL模式"""
        patterns = self.streamer.BILIBILI_LIVE_URL_PATTERNS
        self.assertIn("https://live.bilibili.com/", patterns)
        self.assertIn("http://live.bilibili.com/", patterns)

    def test_fmp4_format_ids(self):
        """测试fmp4格式ID列表"""
        fmp4_ids = self.streamer.FMP4_FORMAT_IDS
        self.assertIn("ultra_high_res-0", fmp4_ids)
        self.assertIn("ultra_high_res-1", fmp4_ids)
        self.assertIn("ultra_high_res-2", fmp4_ids)
        self.assertIn("ultra_high_res-3", fmp4_ids)
        self.assertIn("ultra_high_res-6", fmp4_ids)
        self.assertIn("ultra_high_res-7", fmp4_ids)

    def test_flv_format_ids(self):
        """测试FLV格式ID列表"""
        flv_ids = self.streamer.FLV_FORMAT_IDS
        self.assertIn("ultra_high_res-4", flv_ids)
        self.assertIn("ultra_high_res-5", flv_ids)

    def test_download_dir_created(self):
        """测试下载目录是否创建"""
        self.assertTrue(self.streamer.download_dir.exists())

    def test_kill_process_tree_windows(self):
        """测试Windows环境下进程终止"""
        with patch("os.name", "nt"):
            mock_proc = MagicMock()
            mock_proc.poll.return_value = None
            mock_proc.pid = 99999
            with patch("subprocess.run") as mock_run:
                self.streamer._kill_process_tree(mock_proc)
                mock_run.assert_called_once()
                args = mock_run.call_args[0][0]
                self.assertEqual(args[:4], ["taskkill", "/F", "/T", "/PID"])

    def test_kill_process_tree_already_terminated(self):
        """测试终止已终止的进程"""
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 0
        with patch("subprocess.run") as mock_run:
            self.streamer._kill_process_tree(mock_proc)
            mock_run.assert_not_called()

    @patch("subprocess.run")
    def test_list_formats_invalid_url(self, mock_run):
        """测试查看格式列表时URL无效的情况"""
        result = self.streamer.list_formats("https://www.baidu.com")
        mock_run.assert_not_called()
        self.assertIsNone(result)

    @patch("subprocess.run")
    def test_get_stream_url_success(self, mock_run):
        """测试获取流地址成功"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "https://example.com/stream.m3u8"
        mock_run.return_value = mock_result

        url = self.streamer._get_stream_url("https://live.bilibili.com/123456", "ultra_high_res-2")
        self.assertEqual(url, "https://example.com/stream.m3u8")

    @patch("subprocess.run")
    def test_get_stream_url_failure(self, mock_run):
        """测试获取流地址失败"""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Error"
        mock_run.return_value = mock_result

        url = self.streamer._get_stream_url("https://live.bilibili.com/123456", "ultra_high_res-2")
        self.assertIsNone(url)

    def test_download_live_only_invalid_url(self):
        """测试download_live_only方法 - 无效URL"""
        result = self.streamer.download_live_only(url="https://www.baidu.com/")
        self.assertIsNone(result)

    def test_download_live_only_valid_url(self):
        """测试download_live_only方法 - 有效URL（模拟测试，不实际下载）"""
        result = self.streamer.download_live_only(
            url="https://live.bilibili.com/123456",
            duration=30,
            output_name="test_download_live_only"
        )
        # 由于没有实际下载，应该返回None或视频文件路径
        # 这里不进行实际下载测试，只验证方法调用不报错
        pass

    def tearDown(self):
        """测试后清理"""
        test_cookies = Path("test_cookies.txt")
        if test_cookies.exists():
            test_cookies.unlink()


if __name__ == "__main__":
    print("=" * 60)
    print("运行B站直播流下载器测试")
    print("=" * 60)
    unittest.main(verbosity=2)
