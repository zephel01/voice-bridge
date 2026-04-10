#!/usr/bin/env python3
"""
ASR エンジン ベンチマークスクリプト
Whisper / Moonshine / Qwen3-ASR の精度・速度・メモリ使用量を比較する

使い方:
  # 基本（利用可能な全エンジンで自動テスト）
  python benchmark_asr.py

  # エンジン指定
  python benchmark_asr.py --engines whisper qwen3

  # テスト音声ファイルを指定
  python benchmark_asr.py --audio test_en.wav --language en

  # テスト音声を自動生成（Edge TTS を使用）
  python benchmark_asr.py --generate-audio

  # 結果を JSON に保存
  python benchmark_asr.py --output results.json

  # GPU 使用
  python benchmark_asr.py --device cuda
"""

import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path

import numpy as np

# メモリ計測
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


def get_memory_mb() -> float:
    """現在のプロセスのメモリ使用量（MB）を取得"""
    if HAS_PSUTIL:
        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    return 0.0


def generate_test_audio(language: str = "en", text: str = None, output_path: str = None) -> str:
    """Edge TTS でテスト用音声を生成する

    Args:
        language: 言語コード
        text: 読み上げるテキスト（None の場合デフォルトテキスト）
        output_path: 出力パス（None の場合自動生成）

    Returns:
        生成された音声ファイルのパス
    """
    import asyncio
    import edge_tts

    default_texts = {
        "en": "The quick brown fox jumps over the lazy dog. "
              "Artificial intelligence is transforming how we interact with technology.",
        "ja": "吾輩は猫である。名前はまだ無い。"
              "どこで生れたかとんと見当がつかぬ。",
        "zh": "人工智能正在改变我们与技术互动的方式。"
              "这是一个测试语音识别的句子。",
        "es": "La inteligencia artificial está transformando la forma "
              "en que interactuamos con la tecnología.",
        "fr": "L'intelligence artificielle transforme notre façon "
              "d'interagir avec la technologie.",
        "de": "Künstliche Intelligenz verändert die Art und Weise, "
              "wie wir mit Technologie interagieren.",
        "ko": "인공지능은 우리가 기술과 상호 작용하는 방식을 변화시키고 있습니다.",
    }

    voices = {
        "en": "en-US-JennyNeural",
        "ja": "ja-JP-NanamiNeural",
        "zh": "zh-CN-XiaoxiaoNeural",
        "es": "es-ES-ElviraNeural",
        "fr": "fr-FR-DeniseNeural",
        "de": "de-DE-KatjaNeural",
        "ko": "ko-KR-SunHiNeural",
    }

    if text is None:
        text = default_texts.get(language, default_texts["en"])

    if output_path is None:
        output_path = f"benchmark_audio_{language}.mp3"

    voice = voices.get(language, voices["en"])

    async def _generate():
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)

    asyncio.run(_generate())
    print(f"[Benchmark] テスト音声を生成: {output_path} ({language})")
    return output_path


def load_audio(file_path: str, target_sr: int = 16000) -> tuple[np.ndarray, int]:
    """音声ファイルを読み込んでnumpy配列に変換"""
    try:
        import soundfile as sf
        audio, sr = sf.read(file_path, dtype="float32")
    except ImportError:
        # soundfile がない場合は pydub を試す
        from pydub import AudioSegment
        seg = AudioSegment.from_file(file_path)
        seg = seg.set_channels(1).set_frame_rate(target_sr)
        samples = np.array(seg.get_array_of_samples(), dtype=np.float32)
        audio = samples / (2 ** 15)  # 16bit → float32
        sr = target_sr

    # モノラル化
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    # リサンプリング（必要な場合）
    if sr != target_sr:
        try:
            import librosa
            audio = librosa.resample(audio, orig_sr=sr, target_sr=target_sr)
        except ImportError:
            # 簡易リサンプリング（品質は低い）
            ratio = target_sr / sr
            new_len = int(len(audio) * ratio)
            indices = np.linspace(0, len(audio) - 1, new_len)
            audio = np.interp(indices, np.arange(len(audio)), audio)
        sr = target_sr

    return audio.astype(np.float32), sr


def check_engine_available(engine_name: str) -> bool:
    """エンジンが利用可能かチェック"""
    try:
        if engine_name == "whisper":
            import faster_whisper
            return True
        elif engine_name == "moonshine":
            import moonshine_voice
            return True
        elif engine_name == "qwen3":
            import qwen_asr
            return True
    except ImportError:
        return False
    return False


