# Name： B站Cookies获取工具
# Author: simajinghua
# Version: 1.0.0

"""
功能：
1. 使用Playwright自动化浏览器访问B站获取Cookies
2. 将Cookies转换为Netscape HTTP Cookie File格式（yt-dlp/curl使用）
3. 输出到cookies.txt文件

使用示例：
    # 获取B站Cookies
    python get_bilibili_cookies.py

    # 获取Cookies并指定输出文件
    python get_bilibili_cookies.py --output my_cookies.txt

    # 获取Cookies并保存JSON
    python get_bilibili_cookies.py --save-json
"""

import argparse
import json
import traceback
from pathlib import Path
from typing import List, Optional, Dict


class BilibiliCookiesFetcher:
    """B站Cookies获取器类，使用Playwright获取B站Cookies"""

    # B站域名列表
    BILIBILI_DOMAINS = (
        ".bilibili.com",
        "live.bilibili.com",
        "www.bilibili.com",
    )

    # B站直播页面URL
    BILIBILI_LIVE_URL = "https://live.bilibili.com/"

    def __init__(self, output_file: str = "live.bilibili.com_cookies.txt") -> None:
        """初始化B站Cookies获取器

        Args:
            output_file: 输出的Netscape格式Cookies文件路径
        """
        self.output_file = Path(output_file)

    def _is_bilibili_cookie(self, cookie: Dict) -> bool:
        """判断Cookie是否属于B站域名

        Args:
            cookie: Cookie字典

        Returns:
            bool: 如果是B站Cookie返回True，否则返回False
        """
        domain = cookie.get("domain", "")
        return any(domain.endswith(d) for d in self.BILIBILI_DOMAINS)

    def _format_cookies(self, cookies: List[Dict]) -> List[Dict]:
        """格式化Cookies列表，只保留B站相关的Cookies

        Args:
            cookies: Playwright返回的原始Cookies列表

        Returns:
            List[Dict]: 格式化后的B站Cookies列表
        """
        formatted = []
        for cookie in cookies:
            if self._is_bilibili_cookie(cookie):
                formatted.append({
                    "name": cookie["name"],
                    "value": cookie["value"],
                    "domain": cookie["domain"],
                    "path": cookie.get("path", "/"),
                    "expires": cookie.get("expires"),
                    "secure": cookie.get("secure", False),
                    "httpOnly": cookie.get("httpOnly", False),
                })
        return formatted

    def fetch_cookies(self) -> Optional[List[Dict]]:
        """使用Playwright获取B站Cookies

        需要: pip install playwright && playwright install chromium

        Returns:
            Optional[List[Dict]]: 获取到的B站Cookies列表，失败返回None
        """
        try:
            from playwright.sync_api import sync_playwright

            print("正在启动Chromium浏览器...")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)

                try:
                    context = browser.new_context()
                    page = context.new_page()

                    print(f"正在访问B站直播页面: {self.BILIBILI_LIVE_URL}")
                    page.goto(self.BILIBILI_LIVE_URL, wait_until="networkidle")

                    raw_cookies = context.cookies()
                    print(f"原始Cookies数量: {len(raw_cookies)}")

                    bilibili_cookies = self._format_cookies(raw_cookies)
                    print(f"B站Cookies数量: {len(bilibili_cookies)}")

                    if bilibili_cookies:
                        print("\nCookies示例:")
                        for cookie in bilibili_cookies[:5]:
                            value_preview = str(cookie["value"])[:50]
                            print(f"  {cookie['name']}: {value_preview}...")

                    return bilibili_cookies

                finally:
                    browser.close()
                    print("浏览器已关闭")

        except ImportError:
            print("错误: playwright未安装")
            print("安装命令: pip install playwright")
            print("然后运行: playwright install chromium")
            return None
        except Exception as e:
            print(f"错误: {e}")
            traceback.print_exc()
            return None

    def save_cookies_to_json(self, cookies: List[Dict]) -> Optional[Path]:
        """将Cookies保存到JSON文件

        Args:
            cookies: B站Cookies列表

        Returns:
            Optional[Path]: JSON文件路径，失败返回None
        """
        if not cookies:
            print("没有Cookies可保存")
            return None

        json_path = self.output_file.parent / "bilibili_cookies.json"

        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)

            print(f"Cookies已保存到JSON: {json_path}")
            return json_path

        except Exception as e:
            print(f"保存JSON失败: {e}")
            return None

    def convert_to_netscape(self, cookies: List[Dict]) -> Optional[Path]:
        """将Cookies转换为Netscape HTTP Cookie File格式

        Args:
            cookies: B站Cookies列表

        Returns:
            Optional[Path]: Netscape格式文件路径，失败返回None
        """
        if not cookies:
            print("没有Cookies可转换")
            return None

        try:
            lines = []
            lines.append("# Netscape HTTP Cookie File")
            lines.append("# This file is generated automatically. Do not edit.")
            lines.append("")

            for cookie in cookies:
                domain = cookie.get("domain", "")
                flag = "TRUE" if domain.startswith(".") else "FALSE"
                path = cookie.get("path", "/")
                secure = "TRUE" if cookie.get("secure", False) else "FALSE"

                expires = cookie.get("expires", -1)
                if expires == -1 or expires is None:
                    expires = cookie.get("expiry", -1)
                    if expires == -1 or expires is None:
                        expires = 0

                name = cookie.get("name", "")
                value = cookie.get("value", "")

                line = (
                    f"{domain}\t{flag}\t{path}\t{secure}\t"
                    f"{int(expires)}\t{name}\t{value}"
                )
                lines.append(line)

            with open(self.output_file, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            print(f"Cookies已保存到Netscape格式: {self.output_file}")
            print(f"已转换 {len(cookies)} 个Cookies")

            return self.output_file

        except Exception as e:
            print(f"转换Netscape格式失败: {e}")
            traceback.print_exc()
            return None

    def show_preview(self, lines_count: int = 15) -> None:
        """显示Netscape格式文件预览

        Args:
            lines_count: 显示的行数
        """
        if not self.output_file.exists():
            print(f"文件不存在: {self.output_file}")
            return

        try:
            with open(self.output_file, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")

            print("\n文件内容预览:")
            print("-" * 60)
            for line in lines[:lines_count]:
                print(line)

            if len(lines) > lines_count:
                print(f"... (共 {len(lines)} 行)")
            print("-" * 60)

        except Exception as e:
            print(f"读取文件失败: {e}")


def main():
    """主函数，运行B站Cookies获取工具"""
    parser = argparse.ArgumentParser(
        description="B站Cookies获取工具 - 使用Playwright获取B站Cookies"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="live.bilibili.com_cookies.txt",
        help="输出的Cookies文件名（Netscape格式）",
    )
    parser.add_argument(
        "--save-json",
        action="store_true",
        help="同时保存JSON格式的Cookies文件",
    )

    args = parser.parse_args()

    print("\n" + "#" * 60)
    print("# B站Cookies获取工具")
    print("#" * 60)
    print("\n自动获取B站Cookies并转换为Netscape格式（yt-dlp/curl使用）")
    print("请确保你已经在浏览器中登录过B站，否则获取的Cookies可能无效\n")

    fetcher = BilibiliCookiesFetcher(output_file=args.output)

    cookies = fetcher.fetch_cookies()
    if not cookies:
        print("\n未获取到B站Cookies，程序退出")
        return

    result_file = fetcher.convert_to_netscape(cookies)
    if result_file:
        fetcher.show_preview()

    if args.save_json:
        fetcher.save_cookies_to_json(cookies)

    print("\n" + "#" * 60)
    print("# 完成!")
    print("#" * 60)
    print("\ncookies.txt文件可直接用于yt-dlp或curl")
    print("使用示例: yt-dlp --cookies cookies.txt <bilibili_url>")


if __name__ == "__main__":
    main()
