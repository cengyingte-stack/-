# WeChatLiveCaption
Windows 微信视频/语音通话实时中文字幕工具。

本项目通过 **VB-CABLE + PyAudioWPatch + FunASR + PySide6** 实现：将微信声音单独路由到 VB-CABLE，程序只监听该虚拟音频通道，再使用 FunASR 的中文流式识别模型生成字幕，并以悬浮窗口显示在屏幕上。

> 本项目为个人学习/辅助使用工具，与微信官方无关。  
> 当前版本不是通过微信插件、DLL 注入或 Hook 微信进程实现，而是通过 Windows 音频路由隔离微信声音。

---

## 1. 功能特点

- 微信视频/语音通话实时中文字幕
- 只监听 VB-CABLE 音频通道，可与 Chrome、音乐、系统声音隔离
- FunASR 中文流式语音识别
- 本地 CPU 推理，无需 GPU
- 约 600 ms 一次流式识别
- 自动过滤低音量/静音片段
- 字幕窗口始终置顶
- 支持拖动字幕位置
- 支持快捷键调整字幕大小
- 不主动保存 WAV、PCM 等原始通话音频

---

## 2. 工作原理

整体流程如下：

```text
微信视频/语音
      ↓
Windows 音量混合器
      ↓
微信输出设备指定为 CABLE Input
      ↓
VB-CABLE 虚拟播放设备
      ↓
PyAudioWPatch 获取 VB-CABLE [Loopback]
      ↓
PCM16 音频
      ↓
双声道 → 单声道
      ↓
原始采样率 → 16000 Hz
      ↓
600 ms 分块
      ↓
静音/低能量过滤
      ↓
FunASR Paraformer 中文流式识别
      ↓
PySide6 悬浮字幕
```

音频隔离逻辑：

```text
微信 ──────────→ CABLE Input ─→ 字幕程序 ─→ FunASR ─→ 中文字幕

Chrome ────────→ Realtek/耳机
音乐播放器 ─────→ Realtek/耳机
Windows 系统音 ─→ Realtek/耳机
```

因此程序本身并不是直接识别“微信进程”，而是识别 **VB-CABLE 专用音频通道**。只要 Windows 中仅将微信路由到 VB-CABLE，其他应用声音就不会进入字幕识别。

---

## 3. 运行环境

建议环境：

- Windows 10 / Windows 11
- Python 3.10
- VB-CABLE
- 可联网环境（首次启动 FunASR 时需要下载模型）
- CPU 即可运行

本项目已在 Python 3.10 环境下使用。

---

## 4. 项目文件介绍

```text
WeChatLiveCaption/
│
├─ app.py
├─ requirements.txt
├─ install.bat
├─ start.bat
├─ README.md
└─ .gitignore
```

### `app.py`

主程序。

主要负责：

1. 加载 FunASR `paraformer-zh-streaming` 模型；
2. 扫描 Windows WASAPI Loopback 设备；
3. 查找 VB-CABLE 对应的 Loopback；
4. 实时读取 VB-CABLE PCM 音频；
5. 将多声道音频转换为单声道；
6. 将音频重采样到 16000 Hz；
7. 每约 600 ms 向 FunASR 提交一次音频；
8. 过滤低能量/静音数据；
9. 将识别结果发送给字幕窗口；
10. 使用 PySide6 显示置顶中文字幕。

### `requirements.txt`

Python 依赖列表，例如：

```text
numpy>=1.26,<3
scipy>=1.11
PyAudioWPatch>=0.2.12.8
PySide6>=6.8
modelscope>=1.20
funasr==1.3.22
torch
torchaudio
```

### `install.bat`

用于首次安装项目环境。

主要工作：

```text
创建 .venv
    ↓
升级 pip / setuptools / wheel
    ↓
安装 requirements.txt
```

建议使用 Python 3.10。

### `start.bat`

日常启动脚本。

作用是进入项目虚拟环境并执行：

```text
python app.py
```

配置完成以后，日常使用可以直接双击 `start.bat`。

### `.venv/`

Python 虚拟环境。

