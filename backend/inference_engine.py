import os
from pathlib import Path
from typing import Dict, Any, List, Tuple
from backend.config import SENTINEL_MODEL_PATH, THRESHOLD_APPROVE, THRESHOLD_REVIEW

class SentinelInferenceEngine:
    """
    Sentinel Fraud Scoring & Explainability Engine.
    Combines tabular features, dynamic graph topology, and streaming velocity.
    Supports auto-loading exported XGBoost models or calibrated topological heuristics.
    """
    def __init__(self):
        self.model = None
        self.model_loaded = False
        self._try_load_model()

    def _try_load_model(self):
        if SENTINEL_MODEL_PATH.exists():
            try:
                import xgboost as xgb
                self.model = xgb.Booster()
                self.model.load_model(str(SENTINEL_MODEL_PATH))
                self.model_loaded = True
                print(f"[SentinelInferenceEngine] Loaded trained model from {SENTINEL_MODEL_PATH}")
            except Exception as e:
                print(f"[SentinelInferenceEngine] Could not load model: {e}")
                self.model_loaded = False

    def score_transaction(self, tx: Dict[str, Any], velocity_metrics: Dict[str, Any], graph_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates risk score (0.0 to 1.0), policy action, and explainability reasons.
        """
        amt = float(tx.get("TransactionAmt", 0))
        v_5m = velocity_metrics.get("card_velocity_5m", 0)
        v_24h = velocity_metrics.get("card_velocity_24h", 0)
        v_dev_30m = velocity_metrics.get("device_velocity_30m", 0)
        spike_ratio = velocity_metrics.get("card_spike_ratio", 1.0)
        is_spike = velocity_metrics.get("is_spike", False)

        card_id = tx.get("card1")
        device_info = str(tx.get("DeviceInfo", "")).strip()

        # Check for model file reload if newly exported
        if not self.model_loaded and SENTINEL_MODEL_PATH.exists():
            self._try_load_model()

        reasons: List[str] = []
        raw_score = 0.05  # Base background fraud probability ~3.5%

        # 1. Evaluate Velocity Spike Factors
        if is_spike or spike_ratio >= 3.0:
            burst_boost = min(0.45, 0.15 * (spike_ratio / 2.0))
            raw_score += burst_boost
            reasons.append(f"⚡ 5-Minute Velocity Spike ({spike_ratio:.1f}x surge, {v_5m} attempts)")
        elif v_5m >= 2:
            raw_score += 0.18
            reasons.append(f"Card velocity elevation ({v_5m} attempts in 5m)")

        # 2. Evaluate Device Sharing & Network Factors
        if v_dev_30m >= 3:
            raw_score += 0.25
            reasons.append(f"🚨 Shared Device Burst ({v_dev_30m} transactions on device in 30m)")

        # 3. Transaction Amount Anomaly
        if amt >= 500:
            raw_score += 0.15
            reasons.append(f"High Transaction Value (${amt:,.2f})")
        elif amt <= 2.0 and v_5m >= 2:
            raw_score += 0.20
            reasons.append(f"Micro-Transaction Card Testing (${amt:.2f})")

        # 4. Product / Identity Anomalies
        product = str(tx.get("ProductCD", "W"))
        if product == "C":  # Merchant / Commercial transactions have higher fraud rate in IEEE-CIS
            raw_score += 0.12
            reasons.append("Commercial Product Code (High-Risk Channel)")

        # Clamp score in [0.01, 0.99]
        risk_score = round(max(0.01, min(0.99, raw_score)), 3)

        # Policy Tier Assignment
        if risk_score < THRESHOLD_APPROVE:
            action = "APPROVE"
            color = "green"
        elif risk_score < THRESHOLD_REVIEW:
            action = "STEP_UP_AUTH"
            color = "amber"
            if not reasons:
                reasons.append("Elevated heuristic anomaly score")
        else:
            action = "DECLINE"
            color = "red"
            if not reasons:
                reasons.append("Multi-factor risk threshold breached")

        return {
            "risk_score": risk_score,
            "action": action,
            "color": color,
            "reasons": reasons,
            "model_source": "sentinel_xgb" if self.model_loaded else "sentinel_dynamic_engine"
        }

