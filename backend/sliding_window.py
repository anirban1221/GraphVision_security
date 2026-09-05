from collections import defaultdict, deque
from typing import Dict, Any, Tuple
from backend.config import WINDOW_5M, WINDOW_30M, WINDOW_24H, SPIKE_RATIO_ALERT

class SlidingWindowManager:
    """
    Real-time rolling temporal window manager.
    Tracks card and device activity across 5m, 30m, and 24h spans.
    Computes exact burst velocity counters and spike ratios without latency.
    """
    def __init__(self, window_5m: int = WINDOW_5M, window_30m: int = WINDOW_30M, window_24h: int = WINDOW_24H):
        self.window_5m = window_5m
        self.window_30m = window_30m
        self.window_24h = window_24h

        # Card history: card1 -> deque of timestamps (float/int)
        self.card_history: Dict[int, deque] = defaultdict(deque)

        # Device history: device_clean -> deque of timestamps
        self.device_history: Dict[str, deque] = defaultdict(deque)

        # Global timeline stream for frontend chart: deque of (dt_sec, is_spike, risk_score)
        self.global_timeline: deque = deque(maxlen=200)

    def set_window_spans(self, window_5m: int, window_30m: int, window_24h: int):
        self.window_5m = window_5m
        self.window_30m = window_30m
        self.window_24h = window_24h

    def process_transaction(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ingests a single transaction and returns updated velocity metrics.
        """
        current_dt = float(tx.get("TransactionDT", 0))
        card_id = tx.get("card1")
        device_id = str(tx.get("DeviceInfo", "__UNKNOWN__")).strip()

        # Clean card key
        try:
            card_key = int(card_id) if card_id is not None and str(card_id).replace('.','',1).isdigit() else -1
        except Exception:
            card_key = -1

        # 1. Update & Prune Card History (24-hour retention)
        card_q = self.card_history[card_key]
        cutoff_24h = current_dt - self.window_24h
        while card_q and card_q[0] < cutoff_24h:
            card_q.popleft()

        # Count events prior to current transaction
        cutoff_5m = current_dt - self.window_5m
        v_5m = sum(1 for t in card_q if t >= cutoff_5m)
        v_24h = len(card_q)

        # Append current event
        card_q.append(current_dt)

        # 2. Update & Prune Device History (30-minute retention)
        v_dev_30m = 0
        if device_id and device_id != "__UNKNOWN__" and device_id != "nan":
            dev_q = self.device_history[device_id]
            cutoff_30m = current_dt - self.window_30m
            while dev_q and dev_q[0] < cutoff_30m:
                dev_q.popleft()
            v_dev_30m = len(dev_q)
            dev_q.append(current_dt)

        # 3. Compute Spike Ratio (5m burst vs 24h baseline expected 5m rate)
        # 24 hours has 288 5-minute intervals
        baseline_rate = (v_24h / 288.0)
        card_spike_ratio = (v_5m + 1.0) / (baseline_rate + 1.0)

        # Flag Spike criteria:
        # A) High spike ratio with at least 2 attempts in 5m
        # B) Rapid card cycling burst (>= 3 attempts in 5m)
        is_spike = bool((card_spike_ratio >= SPIKE_RATIO_ALERT and v_5m >= 2) or (v_5m >= 3))

        metrics = {
            "card_velocity_5m": int(v_5m),
            "card_velocity_24h": int(v_24h),
            "device_velocity_30m": int(v_dev_30m),
            "card_spike_ratio": round(float(card_spike_ratio), 2),
            "is_spike": is_spike,
            "window_span_sec": self.window_5m
        }

        return metrics

    def record_timeline_point(self, dt: float, is_spike: bool, risk_score: float, tx_id: int):
        self.global_timeline.append({
            "timestamp": dt,
            "tx_id": tx_id,
            "is_spike": is_spike,
            "risk_score": round(risk_score, 3)
        })

    def get_timeline(self):
        return list(self.global_timeline)

    def reset(self):
        self.card_history.clear()
        self.device_history.clear()
        self.global_timeline.clear()

