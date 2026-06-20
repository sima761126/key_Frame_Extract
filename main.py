"""
视频关键帧提取与文字识别处理流程 - 主程序

处理流程：
1. 视频关键帧提取（使用FFmpeg）
2. 图片文字识别（使用PaddleOCR）
   - 第一阶段：文本检测
   - 第二阶段：文本识别与相似度比较
3. 大模型信息提取与结构化输出

用法：
  python main.py video.mp4                    # 完整流程
  python main.py video.mp4 --reextract         # 强制重新提取帧
  python main.py --clean-pics                  # 清空pics目录
  python main.py --step1 video.mp4             # 仅提取关键帧
  python main.py --step2                       # 仅运行OCR识别
  python main.py --step3                       # 仅生成结构化结果
"""
import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

import dashscope

import config
from video_processor import VideoProcessor, extract_video_frames
from ocr_processor import TextDetectionPipeline, TextRecognitionPipeline

# 加载 .env 文件
try:
    # pyrefly: ignore [missing-import]
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("没有设置python-dotenv")
    pass  # 如果没有 python-dotenv，使用系统环境变量


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

    # 提取摘要信息
    summary_data = call_llm_for_summary_info(content)

    # 保存结果
    result_path = config.OUTPUT_FILES["summary"]
    with open(result_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(summary_data, ensure_ascii=False, indent=2))

    print(f"结构化结果已保存至: {result_path}")

    return structured_data


def extract_structured_info(content: str) -> dict:
    """
    从OCR识别内容中提取结构化产品信息（使用大模型调用）

    Args:
        content: info.md 文件内容（纯文本格式，每行一个文本）

    Returns:
        结构化数据字典
    """
    # 提取所有文本（纯文本格式，每行一个）
    all_texts = []
    for line in content.split("\n"):
        line = line.strip()
        if line:  # 非空行
            all_texts.append(line)

    # 尝试使用大模型提取
    try:
        result = call_llm_for_structured_info(all_texts)
        if result:
            print("大模型提取成功")
            return result
    except Exception as e:
        print(f"大模型调用失败，使用规则提取: {e}")

    # 回退到规则提取（原有逻辑）
    return extract_structured_info_rules(all_texts)


def call_llm_for_structured_info(texts: list) -> dict:
    """
    调用大模型提取结构化信息

    Args:
        texts: OCR识别的文本列表

    Returns:
        结构化数据字典，失败返回None
    """
    import os
    import requests
    import json

    # 构建prompt
    prompt = build_extraction_prompt(texts)

    # 尝试多种大模型接口
    api_keys = {
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
        "DASHSCOPE_API_KEY": os.environ.get("DASHSCOPE_API_KEY"),
        "BAIDU_API_KEY": os.environ.get("BAIDU_API_KEY"),
    }

    # 优先使用通义千问（阿里云）
    if api_keys["DASHSCOPE_API_KEY"]:
        return call_dashscope(prompt)
    
    # 其次使用百度文心一言
    if api_keys["BAIDU_API_KEY"]:
        return call_baidu_ernie(prompt)
    
    # 最后使用OpenAI
    if api_keys["OPENAI_API_KEY"]:
        return call_openai(prompt)

    print("未配置大模型API密钥，跳过大模型调用")
    return None


def call_llm_for_summary_info(texts: list) -> dict:
    """
    调用大模型提取摘要信息

    Args:
        texts: OCR识别的文本列表

    Returns:
        结构化数据字典，失败返回None
    """
    import os
    import requests
    import json

    # 构建prompt
    prompt = build_summary_prompt(texts)

    # 尝试多种大模型接口
    api_keys = {
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
        "DASHSCOPE_API_KEY": os.environ.get("DASHSCOPE_API_KEY"),
        "BAIDU_API_KEY": os.environ.get("BAIDU_API_KEY"),
    }

    # 优先使用通义千问（阿里云）
    if api_keys["DASHSCOPE_API_KEY"]:
        return call_dashscope_text(prompt)

    # 其次使用百度文心一言
    if api_keys["BAIDU_API_KEY"]:
        return call_baidu_ernie(prompt)

    # 最后使用OpenAI
    if api_keys["OPENAI_API_KEY"]:
        return call_openai(prompt)

    print("未配置大模型API密钥，跳过大模型调用")
    return None


