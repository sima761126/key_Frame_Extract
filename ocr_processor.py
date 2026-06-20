"""
图片文字识别模块
使用 PaddleOCR 进行文本检测和识别
包含两阶段处理：
1. 文本检测：判断图片是否包含有价值文本
2. 文本识别：识别并提取文本内容
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from difflib import SequenceMatcher
from tqdm import tqdm
import config


class OCRProcessor:
    """PaddleOCR 文字识别处理器"""

    def __init__(self):
        try:
            from paddleocr import PaddleOCR
            self.ocr = PaddleOCR(
                use_angle_cls=config.OCR_CONFIG["use_angle_cls"],
                lang=config.OCR_CONFIG["lang"]
            )
            self.ocr_available = True
        except ImportError:
            print("警告: PaddleOCR 未正确安装，OCR功能将不可用")
            print("请运行: pip install paddlepaddle paddleocr")
            self.ocr_available = False

        self.ocr_config = config.OCR_CONFIG
        self.preprocess_config = config.IMAGE_PREPROCESS
        self.skip_patterns = config.SKIP_TEXT_PATTERNS
        self.similarity_threshold = config.SIMILARITY_CONFIG["similarity_threshold"]

    def preprocess_image(self, image_path: Path) -> np.ndarray:
        """
        图像预处理：调整大小、去噪

        Args:
            image_path: 图片路径

        Returns:
            处理后的图像（BGR格式，供PaddleOCR使用）
        """
        img = cv2.imread(str(image_path))
        if img is None:
            raise ValueError(f"无法读取图片: {image_path}")

        # 调整大小
        target_size = self.ocr_config["image_resize"]
        h, w = img.shape[:2]
        if h > target_size or w > target_size:
            scale = target_size / max(h, w)
            img = cv2.resize(img, None, fx=scale, fy=scale)

        # 去噪（仅对灰度图）
        if self.preprocess_config["enable_denoise"]:
            strength = self.preprocess_config.get("denoising_strength", 3)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            gray = cv2.fastNlMeansDenoising(gray, None, strength, 7, 21)
            img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

        return img

    def _is_valuable_text(self, text: str) -> bool:
        """
        判断文本是否有价值（排除水印、版权等干扰信息）

        Args:
            text: 待检测文本

        Returns:
            是否有价值
        """
        text_lower = text.lower()
        for pattern in self.skip_patterns:
            if pattern.lower() in text_lower:
                return False
        return True

    def detect_text_regions(self, image_path: Path) -> Tuple[bool, List]:
        """
        第一阶段：文本检测
        判断图片是否包含有价值文字

        Args:
            image_path: 图片路径

        Returns:
            (是否有文字, 检测到的区域列表)
        """
        if not self.ocr_available:
            return False, []

        try:
            # 预处理图像
            processed = self.preprocess_image(image_path)

            # 使用PaddleOCR检测
            result = self.ocr.ocr(processed)

            if not result or not result[0]:
                return False, []

            regions = []
            all_text = []

            for line in result[0]:
                if line:
                    bbox = line[0]  # 边界框
                    text = line[1][0]  # 识别的文本
                    confidence = line[1][1]  # 置信度

                    # 过滤低置信度
                    if confidence < self.ocr_config["confidence_threshold"]:
                        continue

                    # 检查文本是否有价值
                    if self._is_valuable_text(text):
                        regions.append({"bbox": bbox, "text": text, "confidence": confidence})
                        all_text.append(text)

            has_valuable = len(regions) > 0
            return has_valuable, regions

        except Exception as e:
            print(f"文本检测失败 {image_path}: {e}")
            return False, []

    def recognize_text(self, image_path: Path) -> List[Dict]:
        """
        第二阶段：文本识别
        识别图片中的所有文字内容

        Args:
            image_path: 图片路径

        Returns:
            识别结果列表 [{"text": ..., "confidence": ...}, ...]
        """
        if not self.ocr_available:
            return []

        try:
            processed = self.preprocess_image(image_path)
            result = self.ocr.ocr(processed, cls=True)

            if not result or not result[0]:
                return []

            recognized = []
            for line in result[0]:
                if line:
                    text = line[1][0]
                    confidence = line[1][1]

                    if confidence >= self.ocr_config["confidence_threshold"]:
                        # 过滤无价值文本（水印、噪声等）
                        if self._is_valuable_text(text):
                            recognized.append({
                                "text": text,
                                "confidence": confidence
                            })

            return recognized

        except Exception as e:
            print(f"文本识别失败 {image_path}: {e}")
            return []

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        计算两段文本的相似度

        Args:
            text1: 文本1
            text2: 文本2

        Returns:
            相似度 (0.0 - 1.0)
        """
        return SequenceMatcher(None, text1, text2).ratio()

    def similarity_check(self,  prev_texts: List[str], curr_texts: List[str]) -> List[str]:
        """
        合并相邻帧的文本
        相似度超过阈值时进行去重优化

        Args:
            prev_texts: 前一张图片的文本列表
            curr_texts: 当前图片的文本列表

        Returns:
            合并后的文本列表（即更新后的result_texts）
        """

        result_texts = []
        is_replace = False

        # 连接所有文本进行比较
        prev_combined = " ".join(prev_texts)
        curr_combined = " ".join(curr_texts)

        similarity = self.calculate_similarity(prev_combined, curr_combined)

        # 相似度超过阈值
        if similarity > self.similarity_threshold:
            # 保留信息量更多的那个
            if len(prev_combined) < len(curr_combined):
                is_replace = True
                result_texts = curr_texts
        else:
            # 相似度不高，直接增加
            result_texts = curr_texts

        return result_texts,is_replace


