# Name： B站Cookies获取工具测试
# Author: simajinghua
# Version: 1.0.0

"""
B站Cookies获取器测试代码

测试内容：
1. B站Cookie域名判断
2. Cookie格式化（直播和视频模式）
3. Netscape格式转换
4. JSON文件保存
5. 文件预览
6. 模式相关方法测试
"""

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "download"))
from get_bilibili_cookies import BilibiliCookiesFetcher


class TestBilibiliCookiesFetcher(unittest.TestCase):
    """测试B站Cookies获取器（直播和视频模式）"""

    def setUp(self):
        """测试前准备"""
        self.stream_fetcher = BilibiliCookiesFetcher(
            output_file="test_stream_cookies.txt", mode="stream"
        )
        self.video_fetcher = BilibiliCookiesFetcher(
            output_file="test_video_cookies.txt", mode="video"
        )

    def test_bilibili_domains(self):
        """测试B站域名列表"""
        self.assertEqual(
            self.stream_fetcher.BILIBILI_DOMAINS,
            (
                ".bilibili.com",
                "live.bilibili.com",
                "www.bilibili.com",
                "video.bilibili.com",
            ),
        )

    def test_bilibili_live_url(self):
        """测试B站直播页面URL"""
        self.assertEqual(
            self.stream_fetcher.BILIBILI_LIVE_URL, "https://live.bilibili.com/"
        )

    def test_bilibili_video_url(self):
        """测试B站视频页面URL"""
        self.assertEqual(
            self.video_fetcher.BILIBILI_VIDEO_URL, "https://www.bilibili.com/"
        )

    def test_is_bilibili_cookie_stream(self):
        """测试判断B站直播Cookie"""
        bilibili_cookie = {"domain": ".bilibili.com", "name": "test", "value": "value"}
        self.assertTrue(self.stream_fetcher._is_bilibili_cookie(bilibili_cookie))

        live_cookie = {"domain": "live.bilibili.com", "name": "test", "value": "value"}
        self.assertTrue(self.stream_fetcher._is_bilibili_cookie(live_cookie))

        other_cookie = {"domain": "www.baidu.com", "name": "test", "value": "value"}
        self.assertFalse(self.stream_fetcher._is_bilibili_cookie(other_cookie))

    def test_is_bilibili_cookie_video(self):
        """测试判断B站视频Cookie"""
        bilibili_cookie = {"domain": ".bilibili.com", "name": "test", "value": "value"}
        self.assertTrue(self.video_fetcher._is_bilibili_cookie(bilibili_cookie))

        video_cookie = {"domain": "video.bilibili.com", "name": "test", "value": "value"}
        self.assertTrue(self.video_fetcher._is_bilibili_cookie(video_cookie))

        other_cookie = {"domain": "www.baidu.com", "name": "test", "value": "value"}
        self.assertFalse(self.video_fetcher._is_bilibili_cookie(other_cookie))

    def test_format_cookies(self):
        """测试格式化Cookies"""
        raw_cookies = [
            {"domain": ".bilibili.com", "name": "cookie1", "value": "value1"},
            {"domain": "www.baidu.com", "name": "cookie2", "value": "value2"},
            {"domain": "live.bilibili.com", "name": "cookie3", "value": "value3"},
            {"domain": "video.bilibili.com", "name": "cookie4", "value": "value4"},
        ]

        formatted = self.stream_fetcher._format_cookies(raw_cookies)
        self.assertEqual(len(formatted), 3)
        self.assertEqual(formatted[0]["name"], "cookie1")
        self.assertEqual(formatted[1]["name"], "cookie3")
        self.assertEqual(formatted[2]["name"], "cookie4")

    def test_get_url_stream(self):
        """测试获取直播模式URL"""
        self.assertEqual(self.stream_fetcher._get_url(), "https://live.bilibili.com/")

    def test_get_url_video(self):
        """测试获取视频模式URL"""
        self.assertEqual(self.video_fetcher._get_url(), "https://www.bilibili.com/")

    def test_get_mode_name_stream(self):
        """测试获取直播模式名称"""
        self.assertEqual(self.stream_fetcher._get_mode_name(), "直播")

    def test_get_mode_name_video(self):
        """测试获取视频模式名称"""
        self.assertEqual(self.video_fetcher._get_mode_name(), "视频")

    def test_convert_to_netscape(self):
        """测试转换为Netscape格式"""
        cookies = [
            {
                "name": "bili_ticket",
                "value": "test_value",
                "domain": ".bilibili.com",
                "path": "/",
                "expires": 1783132786,
                "secure": False,
                "httpOnly": False,
            }
        ]

        result = self.stream_fetcher.convert_to_netscape(cookies)
        self.assertIsNotNone(result)
        self.assertTrue(result.exists())

        with open(result, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn(".bilibili.com", content)
            self.assertIn("bili_ticket", content)
            self.assertIn("test_value", content)

        result.unlink()

    def test_convert_to_netscape_no_expire(self):
        """测试转换没有过期时间的Cookies"""
        cookies = [
            {
                "name": "session_only",
                "value": "session_value",
                "domain": "www.bilibili.com",
                "path": "/",
                "expires": None,
                "secure": False,
                "httpOnly": False,
            }
        ]

        result = self.video_fetcher.convert_to_netscape(cookies)
        self.assertIsNotNone(result)
        self.assertTrue(result.exists())

        with open(result, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("0\tsession_only\tsession_value", content)

        result.unlink()

    def test_save_cookies_to_json(self):
        """测试保存JSON文件"""
        cookies = [
            {"name": "cookie1", "value": "value1", "domain": ".bilibili.com"},
            {"name": "cookie2", "value": "value2", "domain": "www.bilibili.com"},
        ]

        result = self.stream_fetcher.save_cookies_to_json(cookies)
        self.assertIsNotNone(result)
        self.assertTrue(result.exists())

        result.unlink()

    def test_save_cookies_to_json_empty(self):
        """测试保存空Cookies列表"""
        result = self.video_fetcher.save_cookies_to_json([])
        self.assertIsNone(result)

    def test_show_preview(self):
        """测试显示预览"""
        test_file = self.stream_fetcher.output_file
        test_file.write_text(
            "# Netscape HTTP Cookie File\n.bilibili.com\tTRUE\t/\tFALSE\t0\ttest\tvalue",
            encoding="utf-8",
        )

        self.stream_fetcher.show_preview(lines_count=5)

        test_file.unlink()

    def test_show_preview_nonexistent(self):
        """测试显示不存在文件的预览"""
        self.stream_fetcher.output_file = Path("nonexistent_file.txt")
        self.stream_fetcher.show_preview()


if __name__ == "__main__":
    print("=" * 60)
    print("运行B站Cookies获取器测试")
    print("=" * 60)
    unittest.main(verbosity=2)