def build_extraction_prompt(texts: list) -> str:
    """
    构建大模型提取的prompt

    Args:
        texts: OCR识别的文本列表

    Returns:
        完整的prompt字符串
    """
    result_data_format = """
{
  "品牌": "",
  "产品名称": "",
  "发布日期": "产品发布会日期，时间格式xxxx-xx-xx",
  "发售日期": "产品发售或者首销日期，时间格式xxxx-xx-xx",
  "颜色": "字符串",
  "处理器": "字符串，包括厂商名称和处理器代号，例如：Snapdragon 8 Gen 3",
  "存储与内存": "字符串，只包含 RAM 和 Storage 的数字值，例如：3+64/4+128",
  "发布价格": "根据存储和内存的配置对应的发布价格。如：8GB+128GB/2499",
  "尺寸": "字符串，只包含 Height、Width、Thickness 的数字值，格式为\"高x宽x厚\"，例如：189x70.9x19",
  "重量": "浮点数",
  "屏幕尺寸": "浮点数，例如：6.55，如果有第二块屏幕，用/分隔",
  "屏幕分辨率": "字符串，例如：\"2670 x 1200\"，如果有第二块屏幕，用/分隔",
  "屏幕刷新率": "字符串，例如：\"120Hz\"，如果有第二块屏幕，用/分隔",
  "屏幕面板类型": "字符串，例如：\"AMOLED, LCD\"，如果有第二块屏幕，用/分隔",
  "屏幕背光模式": "字符串，例如：\"LTPS, LTPO\"，如果有第二块屏幕，用/分隔",
  "后置摄像头颗数": "整数",
  "后置摄像头像素": "字符串，只包含数字值，例如：50MP+8MP+2MP",
  "后置摄像头规格": "字符串，相似规格用括号()包围，包含摄像头名称、光圈、OIS、sensor-shift等，不同摄像头规格换行显示",
  "前置摄像头颗数": "整数",
  "前置摄像头像素": "字符串，只包含数字值，例如：8MP+2MP",
  "前置摄像头规格": "字符串，规则同后置摄像头规格",
  "电池": "整数，例如：5000mAh",
  "充电": "浮点数，多种充电配置间用/分隔，例如：90w有线/80w无线",
  "其他": "包括防尘防水、NFC、卫星、传感器、指纹、冷却系统等"
}
"""

    prompt = f"""
你是一个产品信息提取专家。请从以下OCR识别的文本中提取产品的结构化信息。

【识别到的文本内容】
{chr(10).join(texts)}

【输出格式要求】
请严格按照JSON格式输出，只输出JSON数据，不要输出其他任何内容。如果某个字段无法识别到，请留空字符串或适当的默认值。


【JSON输出模板】
{result_data_format}
如果有多个产品,则表示为list结构
{[result_data_format,]}
"""
    return prompt.strip()


def build_summary_prompt(texts: list) -> str:
    """
    构建大模型提取的prompt

    Args:
        texts: OCR识别的文本列表

    Returns:
        完整的prompt字符串
    """
    result_data_format = """
请根据以下发布会视频/文字记录，生成一份**完整的发布会内容总结报告**：

【发布会名称】：
【发布时间】：
【视频来源/链接】：（如有）

请从以下维度进行总结：

**一、发布会整体概况**
- 发布会主题/Slogan
- 整场时长
- 整体基调（技术硬核/情感共鸣/年轻潮流等）
- 开场亮点描述

**二、产品核心信息汇总**
- 产品名称及定位
- 产品设计理念/故事
- 产品外观描述

**三、核心卖点总结（分点列出，含具体数据）**
1. 卖点名称 + 技术原理简述 + 具体数据/参数
2. 卖点名称 + 技术原理简述 + 具体数据/参数
3. ...
（每个卖点标注：演示方式、观众反应、与上代/竞品对比）

**四、完整规格参数表**
| 项目 | 规格参数 |
|------|----------|
| 屏幕 | |
| 处理器 | |
| 内存/存储 | |
| 电池/续航 | |
| 摄像头 | |
| 尺寸/重量 | |
| 连接性 | |
| 其他 | |

**五、价格与购买信息**
- 各版本/配置及对应价格（表格形式）
- 开售时间（精确到时间点）
- 购买渠道
- 预售福利/优惠活动
- 分期/以旧换新政策（如有）

**六、发布会关键节点时间线**
| 时间点 | 环节内容 | 关键信息/金句 |
|--------|----------|---------------|
| 00:00 | | |
| ... | | |

**七、重要信息提取**
- 3个最令人印象深刻的瞬间
- 2个最具传播性的话题/金句
- 1个可能的争议点或槽点

**八、总结评价**
- 发布会的亮点与不足
- 产品竞争力简要分析
- 目标用户画像
"""

    prompt = f"""
你是一个产品信息提取专家。请从以下OCR识别的文本中提取产品的结构化信息。

【识别到的文本内容】
{chr(10).join(texts)}

【输出格式要求】
请严格按照md格式输出，{result_data_format}，对信息进行总结

"""
    return prompt.strip()