**不要上传到 Git。**

其他不建议上传的内容包括：

```text
.venv/
__pycache__/
*.pyc
```

FunASR 下载的模型通常位于用户本机缓存目录，也无需上传到 Git。

---

## 5. 第一次安装

### 5.1 检查 Python

打开 PowerShell：

```powershell
python --version
```

或者：

```powershell
py -0p
```

推荐：

```text
Python 3.10.x
```

---

### 5.2 创建虚拟环境

进入项目目录：

```powershell
cd C:\Users\Administrator\Downloads\WeChatLiveCaption
```

创建环境：

```powershell
py -3.10 -m venv .venv
```

升级基础安装工具：

```powershell
.\.venv\Scripts\python.exe -m pip install -U pip setuptools wheel
```

安装依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## 6. 安装和配置 VB-CABLE

### 6.1 安装

安装 VB-CABLE 驱动后，建议重新启动 Windows。

重启后按：

```text
Win + R
```

输入：

```text
mmsys.cpl
```

正常情况下应该能看到：

播放设备：

```text
CABLE Input
VB-Audio Virtual Cable
```

录制设备：

```text
CABLE Output
VB-Audio Virtual Cable
```

---

## 7. 将微信单独路由到 VB-CABLE

先打开微信电脑版。

进入：

```text
Windows 设置
→ 系统
→ 声音
→ 音量混合器
→ 应用
→ 微信
```

将微信的 **输出设备** 设置为：

```text
CABLE Input (VB-Audio Virtual Cable)
```

注意：

```text
微信输出 → CABLE Input
```

而不是 CABLE Output。

配置完成以后，微信声音会进入 VB-CABLE，Chrome、音乐播放器、Windows 系统声音仍可以继续使用正常的 Realtek 扬声器或耳机。

---

## 8. 让自己同时听见微信声音

微信被路由到 VB-CABLE 后，如果发现耳机听不到对方声音，可以开启 Windows 的“侦听此设备”。

按：

```text
Win + R
```

输入：

```text
mmsys.cpl
```

然后进入：

```text
录制
→ CABLE Output
→ 属性
→ 侦听
```

勾选：

```text
侦听此设备
```

“通过此设备播放”选择自己实际使用的：

```text
Realtek 扬声器
```

或：

```text
耳机
```

此时音频路径为：

```text
                    ┌→ 字幕程序
                    │
微信 → CABLE Input → CABLE Output
                    │
                    └→ 实体扬声器/耳机
```

---

## 9. 启动字幕

在 PowerShell 中进入项目目录：

```powershell
cd C:\Users\Administrator\Downloads\WeChatLiveCaption
```

运行：

```powershell
.\.venv\Scripts\python.exe app.py
```

也可以直接双击：

```text
start.bat
```

---

## 10. 第一次启动

第一次运行时，FunASR 会自动下载：

```text
paraformer-zh-streaming
```

中文流式语音识别模型。

此时字幕窗口可能显示：

```text
正在加载中文流式识别模型…首次启动需要联网下载
```

等待模型下载并加载完成即可。

模型下载完成后，后续一般直接使用本地缓存，无需每次重新下载。

---

## 11. 正常启动状态

成功识别到 VB-CABLE 后，状态栏应该类似：

```text
仅监听微信/VB-CABLE：
CABLE Input (VB-Audio Virtual Cable) [Loopback]
| 48000Hz | 2声道
```

如果显示：

```text
扬声器 (Realtek High Definition Audio) [Loopback]
```

则说明运行的可能仍然是旧版本代码，或者 `app.py` 尚未替换为 VB-CABLE 版本。

---

## 12. 字幕操作

程序启动后：

| 操作 | 功能 |
|---|---|
| 鼠标左键拖动 | 移动字幕窗口 |
| `Ctrl + ↑` | 放大字幕 |
| `Ctrl + ↓` | 缩小字幕 |
| `Esc` | 退出程序 |

字幕窗口默认显示在屏幕下方中央，并保持置顶。

---

## 13. 当前音频处理参数

当前版本主要参数：