def create_transcriber(engine_name: str, language: str, device: str, model_size: str):
    """エンジン名からトランスクライバーを生成"""
    if engine_name == "whisper":
        from transcriber import Transcriber
        return Transcriber(model_size=model_size, language=language, device=device)
    elif engine_name == "moonshine":
        from transcriber_moonshine import Transcriber
        return Transcriber(model_size=model_size, language=language, device=device)
    elif engine_name == "qwen3":
        from transcriber_qwen3 import Transcriber
        return Transcriber(model_size=model_size, language=language, device=device)
    else:
        raise ValueError(f"不明なエンジン: {engine_name}")


def benchmark_engine(
    engine_name: str,
    audio: np.ndarray,
    sample_rate: int,
    language: str,
    device: str,
    model_size: str,
    num_runs: int = 5,
    warmup_runs: int = 1,
    reference_text: str = None,
) -> dict:
    """1つのエンジンをベンチマークする

    Returns:
        ベンチマーク結果の辞書
    """
    result = {
        "engine": engine_name,
        "language": language,
        "device": device,
        "model_size": model_size,
        "audio_duration_sec": len(audio) / sample_rate,
        "available": False,
        "error": None,
    }

    if not check_engine_available(engine_name):
        result["error"] = f"{engine_name} がインストールされていません"
        print(f"  [{engine_name}] スキップ: {result['error']}")
        return result

    # Moonshine の言語制限チェック
    if engine_name == "moonshine" and language in ("fr", "de"):
        result["error"] = f"Moonshine は {language} 非対応"
        print(f"  [{engine_name}] スキップ: {result['error']}")
        return result

    try:
        # モデルロード
        mem_before = get_memory_mb()
        t_load_start = time.perf_counter()

        transcriber = create_transcriber(engine_name, language, device, model_size)
        transcriber.load_model()

        t_load = time.perf_counter() - t_load_start
        mem_after = get_memory_mb()

        result["available"] = True
        result["load_time_sec"] = round(t_load, 3)
        result["memory_delta_mb"] = round(mem_after - mem_before, 1)

        # ウォームアップ
        for _ in range(warmup_runs):
            transcriber.transcribe(audio, sample_rate)

        # 本番計測
        latencies = []
        texts = []
        for i in range(num_runs):
            t_start = time.perf_counter()
            text = transcriber.transcribe(audio, sample_rate)
            t_elapsed = time.perf_counter() - t_start
            latencies.append(t_elapsed)
            texts.append(text)

        result["latencies_sec"] = [round(t, 4) for t in latencies]
        result["avg_latency_sec"] = round(sum(latencies) / len(latencies), 4)
        result["min_latency_sec"] = round(min(latencies), 4)
        result["max_latency_sec"] = round(max(latencies), 4)
        result["std_latency_sec"] = round(np.std(latencies), 4)

        # RTF (Real-Time Factor): 処理時間 / 音声長。1.0未満ならリアルタイムより速い
        audio_duration = len(audio) / sample_rate
        result["rtf_avg"] = round(result["avg_latency_sec"] / audio_duration, 4)

        # 認識テキスト（代表として最後の結果）
        result["transcribed_text"] = texts[-1]
        result["text_length"] = len(texts[-1])

        # テキストの一貫性（全ランで同じ結果が出るか）
        unique_texts = set(texts)
        result["consistency"] = round(1.0 - (len(unique_texts) - 1) / max(num_runs, 1), 3)

        # リファレンステキストとの比較（あれば）
        if reference_text:
            result["reference_text"] = reference_text
            # 簡易的な文字一致率（CER の代わり）
            ref_chars = set(reference_text.lower())
            hyp_chars = set(texts[-1].lower())
            if ref_chars:
                overlap = len(ref_chars & hyp_chars) / len(ref_chars)
                result["char_overlap"] = round(overlap, 3)

        print(f"  [{engine_name}] 完了: avg={result['avg_latency_sec']:.3f}s "
              f"RTF={result['rtf_avg']:.3f} 一貫性={result['consistency']:.1%}")
        print(f"    テキスト: {texts[-1][:100]}...")

    except Exception as e:
        result["error"] = str(e)
        print(f"  [{engine_name}] エラー: {e}")
        traceback.print_exc()

    return result