def call_dashscope(prompt: str) -> dict:
    """
    使用 dashscope SDK 调用阿里云通义千问 API。
    支持从环境变量读取 API Key，并返回解析后的 JSON 对象。
    """
    print("使用千问大模型 (SDK方式)")
    # print(prompt)
    # 构建符合 SDK 要求的 messages 格式
    messages = [
        {'role': 'system',
         'content': '''作为手机终端数据处理专家，你的任务是严格按照规范处理数据，确保关键信息不丢失。
                        没有明确规范或具体内容时，不要假设任何信息；必要时保留字段为空。
                        专业术语无需翻译'''
         },
        {'role': 'user',
         'content':  """
                        所有键必须为中文，值之间不要有额外的空格。值的类型保持字符串，不再分割。
                        严格按照以下 JSON 格式输出："""+ prompt
         }
    ]

    try:
        # 使用 dashscope.Generation.call 进行调用
        response = dashscope.Generation.call(
            api_key=os.getenv('DASHSCOPE_API_KEY'),
            model="qwen-plus",  # 可按需更换模型，如 qwen-turbo, qwen-max
            messages=messages,
            result_format='message',  # 使用 message 格式便于解析
            temperature=0.1,
            max_tokens=4096
        )

        # 检查响应状态
        if response.status_code == 200:
            # 从响应中提取文本内容
            # print(response)
            output_text = response.output.choices[0].message.content
            # print(f"原始响应内容: {output_text[:200]}...")  # 打印前200字符用于调试

            # 尝试提取并解析 JSON（处理可能包含在 markdown 代码块中的情况）
            text = output_text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            # 解析 JSON
            parsed_json = json.loads(text.strip())
            print("解析成功。")
            return parsed_json
        else:
            print(f"API调用失败: {response.status_code} - {response.message}")
            return None

    except dashscope.ApiError as e:
        print(f"DashScope API 错误: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}. 原始内容: {output_text[:200]}")
        return None
    except Exception as e:
        print(f"发生未知错误: {e}")
        return None


