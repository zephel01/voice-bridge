# -*- mode: python ; coding: utf-8 -*-
"""
Voice Bridge - PyInstaller ビルド設定

使い方:
  macOS:  pyinstaller voice_bridge.spec
  Windows: pyinstaller voice_bridge.spec

事前準備:
  pip install pyinstaller
"""

import platform
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

IS_WINDOWS = platform.system() == "Windows"
IS_MACOS = platform.system() == "Darwin"

# --- 依存データ・ライブラリの収集 ---

datas = []
hiddenimports = []
binaries = []

# faster-whisper / CTranslate2
hiddenimports += [
    "ctranslate2",
    "faster_whisper",
    "huggingface_hub",
    "tokenizers",
    "tqdm",
]
datas += collect_data_files("ctranslate2")
binaries += collect_dynamic_libs("ctranslate2")

# deep-translator
hiddenimports += ["deep_translator"]

# edge-tts
hiddenimports += ["edge_tts"]

# pygame
hiddenimports += ["pygame", "pygame.mixer"]
datas += collect_data_files("pygame")

# numpy
hiddenimports += ["numpy"]

# requests
hiddenimports += ["requests"]

# プラットフォーム固有
if IS_MACOS:
    # sounddevice + PortAudio
    hiddenimports += ["sounddevice", "_sounddevice_data"]
    datas += collect_data_files("sounddevice")
    datas += collect_data_files("_sounddevice_data")

if IS_WINDOWS:
    # PyAudioWPatch
    hiddenimports += ["pyaudiowpatch"]

# --- Analysis ---

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 不要なモジュールを除外してサイズ削減
        "matplotlib",
        "scipy",
        "PIL",
        "cv2",
        "torch",           # faster-whisper は CTranslate2 を使うので torch 不要
        "tensorflow",
        "notebook",
        "IPython",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

# --- 実行ファイル ---

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,    # --onedir モード
    name="VoiceBridge",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                # UPX 圧縮はウイルス誤検知の原因になるため無効
    console=False,            # GUI アプリなのでコンソール非表示
    icon=None,                # アイコンファイルがあれば指定: icon="icon.ico"
)

# --- フォルダ出力 ---

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="VoiceBridge",
)

# --- macOS: .app バンドル ---

if IS_MACOS:
    app = BUNDLE(
        coll,
        name="VoiceBridge.app",
        icon=None,            # アイコンファイルがあれば指定: icon="icon.icns"
        bundle_identifier="com.voicebridge.app",
        info_plist={
            "CFBundleDisplayName": "Voice Bridge",
            "CFBundleShortVersionString": "1.0.0",
            "NSMicrophoneUsageDescription":
                "Voice Bridge はシステム音声をキャプチャして翻訳に使用します",
            "NSHumanReadableCopyright":
                "音声合成: VOICEVOX https://voicevox.hiroshiba.jp/",
        },
    )
