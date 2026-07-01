# Name： B站视频下载与切片工具
# Author: simajinghua
# Version: 1.0.0

"""
功能：
1. 查看B站视频可用格式列表
2. 边下载边切片（streaming模式）：
   - 使用yt-dlp下载视频到临时文件
   - 独立线程定期用ffmpeg提取图片和音频
   - 图片：每N秒提取一帧关键帧，格式jpg/png，文件名 frame_起始时间_序号
   - 音频：每N秒切片，格式aac/mp3，文件名 audio_起始时间_序号
3. 先下载后切片（download模式）：
   - 先使用yt-dlp完整下载视频
   - 下载完成后对整个视频进行切片

使用示例：
    # 查看视频格式
    python bilibili_video_downloader.py --list-formats "https://www.bilibili.com/video/BV1xx411c7mZ/"

    # 先下载后切片（默认模式）
    python bilibili_video_downloader.py --video "https://www.bilibili.com/video/BV1xx411c7mZ/"

    # 边下载边切片
    python bilibili_video_downloader.py --video "https://www.bilibili.com/video/BV1xx411c7mZ/" --mode streaming

    # 自定义参数
    python bilibili_video_downloader.py --video "https://www.bilibili.com/video/BV1xx411c7mZ/" \
        --interval 10 --audio-interval 60 --image-format png --audio-format mp3
"""

import argparse
import os
import signal
import subprocess
import threading
import time
import traceback
from pathlib import Path
from typing import Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed


class BilibiliVideoDownloader:
    """B站视频下载器类，负责下载B站视频并进行切片"""

    # B站视频URL模式
    BILIBILI_VIDEO_URL_PATTERNS = (
        "https://www.bilibili.com/video/",
        "http://www.bilibili.com/video/",
        "https://bilibili.com/video/",
        "http://bilibili.com/video/",
        "https://www.bilibili.com/bangumi/play/",
        "http://www.bilibili.com/bangumi/play/",
        "https://bilibili.com/bangumi/play/",
        "http://bilibili.com/bangumi/play/",
    )

    # 默认格式ID
    DEFAULT_FORMAT_ID = None

    def __init__(self, cookies_file: str = "www.bilibili.com_cookies.txt") -> None:
        """初始化B站视频下载器

        Args:
            cookies_file: cookies文件路径，用于登录认证
        """
        self.cookies_file = Path(cookies_file)
        self.download_dir = Path("video_downloads")
        self.download_dir.mkdir(exist_ok=True)
        self._recording_done = False

    def _validate_url(self, url: str) -> bool:
        """验证URL是否为B站视频地址

        Args:
            url: 视频地址

        Returns:
            bool: 如果是B站视频地址返回True，否则返回False
        """
        return any(pattern in url for pattern in self.BILIBILI_VIDEO_URL_PATTERNS)

    def _run_command(self, cmd: list, verbose: bool = True) -> Optional[str]:
        """执行外部命令并返回结果

        Args:
            cmd: 命令列表，如 ['yt-dlp', '--list-formats', url]
            verbose: 是否显示详细输出

        Returns:
            Optional[str]: 命令输出内容，失败返回None
        """
        if verbose:
            print(f"\n执行命令: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
            )

            if result.returncode != 0:
                if verbose:
                    print(f"命令失败 (exit code: {result.returncode})")
                    print(f"stderr: {result.stderr[:500]}")
                return None

            return result.stdout

        except Exception as e:
            if verbose:
                print(f"命令执行异常: {e}")
            return None

    def _kill_process_tree(self, proc: subprocess.Popen) -> None:
        """终止进程及其所有子进程

        在Windows上使用taskkill命令终止进程树，
        在Linux/macOS上使用os.killpg终止进程组。

        Args:
            proc: subprocess.Popen进程对象
        """
        if proc.poll() is None:
            try:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                        capture_output=True,
                        timeout=10,
                    )
                else:
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                        proc.wait(timeout=5)
                    except ProcessLookupError:
                        pass
                    except Exception:
                        proc.kill()
            except Exception as e:
                print(f"[主线程] 终止进程失败: {e}")
                try:
                    proc.kill()
                except Exception:
                    pass

    def list_formats(self, url: str) -> None:
        """查看B站视频可用格式列表

        Args:
            url: B站视频地址
        """
        if not self._validate_url(url):
            print(f"错误: URL '{url}' 不是有效的B站视频地址")
            return

        print(f"\n{'='*60}")
        print(f"查看B站视频格式列表: {url}")
        print(f"{'='*60}")

        cmd = ["yt-dlp", "--list-formats", url]

        if self.cookies_file.exists():
            cmd.insert(1, "--cookies")
            cmd.insert(2, str(self.cookies_file))
            print(f"使用 cookies 文件: {self.cookies_file}")

        output = self._run_command(cmd)

        if output:
            print(output)
        else:
            print("获取格式列表失败")

    def _streaming_slice_loop(
        self,
        video_path: Path,
        frames_dir: Path,
        audio_dir: Path,
        interval: int,
        image_format: str,
        audio_format: str,
        audio_interval: int = 60,
    ) -> None:
        """
        切片线程：定期读取正在写入的视频文件，提取当前时间点的帧和音频

        Args:
            video_path: 视频文件路径
            frames_dir: 图片输出目录
            audio_dir: 音频输出目录
            interval: 视频切片间隔（秒）
            image_format: 图片格式
            audio_format: 音频格式
            audio_interval: 音频切片间隔（秒）
        """
        print("[切片线程] 等待文件开始写入...")

        file_ready = False
        actual_file = None
        while not self._recording_done and not file_ready:
            for f in video_path.parent.glob("*"):
                if f.is_file() and f.suffix in [".mp4", ".flv", ".mkv", ".webm", ".mov"]:
                    file_size = f.stat().st_size
                    if file_size > 500 * 1024:
                        actual_file = f
                        print(f"\n[切片线程] 文件就绪 ({f.name}, {file_size/(1024*1024):.1f}MB)，开始切片")
                        file_ready = True
                        break
            if not file_ready:
                for f in video_path.parent.glob("*.part"):
                    if f.is_file():
                        file_size = f.stat().st_size
                        if file_size > 500 * 1024:
                            actual_file = f
                            print(f"\n[切片线程] 文件就绪 ({f.name}, {file_size/(1024*1024):.1f}MB)，开始切片")
                            file_ready = True
                            break
            time.sleep(0.5)

        if not file_ready:
            print("[切片线程] 文件未就绪，退出")
            return

        slice_start_time = time.time()
        frame_idx = 0
        audio_idx = 0

        while not self._recording_done:
            elapsed = time.time() - slice_start_time

            for f in video_path.parent.glob("*"):
                if f.is_file() and f.suffix in [".mp4", ".flv", ".mkv", ".webm", ".mov"]:
                    if f.stat().st_size > 500 * 1024:
                        actual_file = f
                        break

            expected_frame_idx = int(elapsed / interval)

            while frame_idx <= expected_frame_idx:
                frame_time = frame_idx * interval

                if actual_file and actual_file.exists() and actual_file.stat().st_size > 500 * 1024:
                    try:
                        frame_output = str(frames_dir / f"frame_{frame_time:04d}_{frame_idx + 1:04d}.{image_format}")
                        if not Path(frame_output).exists():
                            cmd_frame = [
                                "ffmpeg",
                                "-ss",
                                str(frame_time),
                                "-i",
                                str(actual_file),
                                "-frames:v",
                                "1",
                                "-q:v",
                                "2",
                                "-y",
                                frame_output,
                            ]
                            subprocess.run(cmd_frame, capture_output=True, timeout=30)
                    except Exception as e:
                        print(f"\n[切片线程] 视频切片错误: {e}")

                frame_idx += 1

                print(f"\r[切片线程] 帧: {frame_idx} | 音频: {audio_idx} | 已录制: {elapsed:.0f}s", end="")

            expected_audio_idx = int(elapsed / audio_interval)

            while audio_idx <= expected_audio_idx:
                audio_time = audio_idx * audio_interval

                if actual_file and actual_file.exists() and actual_file.stat().st_size > 500 * 1024:
                    try:
                        audio_output = str(audio_dir / f"audio_{audio_time:04d}_{audio_idx + 1:04d}.{audio_format}")
                        if not Path(audio_output).exists():
                            cmd_audio = [
                                "ffmpeg",
                                "-ss",
                                str(audio_time),
                                "-i",
                                str(actual_file),
                                "-t",
                                str(audio_interval),
                                "-vn",
                                "-c:a",
                                audio_format,
                                "-b:a",
                                "128k",
                                "-y",
                                audio_output,
                            ]
                            subprocess.run(cmd_audio, capture_output=True, timeout=30)
                    except Exception as e:
                        print(f"\n[切片线程] 音频切片错误: {e}")

                audio_idx += 1

            time.sleep(0.5)

    def _final_slice(
        self,
        video_path: str,
        frames_dir: Path,
        audio_dir: Path,
        interval: int,
        image_format: str,
        audio_format: str,
        audio_interval: int,
        actual_duration: Optional[float] = None,
    ) -> None:
        """
        下载完成后，对整个视频文件进行完整切片
        确保所有时间段都有对应的图片和音频

        Args:
            video_path: 视频文件路径
            frames_dir: 图片输出目录
            audio_dir: 音频输出目录
            interval: 视频切片间隔（秒）
            image_format: 图片格式
            audio_format: 音频格式
            audio_interval: 音频切片间隔（秒）
            actual_duration: 视频的实际时长（秒），用于当ffmpeg无法获取时长时使用
        """
        video_path = Path(video_path)
        actual_file = video_path if video_path.exists() else Path(str(video_path) + ".part")

        if not actual_file.exists():
            print("视频文件不存在，跳过最终切片")
            return

        video_path = actual_file

        try:
            cmd_duration = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)]
            result = subprocess.run(cmd_duration, capture_output=True, text=True, errors="ignore", timeout=30)

            duration = 0.0
            if result.returncode == 0 and result.stdout.strip():
                try:
                    duration = float(result.stdout.strip())
                except ValueError:
                    pass

            if duration == 0 or (actual_duration and actual_duration > duration):
                duration = actual_duration if actual_duration else 60.0

            print(f"视频时长: {duration:.2f}秒")

            frame_count = int(duration / interval) + 1
            audio_count = int(duration / audio_interval) + 1
            print(f"开始切片: 共需提取 {frame_count} 张图片, {audio_count} 段音频")

            temp_frame_pattern = str(frames_dir / f"temp_frame_%04d.{image_format}")
            temp_audio_pattern = str(audio_dir / f"temp_audio_%04d.{audio_format}")

            print("[切片进度] 正在提取图片...")

            def extract_frame(args):
                i, slice_time = args
                frame_output = str(frames_dir / f"frame_{slice_time:04d}_{i + 1:04d}.{image_format}")
                cmd_frame = [
                    "ffmpeg",
                    "-ss", str(slice_time),
                    "-i", str(video_path),
                    "-frames:v", "1",
                    "-q:v", "2",
                    "-y",
                    "-hide_banner",
                    "-loglevel", "error",
                    frame_output,
                ]
                subprocess.run(cmd_frame, capture_output=True, timeout=10)
                return i + 1

            frame_args = [(i, i * interval) for i in range(frame_count)]
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(extract_frame, args) for args in frame_args]
                completed = 0
                for _ in as_completed(futures):
                    completed += 1
                    if completed % 10 == 0 or completed == frame_count:
                        print(f"\r[切片进度] 图片: {completed}/{frame_count}", end="")

            print()

            missing_frames = []
            for i in range(frame_count):
                slice_time = i * interval
                frame_path = frames_dir / f"frame_{slice_time:04d}_{i + 1:04d}.{image_format}"
                if not frame_path.exists() or frame_path.stat().st_size == 0:
                    missing_frames.append((i, slice_time))

            if missing_frames:
                print(f"[切片进度] 补全缺失图片: {len(missing_frames)} 张")
                for i, slice_time in missing_frames:
                    frame_output = str(frames_dir / f"frame_{slice_time:04d}_{i + 1:04d}.{image_format}")
                    cmd_frame = [
                        "ffmpeg",
                        "-ss", str(slice_time),
                        "-i", str(video_path),
                        "-frames:v", "1",
                        "-q:v", "2",
                        "-y",
                        "-hide_banner",
                        "-loglevel", "error",
                        frame_output,
                    ]
                    subprocess.run(cmd_frame, capture_output=True, timeout=10)

            print()

            print("[切片进度] 正在提取音频...")

            def extract_audio(args):
                i, slice_time = args
                audio_output = str(audio_dir / f"audio_{slice_time:04d}_{i + 1:04d}.{audio_format}")
                cmd_audio = [
                    "ffmpeg",
                    "-ss", str(slice_time),
                    "-i", str(video_path),
                    "-t", str(audio_interval),
                    "-vn",
                    "-c:a", audio_format,
                    "-b:a", "128k",
                    "-y",
                    "-hide_banner",
                    "-loglevel", "error",
                    audio_output,
                ]
                subprocess.run(cmd_audio, capture_output=True, timeout=10)
                return i + 1

            audio_args = [(i, i * audio_interval) for i in range(audio_count)]
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(extract_audio, args) for args in audio_args]
                completed = 0
                for _ in as_completed(futures):
                    completed += 1
                    if completed % 5 == 0 or completed == audio_count:
                        print(f"\r[切片进度] 音频: {completed}/{audio_count}", end="")

            print()

            missing_audios = []
            for i in range(audio_count):
                slice_time = i * audio_interval
                audio_path = audio_dir / f"audio_{slice_time:04d}_{i + 1:04d}.{audio_format}"
                if not audio_path.exists() or audio_path.stat().st_size == 0:
                    missing_audios.append((i, slice_time))

            if missing_audios:
                print(f"[切片进度] 补全缺失音频: {len(missing_audios)} 个")
                for i, slice_time in missing_audios:
                    audio_output = str(audio_dir / f"audio_{slice_time:04d}_{i + 1:04d}.{audio_format}")
                    cmd_audio = [
                        "ffmpeg",
                        "-ss", str(slice_time),
                        "-i", str(video_path),
                        "-t", str(audio_interval),
                        "-vn",
                        "-c:a", audio_format,
                        "-b:a", "128k",
                        "-y",
                        "-hide_banner",
                        "-loglevel", "error",
                        audio_output,
                    ]
                    subprocess.run(cmd_audio, capture_output=True, timeout=10)

            print("最终切片完成")

        except Exception as e:
            print(f"最终切片失败: {e}")

    def download_and_slice_streaming(
        self,
        url: str,
        interval: int = 10,
        audio_interval: int = 60,
        image_format: str = "jpg",
        audio_format: str = "aac",
        format_id: Optional[str] = None,
        output_name: Optional[str] = None,
    ) -> Optional[Path]:
        """
        边下载B站视频边切片（streaming模式）

        方案：
        1. 使用yt-dlp下载视频到临时文件（设置分片下载，允许边下载边读取）
        2. 独立线程定期读取临时文件，用ffmpeg提取当前时间点的帧和音频
        3. 每interval秒提取一张图片，每audio_interval秒提取一段音频
        4. 下载完成后进行最终完整切片，补全缺失的帧和音频

        Args:
            url: B站视频地址
            interval: 视频切片间隔（秒），默认10秒
            audio_interval: 音频切片间隔（秒），默认60秒
            image_format: 图片格式 jpg/png
            audio_format: 音频格式 aac/mp3
            format_id: 指定格式ID，默认使用best格式
            output_name: 输出文件名前缀

        Returns:
            Optional[Path]: 输出目录路径，失败返回None
        """
        if not self._validate_url(url):
            print(f"错误: URL '{url}' 不是有效的B站视频地址")
            return None

        print(f"\n{'='*60}")
        print(f"开始B站视频下载（边下载边切片）: {url}")
        print(f"视频切片间隔: {interval}秒")
        print(f"音频切片间隔: {audio_interval}秒")
        print(f"图片格式: {image_format}")
        print(f"音频格式: {audio_format}")
        print(f"{'='*60}")

        video_name = output_name if output_name else f"video_{time.strftime('%Y%m%d_%H%M%S')}"
        output_dir = self.download_dir / video_name
        frames_dir = output_dir / "frames"
        audio_dir = output_dir / "audio"

        frames_dir.mkdir(parents=True, exist_ok=True)
        audio_dir.mkdir(parents=True, exist_ok=True)

        print(f"输出目录: {output_dir}")
        print(f"图片目录: {frames_dir}")
        print(f"音频目录: {audio_dir}")

        temp_video = output_dir / "stream.mp4"
        self._recording_done = False

        print("\n开始下载视频（边下载边切片）...")
        print("按 Ctrl+C 停止")

        download_proc: Optional[subprocess.Popen] = None
        slice_thread: Optional[threading.Thread] = None

        try:
            selected_format = format_id if format_id else self.DEFAULT_FORMAT_ID

            yt_cmd = ["yt-dlp", "-o", str(temp_video), url]
            if self.cookies_file.exists():
                yt_cmd.insert(1, "--cookies")
                yt_cmd.insert(2, str(self.cookies_file))
            if selected_format:
                yt_cmd.extend(["-f", selected_format])
            yt_cmd.extend(["--hls-prefer-ffmpeg"])
            yt_cmd.extend(["--hls-use-mpegts"])
            yt_cmd.extend(["--concurrent-fragments", "1"])

            print(f"指定格式ID: {selected_format if selected_format else '自动选择'}")
            print(f"命令: {' '.join(yt_cmd)}")

            slice_thread = threading.Thread(
                target=self._streaming_slice_loop,
                args=(temp_video, frames_dir, audio_dir, interval, image_format, audio_format, audio_interval),
                daemon=True,
            )
            slice_thread.start()
            print("[切片线程] 已启动")

            print("[下载线程] 开始下载视频...")
            download_proc = subprocess.Popen(yt_cmd)

            start_time = time.time()

            while True:
                elapsed = time.time() - start_time

                if download_proc is None:
                    print("\n[下载线程] 下载进程未启动")
                    break

                proc_status = download_proc.poll()
                if proc_status is not None:
                    print(f"\n[下载线程] 下载进程退出 (code: {proc_status})")
                    break

                actual_file = temp_video if temp_video.exists() else Path(str(temp_video) + ".part")

                if actual_file.exists():
                    file_size = actual_file.stat().st_size
                    frame_count = len(list(frames_dir.glob(f"frame_*.{image_format}")))
                    audio_count = len(list(audio_dir.glob(f"audio_*.{audio_format}")))
                    print(
                        f"\r时间: {int(elapsed)}s | "
                        f"文件: {file_size/(1024*1024):.1f}MB | 图片: {frame_count} | 音频: {audio_count}",
                        end="",
                    )
                else:
                    print(
                        f"\r时间: {int(elapsed)}s | 文件: 不存在",
                        end="",
                    )

                time.sleep(1)

            print("\n[主线程] 下载完成...")
            self._recording_done = True
            print("[主线程] 等待切片线程完成...")
            if slice_thread:
                slice_thread.join(timeout=30)

            actual_video_path = None
            for ext in [".mp4", ".flv", ".mkv", ".webm", ".mov"]:
                candidate = output_dir / f"stream{ext}"
                if candidate.exists():
                    actual_video_path = candidate
                    break
            if not actual_video_path:
                for f in output_dir.glob("stream*"):
                    if f.is_file() and f.suffix in [".mp4", ".flv", ".mkv", ".webm", ".mov"]:
                        actual_video_path = f
                        break

            if not actual_video_path:
                actual_video_path = temp_video

            print(f"[主线程] 使用视频文件: {actual_video_path}")
            print("[主线程] 最终完整切片...")
            actual_duration = elapsed if elapsed > 0 else 60
            self._final_slice(
                str(actual_video_path), frames_dir, audio_dir, interval,
                image_format, audio_format, audio_interval,
                actual_duration=actual_duration
            )

            frame_files = list(frames_dir.glob(f"frame_*.{image_format}"))
            audio_files = list(audio_dir.glob(f"audio_*.{audio_format}"))

            print("\n下载完成!")
            print(f"生成图片: {len(frame_files)} 张")
            print(f"生成音频: {len(audio_files)} 个")

            if frame_files:
                frame_files.sort()
                print("\n图片示例:")
                for f in frame_files[:5]:
                    print(f"  {f.name}")

            if audio_files:
                audio_files.sort()
                print("\n音频示例:")
                for f in audio_files[:5]:
                    print(f"  {f.name}")

            return output_dir

        except KeyboardInterrupt:
            print("\n用户中断下载")
            self._recording_done = True
            if download_proc:
                self._kill_process_tree(download_proc)
            return output_dir

        except Exception as e:
            print(f"\n下载失败: {e}")
            self._recording_done = True
            if download_proc:
                self._kill_process_tree(download_proc)
            traceback.print_exc()
            return None

    def download_and_slice_after(
        self,
        url: str,
        interval: int = 10,
        audio_interval: int = 60,
        image_format: str = "jpg",
        audio_format: str = "aac",
        format_id: Optional[str] = None,
        output_name: Optional[str] = None,
    ) -> Optional[Path]:
        """
        先下载B站视频，下载完成后再切片（download模式）

        方案：
        1. 使用yt-dlp完整下载视频到文件
        2. 下载完成后对整个视频进行切片
        3. 每interval秒提取一张图片，每audio_interval秒提取一段音频

        Args:
            url: B站视频地址
            interval: 视频切片间隔（秒），默认10秒
            audio_interval: 音频切片间隔（秒），默认60秒
            image_format: 图片格式 jpg/png
            audio_format: 音频格式 aac/mp3
            format_id: 指定格式ID，默认使用best格式
            output_name: 输出文件名前缀

        Returns:
            Optional[Path]: 输出目录路径，失败返回None
        """
        if not self._validate_url(url):
            print(f"错误: URL '{url}' 不是有效的B站视频地址")
            return None

        print(f"\n{'='*60}")
        print(f"开始B站视频下载（先下载后切片）: {url}")
        print(f"视频切片间隔: {interval}秒")
        print(f"音频切片间隔: {audio_interval}秒")
        print(f"图片格式: {image_format}")
        print(f"音频格式: {audio_format}")
        print(f"{'='*60}")

        video_name = output_name if output_name else f"video_{time.strftime('%Y%m%d_%H%M%S')}"
        output_dir = self.download_dir / video_name
        frames_dir = output_dir / "frames"
        audio_dir = output_dir / "audio"

        frames_dir.mkdir(parents=True, exist_ok=True)
        audio_dir.mkdir(parents=True, exist_ok=True)

        print(f"输出目录: {output_dir}")
        print(f"图片目录: {frames_dir}")
        print(f"音频目录: {audio_dir}")

        video_path = output_dir / "video.mp4"

        try:
            selected_format = format_id if format_id else self.DEFAULT_FORMAT_ID

            yt_cmd = ["yt-dlp", "-o", str(video_path), url]
            if self.cookies_file.exists():
                yt_cmd.insert(1, "--cookies")
                yt_cmd.insert(2, str(self.cookies_file))
            if selected_format:
                yt_cmd.extend(["-f", selected_format])

            print(f"\n第一步：下载视频")
            print(f"指定格式ID: {selected_format if selected_format else '自动选择'}")
            print(f"命令: {' '.join(yt_cmd)}")
            print("按 Ctrl+C 停止")

            start_time = time.time()

            result = subprocess.run(yt_cmd)

            if result.returncode != 0:
                print(f"下载失败 (exit code: {result.returncode})")
                return None

            download_time = time.time() - start_time
            print(f"\n视频下载完成，耗时: {download_time:.1f}秒")

            actual_video_path = None
            for ext in [".mp4", ".flv", ".mkv", ".webm", ".mov"]:
                candidate = output_dir / f"video{ext}"
                if candidate.exists():
                    actual_video_path = candidate
                    break
            if not actual_video_path:
                for f in output_dir.glob("video*"):
                    if f.is_file() and f.suffix in [".mp4", ".flv", ".mkv", ".webm", ".mov"]:
                        actual_video_path = f
                        break

            if actual_video_path:
                file_size = actual_video_path.stat().st_size
                print(f"视频文件: {actual_video_path}")
                print(f"视频文件大小: {file_size/(1024*1024):.1f}MB")
            else:
                print("视频文件不存在")
                print(f"输出目录内容: {list(output_dir.iterdir())}")
                return None

            print("\n第二步：切片处理")
            self._final_slice(
                str(actual_video_path), frames_dir, audio_dir, interval,
                image_format, audio_format, audio_interval
            )

            frame_files = list(frames_dir.glob(f"frame_*.{image_format}"))
            audio_files = list(audio_dir.glob(f"audio_*.{audio_format}"))

            print("\n处理完成!")
            print(f"下载耗时: {download_time:.1f}秒")
            print(f"生成图片: {len(frame_files)} 张")
            print(f"生成音频: {len(audio_files)} 个")

            if frame_files:
                frame_files.sort()
                print("\n图片示例:")
                for f in frame_files[:5]:
                    print(f"  {f.name}")

            if audio_files:
                audio_files.sort()
                print("\n音频示例:")
                for f in audio_files[:5]:
                    print(f"  {f.name}")

            return output_dir

        except KeyboardInterrupt:
            print("\n用户中断")
            return output_dir

        except Exception as e:
            print(f"\n处理失败: {e}")
            traceback.print_exc()
            return None