```python
TARGET_RATE = 16000
CHUNK_SIZE = [0, 10, 5]
CHUNK_SAMPLES = 9600
ENCODER_LOOK_BACK = 4
DECODER_LOOK_BACK = 1
```

其中：

```text
9600 samples ÷ 16000 Hz ≈ 0.6 秒
```

因此程序约每 600 ms 进行一次流式识别。

---

## 14. 静音过滤

程序会计算每个音频块的 RMS 能量。

当前阈值：

```python
rms < 0.0025
```

低于阈值的片段不会送入 FunASR，可以减少：

- 静音误识别
- 无意义字幕
- CPU 占用

---

## 15. 字幕显示逻辑

FunASR 返回文字后，程序会保留最近几段识别内容。

当前：

```python
history = deque(maxlen=4)
```

最多保存最近 4 个增量片段。

同时限制字幕显示长度，过长时只显示最近约 80 个字符，避免字幕窗口持续增长。

---

## 16. 常见问题

### 16.1 提示“没有找到 VB-CABLE 的 Loopback 设备”

检查：

```text
1. VB-CABLE 是否已经安装；
2. 安装后是否已经重启 Windows；
3. mmsys.cpl → 播放 中是否存在 CABLE Input；
4. PyAudioWPatch 是否安装成功；
5. 当前 app.py 是否为 VB-CABLE 版本。
```

可以使用：

```powershell
.\.venv\Scripts\python.exe -m pyaudiowpatch
```

查看 Windows 当前可识别的音频设备。

---

### 16.2 微信有声音，但是没有字幕

确认 Windows：

```text
设置
→ 系统
→ 声音
→ 音量混合器
→ 微信
```

输出设备确实为：

```text
CABLE Input
```

然后检查：

```text
mmsys.cpl
→ 录制
→ CABLE Output
```

对方讲话时绿色音量条应该跳动。

---

### 16.3 微信通话后自己听不到对方

开启：

```text
CABLE Output
→ 属性
→ 侦听
→ 侦听此设备
```

并选择实际使用的耳机/扬声器。

---

### 16.4 Chrome 的声音也被识别了

正常情况下 Chrome 不应该输出到 VB-CABLE。

检查 Windows 音量混合器：

```text
微信  → CABLE Input
Chrome → 默认 / Realtek / 实体耳机
```

不要把 Windows 的整个默认输出设备设置为 CABLE Input，否则所有应用声音都可能进入字幕程序。

---

### 16.5 FunASR 第一次启动很慢

第一次启动需要下载并加载模型，属于正常现象。

下载完成以后模型会保存在本机缓存目录，后续启动通常不需要重复下载。

---

### 16.6 FunASR 导入时卡在 PySide6 / shiboken

当前代码需要保证导入顺序：

```python
from funasr import AutoModel

from PySide6...
```

即：

```text
FunASR
  ↓
PySide6
```

不要把 PySide6 放到 FunASR 前面导入。

---

## 17. 隐私说明

当前程序的设计为本地音频捕获和本地语音识别。

程序本身：

- 不主动保存通话 WAV 文件；
- 不主动保存 PCM 原始音频；
- 不主动记录完整通话内容到文件；
- FunASR 模型加载完成后在本机进行推理。

首次下载模型时需要联网。

如果后续修改代码增加日志、录音、云端识别或 API 调用，请重新评估隐私和数据安全风险。

---

## 18. 当前限制

当前版本存在以下限制：

1. 并非直接通过微信 PID 进行进程级 WASAPI Loopback；
2. 依赖 VB-CABLE 完成微信与其他应用声音的隔离；
3. 当前主要针对中文语音识别；
4. CPU 性能会影响识别速度；
5. 识别准确率会受到通话质量、噪声、口音和麦克风/扬声器质量影响；
6. 当前主要识别“对方通过微信播放出来的声音”，并不自动把本机麦克风作为第二路音频单独识别。

---

## 19. 停止程序

字幕窗口直接按：

```text
Esc
```

或者在 PowerShell 中：

```text
Ctrl + C
```

即可退出。
