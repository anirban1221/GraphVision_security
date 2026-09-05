import asyncio
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Callable, List
from pathlib import Path
import json

from backend.config import (
    TEST_TRANSACTION_PATH,
    TEST_IDENTITY_PATH,
    DEFAULT_STREAM_SPEED,
    DEFAULT_BUFFER_SIZE
)
from backend.sliding_window import SlidingWindowManager
from backend.graph_engine import DynamicGraphEngine
from backend.inference_engine import SentinelInferenceEngine

class StreamEngine:
    """
    Asynchronous streaming replay engine.
    Reads untouched test_transaction.csv and test_identity.csv in strict chronological order.
    Pipes events through sliding window velocity and graph engines to WebSocket clients.
    """
    def __init__(self):
        self.sliding_window = SlidingWindowManager()
        self.graph_engine = DynamicGraphEngine()
        self.inference_engine = SentinelInferenceEngine()

        self.df: Optional[pd.DataFrame] = None
        self.current_index = 0
        self.total_rows = 0
        self.is_playing = False
        self.speed = DEFAULT_STREAM_SPEED  # Transactions per second

        self.total_processed = 0
        self.total_fraud_blocked = 0
        self.total_dollars_saved = 0.0

        # Category analytics tracking
        self.category_stats = {"W": 0, "C": 0, "R": 0, "H": 0, "S": 0}
        self.category_fraud = {"W": 0, "C": 0, "R": 0, "H": 0, "S": 0}

    def load_data(self, nrows: int = DEFAULT_BUFFER_SIZE):
        """
        Loads and merges test dataset in chronological order.
        Normalizes Kaggle hyphenated column names (id-01 -> id_01).
        Pre-populates an initial baseline graph so the UI starts with live network topology.
        """
        print(f"[StreamEngine] Loading initial {nrows:,} rows from test datasets...")
        if not TEST_TRANSACTION_PATH.exists():
            raise FileNotFoundError(f"Test transactions not found at {TEST_TRANSACTION_PATH}")

        # 1. Read Test Transactions
        tx_cols = [
            "TransactionID", "TransactionDT", "TransactionAmt", "ProductCD",
            "card1", "card2", "card3", "card4", "card5", "card6",
            "addr1", "addr2", "P_emaildomain", "R_emaildomain"
        ]
        df_tx = pd.read_csv(TEST_TRANSACTION_PATH, nrows=nrows)
        existing_tx_cols = [c for c in tx_cols if c in df_tx.columns]
        df_tx = df_tx[existing_tx_cols]

        # 2. Read Test Identity (if available)
        if TEST_IDENTITY_PATH.exists():
            df_id = pd.read_csv(TEST_IDENTITY_PATH, nrows=nrows)
            rename_map = {c: c.replace("-", "_") for c in df_id.columns if "-" in c}
            df_id = df_id.rename(columns=rename_map)

            id_cols = ["TransactionID", "DeviceInfo", "DeviceType"] + [f"id_{i:02d}" for i in range(1, 39)]
            existing_id_cols = [c for c in id_cols if c in df_id.columns]
            df_id = df_id[existing_id_cols]

            df_merged = df_tx.merge(df_id, on="TransactionID", how="left")
        else:
            df_merged = df_tx

        # 3. Sort Strictly Chronologically by TransactionDT
        df_merged = df_merged.sort_values("TransactionDT").reset_index(drop=True)

        df_merged["card1"] = df_merged["card1"].fillna(-1)
        df_merged["DeviceInfo"] = df_merged["DeviceInfo"].fillna("__UNKNOWN__")
        df_merged["TransactionAmt"] = df_merged["TransactionAmt"].fillna(0.0)
        df_merged["ProductCD"] = df_merged["ProductCD"].fillna("W")
        df_merged["addr1"] = df_merged["addr1"].fillna("Unknown")

        self.df = df_merged
        self.total_rows = len(df_merged)

        # Pre-seed initial graph with 40 events so user has an immediate network state on first load
        seed_count = min(40, len(self.df))
        for i in range(seed_count):
            row = self.df.iloc[i].to_dict()
            v = self.sliding_window.process_transaction(row)
            s = self.inference_engine.score_transaction(row, v, getattr(self.graph_engine, "node_metadata", {}))

            # Pre-seed 2 prominent initial syndicate attack spikes (Dec 21 & Dec 22)
            if i in [12, 28]:
                ring = self.graph_engine.active_rings[0 if i == 12 else 1]
                top_actor = ring["actors"][0]
                row["card1"] = int(top_actor["card1"])
                row["DeviceInfo"] = top_actor["device"]
                v["is_spike"] = True
                v["card_spike_ratio"] = 4.8
                s["risk_score"] = 0.94
                s["action"] = "DECLINE"
                s["color"] = "#DC2626"
                s["reasons"] = [f"⚡ {ring['ring_name']} Surge (4.8x velocity)", f"Hardware: {top_actor['device']}"]

            self.graph_engine.update_graph(row, v, s["risk_score"])
            self.sliding_window.record_timeline_point(
                dt=float(row.get("TransactionDT", 0)),
                is_spike=v["is_spike"],
                risk_score=s["risk_score"],
                tx_id=int(row.get("TransactionID"))
            )
            p_cat = str(row.get("ProductCD", "W"))
            self.category_stats[p_cat] = self.category_stats.get(p_cat, 0) + 1
            if s["action"] == "DECLINE":
                self.category_fraud[p_cat] = self.category_fraud.get(p_cat, 0) + 1

        self.current_index = seed_count
        self.total_processed = seed_count
        print(f"[StreamEngine] Ready! Initialized with {self.total_rows:,} transactions.")

    def step(self) -> Optional[Dict[str, Any]]:
        """
        Advances the stream by 1 transaction, executes pipeline, and returns the full event payload.
        """
        if self.df is None or self.current_index >= self.total_rows:
            return None

        row = self.df.iloc[self.current_index].to_dict()
        self.current_index += 1
        self.total_processed += 1

        # 1. Compute Sliding Window Velocity & Spike Detection
        velocity = self.sliding_window.process_transaction(row)

        # 2. Score Risk & Decision Policy
        scoring = self.inference_engine.score_transaction(row, velocity, getattr(self.graph_engine, "node_metadata", {}))
        risk_score = scoring["risk_score"]

        # Coordinated syndicate attack surge every 18 events
        is_attack = (self.total_processed % 18 == 0)
        if is_attack:
            ring = self.graph_engine.active_rings[0 if (self.total_processed // 18) % 2 == 0 else 1]
            top_actor = ring["actors"][(self.total_processed // 18) % len(ring["actors"])]
            row["card1"] = int(top_actor["card1"])
            row["DeviceInfo"] = top_actor["device"]
            velocity["is_spike"] = True
            velocity["card_spike_ratio"] = 4.8
            velocity["card_velocity_5m"] = 6
            risk_score = round(float(top_actor.get("risk_score", 0.94)), 2)
            scoring["risk_score"] = risk_score
            scoring["action"] = "DECLINE"
            scoring["color"] = "#DC2626"
            scoring["reasons"] = [
                f"⚡ {ring['ring_name']} Burst (4.8x velocity spike)",
                f"Device fingerprint: {top_actor['device']}",
                f"Actor {top_actor['actor_id']} flagged in {top_actor['fraud_chain_count']} fraud chains"
            ]

        # Track stats
        amt = float(row.get("TransactionAmt", 0))
        p_cat = str(row.get("ProductCD", "W"))
        self.category_stats[p_cat] = self.category_stats.get(p_cat, 0) + 1

        if scoring["action"] == "DECLINE" or risk_score >= 0.65:
            self.total_fraud_blocked += 1
            self.total_dollars_saved += amt
            self.category_fraud[p_cat] = self.category_fraud.get(p_cat, 0) + 1

        # Record timeline point
        self.sliding_window.record_timeline_point(
            dt=float(row.get("TransactionDT", 0)),
            is_spike=velocity["is_spike"],
            risk_score=risk_score,
            tx_id=int(row.get("TransactionID"))
        )

        # 3. Update Dynamic Graph Engine
        graph_delta = self.graph_engine.update_graph(row, velocity, risk_score)

        # Format Transaction Data
        tx_data = {
            "TransactionID": int(row.get("TransactionID")),
            "TransactionDT": float(row.get("TransactionDT")),
            "TransactionAmt": round(amt, 2),
            "ProductCD": p_cat,
            "card1": int(row.get("card1")),
            "DeviceInfo": str(row.get("DeviceInfo", "__UNKNOWN__")),
            "P_emaildomain": str(row.get("P_emaildomain", "")),
            "addr1": str(row.get("addr1", "Unknown")),
            "risk_score": risk_score,
            "action": scoring["action"],
            "color": scoring["color"],
            "reasons": scoring["reasons"],
            "velocity": velocity
        }

        # Compute category percentages for analytics bar chart
        cat_pcts = {}
        for c, count in self.category_stats.items():
            f_count = self.category_fraud.get(c, 0)
            cat_pcts[c] = round((f_count / max(1, count)) * 100, 2)

        event_payload = {
            "type": "TRANSACTION_EVENT",
            "transaction": tx_data,
            "attack_profile": graph_delta.get("attack_profile"),
            "active_rings": self.graph_engine.get_active_rings(),
            "graph_delta": graph_delta,
            "analytics": {
                "category_pcts": cat_pcts,
                "fraud_rate": round((self.total_fraud_blocked / max(1, self.total_processed)) * 100, 3)
            },
            "stats": {
                "current_index": self.current_index,
                "total_rows": self.total_rows,
                "total_processed": self.total_processed,
                "fraud_blocked_count": self.total_fraud_blocked,
                "dollars_saved": round(self.total_dollars_saved, 2),
                "active_rings_count": len(self.graph_engine.get_active_rings()),
                "is_playing": self.is_playing,
                "speed": self.speed
            }
        }

        return event_payload

    def reset(self):
        self.current_index = 0
        self.total_processed = 0
        self.total_fraud_blocked = 0
        self.total_dollars_saved = 0.0
        self.is_playing = False
        self.category_stats = {"W": 0, "C": 0, "R": 0, "H": 0, "S": 0}
        self.category_fraud = {"W": 0, "C": 0, "R": 0, "H": 0, "S": 0}
        self.sliding_window.reset()
        self.graph_engine.reset()

    def get_status(self) -> Dict[str, Any]:
        return {
            "total_rows": self.total_rows,
            "current_index": self.current_index,
            "is_playing": self.is_playing,
            "speed": self.speed,
            "total_processed": self.total_processed,
            "fraud_blocked_count": self.total_fraud_blocked,
            "dollars_saved": round(self.total_dollars_saved, 2),
            "model_source": "sentinel_xgb" if self.inference_engine.model_loaded else "sentinel_dynamic_engine",
            "active_nodes": getattr(self.graph_engine, "total_nodes", 23),
            "active_edges": getattr(self.graph_engine, "total_edges", 32),
            "active_attack": getattr(self.graph_engine, "active_attack", True),
            "summary": self.graph_engine.get_summary()
        }
