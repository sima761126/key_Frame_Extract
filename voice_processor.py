import os
import sys
import time
import warnings
from pathlib import Path
from tqdm import tqdm

warnings.filterwarnings('ignore')

# ============ 解决网络和SSL问题 ============
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HF_HUB_DISABLE_SSL_VERIFY'] = '1'
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''

import ssl

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# ============ 导入库 ============
from faster_whisper import WhisperModel
import numpy as np
import librosa
import soundfile as sf
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


class VoiceProcessor:
    def __init__(self, model_name="base", device="cpu", compute_type="int8", model_dir=None):
        """初始化 faster-whisper 语音处理器"""
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type

        # 确定模型路径
        self.model_path = self._get_model_path(model_name, model_dir)

        print(f"{'=' * 60}")
        print(f"🚀 初始化 faster-whisper (使用本地模型)")
        print(f"{'=' * 60}")
        print(f"模型: {model_name}")
        print(f"设备: {device}")
        print(f"计算类型: {compute_type}")
        print(f"模型路径: {self.model_path}")
        print(f"{'=' * 60}\n")

        if not self._check_model_files():
            print("❌ 模型文件不完整!")
            print(f"请确保以下文件存在于: {self.model_path}")
            print("  - config.json")
            print("  - model.bin")
            print("  - tokenizer.json")
            print("  - vocabulary.txt")
            raise FileNotFoundError(f"模型文件不完整: {self.model_path}")

        print("正在加载本地模型...")
        start_time = time.time()

        try:
            self.model = WhisperModel(
                str(self.model_path),
                device=device,
                compute_type=compute_type,
                cpu_threads=4,
                num_workers=1
            )
            elapsed = time.time() - start_time
            print(f"✅ 模型加载成功! 耗时: {elapsed:.2f}秒\n")
        except Exception as e:
            print(f"❌ 模型加载失败: {e}")
            raise

    def _get_model_path(self, model_name, model_dir=None):
        """获取模型路径"""
        if model_dir:
            model_path = Path(model_dir)
            if model_path.exists():
                return model_path

        possible_paths = [
            Path(f"./models/faster-whisper-{model_name}"),
            Path(f"models/faster-whisper-{model_name}"),
            Path(f"D:/Python Project/key_Frame_Extract-master/models/faster-whisper-{model_name}"),
            Path(f"D:\\Python Project\\key_Frame_Extract-master\\models\\faster-whisper-{model_name}"),
            Path(f"~/models/faster-whisper-{model_name}").expanduser(),
        ]

        for path in possible_paths:
            if path.exists() and path.is_dir() and (path / "model.bin").exists():
                print(f"✅ 找到本地模型: {path}")
                return path

        default_path = Path(f"./models/faster-whisper-{model_name}")
        print(f"⚠️ 未找到本地模型，使用默认路径: {default_path}")
        return default_path

    def _check_model_files(self):
        """检查模型文件是否完整"""
        required_files = ["config.json", "model.bin", "tokenizer.json", "vocabulary.txt"]
        missing_files = []
        for file in required_files:
            if not (self.model_path / file).exists():
                missing_files.append(file)

        if missing_files:
            print(f"❌ 缺少模型文件: {', '.join(missing_files)}")
            return False

        model_bin = self.model_path / "model.bin"
        file_size_mb = model_bin.stat().st_size / 1024 / 1024
        if file_size_mb < 100:
            print(f"⚠️ model.bin 文件大小异常: {file_size_mb:.2f} MB")
            return False

        print(f"✅ 模型文件完整 (model.bin: {file_size_mb:.2f} MB)")
        return True

    def load_audio(self, audio_path):
        """加载音频文件"""
        try:
            audio, sr = librosa.load(audio_path, sr=16000, mono=True)
            audio = audio.astype(np.float32)
            return audio, sr
        except Exception as e:
            try:
                audio, sr = sf.read(audio_path)
                if sr != 16000:
                    audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
                audio = audio.astype(np.float32)
                return audio, 16000
            except Exception as e2:
                raise Exception(f"音频加载失败: {e2}")

    def transcribe_single(self, audio_path, language=None, task="transcribe",
                          beam_size=5, vad_filter=True):
        """转录单个音频文件"""
        try:
            if not os.path.exists(audio_path):
                return {"file": audio_path, "success": False, "error": "文件不存在"}

            audio, sr = self.load_audio(audio_path)

            segments, info = self.model.transcribe(
                audio,
                language=language,
                task=task,
                beam_size=beam_size,
                vad_filter=vad_filter,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    threshold=0.5
                )
            )

            full_text = ""
            segment_list = []

            for segment in segments:
                full_text += segment.text + " "
                segment_list.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text
                })

            return {
                "file": audio_path,
                "success": True,
                "text": full_text.strip(),
                "language": info.language,
                "language_probability": info.language_probability,
                "segments": segment_list,
                "segment_count": len(segment_list),
                "duration": None
            }

        except Exception as e:
            return {"file": audio_path, "success": False, "error": str(e)}

    def transcribe(self, audio_path, language=None, task="transcribe",
                   beam_size=5, vad_filter=True):
        """转录音频文件（单个）"""
        try:
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"文件不存在: {audio_path}")

            print(f"\n🎤 转录: {os.path.basename(audio_path)}")

            audio, sr = self.load_audio(audio_path)

            print("开始转录...")
            start_time = time.time()

            segments, info = self.model.transcribe(
                audio,
                language=language,
                task=task,
                beam_size=beam_size,
                vad_filter=vad_filter,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    threshold=0.5
                )
            )

            full_text = ""
            segment_list = []

            for segment in segments:
                full_text += segment.text + " "
                segment_list.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text
                })

            elapsed = time.time() - start_time

            print(f"✅ 转录完成! 耗时: {elapsed:.2f}秒")
            print(f"检测语言: {info.language} (概率: {info.language_probability:.2%})")
            print(f"片段数量: {len(segment_list)}")

            return {
                "text": full_text.strip(),
                "language": info.language,
                "language_probability": info.language_probability,
                "segments": segment_list,
                "segment_count": len(segment_list),
                "duration": elapsed
            }

        except Exception as e:
            print(f"❌ 转录错误: {e}")
            import traceback
            traceback.print_exc()
            return None

    def transcribe_segments(self, segments, language=None, task="transcribe",
                            beam_size=5, vad_filter=True, parallel=False,
                            max_workers=4, show_progress=True):
        """批量转录多个音频切片"""
        total_segments = len(segments)

        print(f"\n{'=' * 60}")
        print(f"📦 开始批量转录 {total_segments} 个音频切片")
        print(f"{'=' * 60}")
        print(f"模式: {'并行' if parallel else '顺序'}")
        if parallel:
            print(f"并行数: {max_workers}")
        print(f"语言: {language if language else '自动检测'}")
        print(f"任务: {task}")
        print(f"{'=' * 60}\n")

        results = []
        start_time = time.time()

        if parallel:
            results = self._transcribe_parallel(
                segments, language, task, beam_size, vad_filter,
                max_workers, show_progress
            )
        else:
            results = self._transcribe_sequential(
                segments, language, task, beam_size, vad_filter,
                show_progress
            )

        success_count = sum(1 for r in results if r.get("success", False))
        failed_count = total_segments - success_count
        elapsed = time.time() - start_time

        total_chars = sum(len(r.get("text", "")) for r in results if r.get("success", False))
        total_segments_count = sum(r.get("segment_count", 0) for r in results if r.get("success", False))

        print(f"\n{'=' * 60}")
        print(f"📊 批量转录完成")
        print(f"{'=' * 60}")
        print(f"总计: {total_segments} 个切片")
        print(f"✅ 成功: {success_count} 个")
        print(f"❌ 失败: {failed_count} 个")
        print(f"📝 总字符数: {total_chars}")
        print(f"🎯 总片段数: {total_segments_count}")
        print(f"⏱️  总耗时: {elapsed:.2f}秒")
        if success_count > 0:
            print(f"⚡ 平均耗时: {elapsed / success_count:.2f}秒/切片")
        print(f"{'=' * 60}\n")

        return {
            "total": total_segments,
            "success": success_count,
            "failed": failed_count,
            "total_chars": total_chars,
            "total_segments": total_segments_count,
            "duration": elapsed,
            "results": results
        }

    def _transcribe_sequential(self, segments, language, task, beam_size,
                               vad_filter, show_progress):
        """顺序处理"""
        results = []
        total = len(segments)

        if show_progress:
            pbar = tqdm(
                total=total,
                desc="🎤 转录进度",
                unit="切片",
                ncols=100,
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
                colour="green",
                position=0,
                leave=True
            )

        for idx, segment_path in enumerate(segments, 1):
            if show_progress:
                filename = os.path.basename(segment_path)[:25]
                pbar.set_description(f"🎤 [{idx}/{total}] {filename}")

            result = self.transcribe_single(
                segment_path, language, task, beam_size, vad_filter
            )

            result["index"] = idx
            results.append(result)

            if show_progress:
                if result.get("success", False):
                    text_len = len(result.get("text", ""))
                    pbar.set_postfix_str(f"✅ {text_len}字符")
                else:
                    pbar.set_postfix_str(f"❌ {result.get('error', '失败')[:20]}")
                pbar.update(1)

        if show_progress:
            pbar.close()

        return results

    def _transcribe_parallel(self, segments, language, task, beam_size,
                             vad_filter, max_workers, show_progress):
        """并行处理"""
        results = []
        results_lock = threading.Lock()
        total = len(segments)

        if show_progress:
            pbar = tqdm(
                total=total,
                desc="⚡ 并行转录",
                unit="切片",
                ncols=100,
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
                colour="blue",
                position=0,
                leave=True
            )

        success_count = 0
        fail_count = 0

        def transcribe_with_progress(segment_path, idx):
            nonlocal success_count, fail_count

            result = self.transcribe_single(
                segment_path, language, task, beam_size, vad_filter
            )
            result["index"] = idx

            if show_progress:
                with results_lock:
                    if result.get("success", False):
                        success_count += 1
                    else:
                        fail_count += 1
                    pbar.set_postfix_str(f"✅ {success_count}成功/❌ {fail_count}失败")
                    pbar.update(1)

            return result

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(transcribe_with_progress, segment_path, idx): segment_path
                for idx, segment_path in enumerate(segments, 1)
            }

            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    segment_path = futures[future]
                    results.append({
                        "file": segment_path,
                        "success": False,
                        "error": str(e),
                        "index": len(results) + 1
                    })

        if show_progress:
            pbar.close()

        results.sort(key=lambda x: x.get("index", 0))
        return results

    def transcribe_segments_sequential(self, segments, language=None, task="transcribe",
                                       beam_size=5, vad_filter=True, show_progress=True):
        """顺序批量转录多个音频切片"""
        return self.transcribe_segments(
            segments, language, task, beam_size, vad_filter,
            parallel=False, show_progress=show_progress
        )

    def transcribe_segments_parallel(self, segments, language=None, task="transcribe",
                                     beam_size=5, vad_filter=True, max_workers=4,
                                     show_progress=True):
        """并行批量转录多个音频切片"""
        return self.transcribe_segments(
            segments, language, task, beam_size, vad_filter,
            parallel=True, max_workers=max_workers, show_progress=show_progress
        )

    def save_to_markdown(self, results, output_path, title=None):
        """
        将转录结果保存为纯文本文件（只包含转录文本）

        Args:
            results: transcribe_segments 返回的结果字典
            output_path: 输出文件路径
            title: 标题（可选，默认不添加）
        """
        # 确保输出目录存在
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 收集所有成功的转录文本
        result_list = results.get('results', [])
        texts = []

        for result in result_list:
            if result.get('success', False):
                text = result.get('text', '').strip()
                if text:
                    texts.append(text)

        # 合并所有文本（用换行分隔）
        if texts:
            content = '\n\n'.join(texts)
        else:
            content = ""

        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✅ 转录文本已保存: {output_path}")
        print(f"📝 总字符数: {len(content)}")
        return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python voice_processor.py <音频文件路径> [模型名称] [语言代码]")
        print("\n示例:")
        print("  python voice_processor.py audio.wav")
        print("  python voice_processor.py audio.wav base")
        print("  python voice_processor.py audio.wav base zh")
        sys.exit(1)

    audio_file = sys.argv[1]
    model_name = sys.argv[2] if len(sys.argv) > 2 else "base"
    language = sys.argv[3] if len(sys.argv) > 3 else None

    if not os.path.isabs(audio_file):
        audio_file = os.path.abspath(audio_file)

    print(f"\n🎤 语音转录工具 (faster-whisper - 本地模型)")
    print(f"{'=' * 60}")
    print(f"音频文件: {audio_file}")
    print(f"模型名称: {model_name}")
    print(f"语言代码: {language if language else '自动检测'}")

    if os.path.exists(audio_file):
        file_size = os.path.getsize(audio_file) / 1024 / 1024
        print(f"文件大小: {file_size:.2f} MB")
    else:
        print(f"❌ 错误: 音频文件不存在!")
        sys.exit(1)

    print(f"{'=' * 60}\n")

    results = transcribe_video_audio(audio_file, model_name, language)