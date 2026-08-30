# -*- coding: utf-8 -*-
import sys
import time
import threading
from collections import deque

import numpy as np
from scipy.signal import resample_poly
import pyaudiowpatch as pyaudio

# 关键：FunASR 必须放在 PySide6 前面
from funasr import AutoModel

from PySide6.QtCore import Qt, QObject, Signal, QPoint
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout

from funasr import AutoModel


TARGET_RATE = 16000
CHUNK_SIZE = [0, 10, 5]          # 600ms 输出粒度
CHUNK_SAMPLES = CHUNK_SIZE[1] * 960  # 9600 samples @ 16kHz
ENCODER_LOOK_BACK = 4
DECODER_LOOK_BACK = 1


class Bus(QObject):
    subtitle = Signal(str)
    status = Signal(str)
    fatal = Signal(str)


class CaptionWorker(threading.Thread):
    def __init__(self, bus: Bus):
        super().__init__(daemon=True)
        self.bus = bus
        self.stop_event = threading.Event()

    def stop(self):
        self.stop_event.set()

    @staticmethod
    def pcm16_to_float_mono(raw: bytes, channels: int):
        x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        if channels > 1:
            usable = (len(x) // channels) * channels
            x = x[:usable].reshape(-1, channels).mean(axis=1)
        return x

    @staticmethod
    def resample_to_16k(x: np.ndarray, src_rate: int):
        if src_rate == TARGET_RATE:
            return x.astype(np.float32, copy=False)
        # 用最大公约数减少 polyphase 参数
        import math
        g = math.gcd(src_rate, TARGET_RATE)
        up = TARGET_RATE // g
        down = src_rate // g
        return resample_poly(x, up, down).astype(np.float32, copy=False)

    def run(self):
        try:
            self.bus.status.emit("正在加载中文流式识别模型…首次启动需要联网下载")
            model = AutoModel(
                model="paraformer-zh-streaming",
                device="cpu",
                disable_update=True,
                disable_pbar=True,
            )
            self.bus.status.emit("模型已加载，正在连接 Windows 系统音频…")

            with pyaudio.PyAudio() as p:
                try:
                    dev = p.get_default_wasapi_loopback()
                except Exception as e:
                    raise RuntimeError(
                        "找不到默认 WASAPI Loopback 设备。\n"
                        "请确认 Windows 有可用的扬声器/耳机，并先播放一次声音。\n"
                        f"详细信息：{e}"
                    )

                src_rate = int(dev["defaultSampleRate"])
                channels = int(dev["maxInputChannels"])
                device_index = int(dev["index"])

                self.bus.status.emit(
                    f"正在监听：{dev['name']} | {src_rate}Hz | {channels}声道"
                )

                frames_per_buffer = 2048
                audio_buf = np.empty(0, dtype=np.float32)
                cache = {}
                history = deque(maxlen=4)

                with p.open(
                    format=pyaudio.paInt16,
                    channels=channels,
                    rate=src_rate,
                    input=True,
                    input_device_index=device_index,
                    frames_per_buffer=frames_per_buffer,
                ) as stream:
                    while not self.stop_event.is_set():
                        try:
                            raw = stream.read(frames_per_buffer, exception_on_overflow=False)
                        except Exception:
                            time.sleep(0.03)
                            continue

                        mono = self.pcm16_to_float_mono(raw, channels)
                        mono16 = self.resample_to_16k(mono, src_rate)
                        audio_buf = np.concatenate((audio_buf, mono16))

                        while len(audio_buf) >= CHUNK_SAMPLES:
                            chunk = audio_buf[:CHUNK_SAMPLES]
                            audio_buf = audio_buf[CHUNK_SAMPLES:]

                            # 极低能量直接跳过，减少静音误识别与 CPU 占用
                            rms = float(np.sqrt(np.mean(np.square(chunk)) + 1e-12))
                            if rms < 0.0025:
                                continue

                            res = model.generate(
                                input=chunk,
                                cache=cache,
                                is_final=False,
                                chunk_size=CHUNK_SIZE,
                                encoder_chunk_look_back=ENCODER_LOOK_BACK,
                                decoder_chunk_look_back=DECODER_LOOK_BACK,
                            )
                            txt = ""
                            if res and isinstance(res, list):
                                txt = (res[0].get("text", "") or "").strip()

                            if txt:
                                history.append(txt)
                                # 流式模型通常返回当前增量；保留最近几段便于阅读
                                shown = "".join(history)
                                if len(shown) > 80:
                                    shown = shown[-80:]
                                self.bus.subtitle.emit(shown)

                # 尝试刷新末尾缓存
                if len(audio_buf) > 0:
                    try:
                        res = model.generate(
                            input=audio_buf,
                            cache=cache,
                            is_final=True,
                            chunk_size=CHUNK_SIZE,
                            encoder_chunk_look_back=ENCODER_LOOK_BACK,
                            decoder_chunk_look_back=DECODER_LOOK_BACK,
                        )
                    except Exception:
                        pass

        except Exception as e:
            self.bus.fatal.emit(str(e))


class Overlay(QWidget):
    def __init__(self, bus: Bus):
        super().__init__()
        self.bus = bus
        self.drag_pos = None

        self.setWindowTitle("微信实时字幕")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(900, 150)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        self.caption = QLabel("字幕准备中…")
        self.caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.caption.setWordWrap(True)
        self.caption.setFont(QFont("Microsoft YaHei UI", 24))
        self.caption.setStyleSheet("""
            QLabel {
                color: white;
                background: rgba(0, 0, 0, 190);
                border-radius: 14px;
                padding: 16px 24px;
            }
        """)

        self.status = QLabel("正在启动")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setFont(QFont("Microsoft YaHei UI", 9))
        self.status.setStyleSheet("""
            QLabel {
                color: rgba(255,255,255,210);
                background: rgba(0,0,0,120);
                border-radius: 8px;
                padding: 4px 10px;
            }
        """)

        layout.addWidget(self.caption)
        layout.addWidget(self.status)

        bus.subtitle.connect(self.caption.setText)
        bus.status.connect(self.status.setText)
        bus.fatal.connect(self.on_fatal)

        QShortcut(QKeySequence("Esc"), self, activated=self.close)
        QShortcut(QKeySequence("Ctrl+Up"), self, activated=self.font_up)
        QShortcut(QKeySequence("Ctrl+Down"), self, activated=self.font_down)

    def font_up(self):
        f = self.caption.font()
        f.setPointSize(min(44, f.pointSize() + 2))
        self.caption.setFont(f)

    def font_down(self):
        f = self.caption.font()
        f.setPointSize(max(14, f.pointSize() - 2))
        self.caption.setFont(f)

    def on_fatal(self, msg):
        self.caption.setText("启动失败")
        self.status.setText(msg)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.drag_pos is not None and (event.buttons() & Qt.MouseButton.LeftButton):
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    bus = Bus()
    overlay = Overlay(bus)

    # 默认放在屏幕下方中央
    screen = app.primaryScreen().availableGeometry()
    x = screen.x() + (screen.width() - overlay.width()) // 2
    y = screen.y() + screen.height() - overlay.height() - 80
    overlay.move(QPoint(x, y))
    overlay.show()

    worker = CaptionWorker(bus)
    worker.start()

    def cleanup():
        worker.stop()

    app.aboutToQuit.connect(cleanup)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
