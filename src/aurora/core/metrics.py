"""Lightweight metrics collection framework."""

import time
from contextlib import contextmanager
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Generator, List

from pydantic import BaseModel, ConfigDict, Field


class MetricType(str, Enum):
    """Types of metrics collected."""
    COUNTER = "COUNTER"
    GAUGE = "GAUGE"
    HISTOGRAM = "HISTOGRAM"
    TIMER = "TIMER"


class MetricSnapshot(BaseModel):
    """An immutable, point-in-time report of captured system metrics."""
    model_config = ConfigDict(frozen=True)

    generated_at: datetime
    counters: Dict[str, int] = Field(default_factory=dict)
    gauges: Dict[str, float] = Field(default_factory=dict)
    timers: Dict[str, List[float]] = Field(default_factory=dict)

    @property
    def files_loaded(self) -> int:
        """Helper to get files loaded count."""
        return self.counters.get("files_loaded", 0)

    @property
    def bytes_read(self) -> int:
        """Helper to get total bytes read."""
        return self.counters.get("bytes_read", 0)

    @property
    def failures(self) -> int:
        """Helper to get total failures."""
        return self.counters.get("failures", 0)

    @property
    def skipped_files(self) -> int:
        """Helper to get skipped files."""
        return self.counters.get("skipped_files", 0)

    @property
    def average_load_time(self) -> float:
        """Helper to compute average timing metric."""
        times = self.timers.get("document_load_time", [])
        if not times:
            return 0.0
        return sum(times) / len(times)


class MetricsCollector:
    """Core metrics collector for in-memory logging and analytics."""

    def __init__(self) -> None:
        self._counters: Dict[str, int] = {}
        self._gauges: Dict[str, float] = {}
        self._timers: Dict[str, List[float]] = {}

    def increment(self, name: str, value: int = 1) -> None:
        """Increment a counter metric."""
        self._counters[name] = self._counters.get(name, 0) + value

    def set_gauge(self, name: str, value: float) -> None:
        """Set a gauge metric value."""
        self._gauges[name] = value

    def record_time(self, name: str, duration: float) -> None:
        """Append timing value to timer metric."""
        if name not in self._timers:
            self._timers[name] = []
        self._timers[name].append(duration)

    @contextmanager
    def time_block(self, name: str) -> Generator[None, None, None]:
        """Context manager to measure and record block execution times."""
        start_time = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start_time
            self.record_time(name, duration)

    def reset(self) -> None:
        """Reset all metrics."""
        self._counters.clear()
        self._gauges.clear()
        self._timers.clear()

    def emit_snapshot(self) -> MetricSnapshot:
        """Compile and emit an immutable snapshot of all metrics."""
        return MetricSnapshot(
            generated_at=datetime.now(timezone.utc),
            counters=dict(self._counters),
            gauges=dict(self._gauges),
            timers={k: list(v) for k, v in self._timers.items()},
        )
