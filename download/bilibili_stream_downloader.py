# Name： B站直播流下载与实时切片工具
# Author: simajinghua
# Version: 1.0.0

"""
功能：
1. 查看B站直播可用格式列表
2. 边下载边切片：
   - 使用yt-dlp或ffmpeg下载直播流到FLV文件
   - 独立线程定期用ffmpeg提取图片和音频
   - 图片：每N秒提取一帧关键帧，格式jpg/png，文件名 frame_起始时间_序号
   - 音频：每N秒切片，格式aac/mp3，文件名 audio_起始时间_序号

使用示例：
    # 查看直播格式
    python bilibili_stream_downloader.py --list-formats "https://live.bilibili.com/123456"

    # 直播录制并切片（默认视频10秒间隔，音频60秒间隔）
    python bilibili_stream_downloader.py --live "https://live.bilibili.com/123456"

    # 自定义参数
    python bilibili_stream_downloader.py --live "https://live.bilibili.com/123456" \
        --interval 10 --audio-interval 60 --duration 3600 --image-format png --audio-format mp3
"""

import argparse
import os
import signal
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Optional, Set


class BilibiliLiveStreamer:
    """B站直播流下载器类，负责下载B站直播流并进行实时切片"""

    # B站直播URL模式
    BILIBILI_LIVE_URL_PATTERNS = (
        "https://live.bilibili.com/",
        "http://live.bilibili.com/",
    )

    # B站fmp4/m3u8格式ID列表（需要特殊处理）
    FMP4_FORMAT_IDS = (
        "ultra_high_res-0",
        "ultra_high_res-1",
        "ultra_high_res-2",
        "ultra_high_res-3",
        "ultra_high_res-6",
        "ultra_high_res-7",
    )

    # B站FLV格式ID列表（可直接下载）
    FLV_FORMAT_IDS = ("ultra_high_res-4", "ultra_high_res-5")

    # 默认格式ID
    DEFAULT_FORMAT_ID = "ultra_high_res-0"

    def __init__(self, cookies_file: str = "cookies.txt") -> None:
        """初始化B站直播下载器

        Args:
            cookies_file: cookies文件路径，用于登录认证
        """
        self.cookies_file = Path(cookies_file)
        self.download_dir = Path("live_downloads")
        self.download_dir.mkdir(exist_ok=True)
        self._recording_done = False

    def _validate_url(self, url: str) -> bool:
        """验证URL是否为B站直播地址

        Args:
            url: 直播地址

        Returns:
            bool: 如果是B站直播地址返回True，否则返回False
        """
        return any(pattern in url for pattern in self.BILIBILI_LIVE_URL_PATTERNS)

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
        这确保yt-dlp及其子进程（如ffmpeg）都被彻底终止。

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
        """查看B站直播可用格式列表

        Args:
            url: B站直播地址
        """
        if not self._validate_url(url):
            print(f"错误: URL '{url}' 不是有效的B站直播地址")
            return

        print(f"\n{'='*60}")
        print(f"查看B站直播格式列表: {url}")
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

    def _is_fmp4_format(self, format_id: Optional[str]) -> bool:
        """判断格式ID是否为fmp4/m3u8格式

        Args:
            format_id: 格式ID

        Returns:
            bool: 如果是fmp4格式返回True，否则返回False
        """
        if not format_id:
            return False
        return any(fid in format_id for fid in self.FMP4_FORMAT_IDS)

    def _get_stream_url(self, url: str, format_id: str) -> Optional[str]:
        """获取B站直播流的实际URL

        Args:
            url: B站直播地址
            format_id: 格式ID

        Returns:
            Optional[str]: 流地址，失败返回None
        """
        cmd = ["yt-dlp", "--get-url", url]
        if self.cookies_file.exists():
            cmd.insert(1, "--cookies")
            cmd.insert(2, str(self.cookies_file))
        cmd.extend(["-f", format_id])

        print(f"获取流地址: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"获取流地址失败: {result.stderr}")
            return None

        return result.stdout.strip()

    def download_live_only(
        self,
        url: str,
        duration: int = 3600,
        format_id: Optional[str] = None,
        output_name: Optional[str] = None,
    ) -> Optional[Path]:
        """
        只下载B站直播流，不进行切片（输出MP4格式）

        Args:
            url: B站直播地址
            duration: 录制时长（秒），默认60分钟
            format_id: 指定格式ID，默认使用ultra_high_res-4
            output_name: 输出文件名前缀

        Returns:
            Optional[Path]: 视频文件路径，失败返回None
        """
        if not self._validate_url(url):
            print(f"错误: URL '{url}' 不是有效的B站直播地址")
            return None

        print(f"\n{'='*60}")
        print(f"开始B站直播下载（仅下载）: {url}")
        print(f"录制时长: {duration}秒 ({duration/60:.1f}分钟)")
        print(f"输出格式: MP4")
        print(f"{'='*60}")

        video_name = output_name if output_name else f"live_{time.strftime('%Y%m%d_%H%M%S')}"
        output_dir = self.download_dir / video_name
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"输出目录: {output_dir}")

        video_path = output_dir / "stream.mp4"

        recording_proc: Optional[subprocess.Popen] = None

        try:
            selected_format = format_id if format_id else self.DEFAULT_FORMAT_ID

            print(f"指定格式ID: {selected_format}")

            yt_cmd = [
                "yt-dlp",
                "-q",
                "-o", str(video_path),
                "-f", selected_format,
                "--hls-prefer-ffmpeg",
                "--hls-use-mpegts",
                "--concurrent-fragments", "1",
                "--merge-output-format", "mp4",
                "--external-downloader", "ffmpeg",
                "--external-downloader-args", f"ffmpeg_i:-t {duration}",
                url,
            ]
            if self.cookies_file.exists():
                yt_cmd.insert(1, "--cookies")
                yt_cmd.insert(2, str(self.cookies_file))

            print(f"下载命令: {' '.join(yt_cmd)}")
            recording_proc = subprocess.Popen(yt_cmd)

            print("按 Ctrl+C 停止录制")

            start_time = time.time()
            progress_bar_length = 40

            while recording_proc.poll() is None:
                elapsed = time.time() - start_time
                progress = min(elapsed / duration, 1.0)
                bar_filled = int(progress * progress_bar_length)
                bar_empty = progress_bar_length - bar_filled

                elapsed_min = int(elapsed // 60)
                elapsed_sec = int(elapsed % 60)
                duration_min = int(duration // 60)
                duration_sec = int(duration % 60)

                file_size = 0
                if video_path.exists():
                    file_size = video_path.stat().st_size / (1024 * 1024)

                progress_bar = f"[{'='*bar_filled}{' '*bar_empty}]"
                progress_percent = f"{progress*100:.1f}%"
                time_info = f"{elapsed_min:02d}:{elapsed_sec:02d}/{duration_min:02d}:{duration_sec:02d}"
                size_info = f"{file_size:.1f}MB"

                progress_line = f"\r进度: {progress_bar} {progress_percent} | 时间: {time_info} | 文件: {size_info}"
                sys.stdout.write(progress_line)
                sys.stdout.flush()

                time.sleep(1)

            download_time = time.time() - start_time

            if video_path.exists():
                file_size = video_path.stat().st_size / (1024 * 1024)
                print(f"\n直播下载完成，耗时: {download_time:.1f}秒")
                print(f"视频文件: {video_path}")
                print(f"视频文件大小: {file_size:.1f}MB")
                return video_path
            else:
                part_file = video_path.with_suffix(".mp4.part")
                if part_file.exists():
                    print(f"\n视频文件未完成写入，但存在临时文件: {part_file}")
                    print(f"可尝试手动将 .part 文件重命名为 .mp4")
                else:
                    print("\n视频文件不存在")
                    print(f"输出目录内容: {list(output_dir.iterdir())}")
                return None

        except KeyboardInterrupt:
            print("\n用户中断")
            if recording_proc:
                recording_proc.terminate()
                recording_proc.wait(timeout=10)
            return video_path if video_path.exists() else None

        except Exception as e:
            print(f"\n下载失败: {e}")
            traceback.print_exc()
            if recording_proc:
                recording_proc.terminate()
                recording_proc.wait(timeout=10)
            return None

    def download_and_slice_live(
        self,
        url: str,
        interval: int = 10,
        duration: int = 3600,
        image_format: str = "jpg",
        audio_format: str = "aac",
        format_id: Optional[str] = None,
        output_name: Optional[str] = None,
        audio_interval: int = 60,
    ) -> Optional[Path]:
        """
        边下载B站直播流边切片

        方案：
        1. 根据格式类型选择下载方式：
           - FLV格式：直接使用yt-dlp下载到FLV临时文件
           - fmp4/m3u8格式：先用yt-dlp获取流地址，再用ffmpeg下载并转码为FLV
        2. 独立线程定期读取FLV文件，用ffmpeg提取当前时间点的帧和音频
        3. 每interval秒提取一张图片，每audio_interval秒提取一段音频

        Args:
            url: B站直播地址
            interval: 视频切片间隔（秒），默认10秒
            audio_interval: 音频切片间隔（秒），默认60秒
            duration: 录制时长（秒），默认60分钟
            image_format: 图片格式 jpg/png
            audio_format: 音频格式 aac/mp3
            format_id: 指定格式ID，默认使用ultra_high_res-4
            output_name: 输出文件名前缀

        Returns:
            Optional[Path]: 输出目录路径，失败返回None
        """
        if not self._validate_url(url):
            print(f"错误: URL '{url}' 不是有效的B站直播地址")
            return None

        print(f"\n{'='*60}")
        print(f"开始B站直播录制: {url}")
        print(f"视频切片间隔: {interval}秒")
        print(f"音频切片间隔: {audio_interval}秒")
        print(f"录制时长: {duration}秒 ({duration/60:.1f}分钟)")
        print(f"图片格式: {image_format}")
        print(f"音频格式: {audio_format}")
        print(f"{'='*60}")

        video_name = output_name if output_name else f"live_{time.strftime('%Y%m%d_%H%M%S')}"
        output_dir = self.download_dir / video_name
        frames_dir = output_dir / "frames"
        audio_dir = output_dir / "audio"

        frames_dir.mkdir(parents=True, exist_ok=True)
        audio_dir.mkdir(parents=True, exist_ok=True)

        print(f"输出目录: {output_dir}")
        print(f"图片目录: {frames_dir}")
        print(f"音频目录: {audio_dir}")

        temp_video = output_dir / "stream.flv"
        self._recording_done = False

        print("\n开始录制直播流（边下载边切片）...")
        print("按 Ctrl+C 停止录制")

        recording_proc: Optional[subprocess.Popen] = None
        slice_thread: Optional[threading.Thread] = None

        try:
            selected_format = format_id if format_id else self.DEFAULT_FORMAT_ID
            is_fmp4 = self._is_fmp4_format(selected_format)

            if is_fmp4:
                print(f"指定格式ID: {selected_format} (fmp4/m3u8格式，将获取流地址后用ffmpeg下载)")

                stream_url = self._get_stream_url(url, selected_format)
                if not stream_url:
                    raise Exception("无法获取直播流地址")

                print(f"流地址: {stream_url[:50]}...")

                ffmpeg_cmd = [
                    "ffmpeg",
                    "-i",
                    stream_url,
                    "-c:v",
                    "copy",
                    "-c:a",
                    "copy",
                    "-f",
                    "flv",
                    str(temp_video),
                ]

                print(f"ffmpeg命令: {' '.join(ffmpeg_cmd)}")
                recording_proc = subprocess.Popen(ffmpeg_cmd)

            else:
                yt_cmd = ["yt-dlp", "-o", str(temp_video), url]
                if self.cookies_file.exists():
                    yt_cmd.insert(1, "--cookies")
                    yt_cmd.insert(2, str(self.cookies_file))
                yt_cmd.extend(["-f", selected_format])

                print(f"指定格式ID: {selected_format}")

            slice_thread = threading.Thread(
                target=self._streaming_slice_loop,
                args=(temp_video, frames_dir, audio_dir, interval, image_format, audio_format, audio_interval),
                daemon=True,
            )
            slice_thread.start()
            print("[切片线程] 已启动")

            print("[录制线程] 开始录制直播流...")
            if not is_fmp4:
                print(f"命令: {' '.join(yt_cmd)}")
                recording_proc = subprocess.Popen(yt_cmd)

            start_time = time.time()

            while True:
                elapsed = time.time() - start_time

                if recording_proc is None:
                    print("\n[录制线程] 录制进程未启动")
                    break

                proc_status = recording_proc.poll()
                if proc_status is not None:
                    print(f"\n[录制线程] 录制进程退出 (code: {proc_status})")
                    break

                if elapsed >= duration:
                    print("\n[录制线程] 达到指定时长")
                    break

                actual_file = temp_video if temp_video.exists() else Path(str(temp_video) + ".part")

                if actual_file.exists():
                    file_size = actual_file.stat().st_size
                    progress = min(100, int(elapsed / duration * 100))
                    frame_count = len(list(frames_dir.glob(f"frame_*.{image_format}")))
                    audio_count = len(list(audio_dir.glob(f"audio_*.{audio_format}")))
                    print(
                        f"\r进度: {progress}% | 时间: {int(elapsed)}s | "
                        f"文件: {file_size/(1024*1024):.1f}MB | 图片: {frame_count} | 音频: {audio_count}",
                        end="",
                    )
                else:
                    print(
                        f"\r进度: {min(100, int(elapsed / duration * 100))}% | 时间: {int(elapsed)}s | 文件: 不存在",
                        end="",
                    )

                time.sleep(1)

            print("\n[主线程] 停止录制...")
            if recording_proc:
                self._kill_process_tree(recording_proc)

            self._recording_done = True
            print("[主线程] 等待切片线程完成...")
            if slice_thread:
                slice_thread.join(timeout=30)

            print("[主线程] 最终完整切片...")
            actual_duration = elapsed if elapsed > 0 else duration
            self._final_slice(
                str(temp_video), frames_dir, audio_dir, interval,
                image_format, audio_format, audio_interval,
                actual_duration=actual_duration
            )

            frame_files = list(frames_dir.glob(f"frame_*.{image_format}"))
            audio_files = list(audio_dir.glob(f"audio_*.{audio_format}"))

            print("\n录制完成!")
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
            print("\n用户中断录制")
            self._recording_done = True
            if recording_proc:
                self._kill_process_tree(recording_proc)
            return output_dir

        except Exception as e:
            print(f"\n录制失败: {e}")
            self._recording_done = True
            if recording_proc:
                self._kill_process_tree(recording_proc)
            traceback.print_exc()
            return None

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
        切片线程：定期读取正在写入的FLV文件，提取当前时间点的帧和音频

        Args:
            video_path: FLV文件路径
            frames_dir: 图片输出目录
            audio_dir: 音频输出目录
            interval: 视频切片间隔（秒）
            image_format: 图片格式
            audio_format: 音频格式
            audio_interval: 音频切片间隔（秒）
        """
        print("[切片线程] 等待文件开始写入...")

        file_ready = False
        while not self._recording_done and not file_ready:
            actual_file = video_path if video_path.exists() else Path(str(video_path) + ".part")

            if actual_file.exists():
                file_size = actual_file.stat().st_size
                if file_size > 500 * 1024:
                    print(f"\n[切片线程] 文件就绪 ({file_size/(1024*1024):.1f}MB)，开始切片")
                    file_ready = True
            time.sleep(0.5)

        if not file_ready:
            print("[切片线程] 文件未就绪，退出")
            return

        slice_start_time = time.time()
        frame_idx = 0
        audio_idx = 0

        while not self._recording_done:
            elapsed = time.time() - slice_start_time

            expected_frame_idx = int(elapsed / interval)

            while frame_idx <= expected_frame_idx:
                frame_time = frame_idx * interval
                actual_file = video_path if video_path.exists() else Path(str(video_path) + ".part")

                if actual_file.exists() and actual_file.stat().st_size > 500 * 1024:
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
                actual_file = video_path if video_path.exists() else Path(str(video_path) + ".part")

                if actual_file.exists() and actual_file.stat().st_size > 500 * 1024:
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
        录制完成后，对整个视频文件进行完整切片
        确保所有时间段都有对应的图片和音频

        此方法会：
        1. 获取视频总时长（优先使用传入的录制时长）
        2. 检查已存在的切片文件
        3. 补全缺失的视频帧和音频片段

        Args:
            video_path: 视频文件路径
            frames_dir: 图片输出目录
            audio_dir: 音频输出目录
            interval: 视频切片间隔（秒）
            image_format: 图片格式
            audio_format: 音频格式
            audio_interval: 音频切片间隔（秒）
            actual_duration: 录制的实际时长（秒），用于当ffmpeg无法获取时长时使用
        """
        video_path = Path(video_path)
        actual_file = video_path if video_path.exists() else Path(str(video_path) + ".part")

        if not actual_file.exists():
            print("视频文件不存在，跳过最终切片")
            return

        video_path = actual_file

        try:
            cmd_duration = ["ffmpeg", "-i", str(video_path), "-f", "null", "-", "-hide_banner"]
            result = subprocess.run(cmd_duration, capture_output=True, text=True, errors="ignore")

            duration = 0.0
            for line in result.stderr.split("\n"):
                if "Duration:" in line:
                    parts = line.split(",")[0].split("Duration:")[1].strip().split(":")
                    duration = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                    break

            if duration == 0 or (actual_duration and actual_duration > duration):
                duration = actual_duration if actual_duration else 60.0

            print(f"视频时长: {duration:.2f}秒")

            existing_frames: Set[int] = set()
            for f in frames_dir.glob(f"frame_*.{image_format}"):
                start_time = int(f.name.split("_")[1])
                existing_frames.add(start_time)

            existing_audios: Set[int] = set()
            for f in audio_dir.glob(f"audio_*.{audio_format}"):
                start_time = int(f.name.split("_")[1])
                existing_audios.add(start_time)

            print(f"已存在图片: {len(existing_frames)} 个")
            print(f"已存在音频: {len(existing_audios)} 个")

            frame_count = int(duration / interval) + 1
            for i in range(frame_count):
                slice_time = i * interval
                if slice_time not in existing_frames:
                    frame_output = str(frames_dir / f"frame_{slice_time:04d}_{i + 1:04d}.{image_format}")
                    cmd_frame = [
                        "ffmpeg",
                        "-ss",
                        str(slice_time),
                        "-i",
                        str(video_path),
                        "-frames:v",
                        "1",
                        "-q:v",
                        "2",
                        "-y",
                        frame_output,
                    ]
                    subprocess.run(cmd_frame, capture_output=True, timeout=30)

            audio_count = int(duration / audio_interval) + 1
            for i in range(audio_count):
                slice_time = i * audio_interval
                if slice_time not in existing_audios:
                    audio_output = str(audio_dir / f"audio_{slice_time:04d}_{i + 1:04d}.{audio_format}")
                    cmd_audio = [
                        "ffmpeg",
                        "-ss",
                        str(slice_time),
                        "-i",
                        str(video_path),
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

            print("最终切片完成")

        except Exception as e:
            print(f"最终切片失败: {e}")


def main() -> None:
    """主函数：解析命令行参数并执行相应操作"""
    parser = argparse.ArgumentParser(description="B站直播流下载与实时切片工具")

    parser.add_argument("--list-formats", "-l", type=str, help="查看B站直播可用格式列表")
    parser.add_argument("--live", "-d", type=str, help="开始B站直播录制并切片")
    parser.add_argument("--format", "-f", type=str, help="指定直播格式ID")
    parser.add_argument("--interval", "-i", type=int, default=10, help="视频切片间隔（秒），默认10秒")
    parser.add_argument("--audio-interval", "-a", type=int, default=60, help="音频切片间隔（秒），默认60秒")
    parser.add_argument("--duration", "-t", type=int, default=3600, help="录制时长（秒），默认3600秒(60分钟)")
    parser.add_argument("--image-format", type=str, default="jpg", choices=["jpg", "png"], help="图片格式")
    parser.add_argument("--audio-format", type=str, default="aac", choices=["aac", "mp3"], help="音频格式")
    parser.add_argument("--output", "-o", type=str, help="输出目录名")
    parser.add_argument("--cookies", type=str, default="cookies.txt", help="cookies文件路径")

    args = parser.parse_args()

    downloader = BilibiliLiveStreamer(cookies_file=args.cookies)

    if args.list_formats:
        downloader.list_formats(args.list_formats)
    elif args.live:
        if args.download_only:
            downloader.download_live_only(
                url=args.live,
                duration=args.duration,
                format_id=args.format,
                output_name=args.output,
            )
        else:
            downloader.download_and_slice_live(
                url=args.live,
                interval=args.interval,
                audio_interval=args.audio_interval,
                duration=args.duration,
                image_format=args.image_format,
                audio_format=args.audio_format,
                format_id=args.format,
                output_name=args.output,
            )
    else:
        print("请指定 --list-formats 或 --live 参数")
        parser.print_help()


if __name__ == "__main__":
    main()
