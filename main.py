import json
import argparse
import os
from video_processor import VideoProcessor
from ocr_processor import OCRProcessor
from config import OUTPUT_FILES

def extract_info_with_llm(text_content):
    """
    使用大模型从识别文本中提取结构化信息
    
    Args:
        text_content: 识别出的文本内容
    
    Returns:
        dict: 结构化的提取结果
    """
    extracted_info = {
        "product_releases": [],
        "product_specs": [],
        "release_times": [],
        "storage_specs": [],
        "prices": [],
        "sale_start_times": []
    }
    
    lines = text_content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if any(keyword in line for keyword in ["发布", "新品", "发布日期", "新品上市"]):
            extracted_info["product_releases"].append(line)
        
        if any(keyword in line for keyword in ["规格", "参数", "尺寸", "配置"]):
            extracted_info["product_specs"].append(line)
        
        if any(keyword in line for keyword in ["发布时间", "日期", "年月日"]):
            extracted_info["release_times"].append(line)
        
        if any(keyword in line for keyword in ["存储", "内存", "容量", "GB", "TB"]):
            extracted_info["storage_specs"].append(line)
        
        if any(keyword in line for keyword in ["价格", "售价", "¥", "元"]):
            extracted_info["prices"].append(line)
        
        if any(keyword in line for keyword in ["上市时间", "开售", "发售", "预售"]):
            extracted_info["sale_start_times"].append(line)
    
    return extracted_info

def process_video(video_path):
    """
    完整处理流程：关键帧提取 -> OCR识别 -> 信息提取
    
    Args:
        video_path: 输入视频文件路径
    """
    print("=" * 50)
    print("视频关键帧提取与文字识别处理流程")
    print("=" * 50)
    
    video_processor = VideoProcessor()
    ocr_processor = OCRProcessor()
    
    # print("\n[阶段1/3] 提取视频关键帧")
    # print("-" * 30)
    # frame_count = video_processor.extract_keyframes(video_path)
    # print(f"成功提取 {frame_count} 个关键帧")
    #
    # if frame_count == 0:
    #     print("未提取到关键帧，程序退出")
    #     return
    #
    # image_files = video_processor.get_extracted_frames()
    # print(f"关键帧文件列表: {image_files}")
    #
    #
    # print("\n[阶段2/3] OCR文字识别")
    # print("-" * 30)
    #
    # print("\n第一阶段：文本检测")
    # detected_count = ocr_processor.phase_one_detection(image_files)
    #
    # if detected_count == 0:
    #     print("未检测到有价值的文本，程序退出")
    #     return
    
    print("\n第二阶段：文本识别")
    recognized_count = ocr_processor.phase_two_recognition()
    
    if recognized_count == 0:
        print("未识别到文本内容，程序退出")
        return
    
    print("\n[阶段3/3] 大模型信息提取")
    print("-" * 30)
    
    if not OUTPUT_FILES["info"].exists():
        print("info.md 文件不存在")
        return
    
    with open(OUTPUT_FILES["info"], "r", encoding="utf-8") as f:
        text_content = f.read()
    
    extracted_info = extract_info_with_llm(text_content)
    
    with open(OUTPUT_FILES["result"], "w", encoding="utf-8") as f:
        json.dump(extracted_info, f, ensure_ascii=False, indent=2)
    
    print(f"信息提取完成，结果已保存至 {OUTPUT_FILES['result']}")
    
    print("\n" + "=" * 50)
    print("处理流程完成！")
    print("=" * 50)
    
    print("\n提取结果摘要：")
    print(f"- 产品发布信息: {len(extracted_info['product_releases'])} 条")
    print(f"- 产品规格信息: {len(extracted_info['product_specs'])} 条")
    print(f"- 发布时间: {len(extracted_info['release_times'])} 条")
    print(f"- 存储规格: {len(extracted_info['storage_specs'])} 条")
    print(f"- 价格信息: {len(extracted_info['prices'])} 条")
    print(f"- 上市时间: {len(extracted_info['sale_start_times'])} 条")

def main():
    parser = argparse.ArgumentParser(description='视频关键帧提取与文字识别处理流程')
    parser.add_argument('video_path', help='输入视频文件路径')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.video_path):
        print(f"错误：视频文件不存在 - {args.video_path}")
        return
    
    process_video(args.video_path)

if __name__ == "__main__":
    main()