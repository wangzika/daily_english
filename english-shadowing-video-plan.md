# YouTube 英语句子跟读视频：本地生成实施文档

版本：2026-11-01。目标：输入一份句子表，在本机批量生成可供人工审看的 1080p MP4 跟读视频。首版采用美式英语、横屏、单一声音、无背景音乐。

## 1. 成品定义

每句按固定顺序播放：

| 阶段 | 画面提示 | 声音 | 时长 |
|---|---|---|---|
| 正常语速 | Listen | 英语正常读一遍 | 由音频决定 |
| 过渡 | Listen slowly | 静音 | 1.0 秒 |
| 慢速精读 | Listen slowly (Word by Word) | 逐词断点清晰朗读 | 由音频决定 |
| 跟读 | Your turn，倒计时 | 静音 | 默认 4 秒，可逐句设置 |
| 换句 | 下一句 | 静音 | 0.3 秒 |

英文句子在以上各阶段始终显示。中文释义默认在慢速读完后才显示，降低第一次听音时的阅读依赖。每条视频先做 15–25 句。输出 `1920×1080 / 30 fps / H.264 / AAC / MP4`，另输出 `timeline.json` 记录每句的精确起止时间，方便复查和后续做字幕。

### 1.1 画面视觉规范（对标现代高质感播客风）

- **背景风格**：深墨绿质感暗调渐变（从中心偏暗墨绿 `#123024` 向外围深黑绿 `#07120D` 平滑渐变，无色阶断层）。
- **顶部胶囊（Header Pill）**：半透明深色圆角药丸框。左侧为亮黄色频道/栏目名（如 `VibeEnglish`），右侧为白底加粗标签（如 `PODCAST`）。
- **英文排版**：大号无衬线粗斜体（Bold Italic），纯白高亮（`#FFFFFF`）辅以柔和浅蓝/青色外发光晕（Soft Blue/Cyan Glow），两行内自然换行。
- **逐词美式音标表（Phonetic Badges）**：慢速与跟读阶段自动展示每个单词的美式标准 IPA 音标卡片（如 `/hˈævənt/`），上白下青蓝。
- **中文释义**：位于音标卡片下方，采用加粗无衬线字体，填充亮鲜黄色（`#FFDE00`），外带纯黑高对比描边（Black Stroke Outline，6px），确保辨识度极高。
- **倒计时提示**：跟读阶段显示圆角胶囊进度指示（`Your turn: 4s` 到 `1s`）。

## 2. 技术选择

| 模块 | 首版选择 | 理由 |
|---|---|---|
| 英语 TTS | Piper，`en_US-lessac-medium` 候选音色 | 可本地运行，Python API 支持逐句合成和 `length_scale` 语速设置 |
| 排版 | Pillow | 英文、中文、长句换行与阶段标签容易控制 |
| 音视频拼接 | FFmpeg、ffprobe | 能生成静音、统一音频格式、编码和检查成品 |
| 内容数据 | UTF-8 CSV | 可用表格编辑，易于版本管理 |

先试听候选音色，再决定是否长期使用。Piper 程序和每个语音模型各有许可信息；`lessac` 的 MODEL_CARD 还列出训练数据许可链接。正式发布，尤其计划变现时，须记录并核对所用音色对应的许可。不要直接用非商业许可的 XTTS-v2 作为商业频道语音。