def call_dashscope_text(prompt: str) -> dict:
    """
    使用 dashscope SDK 调用阿里云通义千问 API。
    支持从环境变量读取 API Key，并返回解析后的 MD 对象。
    """
    print("使用千问大模型 (SDK方式)")
    # print('call_dashscope_text:',prompt)
    # 构建符合 SDK 要求的 messages 格式
    messages = [
        {'role': 'system',
         'content': '''作为手机终端数据处理专家，你的任务是严格按照规范处理数据，确保关键信息不丢失。
                        没有明确规范或具体内容时，不要假设任何信息；必要时保留字段为空。
                        专业术语无需翻译'''
         },
        {'role': 'user',
         'content':  """
                        所有键必须为中文，值之间不要有额外的空格。值的类型保持字符串，不再分割。
                        严格按照 MD 格式输出："""+ prompt
         }
    ]
    # print('call_dashscope_text:', messages)
    try:
        # 使用 dashscope.Generation.call 进行调用
        response = dashscope.Generation.call(
            api_key=os.getenv('DASHSCOPE_API_KEY'),
            model="qwen-plus",  # 可按需更换模型，如 qwen-turbo, qwen-max
            messages=messages,
            result_format='message',  # 使用 message 格式便于解析
            temperature=0.1,
            max_tokens=4096
        )

        # 检查响应状态
        if response.status_code == 200:
            # 从响应中提取文本内容
            # print(response)
            output_text = response.output.choices[0].message.content
            # print(f"原始响应内容: {output_text}...")  # 打印前200字符用于调试

            # 尝试提取并解析 JSON（处理可能包含在 markdown 代码块中的情况）
            text = output_text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```markdown" in text:
                text = text.split("```markdown")[1].split("```")[0]

            # 解析 JSON
            parsed_content = text.strip()
            print("解析成功。")
            return parsed_content
        else:
            print(f"API调用失败: {response.status_code} - {response.message}")
            return None

    # except dashscope.ApiError as e:
    #     print(f"DashScope API 错误: {e}")
    #     return None
    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}. 原始内容: {output_text[:200]}")
        return None
    except Exception as e:
        print(f"发生未知错误: {e}")
        return None

def call_baidu_ernie(prompt: str) -> dict:
    """调用百度文心一言API"""
    import os
    import requests
    import json

    api_key = os.environ.get("BAIDU_API_KEY")
    secret_key = os.environ.get("BAIDU_SECRET_KEY")
    
    # 获取access_token
    token_url = "https://aip.baidubce.com/oauth/2.0/token"
    token_params = {
        "grant_type": "client_credentials",
        "client_id": api_key,
        "client_secret": secret_key
    }
    token_response = requests.post(token_url, params=token_params)
    if token_response.status_code != 200:
        return None
    
    access_token = token_response.json().get("access_token")
    if not access_token:
        return None
    
    url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions"
    headers = {"Content-Type": "application/json"}
    params = {"access_token": access_token}
    
    data = {
        "messages": [
            {"role": "system", "content": "你是一个产品信息提取专家"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }
    
    response = requests.post(url, headers=headers, params=params, data=json.dumps(data))
    if response.status_code == 200:
        result = response.json()
        if "result" in result:
            try:
                return json.loads(result["result"])
            except:
                print(f"JSON解析失败: {result['result']}")
    return None


def call_openai(prompt: str) -> dict:
    """调用OpenAI API"""
    import os
    import openai
    import json

    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    
    client = openai.OpenAI(api_key=api_key, base_url=base_url)
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "你是一个产品信息提取专家，只输出JSON格式的结构化数据"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1
    )
    
    content = response.choices[0].message.content
    try:
        return json.loads(content)
    except:
        print(f"JSON解析失败: {content}")
        return None


def extract_structured_info_rules(texts: list) -> dict:
    """
    使用规则提取结构化信息（回退方案）

    Args:
        texts: OCR识别的文本列表

    Returns:
        结构化数据字典
    """
    # 合并所有文本用于搜索
    full_text = "\n".join(texts)

    # 初始化结果（按照用户指定的格式）
    result = {
        "品牌": "",
        "产品名称": "",
        "发布日期": "",
        "发售日期": "",
        "颜色": "",
        "处理器": "",
        "存储与内存": "",
        "发布价格": "",
        "尺寸": "",
        "重量": "",
        "屏幕尺寸": "",
        "屏幕分辨率": "",
        "屏幕刷新率": "",
        "屏幕面板类型": "",
        "屏幕背光模式": "",
        "后置摄像头颗数": 0,
        "后置摄像头像素": "",
        "后置摄像头规格": "",
        "前置摄像头颗数": 0,
        "前置摄像头像素": "",
        "前置摄像头规格": "",
        "电池": "",
        "充电": "",
        "其他": "",
        "raw_texts": texts
    }

    import re

    # 提取品牌和产品名称
    brands = ["小米", "红米", "Redmi", "MI", "OPPO", "vivo", "华为", "荣耀", "苹果", "iPhone", "三星", "Samsung"]
    product_keywords = ["Max", "Ultra", "Pro", "Plus", "Note", "系列", "手机"]
    
    for text in texts:
        # 识别品牌
        for brand in brands:
            if brand in text:
                if not result["品牌"]:
                    result["品牌"] = brand
        
        # 识别产品名称（包含产品关键词）
        if any(keyword in text for keyword in product_keywords):
            if not result["产品名称"]:
                result["产品名称"] = text.strip()

    # 提取日期信息
    date_patterns = [
        r'(\d{4})[-/年](\d{1,2})[-/月](\d{ 1,2})[日号]?',
        r'(\d{4})年(\d{1,2})月(\d{1,2})日',
        r'(\d{4})[-/](\d{2})[-/](\d{2})'
    ]
    
    for pattern in date_patterns:
        matches = re.findall(pattern, full_text)
        for match in matches:
            date_str = f"{match[0]}-{int(match[1]):02d}-{int(match[2]):02d}"
            if not result["发布日期"]:
                result["发布日期"] = date_str
            elif not result["发售日期"]:
                result["发售日期"] = date_str

    # 提取价格信息
    price_patterns = [
        r'(\d{1,4})[,.]?(\d{3})?元',
        r'(\d+)元起',
        r'售价\s*(\d+)',
        r'价格\s*(\d+)'
    ]
    prices = []
    for pattern in price_patterns:
        matches = re.findall(pattern, full_text)
        for match in matches:
            if isinstance(match, tuple):
                prices.append(''.join(match))
            else:
                prices.append(match)
    if prices:
        result["发布价格"] = '/'.join(sorted(set(prices)))

    # 提取存储与内存
    storage_patterns = [
        r'(\d+)GB\s*[+×x]\s*(\d+)GB',
        r'(\d+)\+(\d+)\s*GB',
        r'(\d+)G\s*/\s*(\d+)G'
    ]
    storages = []
    for pattern in storage_patterns:
        matches = re.findall(pattern, full_text)
        for match in matches:
            storages.append(f"{match[0]}+{match[1]}")
    if storages:
        result["存储与内存"] = '/'.join(sorted(set(storages)))

    # 提取处理器
    cpu_keywords = ["骁龙", "Snapdragon", "天玑", "Dimensity", "麒麟", "A18", "A17"]
    for text in texts:
        for keyword in cpu_keywords:
            if keyword in text:
                if not result["处理器"]:
                    result["处理器"] = text.strip()
                    break

    # 提取电池容量
    battery_pattern = r'(\d+)mAh'
    battery_matches = re.findall(battery_pattern, full_text)
    if battery_matches:
        result["电池"] = f"{battery_matches[0]}mAh"

    # 提取充电功率
    charge_patterns = [
        r'(\d+)[Ww]快充',
        r'(\d+)[Ww]有线',
        r'(\d+)[Ww]无线',
        r'(\d+)[Ww]充电'
    ]
    charges = []
    for pattern in charge_patterns:
        matches = re.findall(pattern, full_text)
        charges.extend(matches)
    if charges:
        result["充电"] = '/'.join(sorted(set(charges))) + "W"

    # 提取屏幕尺寸
    screen_pattern = r'(\d+\.?\d*)英寸'
    screen_matches = re.findall(screen_pattern, full_text)
    if screen_matches:
        result["屏幕尺寸"] = screen_matches[0]

    # 提取摄像头像素
    camera_patterns = [
        r'(\d+)[Mm][Pp]',
        r'(\d+)百万像素'
    ]
    camera_pixels = []
    for pattern in camera_patterns:
        matches = re.findall(pattern, full_text)
        camera_pixels.extend(matches)
    if camera_pixels:
        result["后置摄像头像素"] = '+'.join(camera_pixels[:3])

    # 提取屏幕刷新率
    refresh_pattern = r'(\d+)Hz'
    refresh_matches = re.findall(refresh_pattern, full_text)
    if refresh_matches:
        result["屏幕刷新率"] = refresh_matches[0] + "Hz"

    # 提取其他信息
    other_features = []
    other_keywords = ["NFC", "防水", "防尘", "卫星", "指纹", "散热", "冷却"]
    for text in texts:
        for keyword in other_keywords:
            if keyword in text and keyword not in other_features:
                other_features.append(keyword)
    if other_features:
        result["其他"] = ','.join(other_features)

    # 清理空字段（保留raw_texts）
    result = {k: v for k, v in result.items() if v or k == "raw_texts"}

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
        # 清空pics目录
        import shutil
        pics_dir = config.PICS_DIR
        if pics_dir.exists():
            shutil.rmtree(pics_dir)
            pics_dir.mkdir(exist_ok=True)
            print("已清空pics目录")

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
  python main.py --clean-pics                  # 清空pics目录
  python main.py --step1 video.mp4             # 仅提取关键帧
  python main.py --step2                       # 仅运行OCR识别
  python main.py --step3                       # 仅生成结构化结果
        """
    )

    parser.add_argument("video", nargs="?", help="视频文件路径")
    parser.add_argument("--reextract", action="store_true", help="强制重新提取关键帧")
    parser.add_argument("--clean-pics", action="store_true", help="清空pics目录所有图片")
    parser.add_argument("--step1", action="store_true", help="仅执行步骤1：提取关键帧")
    parser.add_argument("--step2", action="store_true", help="仅执行步骤2：OCR识别")
    parser.add_argument("--step3", action="store_true", help="仅执行步骤3：结构化输出")

    args = parser.parse_args()

    # 处理 --clean-pics 参数
    if args.clean_pics:
        pics_dir = config.PICS_DIR
        if pics_dir.exists():
            import shutil
            count = len(list(pics_dir.glob("*.jpg")))
            shutil.rmtree(pics_dir)
            pics_dir.mkdir(exist_ok=True)
            print(f"已清空pics目录，删除了 {count} 张图片")
        else:
            print("pics目录不存在，无需清空")
        return

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