class TextDetectionPipeline:
    """文本检测流水线"""

    def __init__(self):
        self.processor = OCRProcessor()
        self.pics_dir = config.PICS_DIR
        self.output_files = config.OUTPUT_FILES

    def run_detection(self, frame_list: List[Path] = None) -> List[Path]:
        """
        运行第一阶段：文本检测
        筛选出包含有价值文字的图片

        Args:
            frame_list: 帧图片列表，None时自动扫描pics目录

        Returns:
            包含文字的图片路径列表
        """
        if frame_list is None:
            if not self.pics_dir.exists():
                print("pics目录不存在，请先运行视频帧提取")
                return []
            frame_list = sorted(self.pics_dir.glob("*.jpg"))

        havetext_list = []
        print(f"\n=== 第一阶段：文本检测 ===")
        print(f"待检测图片: {len(frame_list)} 张")

        for frame_path in tqdm(frame_list, desc="文本检测"):
            has_text, regions = self.processor.detect_text_regions(frame_path)
            if has_text:
                havetext_list.append(frame_path)

        # 保存结果
        with open(self.output_files["havetext"], "w", encoding="utf-8") as f:
            for path in havetext_list:
                f.write(f"{path.name}\n")

        print(f"检测完成: {len(havetext_list)}/{len(frame_list)} 张图片包含文字")
        print(f"结果已保存至: {self.output_files['havetext']}")

        return havetext_list


class TextRecognitionPipeline:
    """文本识别流水线"""

    def __init__(self):
        self.processor = OCRProcessor()
        self.output_files = config.OUTPUT_FILES

    def run_recognition(self, havetext_list: List[Path] = None) -> List[Dict]:
        """
        运行第二阶段：文本识别
        识别并比较相邻图片的文本内容

        Args:
            havetext_list: 包含文字的图片列表

        Returns:
            识别结果列表
        """
        # 从havetext.md读取
        if havetext_list is None:
            havetext_path = self.output_files["havetext"]
            if not havetext_path.exists():
                print("havetext.md 不存在，请先运行文本检测")
                return []

            with open(havetext_path, "r", encoding="utf-8") as f:
                filenames = [line.strip() for line in f if line.strip()]

            pics_dir = config.PICS_DIR
            havetext_list = [pics_dir / fname for fname in filenames]

        print(f"\n=== 第二阶段：文本识别 ===")
        print(f"待识别图片: {len(havetext_list)} 张")

        results = []
        prev_texts = []
        merged_texts = []

        for i, img_path in enumerate(tqdm(havetext_list, desc="文本识别")):
            # print('文本识别:', img_path)
            curr_texts_raw = self.processor.recognize_text(img_path)
            curr_texts = [item["text"] for item in curr_texts_raw]
            # 合并文本
            result_texts,is_replace = self.processor.similarity_check(prev_texts, curr_texts)

            # if is_replace:
            #     prev_set = set(prev_texts)
            #     merged_texts = [x for x in merged_texts if x not in prev_set]
            # merged_texts.extend(result_texts)
            # print('文本识别13', merged_texts)
            # 保存结果
            if result_texts == []:
                prev_texts = curr_texts
            else:
                prev_texts = result_texts
                if is_replace:
                    results[-1]["texts"] = ''

            results.append({
                "filename": img_path.name,
                "texts": result_texts,
                "confidence": curr_texts_raw
            })
        # if isinstance(results, dict):
        #     results['texts'] = merged_texts
        # elif isinstance(results, list):
        #     # 如果是列表，根据约定存放到特定位置
        #     results.append(merged_texts)

        # print(type(results),results)
            # 保存到info.md
        self._save_results(results)

        print(f"识别完成: {len(results)} 个有效帧")
        print(f"结果已保存至: {self.output_files['info']}")

        return results

    def _save_results(self, results: List[Dict]) -> None:
        """保存识别结果到info.md（纯文本列表格式）"""
        with open(self.output_files["info"], "w", encoding="utf-8") as f:
            for item in results:
                if isinstance(item, dict):
                    # print('item:', item)
                    for text in item["texts"]:
                        f.write(f"{text}\n")
                # elif isinstance(item, list):
                #     print('item1:', item)
                #     for text in item:
                #         f.write(f"{text}\n")



def run_text_detection(frame_list: List[Path] = None) -> List[Path]:
    """便捷函数：运行文本检测"""
    pipeline = TextDetectionPipeline()
    return pipeline.run_detection(frame_list)


def run_text_recognition(havetext_list: List[Path] = None) -> List[Dict]:
    """便捷函数：运行文本识别"""
    pipeline = TextRecognitionPipeline()
    return pipeline.run_recognition(havetext_list)


if __name__ == "__main__":
    # 测试代码
    print("OCR处理器测试")
    processor = OCRProcessor()
    if processor.ocr_available:
        print("PaddleOCR 已就绪")
    else:
        print("PaddleOCR 不可用")