参考资料：[Piper Python API](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/API_PYTHON.md)、[Piper CLI](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/CLI.md)、[lessac 模型卡](https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/lessac/medium/MODEL_CARD)、[FFmpeg 滤镜文档](https://ffmpeg.org/ffmpeg-filters.html)。

## 3. 本机环境与安装

建议 Linux/macOS；Windows 可用 WSL2。Python 3.10–3.12，先用 CPU 即可。安装 FFmpeg、带中文和英文字形的字体。以 Ubuntu 为例：

```bash
sudo apt update
sudo apt install -y ffmpeg fonts-noto-cjk python3-venv
mkdir -p english-shadowing/{data,models,output,work}
cd english-shadowing
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install piper-tts Pillow
python -m piper.download_voices --data-dir models en_US-lessac-medium
```

确认 `models/` 中同时有 `.onnx` 和 `.onnx.json`。模型下载需要网络；下载完成后，语音合成和视频生成可离线运行。用下面的命令试听：

```bash
python -m piper --data-dir models -m en_US-lessac-medium -f work/voice-check.wav -- "Could you say that again?"
```

若本机没有 `sudo` 或是其他系统，只需确保 `ffmpeg`、`ffprobe`、Python 与可用字体在路径中；实施脚本不要把字体路径写死，应通过配置指定。

## 4. 项目目录与文件职责

```text
english-shadowing/
├── .venv/
├── config.json                 # 语音、画面、时间参数
├── data/
│   └── daily_001.csv           # 本期句子
├── models/                      # Piper 模型与配置文件
├── scripts/
│   ├── validate.py              # 检查 CSV 与配置
│   ├── synthesize.py            # 两档语速 WAV
│   └── render.py                # 时间轴、卡片与 MP4
├── work/daily_001/             # 可清理的中间文件
└── output/daily_001/
    ├── video.mp4
    ├── timeline.json
    └── review.csv               # 人工试听记录
```

`validate.py`、`synthesize.py`、`render.py` 是待实现模块的明确边界。可以先合成一个 `build.py`，稳定后再拆分。

## 5. 输入数据与配置

`data/daily_001.csv`：

```csv
id,topic,level,english,chinese,pause_seconds
1,daily,A1,Could you say that again?,你能再说一遍吗？,4
2,daily,A1,I need a little more time.,我还需要一点时间。,4
3,daily,A2,Would you mind speaking more slowly?,你介意说慢一点吗？,5
```

规则：`id` 唯一；`english` 与 `chinese` 非空；`pause_seconds` 为 2–8；英语句子长度建议不超过 100 个字符。CSV 使用 UTF-8 编码，含逗号的字段由标准 CSV 库正确加引号。脚本不自动改写英文原句，只报告异常供人工修订。

`config.json`：

```json
{
  "voice_model": "models/en_US-lessac-medium.onnx",
  "normal_length_scale": 1.0,
  "slow_length_scale": 1.25,
  "audio_sample_rate": 48000,
  "width": 1920,
  "height": 1080,
  "fps": 30,
  "transition_seconds": 1.0,
  "next_seconds": 0.3,
  "font_path": "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
  "show_translation_after_slow": true
}
```

Piper 的 `length_scale` 越大，语音越慢。`1.25` 是首版试听起点，不能等同于严格的 0.8 倍语速；最终以实际听感为准。优先分别合成两次，避免直接拉伸正常音频影响音质。[Piper API](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/API_PYTHON.md)

## 6. 生成程序的处理步骤

### 6.1 数据检查

读取 CSV 和配置，检查列名、重复 ID、空值、停顿范围、模型文件、字体文件、FFmpeg 是否存在。任何一项失败就停止，并给出行号和原因。输出内容按 CSV 行顺序排列。

### 6.2 一次加载模型，逐句生成音频

在 `synthesize.py` 中只加载一次 `PiperVoice`。对每句分别调用 `synthesize_wav`，使用 `SynthesisConfig(length_scale=1.0)` 和 `SynthesisConfig(length_scale=1.25)`，写成 `001_normal.wav`、`001_slow.wav`。用 `wave` 或 `ffprobe` 读取实际长度，不能用字符数推算。合成后用 FFmpeg 将全部 WAV 统一成单声道 48 kHz PCM，再参与拼接。若某句读音异常，在 CSV 中修改拼写或通过专门的发音覆盖字段处理，并只重生成该句。

核心接口示意：

```python
from piper import PiperVoice, SynthesisConfig

voice = PiperVoice.load("models/en_US-lessac-medium.onnx")
# 对每一行：以 wave.open(path, "wb") 打开文件，
# 调用 voice.synthesize_wav(text, wav_file, syn_config=SynthesisConfig(length_scale=...))
```

### 6.3 构造精确时间轴

每句计算：

```text
normal_start = cursor
normal_end = normal_start + normal_wav_duration
slow_start = normal_end + transition_seconds
slow_end = slow_start + slow_wav_duration
repeat_start = slow_end
repeat_end = repeat_start + pause_seconds
sentence_end = repeat_end + next_seconds
cursor = sentence_end
```

所有时间用秒数浮点值保存到 `timeline.json`，渲染前再按 `fps` 对齐到帧。音频与画面都从同一份时间轴生成。最后一帧可延长至音频结束，避免尾部被截断。

### 6.4 拼接音频

每句的音频片段顺序为 `normal.wav → 0.4 秒静音 → slow.wav → pause_seconds 秒静音 → 0.3 秒静音`。可用 FFmpeg 的 `anullsrc` 生成静音，统一采样率后用 concat filter 拼接。输出 `work/daily_001/full_audio.wav`。背景音乐首版不加，保证发音清楚。

### 6.5 绘制视频帧

Pillow 根据当前帧时间查询 `timeline.json`，绘制背景和文字：

- 深色纯色背景，英文居中且保持高对比度。
- 顶部：`Sentence 03 / 20`；阶段标签 `Listen / Listen slowly / Your turn`。
- 英文最大两行，按实际字体宽度换行，不按字符数硬切。
- 中文在慢速结束后出现；若不需要释义，配置可关闭。
- 跟读阶段显示 4、3、2、1 倒计时或进度条，数值以剩余秒数计算。
- 字体和字号按 1920×1080 设计；英文基准 76 px，中文 42 px，左右安全边距至少 140 px。

首版可按句子和阶段渲染静态 PNG，再用 FFmpeg 的 `-loop 1 -t <阶段时长>` 制成片段；倒计时可以为跟读阶段生成每秒一张 PNG。这样无需逐帧调用 Pillow，速度和复杂度都更可控。最后将片段与完整音频合成，编码参数建议 `libx264 -crf 20 -preset medium -pix_fmt yuv420p`，音频 `aac -b:a 192k`。

### 6.6 输出与复用

输出到 `output/daily_001/video.mp4`。中间文件名包含句子 ID 和参数哈希；只有句子内容、音色或语速变化时才重新合成对应 WAV。改字体、背景、字幕样式时复用音频。处理失败保留 `work/` 供排查，成功后可手动清理。

## 7. 命令行约定

建议最终提供一个统一入口：

```bash
python scripts/build.py --input data/daily_001.csv --config config.json --output output/daily_001
```

支持参数：`--audio-only` 只生成并试听语音；`--render-only` 复用已有音频；`--from-id 3 --to-id 5` 只处理部分句子；`--force` 重建缓存。每次构建打印句数、总时长、模型名、输出路径、失败行号。

## 8. 人工审核与验收

第一条样片用 5 句制作，再扩展到 20 句。验收清单：

1. 每句英文显示内容与读音一致，无漏词、错读、异常重音。
2. 正常版自然；慢速版清晰但不拖沓。缩写、数字、专有名词逐条试听。
3. 阶段标签与音频对应；跟读静音足够长，倒计时没有提前跳句。
4. 长句无截断，中文无乱码；手机小屏观看仍能读清主要英文。
5. 用 `ffprobe` 确认 MP4 视频为 1920×1080、30 fps，音频存在，时长与 `timeline.json` 的末尾时间相差不超过一帧加音频编码容差。
6. 将每个异常记入 `review.csv`，修正后只重建受影响的句子。

## 9. 内容与发布节奏

首批选一个系列，例如“日常高频回应”，每期 20 句，句子尽量围绕同一个真实场景。每句可加入一句简短用法提示或容易读错的词，提升实际教学价值。YouTube 对大量模板化、变化很少且教育价值低的内容设有变现限制，因此每期应有明确主题、逐步难度和自己的讲解设计；不要把随机句子简单批量堆在同一模板中。[YouTube 频道变现政策](https://support.google.com/youtube/answer/1311392?hl=en)

先做横屏长视频。竖屏 Shorts 可在横屏流程稳定后增加第二套画布尺寸和排版配置，复用同一份 CSV、音频和时间轴。

## 10. 实施里程碑

| 阶段 | 交付物 | 完成标准 |
|---|---|---|
| 1. 声音样本 | 5 句正常/慢速 WAV | 发音和许可可接受 |
| 2. 首条样片 | 5 句 MP4、时间轴 | 声画同步，手机可读 |
| 3. 批量版本 | 20 句 MP4、审核记录 | 一条命令生成，出错可定位到句子 |
| 4. 频道模板 | 固定色彩、封面和系列结构 | 后续换 CSV 即可生产新一期 |

首版不需要部署大语言模型。若以后要自动生成句子，可增加本地 LLM 起草模块，但句子、释义和发音仍需人工审核。设备配置会影响合成与编码速度；这套方案原则上能在普通 CPU 机器运行，GPU 不是首版前提。
