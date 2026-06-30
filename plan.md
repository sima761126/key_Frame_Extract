# 视频关键帧提取与文字识别处理流程

## 1. 提取视频内容的关键帧

### 1.1 使用 FFmpeg 提取关键帧

使用以下命令将视频内容转换为 JPG 图片序列：

```bash
ffmpeg -i input视频文件 -vf "select='eq(pict_type\,I)'" -vsync vfr output图片文件
```

### 1.2 参数说明

| 参数 | 说明 |
|------|------|
| **input视频文件** | 待处理的视频文件，支持格式：MP4、AVI、FLV、MKV、TS 等 |
| **output图片文件** | 输出的图片序列，每张图片代表一帧内容。命名格式：`xxxx_%04d.后缀`<br>• `xxxx`：自定义图片系列名称<br>• `%04d`：图片序列号（从1开始编号）<br>• `后缀`：图片格式，如 jpg、png 等 |

### 1.3 文件存储

- 图片序列保存在设定目录下的 `pics` 文件夹中
- 如 `pics` 文件夹不存在，则自动创建

---

## 2. 图片文字识别与分析

### 2.1 技术方案

使用 **PaddleOCR** 库进行两步操作：

| 步骤 | 功能 | 说明 |
|------|------|------|
| **文本检测** | 判断是否存在文字，定位文字区域 | 返回边界框坐标 |
| **文本识别** | 识别文字区域的具体字符内容 | 裁剪区域并识别 |

### 2.2 预处理优化

- **图像增强**：背景复杂或光线暗时，使用 OpenCV 进行灰度化、二值化（`cv2.threshold`）或去噪处理，可显著提升识别率
- **置信度过滤**：设置置信度阈值（如 `confidence > 0.8`），过滤误识别的噪点

### 2.3 处理流程

#### 第一阶段：文本检测

1. 按次序读取 `pics` 目录下的图片文件
2. 对每张图片进行文本检测，判断是否包含**有价值的内容信息**（排除水印、默认提示等干扰信息）
3. 如包含有价值文本：
   - 将图片文件名保存至 `havetext.md`
4. 如不包含有价值文本：
   - 跳过该图片，不保存
5. 重复上述步骤，直至所有图片处理完毕

#### 第二阶段：文本识别

1. 从 `havetext.md` 读取所有待处理的图片文件名
2. 依次对每张图片进行文本识别处理
3. 对于下一张图片，识别的内容同前一张进行相似度比较：
   - 如果相似度超过 60%，则进行如下判断：
     - 如果前一张的文本信息**等于或多于**后一张，则**保留前一张**，后一张的内容不保留
     - 如果前一张的文本信息**等于或少于**后一张，则**用后一张的信息替换**前一张的信息
4. 识别出的文字内容保存至 `info.md`
5. 重复上述步骤，直至所有图片处理完毕

---

## 3. 大模型信息提取与结构化输出

### 3.1 处理对象

对 `info.md` 文件内容进行大模型分析处理

### 3.2 信息提取要求

利用语言大模型，从识别文本中提取以下信息：

| 提取项 | 说明 |
|--------|------|
| **产品发布信息** | 识别出现的所有产品发布相关内容 |
| **产品规格信息** | 整理每种产品的详细规格 |
| **发布时间** | 产品的发布或公告时间 |
| **存储规格** | 产品的存储容量配置 |
| **对应价格** | 各规格对应的价格信息 |
| **上市/开售时间** | 产品正式发售或开售时间 |

### 3.3 输出格式

将整理后的结果保存为 `result.json` 文件（JSON 格式结构化数据）

后续：
1. 发布会总结
2. 增加语音内容
3. 生成ppt

### 发布会总结
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

### 如果需要提取第 34 秒的关键帧
#### 您最初的目标是提取 t=34s 附近的关键帧。可以使用以下命令：

##### bash
yt-dlp -f bestvideo -o - https://www.youtube.com/watch?v=ZAyGqCC649o | ffmpeg -i pipe:0 -ss 34 -frames:v 1 -q:v 2 frame_34s.jpg
参数说明：

- f bestvideo：选择最佳画质的视频流。

- o ：将视频数据输出到标准输出（stdout）。

- | ffmpeg -i pipe:0：FFmpeg 从标准输入（pipe:0）读取数据

- ss 34：跳转到第 34 秒

- frames:v 1：只输出 1 帧

- q:v 2：高质量 JPEG

