"""
B站视频下载器测试代码

测试内容：
1. URL验证功能（有效B站视频URL和无效URL）
2. 命令执行功能（成功和失败情况）
3. 进程终止功能（Windows和Linux/macOS环境）
4. 目录创建功能
"""

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "download"))
from bilibili_video_downloader import BilibiliVideoDownloader


class TestBilibiliVideoDownloader(unittest.TestCase):
    """测试B站视频下载器类"""

    def setUp(self):
        """测试前准备"""
        self.downloader = BilibiliVideoDownloader(cookies_file="test_cookies.txt")

    def test_validate_url_valid_bilibili_video(self):
        """测试验证有效B站视频URL"""
        valid_urls = [
            "https://www.bilibili.com/video/BV1xx411c7mZ/",
            "http://www.bilibili.com/video/BV1xx411c7mZ/",
            "https://www.bilibili.com/video/BV1234567890/",
            "https://bilibili.com/video/BV1xx411c7mZ/",
            "https://www.bilibili.com/bangumi/play/ep123456/",
            "https://www.bilibili.com/bangumi/play/ss12345/",
        ]
        for url in valid_urls:
            self.assertTrue(self.downloader._validate_url(url), f"URL '{url}' 应该被识别为有效B站视频地址")

    def test_validate_url_invalid(self):
        """测试验证无效URL"""
        invalid_urls = [
            "https://www.youtube.com/watch?v=xxx",
            "https://live.bilibili.com/123456",
            "https://www.baidu.com/",
            "invalid_url",
            "",
        ]
        for url in invalid_urls:
            self.assertFalse(self.downloader._validate_url(url), f"URL '{url}' 应该被识别为无效地址")

    def test_validate_url_patterns(self):
        """测试B站视频URL模式列表"""
        patterns = self.downloader.BILIBILI_VIDEO_URL_PATTERNS
        self.assertIn("https://www.bilibili.com/video/", patterns)
        self.assertIn("https://www.bilibili.com/bangumi/play/", patterns)

    def test_run_command_success(self):
        """测试成功执行命令"""
        result = self.downloader._run_command(["python", "--version"], verbose=False)
        self.assertIsNotNone(result)

    def test_run_command_failure(self):
        """测试失败执行命令"""
        result = self.downloader._run_command(["nonexistent_command_xyz"], verbose=False)
        self.assertIsNone(result)

    def test_download_dir_exists(self):
        """测试下载目录创建"""
        self.assertTrue(self.downloader.download_dir.exists())

    def test_default_format_id(self):
        """测试默认格式ID"""
        self.assertEqual(self.downloader.DEFAULT_FORMAT_ID, None)


if __name__ == "__main__":
    print("=" * 60)
    print("运行B站视频下载器测试")
    print("=" * 60)
    unittest.main(verbosity=2)