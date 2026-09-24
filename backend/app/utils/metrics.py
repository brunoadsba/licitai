"""
Métricas in-memory (piloto single-process).

Contadores e gauges simples; não substitui OpenTelemetry/Prometheus em produção.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field


@dataclass
class MetricsRegistry:
    counters: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    gauges: dict[str, float] = field(default_factory=dict)
    # analysis_duration: soma e count para média
    _duration_sum: float = 0.0
    _duration_count: int = 0
    _latencies_ms: deque[float] = field(default_factory=lambda: deque(maxlen=500))
    _cost_usd: float = 0.0
    started_at: float = field(default_factory=time.time)

    def inc(self, name: str, value: float = 1.0) -> None:
        self.counters[name] += value

    def set_gauge(self, name: str, value: float) -> None:
        self.gauges[name] = value

    def observe_analysis_duration(self, seconds: float) -> None:
        self._duration_sum += max(0.0, seconds)
        self._duration_count += 1
        self.counters["analysis_completed"] += 1
        self.observe_latency_ms(seconds * 1000)

    def observe_latency_ms(self, milliseconds: float) -> None:
        self._latencies_ms.append(max(0.0, milliseconds))

    def add_cost_usd(self, value: float) -> None:
        self._cost_usd += max(0.0, value)
        self.counters["cost_usd"] += max(0.0, value)

    def _percentile(self, pct: float) -> float:
        if not self._latencies_ms:
            return 0.0
        ordered = sorted(self._latencies_ms)
        idx = min(len(ordered) - 1, max(0, int(round((pct / 100) * (len(ordered) - 1)))))
        return ordered[idx]

    def snapshot(self) -> dict:
        avg = (
            self._duration_sum / self._duration_count
            if self._duration_count
            else 0.0
        )
        counters = dict(self.counters)
        for key in (
            "llm_errors",
            "job_errors",
            "analysis_completed",
            "review_approved",
            "review_rejected",
            "review_adjusted",
        ):
            counters.setdefault(key, 0.0)
        return {
            "uptime_seconds": round(time.time() - self.started_at, 1),
            "counters": counters,
            "gauges": dict(self.gauges),
            "analysis_duration_avg_seconds": round(avg, 3),
            "analysis_duration_count": self._duration_count,
            "latency_ms_p50": round(self._percentile(50), 1),
            "latency_ms_p95": round(self._percentile(95), 1),
            "cost_usd": round(self._cost_usd, 6),
        }


metrics = MetricsRegistry()
