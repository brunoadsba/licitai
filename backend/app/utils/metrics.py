"""
Métricas in-memory (piloto single-process).

Contadores e gauges simples; não substitui OpenTelemetry/Prometheus em produção.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class MetricsRegistry:
    _lock: threading.Lock = field(default_factory=threading.Lock)
    counters: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    gauges: dict[str, float] = field(default_factory=dict)
    # analysis_duration: soma e count para média
    _duration_sum: float = 0.0
    _duration_count: int = 0
    started_at: float = field(default_factory=time.time)

    def inc(self, name: str, value: float = 1.0) -> None:
        with self._lock:
            self.counters[name] += value

    def set_gauge(self, name: str, value: float) -> None:
        with self._lock:
            self.gauges[name] = value

    def observe_analysis_duration(self, seconds: float) -> None:
        with self._lock:
            self._duration_sum += max(0.0, seconds)
            self._duration_count += 1
            self.counters["analysis_completed"] += 1

    def snapshot(self) -> dict:
        with self._lock:
            avg = (
                self._duration_sum / self._duration_count
                if self._duration_count
                else 0.0
            )
            return {
                "uptime_seconds": round(time.time() - self.started_at, 1),
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "analysis_duration_avg_seconds": round(avg, 3),
                "analysis_duration_count": self._duration_count,
            }


metrics = MetricsRegistry()
