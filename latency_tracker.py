"""
レイテンシ計測モジュール
パイプラインの各ステージ（ASR, 翻訳, TTS）の所要時間を記録・集計する

使い方:
    tracker = LatencyTracker()

    tracker.start("asr")
    text = transcriber.transcribe(audio)
    tracker.stop("asr")

    tracker.start("translate")
    translated = translator.translate(text)
    tracker.stop("translate")

    tracker.start("tts")
    audio_path = tts.synthesize(translated)
    tracker.stop("tts")

    # 1回の処理が終わったら記録
    tracker.record_cycle()

    # 統計を取得
    stats = tracker.get_stats()
    print(stats)
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class StageStats:
    """1ステージの統計情報"""
    name: str
    count: int = 0
    total_sec: float = 0.0
    min_sec: float = float("inf")
    max_sec: float = 0.0

    @property
    def avg_sec(self) -> float:
        return self.total_sec / self.count if self.count > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "count": self.count,
            "avg_sec": round(self.avg_sec, 3),
            "min_sec": round(self.min_sec, 3) if self.min_sec != float("inf") else 0.0,
            "max_sec": round(self.max_sec, 3),
            "total_sec": round(self.total_sec, 3),
        }


@dataclass
class CycleRecord:
    """1サイクル（ASR→翻訳→TTS）の記録"""
    stages: dict = field(default_factory=dict)  # stage_name -> duration_sec
    total_sec: float = 0.0
    timestamp: float = 0.0


class LatencyTracker:
    """パイプラインのレイテンシを計測・集計するトラッカー"""

    STAGE_ORDER = ["asr", "translate", "tts"]

    def __init__(self, max_history: int = 100):
        """
        Args:
            max_history: 保持するサイクル履歴の最大数
        """
        self._max_history = max_history
        self._stage_starts: dict[str, float] = {}
        self._current_cycle: dict[str, float] = {}
        self._history: list[CycleRecord] = []
        self._stats: dict[str, StageStats] = {}
        self._total_stats = StageStats(name="total")

    def start(self, stage: str) -> None:
        """ステージの計測を開始"""
        self._stage_starts[stage] = time.perf_counter()

    def stop(self, stage: str) -> float:
        """ステージの計測を終了し、所要時間を返す"""
        if stage not in self._stage_starts:
            return 0.0
        elapsed = time.perf_counter() - self._stage_starts.pop(stage)
        self._current_cycle[stage] = elapsed
        return elapsed

    def record_cycle(self, extra_latency: float = 0.0) -> CycleRecord:
        """現在のサイクルを記録し、統計を更新する

        Args:
            extra_latency: チャンク蓄積時間など、計測外の追加レイテンシ（秒）

        Returns:
            記録されたサイクル
        """
        total = sum(self._current_cycle.values()) + extra_latency
        record = CycleRecord(
            stages=dict(self._current_cycle),
            total_sec=total,
            timestamp=time.time(),
        )

        # 履歴に追加（上限超えたら古いものを削除）
        self._history.append(record)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        # ステージ別統計を更新
        for stage, duration in self._current_cycle.items():
            if stage not in self._stats:
                self._stats[stage] = StageStats(name=stage)
            s = self._stats[stage]
            s.count += 1
            s.total_sec += duration
            s.min_sec = min(s.min_sec, duration)
            s.max_sec = max(s.max_sec, duration)

        # 合計統計
        self._total_stats.count += 1
        self._total_stats.total_sec += total
        self._total_stats.min_sec = min(self._total_stats.min_sec, total)
        self._total_stats.max_sec = max(self._total_stats.max_sec, total)

        self._current_cycle.clear()
        return record

    def get_stats(self) -> dict:
        """全ステージの統計を辞書で返す"""
        result = {}
        for stage in self.STAGE_ORDER:
            if stage in self._stats:
                result[stage] = self._stats[stage].to_dict()
        # STAGE_ORDER にないカスタムステージも含める
        for stage, stats in self._stats.items():
            if stage not in result:
                result[stage] = stats.to_dict()
        result["total"] = self._total_stats.to_dict()
        return result

    def get_last_cycle(self) -> CycleRecord | None:
        """直近のサイクル記録を返す"""
        return self._history[-1] if self._history else None

    def get_history(self) -> list[CycleRecord]:
        """全サイクル履歴を返す"""
        return list(self._history)

    def format_cycle(self, record: CycleRecord | None = None) -> str:
        """サイクル記録を読みやすい文字列に変換"""
        if record is None:
            record = self.get_last_cycle()
        if record is None:
            return "[Latency] データなし"

        parts = []
        for stage in self.STAGE_ORDER:
            if stage in record.stages:
                parts.append(f"{stage}={record.stages[stage]:.2f}s")
        # カスタムステージ
        for stage, dur in record.stages.items():
            if stage not in self.STAGE_ORDER:
                parts.append(f"{stage}={dur:.2f}s")

        parts.append(f"合計={record.total_sec:.2f}s")
        return "[Latency] " + " ".join(parts)

    def format_stats(self) -> str:
        """統計情報を読みやすい文字列に変換"""
        stats = self.get_stats()
        if not stats:
            return "[Latency Stats] データなし"

        lines = ["[Latency Stats]"]
        for stage_name, s in stats.items():
            lines.append(
                f"  {s['name']:>10}: avg={s['avg_sec']:.3f}s "
                f"min={s['min_sec']:.3f}s max={s['max_sec']:.3f}s "
                f"(n={s['count']})"
            )
        return "\n".join(lines)

    def reset(self) -> None:
        """全データをリセット"""
        self._stage_starts.clear()
        self._current_cycle.clear()
        self._history.clear()
        self._stats.clear()
        self._total_stats = StageStats(name="total")


if __name__ == "__main__":
    # テスト
    tracker = LatencyTracker()

    # 3サイクル分のダミーデータ
    for i in range(3):
        tracker.start("asr")
        time.sleep(0.1)
        tracker.stop("asr")

        tracker.start("translate")
        time.sleep(0.05)
        tracker.stop("translate")

        tracker.start("tts")
        time.sleep(0.08)
        tracker.stop("tts")

        record = tracker.record_cycle(extra_latency=4.0)
        print(tracker.format_cycle(record))

    print()
    print(tracker.format_stats())
