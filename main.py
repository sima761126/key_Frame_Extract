"""
视频关键帧提取与文字识别处理流程 - 主程序

处理流程：
1. 视频关键帧提取（使用FFmpeg）
2. 图片文字识别（使用PaddleOCR）
   - 第一阶段：文本检测
   - 第二阶段：文本识别与相似度比较
3. 大模型信息提取与结构化输出

用法：
    python main.py <视频文件路径>        # 完整流程
    python main.py --step1 <视频文件>    # 仅提取关键帧
    python main.py --step2              # 仅运行OCR识别
    python main.py --reextract          # 强制重新提取帧
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

import config
from video_processor import VideoProcessor, extract_video_frames
from ocr_processor import TextDetectionPipeline, TextRecognitionPipeline


def step1_extract_frames(video_path: Path, force: bool = False) -> list:
    """
    步骤1：提取视频关键帧

    Args:
        video_path: 视频文件路径
        force: 是否强制重新提取

    Returns:
        帧图片路径列表
    """
    print("=" * 60)
    print("步骤1: 视频关键帧提取")
    print("=" * 60)

    processor = VideoProcessor()
    frames = processor.extract_frames(video_path, force_reextract=force)

    return frames


def step2_ocr_processing(frame_list: list = None) -> tuple:
    """
    步骤2：OCR文字识别处理

    Args:
        frame_list: 帧图片列表，None时自动读取pics目录

    Returns:
        (havetext_list, ocr_results)
    """
    print("\n" + "=" * 60)
    print("步骤2: 图片文字识别")
    print("=" * 60)

    # 第一阶段：文本检测
    detection_pipeline = TextDetectionPipeline()
    havetext_list = detection_pipeline.run_detection(frame_list)

    # 第二阶段：文本识别
    recognition_pipeline = TextRecognitionPipeline()
    ocr_results = recognition_pipeline.run_recognition(havetext_list)

    return havetext_list, ocr_results


def step3_extract_structured_info() -> dict:
    """
    步骤3：大模型信息提取与结构化输出

    对 info.md 内容进行分析，提取结构化信息

    Returns:
        结构化数据字典
    """
    print("\n" + "=" * 60)
    print("步骤3: 大模型信息提取")
    print("=" * 60)

    info_path = config.OUTPUT_FILES["info"]
    if not info_path.exists():
        print("info.md 不存在，请先运行OCR识别")
        return {}

    # 读取识别结果
    with open(info_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 提取结构化信息（基于规则的关键信息提取）
    structured_data = extract_structured_info(content)

    # 保存结果
    result_path = config.OUTPUT_FILES["result"]
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(structured_data, f, ensure_ascii=False, indent=2)

    print(f"结构化结果已保存至: {result_path}")

    return structured_data


def extract_structured_info(content: str) -> dict:
    """
    从OCR识别内容中提取结构化信息

    Args:
        content: info.md 文件内容

    Returns:
        结构化数据字典
    """
    # 提取所有文本
    all_texts = []
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("- "):
            text = line[2:].split("(置信度")[0].strip()
            all_texts.append(text)

    # 初始化结果
    result = {
        "product_releases": [],
        "product_specs": [],
        "release_times": [],
        "storage_specs": [],
        "prices": [],
        "sale_start_times": [],
        "raw_texts": all_texts
    }

    # 关键词匹配
    keywords = {
        "product_releases": ["发布会", "发布", "首发", "亮相", "揭晓"],
        "product_specs": ["处理器", "芯片", "电池", "屏幕", "摄像头", "像素", "系统"],
        "release_times": ["发布", "发布于", "发布时间", "发布时间"],
        "storage_specs": ["GB", "TB", "存储", "内存", "容量"],
        "prices": ["售价", "价格", "元", "元起", "元终于"],
        "sale_start_times": ["开售", "上市", "发售", "开卖", "正式销售"]
    }

    for text in all_texts:
        for category, patterns in keywords.items():
            if any(p in text for p in patterns):
                if text not in result[category]:
                    result[category].append(text)

    # 清理空列表
    result = {k: v for k, v in result.items() if v}

    return result


def run_full_pipeline(video_path: Path, force: bool = False) -> dict:
    """
    运行完整处理流程

    Args:
        video_path: 视频文件路径
        force: 是否强制重新提取

    Returns:
        最终结果字典
    """
    print("\n" + "#" * 60)
    print("# 视频关键帧提取与文字识别处理流程")
    print("#" * 60)
    print(f"# 视频文件: {video_path.name}")
    print(f"# 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("#" * 60)

    try:
        # 步骤1：提取关键帧
        frames = step1_extract_frames(video_path, force)

        # 步骤2：OCR处理
        havetext_list, ocr_results = step2_ocr_processing(frames)

        # 步骤3：结构化输出
        structured_data = step3_extract_structured_info()

        print("\n" + "#" * 60)
        print("# 处理完成!")
        print(f"# 关键帧: {len(frames)} 张")
        print(f"# 含文字帧: {len(havetext_list)} 张")
        print(f"# 有效识别帧: {len(ocr_results)} 张")
        print(f"# 结果文件: {config.OUTPUT_FILES['result']}")
        print(f"# 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("#" * 60)

        return structured_data

    except Exception as e:
        print(f"\n错误: {e}")
        raise


def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(
        description="视频关键帧提取与文字识别处理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py video.mp4                    # 完整流程
  python main.py video.mp4 --reextract         # 强制重新提取帧
  python main.py --step1 video.mp4             # 仅提取关键帧
  python main.py --step2                       # 仅运行OCR识别
  python main.py --step3                       # 仅生成结构化结果
        """
    )

    parser.add_argument("video", nargs="?", help="视频文件路径")
    parser.add_argument("--reextract", action="store_true", help="强制重新提取关键帧")
    parser.add_argument("--step1", action="store_true", help="仅执行步骤1：提取关键帧")
    parser.add_argument("--step2", action="store_true", help="仅执行步骤2：OCR识别")
    parser.add_argument("--step3", action="store_true", help="仅执行步骤3：结构化输出")

    args = parser.parse_args()

    # 步骤1单独执行
    if args.step1:
        if not args.video:
            print("错误: --step1 需要指定视频文件")
            sys.exit(1)
        step1_extract_frames(Path(args.video), args.reextract)
        return

    # 步骤2单独执行
    if args.step2:
        step2_ocr_processing()
        return

    # 步骤3单独执行
    if args.step3:
        step3_extract_structured_info()
        return

    # 完整流程
    if not args.video:
        parser.print_help()
        print("\n错误: 请指定视频文件路径")
        sys.exit(1)

    video_path = Path(args.video)
    if not video_path.exists():
        print(f"错误: 视频文件不存在: {video_path}")
        sys.exit(1)

    run_full_pipeline(video_path, args.reextract)


if __name__ == "__main__":
    main()