def print_comparison(results: list[dict]) -> None:
    """ベンチマーク結果の比較表を表示"""
    available = [r for r in results if r["available"]]
    if not available:
        print("\n利用可能なエンジンがありませんでした。")
        return

    print("\n" + "=" * 80)
    print("ASR エンジン ベンチマーク比較結果")
    print("=" * 80)

    # ヘッダー
    header = f"{'エンジン':>12} | {'平均(s)':>8} | {'最小(s)':>8} | {'最大(s)':>8} | {'RTF':>6} | {'一貫性':>6} | {'メモリ(MB)':>10} | {'ロード(s)':>8}"
    print(header)
    print("-" * len(header))

    # 各エンジン
    for r in available:
        row = (
            f"{r['engine']:>12} | "
            f"{r['avg_latency_sec']:8.3f} | "
            f"{r['min_latency_sec']:8.3f} | "
            f"{r['max_latency_sec']:8.3f} | "
            f"{r['rtf_avg']:6.3f} | "
            f"{r['consistency']:6.1%} | "
            f"{r.get('memory_delta_mb', 0):10.1f} | "
            f"{r.get('load_time_sec', 0):8.2f}"
        )
        print(row)

    # 最速エンジン
    fastest = min(available, key=lambda r: r["avg_latency_sec"])
    print(f"\n最速: {fastest['engine']} (平均 {fastest['avg_latency_sec']:.3f}s, RTF {fastest['rtf_avg']:.3f})")

    # 非対応エンジン
    skipped = [r for r in results if not r["available"]]
    if skipped:
        print(f"\nスキップ: {', '.join(r['engine'] + '(' + (r['error'] or '不明') + ')' for r in skipped)}")


def main():
    parser = argparse.ArgumentParser(
        description="ASR エンジン ベンチマーク（Whisper / Moonshine / Qwen3-ASR）"
    )
    parser.add_argument(
        "--engines", nargs="+",
        default=["whisper", "moonshine", "qwen3"],
        choices=["whisper", "moonshine", "qwen3"],
        help="テストするエンジン（デフォルト: 全て）",
    )
    parser.add_argument(
        "--audio", type=str, default=None,
        help="テスト音声ファイルのパス",
    )
    parser.add_argument(
        "--language", type=str, default="en",
        choices=["en", "ja", "zh", "es", "fr", "de", "ko"],
        help="テスト言語（デフォルト: en）",
    )
    parser.add_argument(
        "--generate-audio", action="store_true",
        help="Edge TTS でテスト音声を自動生成する",
    )
    parser.add_argument(
        "--reference-text", type=str, default=None,
        help="正解テキスト（精度評価用）",
    )
    parser.add_argument(
        "--device", type=str, default="cpu",
        choices=["cpu", "cuda"],
        help="デバイス（デフォルト: cpu）",
    )
    parser.add_argument(
        "--model-size", type=str, default="small",
        help="モデルサイズ（デフォルト: small）",
    )
    parser.add_argument(
        "--num-runs", type=int, default=5,
        help="計測回数（デフォルト: 5）",
    )
    parser.add_argument(
        "--warmup", type=int, default=1,
        help="ウォームアップ回数（デフォルト: 1）",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="結果を JSON ファイルに保存するパス",
    )

    args = parser.parse_args()

    # テスト音声を用意
    if args.audio:
        audio_path = args.audio
    elif args.generate_audio:
        audio_path = generate_test_audio(language=args.language)
    else:
        # カレントディレクトリにテスト音声があるか探す
        candidates = [
            f"benchmark_audio_{args.language}.mp3",
            f"benchmark_audio_{args.language}.wav",
            f"test_{args.language}.wav",
            f"test_{args.language}.mp3",
        ]
        audio_path = None
        for c in candidates:
            if os.path.exists(c):
                audio_path = c
                break

        if audio_path is None:
            print("テスト音声ファイルが見つかりません。")
            print("以下のいずれかを指定してください:")
            print("  --audio <ファイルパス>      : 既存の音声ファイルを使用")
            print("  --generate-audio            : Edge TTS で自動生成")
            sys.exit(1)

    # 音声を読み込み
    print(f"\n音声ファイル: {audio_path}")
    audio, sr = load_audio(audio_path)
    duration = len(audio) / sr
    print(f"音声長: {duration:.1f}秒 / サンプルレート: {sr}Hz")
    print(f"言語: {args.language} / デバイス: {args.device} / モデル: {args.model_size}")
    print(f"計測: {args.num_runs}回 (ウォームアップ: {args.warmup}回)")

    # ベンチマーク実行
    print(f"\n--- ベンチマーク開始 ---")
    results = []
    for engine in args.engines:
        print(f"\n[{engine}] テスト中...")
        result = benchmark_engine(
            engine_name=engine,
            audio=audio,
            sample_rate=sr,
            language=args.language,
            device=args.device,
            model_size=args.model_size,
            num_runs=args.num_runs,
            warmup_runs=args.warmup,
            reference_text=args.reference_text,
        )
        results.append(result)

    # 結果表示
    print_comparison(results)

    # JSON 保存
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n結果を保存: {args.output}")


if __name__ == "__main__":
    main()