### 如果您想提取多个关键帧
#### 从第 34 秒开始提取 10 个关键帧
##### bash
yt-dlp -f bestvideo -o - https://www.youtube.com/watch?v=ZAyGqCC649o | ffmpeg -i pipe:0 -ss 34 -vf "select='eq(pict_type,I)'" -fps_mode vfr -frames:v 10 -q:v 2 frame_%03d.jpg
#### 每隔 5 秒提取一个关键帧（从第 0 秒开始）
##### bash
yt-dlp -f bestvideo -o - https://www.youtube.com/watch?v=ZAyGqCC649o | ffmpeg -i pipe:0 -vf "select='eq(pict_type,I)*not(mod(t,5))'" -fps_mode vfr -q:v 2 frame_%03d.jpg

## 直播
### 第一步：查看直播流可用格式
- 单独运行以下命令，查看该直播流支持哪些格式：

  bash
  - yt-dlp --cookies cookies.txt --list-formats https://live.bilibili.com/1990578339
  - 执行后会输出类似这样的格式列表：

text
[info] Available formats for 1990578339:
ID  EXT   PROTO  RESOLUTION  FPS  |  CODECS
0   flv   https  1920x1080   30   |  h264
1   flv   https  1280x720    30   |  h264
2   flv   https  852x480     30   |  h264
...
### 第二步：使用正确的格式代码
根据列表中的 ID（如 0、1、2），替换 -f 参数。例如，选择最高清格式（假设 ID 为 0）：

bash
  - yt-dlp --cookies cookies.txt -f 0 -o - https://live.bilibili.com/1990578339 | ffmpeg -i pipe:0 -frames:v 1 -q:v 2 frame.jpg
  -如果不确定选哪个，通常可以选择分辨率最高的那一个。  

连续帧
  - yt-dlp --cookies live.bilibili.com_cookies.txt -f ultra_high_res-0  -o - https://live.bilibili.com/1990578339 | ffmpeg -i pipe:0 -vf "select='eq(pict_type,I)'" -fps_mode vfr -q:v 2 keyframe_%03d.jpg
bash
yt-dlp --cookies live.bilibili.com_cookies.txt -f ultra_high_res-0 -o - https://live.bilibili.com/1990578339 | ffmpeg -i pipe:0 -vf "fps=0.2" -fps_mode vfr -q:v 2 frame_%03d.jpg
参数说明：

-vf "fps=0.2"：设置帧率为 0.2 帧/秒，即每 5 秒取 1 帧（1/5=0.2）

frame_%03d.jpg：输出为 frame_001.jpg、frame_002.jpg……

📌 其他时间间隔选项
提取间隔	fps 参数值	说明
每 5 秒 1 帧	fps=0.2	1 ÷ 5 = 0.2
每 10 秒 1 帧	fps=0.1	1 ÷ 10 = 0.1
每 30 秒 1 帧	fps=0.0333	1 ÷ 30 ≈ 0.0333
每 1 分钟 1 帧	fps=0.0167	1 ÷ 60 ≈ 0.0167
 ## 下载视频MP4
yt-dlp --cookies live.bilibili.com_cookies.txt -f best -o xfold6.mp4 https://live.bilibili.com/1990578339

## 同时处理音频流，并使用 ffmpeg 的 segment 复用器按分钟切片。

bash
 - yt-dlp --cookies live.bilibili.com_cookies.txt -f ultra_high_res-0 -o - https://live.bilibili.com/1990578339 | ffmpeg -i pipe:0 -vf "fps=0.2" -fps_mode vfr -q:v 2 frame_%04d.png -map 0:a -f segment -segment_time 60 -c:a aac -b:a 128k audio_%03d.aac
- 命令解析：

-map 0:a：从输入中选择音频流。

-f segment -segment_time 60：使用分段复用器，每 60 秒切一刀。

-c:a aac -b:a 128k：音频编码为 AAC，比特率 128k。

audio_%03d.aac：输出音频文件命名模板，会生成 audio_001.aac、audio_002.aac...

#### 其他音频切片方案
方案	命令（FFmpeg 部分）	特点
- 按固定时长切片（如 5 分钟）	-map 0:a -f segment -segment_time 300 -c copy audio_%03d.aac	-c copy 直接复制，速度快但可能切不准
- 按关键帧切片（精确切割）	-map 0:a -f segment -segment_time 60 -force_key_frames "expr:gte(t,n_forced*60)" -c:a aac audio_%03d.aac	在指定时间点强制插入关键帧，切割更精确
- 只提取完整音频（不切片）	-map 0:a -c:a aac -b:a 128k output.aac	生成一个完整的音频文件