def main() -> None:
    """主函数：解析命令行参数并执行相应操作"""
    parser = argparse.ArgumentParser(description="B站视频下载与切片工具")

    parser.add_argument("--list-formats", "-l", type=str, help="查看B站视频可用格式列表")
    parser.add_argument("--video", "-d", type=str, help="开始B站视频下载并切片")
    parser.add_argument("--mode", "-m", type=str, choices=["streaming", "download"],
                        default="download", help="下载模式：download（先下载后切，默认）或 streaming（边下载边切）")
    parser.add_argument("--format", "-f", type=str, help="指定视频格式ID")
    parser.add_argument("--interval", "-i", type=int, default=10, help="视频切片间隔（秒），默认10秒")
    parser.add_argument("--audio-interval", "-a", type=int, default=60, help="音频切片间隔（秒），默认60秒")
    parser.add_argument("--image-format", type=str, default="jpg", choices=["jpg", "png"], help="图片格式")
    parser.add_argument("--audio-format", type=str, default="aac", choices=["aac", "mp3"], help="音频格式")
    parser.add_argument("--output", "-o", type=str, help="输出目录名")
    parser.add_argument("--cookies", type=str, default="www.bilibili.com_cookies.txt", help="cookies文件路径")

    args = parser.parse_args()

    downloader = BilibiliVideoDownloader(cookies_file=args.cookies)

    if args.list_formats:
        downloader.list_formats(args.list_formats)
    elif args.video:
        if args.mode == "download":
            downloader.download_and_slice_after(
                url=args.video,
                interval=args.interval,
                audio_interval=args.audio_interval,
                image_format=args.image_format,
                audio_format=args.audio_format,
                format_id=args.format,
                output_name=args.output,
            )
        else:
            downloader.download_and_slice_streaming(
                url=args.video,
                interval=args.interval,
                audio_interval=args.audio_interval,
                image_format=args.image_format,
                audio_format=args.audio_format,
                format_id=args.format,
                output_name=args.output,
            )
    else:
        print("请指定 --list-formats 或 --video 参数")
        parser.print_help()


if __name__ == "__main__":
    main()
