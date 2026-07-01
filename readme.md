# key_Frame_Extract


[![Version](https://img.shields.io/badge/version-v1.0.0-blue.svg)](https://github.com/hugohe3/ppt-master/releases)
[![PyPI Version](https://img.shields.io/pypi/v/python_pptx_interface.svg)](https://pypi.org/project/python_pptx_interface/)
[![License: MIT](http://img.shields.io/:license-MIT-blue.svg?style=flat-square)](http://badges.MIT-license.org)

## 项目简介

`key_Frame_Extract` 是一个面向视频内容处理的 Python 项目，主要包含以下能力：

1. 从视频中提取关键帧
2. 对关键帧进行 OCR 文字识别
3. 从视频中提取音频并进行语音转写
4. 基于 OCR 与语音内容生成结构化结果与摘要

## 主要流程

项目主流程位于 `main.py`，整体步骤如下：

1. 视频关键帧提取
2. 图片文字识别
3. 语音识别
4. 结构化信息提取与摘要生成

## 运行环境

- Python 3.10 及以上
- 已安装 FFmpeg，并已加入系统 `PATH`

## 安装依赖

在项目目录下执行：

```bash
pip install -r requirements.txt
```

如果默认源下载较慢，可使用镜像源：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 主要依赖

- paddlepaddle
- paddleocr
- ffmpeg-python
- opencv-python
- numpy
- tqdm
- faster-whisper
- python-dotenv
- requests

## 使用方法

### 完整流程

```bash
python main.py video.mp4
```

### 强制重新提取关键帧

```bash
python main.py video.mp4 --reextract
```

### 清空图片目录

```bash
python main.py --clean-pics
```

### 仅执行步骤 1：提取关键帧

```bash
python main.py --step1 video.mp4
```

### 仅执行步骤 2：OCR 识别

```bash
python main.py --step2
```

### 仅执行步骤 3：语音识别

```bash
python main.py --step3 video.mp4
```

### 仅执行步骤 4：结构化输出

```bash
python main.py --step4
```

## 输出文件说明

项目运行后，默认会在项目目录下生成或使用以下文件与目录：

- `pics/`：提取出的关键帧图片
- `audio/`：提取和切分后的音频文件
- `havetext.md`：包含文字的图片列表
- `info.md`：OCR 识别结果
- `voice.md`：语音识别结果
- `result.json`：结构化结果
- `summary.md`：摘要结果

## 注意事项

1. 运行语音识别时，Whisper 模型可能会自动下载到本地。
2. 若未正确安装 PaddleOCR、FFmpeg 或相关依赖，部分功能将无法使用。
3. 如果需要调用大模型能力，请提前配置对应的环境变量，例如 `DASHSCOPE_API_KEY`、`OPENAI_API_KEY` 等。

## 当前规范说明

根据当前项目协作要求：

1. 所有注释应采用中文
2. Python 代码应尽量遵循通用编码规范
3. 所有过程需要确认是否按要求执行
