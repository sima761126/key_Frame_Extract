# Name： B站Cookies获取工具测试
# Author: simajinghua
# Version: 1.0.0

"""
测试B站Cookies获取工具的各项功能
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

from get_bilibili_cookies import BilibiliCookiesFetcher


class TestBilibiliCookiesFetcher(unittest.TestCase):
    """测试B站Cookies获取器类"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.output_file = os.path.join(self.temp_dir, "test_cookies.txt")
        self.fetcher = BilibiliCookiesFetcher(output_file=self.output_file)

    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)

    def test_is_bilibili_cookie_true(self):
        """测试判断B站Cookie返回True"""
        test_cookies = [
            {"domain": ".bilibili.com", "name": "test", "value": "value"},
            {"domain": "live.bilibili.com", "name": "test", "value": "value"},
            {"domain": "www.bilibili.com", "name": "test", "value": "value"},
            {"domain": "api.bilibili.com", "name": "test", "value": "value"},
        ]
        for cookie in test_cookies:
            self.assertTrue(
                self.fetcher._is_bilibili_cookie(cookie),
                f"Cookie '{cookie['domain']}' 应该被识别为B站Cookie"
            )

    def test_is_bilibili_cookie_false(self):
        """测试判断非B站Cookie返回False"""
        test_cookies = [
            {"domain": ".youtube.com", "name": "test", "value": "value"},
            {"domain": "www.baidu.com", "name": "test", "value": "value"},
            {"domain": "", "name": "test", "value": "value"},
            {"domain": "example.com", "name": "test", "value": "value"},
        ]
        for cookie in test_cookies:
            self.assertFalse(
                self.fetcher._is_bilibili_cookie(cookie),
                f"Cookie '{cookie['domain']}' 不应该被识别为B站Cookie"
            )

    def test_format_cookies_only_bilibili(self):
        """测试格式化Cookies只保留B站相关的"""
        raw_cookies = [
            {"domain": ".bilibili.com", "name": "bili_cookie", "value": "bili_value"},
            {"domain": "live.bilibili.com", "name": "live_cookie", "value": "live_value"},
            {"domain": ".youtube.com", "name": "youtube_cookie", "value": "youtube_value"},
        ]

        result = self.fetcher._format_cookies(raw_cookies)

        self.assertEqual(len(result), 2)
        cookie_names = [c["name"] for c in result]
        self.assertIn("bili_cookie", cookie_names)
        self.assertIn("live_cookie", cookie_names)
        self.assertNotIn("youtube_cookie", cookie_names)

    def test_format_cookies_empty(self):
        """测试格式化空Cookies列表"""
        result = self.fetcher._format_cookies([])
        self.assertEqual(result, [])

    def test_convert_to_netscape_basic(self):
        """测试转换Netscape格式基本功能"""
        test_cookies = [
            {
                "name": "test_cookie",
                "value": "test_value",
                "domain": ".bilibili.com",
                "path": "/",
                "expires": 1782873587,
                "secure": False,
            }
        ]

        result_file = self.fetcher.convert_to_netscape(test_cookies)

        self.assertIsNotNone(result_file)
        self.assertTrue(os.path.exists(result_file))

        with open(result_file, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("# Netscape HTTP Cookie File", content)
        self.assertIn(".bilibili.com", content)
        self.assertIn("test_cookie", content)
        self.assertIn("test_value", content)

    def test_convert_to_netscape_empty(self):
        """测试转换空Cookies列表"""
        result = self.fetcher.convert_to_netscape([])
        self.assertIsNone(result)

    def test_convert_to_netscape_expiry_field(self):
        """测试转换使用expiry字段的Cookies"""
        test_cookies = [
            {
                "name": "session_cookie",
                "value": "session_value",
                "domain": "live.bilibili.com",
                "path": "/",
                "expiry": 1782873587,
                "secure": True,
            }
        ]

        result_file = self.fetcher.convert_to_netscape(test_cookies)

        self.assertIsNotNone(result_file)

    def test_convert_to_netscape_no_expires(self):
        """测试转换没有过期时间的Cookies"""
        test_cookies = [
            {
                "name": "session_only",
                "value": "no_expire",
                "domain": ".bilibili.com",
                "path": "/",
            }
        ]

        result_file = self.fetcher.convert_to_netscape(test_cookies)

        self.assertIsNotNone(result_file)

        with open(result_file, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("0\tsession_only\tno_expire", content)

    def test_save_cookies_to_json(self):
        """测试保存JSON文件"""
        test_cookies = [
            {"name": "test1", "value": "value1", "domain": ".bilibili.com"},
            {"name": "test2", "value": "value2", "domain": "live.bilibili.com"},
        ]

        result_file = self.fetcher.save_cookies_to_json(test_cookies)

        self.assertIsNotNone(result_file)
        self.assertTrue(os.path.exists(result_file))

        with open(result_file, "r", encoding="utf-8") as f:
            saved_cookies = json.load(f)

        self.assertEqual(len(saved_cookies), 2)

    def test_save_cookies_to_json_empty(self):
        """测试保存空Cookies列表"""
        result = self.fetcher.save_cookies_to_json([])
        self.assertIsNone(result)

    def test_show_preview_file_not_exists(self):
        """测试预览不存在的文件"""
        self.fetcher.output_file = Path("non_existent_file.txt")
        try:
            self.fetcher.show_preview()
        except Exception:
            self.fail("show_preview()应该处理文件不存在的情况")

    def test_show_preview_valid_file(self):
        """测试预览有效文件"""
        test_cookies = [
            {"name": "test", "value": "value", "domain": ".bilibili.com", "path": "/"}
        ]
        self.fetcher.convert_to_netscape(test_cookies)

        try:
            self.fetcher.show_preview(lines_count=5)
        except Exception:
            self.fail("show_preview()应该能正常显示有效文件")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("运行B站Cookies获取工具测试")
    print("=" * 60)
    unittest.main(verbosity=2)
