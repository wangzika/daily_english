# YouTube 英语句子跟读视频：本地全流程批量生成系统

本项目是一套专为 **YouTube 口语教学 / 句子跟读（Shadowing）** 打造的本地全自动视频生成工作流。输入一份包含中英文的 CSV 句子表，一键全自动生成对标高质感现代播客风的 **1080p 30fps MP4 高清视频** 与 **高精度时间轴 JSON**。

---

## 目录
- [一、 成品特色与单句教学流](#一-成品特色与单句教学流)
- [二、 系统架构与实现原理](#二-系统架构与实现原理)
- [三、 目录结构](#三-目录结构)
- [四、 快速上手指南](#四-快速上手指南)
- [五、 参数微调指南（重点）](#五-参数微调指南重点)
  - [1. 语速与停顿节奏调整](#1-语速与停顿节奏调整)
  - [2. 背景风格与配色微调](#2-背景风格与配色微调)
  - [3. 音标表与文字样式微调](#3-音标表与文字样式微调)
  - [4. 顶部频道品牌定制](#4-顶部频道品牌定制)
- [六、 句子表 CSV 编写规范](#六-句子表-csv-编写规范)
- [七、 常见问题与技巧](#七-常见问题与技巧)

---

## 一、 成品特色与单句教学流

### 1. 经典播客视觉设计（1080p 16:9）
* **背景基底**：基于数学矩阵渲染的无色阶断层**深墨绿暗调径向微光渐变**（可自定义各种冷暖色系）。
* **顶部品牌胶囊**：半透明圆角药丸框，亮黄频道名（如 `VibeEnglish`）+ 白色加粗分类标签（如 `PODCAST`）。
* **核心英文排版**：大号无衬线粗斜体（Bold Italic），纯白字身辅以**青蓝霓虹辉光（Soft Cyan Glow）**，两行自然对齐。
* **逐词美式国际音标表（IPA Badges）**：自动提取每个单词的美式标准音标，以青蓝色卡片排列在句子下方。
* **高辨识度中文释义**：**亮鲜黄色 + 纯黑高对比描边（Black Stroke）**，视觉冲击力极强。
* **开口跟读倒计时**：跟读阶段显示 `Your turn: 4s` $\rightarrow$ `3s` $\rightarrow$ `2s` $\rightarrow$ `1s` 动感进度胶囊。

### 2. 递进式单句播放节奏

```text
[阶段 1: Listen]               英文原句朗读 (正常语速)        ── 盲听输入，中文与音标隐藏
         │
[阶段 2: Transition]           1.0 秒静音缓冲                ── 节奏过渡
         │
[阶段 3: Listen slowly]        逐词断点慢速朗读 (Word by Word) ── 音标卡片浮现，眼听口同步
         │
[阶段 4: Your turn]            静音跟读倒计时 (默认 4 秒)     ── 亮黄中文释义浮现，开口跟读
         │
[阶段 5: Next]                 0.3 秒换句静音                ── 平滑切换至下一句
```

---

## 二、 系统架构与实现原理

系统由四个核心 Python 模块组成，各模块职责清晰，松耦合且具备缓存复用机制：

```
       [ data/*.csv + config.json ]
                    │
                    ▼
          [ scripts/validate.py ]   ── 校验环境工具、字体、模型与 CSV 格式
                    │
                    ▼
         [ scripts/synthesize.py ]  ── 调用 Piper TTS 一次加载模型，生成正常速与逐词断点 WAV
                    │
                    ▼
           [ scripts/render.py ]    ── 提取美式 IPA、Pillow 绘制状态图卡、FFmpeg 生成主音轨
                    │
                    ▼
          [ scripts/build.py ]     ── FFmpeg 合并音画，极速输出 1080p MP4 与 timeline.json
```

1. **音频合成引擎 (`synthesize.py`)**：
   - 采用高性能本地离线引擎 **Piper TTS**（模型：`en_US-lessac-medium`）。
   - 一次性加载 ONNX 模型常驻内存；
   - 正常朗读使用 `length_scale=1.0`；
   - 慢速朗读采用**逐词断点重构**（`make_word_by_word_text`），自动在词与词之间注入短语停顿，实现咬字极其清晰的单词级跟读音频。
2. **音标提取引擎 (`render.py`)**：
   - 调用 Piper 内置的 `EspeakPhonemizer`，离线逐词解析出精准的美式国际音标（IPA），无需网络或外置字典。
3. **图像与卡片渲染 (`render.py`)**：
   - 使用 **NumPy** 计算径向光照矩阵，彻底消除传统绘图的色彩环状条纹（Color Banding）；
   - 使用 **Pillow** 进行两级高斯模糊制作文字辉光，并使用矢量字体（`DejaVuSans.ttf`）绘制全集音标符号；
   - 采用智能词宽折行算法，无论句子长短皆保持两行优雅排版。
4. **视频压制管线 (`render.py` + FFmpeg)**：
   - 不采用低效的逐帧绘图，而是按阶段生成关键状态卡，配合 FFmpeg `concat demuxer` 与精准时间轴以毫秒级对齐；
   - 压制编码：`libx264`（CRF 20，yuv420p）+ `aac` 48kHz，15 句长达 2 分半的高清视频在普通 CPU 上 **40 秒左右即可渲染完成**。

---

## 三、 目录结构

```text
english_program/
├── config.json                     # 全局参数配置文件（语速、背景、颜色、字体等）
├── README.md                       # 本操作与定制文档
├── english-shadowing-video-plan.md # 初始需求设计方案
├── data/                           # 句子数据表格目录
│   ├── daily_001.csv               # 第 1 期样表
│   └── daily_002.csv               # 第 2 期精选日常口语 15 句
├── models/                         # 本地 TTS 语音模型
│   ├── en_US-lessac-medium.onnx
│   └── en_US-lessac-medium.onnx.json
├── scripts/                        # 核心功能模块
│   ├── validate.py                 # 输入数据与环境检查
│   ├── synthesize.py               # 双语速/逐词音频批量合成
│   ├── render.py                   # 音标提取、卡片渲染与 MP4 压制
│   └── build.py                    # 统一对外 CLI 执行总入口
├── work/                           # 临时缓存目录（音频片段、阶段图卡等）
└── output/                         # 最终视频与交付物
    ├── daily_001/
    └── daily_002/
        ├── video.mp4               # 最终 1080p MP4 视频文件
        └── timeline.json           # 精准起止时间轴 JSON
```

---

## 四、 快速上手指南

### 1. 激活虚拟环境
在项目根目录下打开终端：
```bash
source .venv/bin/activate
```

### 2. 常用执行命令

#### ① 全流程生成（推荐）
输入任意 CSV 表格，自动完成音频合成与视频压制：
```bash
python scripts/build.py --input data/daily_002.csv --output output/daily_002
```

#### ② 仅试听音频（不渲染视频）
适合批量录制或人工审听发音：
```bash
python scripts/build.py --input data/daily_002.csv --audio-only
```

#### ③ 仅重刷视频画面（极速秒级出片）
当你修改了字体、背景颜色、排版或微调了中文翻译，只需重新渲染画面，**无需重复生成音频**：
```bash
python scripts/build.py --input data/daily_002.csv --render-only
```

#### ④ 仅生成指定句子范围
例如只生成第 3 句到第 7 句测试效果：
```bash
python scripts/build.py --input data/daily_002.csv --from-id 3 --to-id 7
```

#### ⑤ 强制重新生成所有缓存（`--force`）
如果更改了语音模型或语速，强制刷新所有本地缓存：
```bash
python scripts/build.py --input data/daily_002.csv --force
```

---

## 五、 参数微调指南（重点）

项目的所有参数均集中存放在 [config.json](file:///home/wzb/english_program/config.json) 中。你可以根据个人喜好或不同视频主题进行快速微调：

### 1. 语速、停顿与音质降噪微调（消除呲呲杂音 & 逐词匀速朗读）

```json
{
  "normal_length_scale": 1.0,     // 正常语速（数值越小越快，0.9为稍快，1.0为标准）
  "slow_length_scale": 1.25,      // 慢速逐词语速（推荐 1.2 ~ 1.3，每个单词独立念出，均匀扎实）
  "word_by_word_slow": true,      // true: 第二次读开启词典级逐词匀速精读模式；false: 普通慢速连读
  "word_pause_seconds": 0.28,     // 逐词精读时每个单词之间的固定呼吸停顿（秒，推荐 0.25 ~ 0.35）
  "noise_scale": 0.333,           // 声学历化随机噪声（降低可彻底消除清辅音/摩擦音如s,t,ch的呲呲白噪声）
  "noise_w_scale": 0.6,           // 辅音时长波动控制（推荐0.5~0.6，发音更扎实稳重）
  "audio_volume": 0.92,           // 音量动态余量（保留-0.7dB Headroom，杜绝48kHz重采样时的破音削波）
  "show_bottom_subtitles": false, // 是否显示视频底部的黑色英文小字幕条（默认 false 保持画面清爽）
  "transition_seconds": 1.0,      // 正常读与慢速读之间的静音缓冲（默认 1.0 秒）
  "next_seconds": 0.3,            // 切换到下一句的静音缓冲（默认 0.3 秒）
  "default_pause_seconds": 4.0    // 跟读默认留白时长（秒）
}
```

> **提示**：
> - **为什么逐词慢读时以前每个词语速不一、像整句语速？**
>   - 原先采用逗号拼接整句合成，神经网络依然按整句抑扬顿挫预测音素时长，导致虚词（如 been, and, to）被飞快轻读带过，实词则被拖长。
>   - **全新升级为词典级独立合成（Discrete Citation Synthesis）**：每个单词单独作为独立发音单元合成（饱满的 Dictionary Form），各词前后经过微淡入淡出（Micro-Fade）与等长间隔填充（`word_pause_seconds`），真正实现字字清晰、节奏如钟表般匀称的教学级慢读！
> - **为什么以前个别单词会有呲呲声？**
>   1. Piper 默认的 `noise_scale=0.667` 会在清辅音（如 `s`, `x`, `sh`, `ch`, `t`, `k`）上添加较重的随机噪声；逐词精读时辅音被单独隔离，呲呲气流声格外明显。将 `noise_scale` 设为 `0.333`，声音会变得极其纯净通透。
>   2. 系统在 FFmpeg 重采样层内置了 **Soxr Sinc 专业级重采样 + 齿音衰减（de-esser）**，彻底消除数码爆音。
> - 如果在 CSV 表格中为某句单独填写了 `pause_seconds`（如长句设为 5 秒），将优先使用该句的专属设置。

---

### 2. 背景风格与配色微调

背景采用径向微光（中心发亮，外围逐渐变暗深邃）。在 `config.json` 的 `theme` 字段中调整 RGB 配色：

#### ① 当前预设：暗夜墨绿（质感播客风）
```json
"theme": {
  "bg_gradient_start": "#123024", // 中心微光色
  "bg_gradient_end": "#07120d"    // 外围深暗色
}
```

#### ② 推荐配色方案：
* **深海幽蓝（科技/商务风）**：
  ```json
  "bg_gradient_start": "#14253d",
  "bg_gradient_end": "#09101a"
  ```
* **黑曜石金（沉稳高阶风）**：
  ```json
  "bg_gradient_start": "#2b261c",
  "bg_gradient_end": "#110e0a"
  ```
* **午夜紫罗兰（雅致文艺风）**：
  ```json
  "bg_gradient_start": "#241834",
  "bg_gradient_end": "#0d0814"
  ```

---

### 3. 音标表与文字样式微调

```json
{
  "show_phonetics": true,           // 是否显示逐词国际音标表（true/false）
  "show_translation_after_slow": true, // 是否在慢速读完后才显示中文（true: 慢速后显示; false: 全程显示）
  "theme": {
    "english_text_color": [255, 255, 255],     // 英文文字颜色（纯白）
    "english_glow_color": [45, 120, 255, 255], // 英文外发光霓虹辉光（青蓝色）
    "chinese_text_color": [255, 222, 0],       // 中文填充色（高饱和鲜黄色）
    "chinese_stroke_color": [0, 0, 0],         // 中文外描边颜色（纯黑）
    "chinese_stroke_width": 6,                 // 中文描边粗细（像素，推荐 5~7）
    "ipa_card_bg": [14, 32, 25, 225],          // 音标小卡片背景色（半透明深色）
    "ipa_card_border": [55, 105, 82, 230],     // 音标卡片外框线颜色
    "ipa_word_color": [240, 248, 255],         // 音标卡片中的英文词颜色
    "ipa_phonetic_color": [105, 220, 255]      // 音标颜色（亮青蓝色）
  }
}
```

---

### 4. 顶部频道品牌定制

```json
{
  "header_title": "VibeEnglish", // 顶部胶囊左侧黄色名称（填你的频道或栏目名）
  "header_badge": "PODCAST"      // 顶部胶囊右侧白色加粗标签（如 PODCAST, SHADOWING, DAILY A1 等）
}
```

---

## 六、 句子表 CSV 编写规范

所有句子数据存放在 `data/*.csv`。标准格式如下：

```csv
id,topic,level,english,chinese,pause_seconds
1,daily,A1,"That makes a lot of sense.","這很有道理。",4
2,daily,A1,"I couldn't agree more.","我完全同意你的看法。",4
3,daily,A1,"Take your time, no rush at all.","慢慢來，完全不用著急。",4
```

### 字段说明：
1. `id`：句子唯一编号（建议数字递增，生成时会对应输出图卡与音频缓存名）；
2. `topic`：分类主题（如 `daily`, `travel`, `business`）；
3. `level`：难度等级（如 `A1`, `A2`, `B1`）；
4. `english`：英文原句；
5. `chinese`：中文释义；
6. `pause_seconds`：跟读停留秒数（通常 3~6 秒，短句 3~4 秒，长句 5~6 秒）。

> [!IMPORTANT]
> **重要规则（CSV 转义）**：
> 如果英文字句中包含**逗号**（如 `Take your time, no rush at all.`），必须用半角双引号 `""` 将整句话包裹起来，避免 CSV 解析器将其误识别为列分隔符。

---

## 七、 常见问题与技巧

1. **改了样式怎么快速看效果？**
   * 修改 `config.json` 或 `render.py` 后，执行：
     ```bash
     python scripts/build.py --input data/daily_002.csv --render-only
     ```
     无需等待 TTS 音频重新生成，数秒内即可重新生成整期视频。
2. **只想修改某一个句子的读音或翻译？**
   * 在 CSV 中修改该句对应文本；
   * 使用 `--from-id X --to-id X` 仅针对该句单句重建并检查，确认无误再全量导出。
3. **生成的视频在哪里查看？**
   * 导出的 MP4 文件默认保存在 `output/<csv文件名>/video.mp4`，可以使用任意播放器（VLC, MPV, 浏览器等）直接打开播放。
