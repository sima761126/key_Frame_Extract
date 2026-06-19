import cv2
import numpy as np
from paddleocr import PaddleOCR
from config import PICS_DIR, OUTPUT_FILES, OCR_CONFIG, SKIP_TEXT_PATTERNS

class OCRProcessor:
    def __init__(self):
        self.ocr = PaddleOCR(use_textline_orientation=True, lang='ch')
        self.pics_dir = PICS_DIR
        self.confidence_threshold = OCR_CONFIG["confidence_threshold"]
    
    def _preprocess_image(self, image_path):
        """图像预处理：灰度化、二值化、去噪"""
        img = cv2.imread(str(image_path))
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        blurred = cv2.GaussianBlur(gray, (OCR_CONFIG["denoising_strength"], OCR_CONFIG["denoising_strength"]), 0)
        
        _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return binary
    
    def _is_meaningful_text(self, text):
        """判断文本是否为有价值的内容（排除水印、默认提示等干扰信息）"""
        text_lower = text.lower().strip()
        
        if not text_lower or len(text_lower) < 2:
            return False
        
        for pattern in SKIP_TEXT_PATTERNS:
            if pattern.lower() in text_lower:
                return False
        
        return True
    
    def detect_text(self, image_path):
        """
        文本检测：判断图片是否包含有价值的文字内容
        
        Args:
            image_path: 图片文件名
        
        Returns:
            bool: 是否包含有价值文本
        """
        full_path = self.pics_dir / image_path
        
        if not full_path.exists():
            return False
        
        try:
            result = self.ocr.ocr(str(full_path))
            
            if result and len(result) > 0:
                for line in result[0]:
                    if len(line) >= 2:
                        text = line[1][0]
                        confidence = line[1][1]
                        
                        if confidence >= self.confidence_threshold and self._is_meaningful_text(text):
                            return True
            
            return False
        except Exception as e:
            print(f"检测图片 {image_path} 时出错: {e}")
            return False
    
    def recognize_text(self, image_path):
        """
        文本识别：识别图片中的文字内容
        
        Args:
            image_path: 图片文件名
        
        Returns:
            list: 识别出的文字列表
        """
        full_path = self.pics_dir / image_path
        
        if not full_path.exists():
            return []
        
        try:
            result = self.ocr.ocr(str(full_path), cls=True)
            recognized_texts = []
            
            if result and len(result) > 0:
                for line in result[0]:
                    if len(line) >= 2:
                        text = line[1][0]
                        confidence = line[1][1]
                        
                        if confidence >= self.confidence_threshold and self._is_meaningful_text(text):
                            recognized_texts.append({
                                "text": text,
                                "confidence": confidence
                            })
            
            return recognized_texts
        except Exception as e:
            print(f"识别图片 {image_path} 时出错: {e}")
            return []
    
    def phase_one_detection(self, image_files):
        """
        第一阶段：文本检测
        检测所有图片，将包含有价值文本的图片文件名保存至havetext.md
        
        Args:
            image_files: 图片文件名列表
        
        Returns:
            int: 检测到有价值文本的图片数量
        """
        have_text_images = []
        
        for image_file in image_files:
            if self.detect_text(image_file):
                have_text_images.append(image_file)
                print(f"检测到有价值文本: {image_file}")
        
        with open(OUTPUT_FILES["havetext"], "w", encoding="utf-8") as f:
            for image in have_text_images:
                f.write(f"{image}\n")
        
        print(f"第一阶段完成，共检测到 {len(have_text_images)} 张包含有价值文本的图片")
        return len(have_text_images)
    
    def phase_two_recognition(self):
        """
        第二阶段：文本识别
        从havetext.md读取图片列表，识别文字内容并保存至info.md
        
        Returns:
            int: 成功识别的图片数量
        """
        if not OUTPUT_FILES["havetext"].exists():
            print("havetext.md 文件不存在，请先执行第一阶段")
            return 0
        
        with open(OUTPUT_FILES["havetext"], "r", encoding="utf-8") as f:
            image_files = [line.strip() for line in f if line.strip()]
        
        results = []
        for image_file in image_files:
            texts = self.recognize_text(image_file)
            if texts:
                results.append({
                    "image": image_file,
                    "texts": texts
                })
                print(f"识别完成: {image_file} text:{texts}")
        
        with open(OUTPUT_FILES["info"], "w", encoding="utf-8") as f:
            for item in results:
                f.write(f"## {item['image']}\n\n")
                for text_info in item["texts"]:
                    f.write(f"- {text_info['text']} (置信度: {text_info['confidence']:.2f})\n")
                f.write("\n")
        
        print(f"第二阶段完成，共识别 {len(results)} 张图片")
        return len(results)