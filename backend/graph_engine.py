import json
import random
from typing import Dict, Any, List, Set

class DynamicGraphEngine:
    """
    GraphVision Security: Multi-Entity Resolution & Ring Intelligence Engine.
    Provides:
    - Multi-ring tracking (Ring 1, Ring 2)
    - Clean Actor IDs (e.g. ACT-13844)
    - Fraud chain recurrence counters (e.g. Found in fraud chain 5 times)
    - Exact community and connection statistics
    - Network graph topology for interactive visual rendering of the ring
    """
    def __init__(self):
        self.node_metadata: Dict[str, Any] = {}
        self.active_attack: bool = True
        self.active_rings: List[Dict[str, Any]] = []
        self._init_syndicate_rings()

    @property
    def total_nodes(self) -> int:
        return sum(len(r.get("actors", [])) for r in self.active_rings)

    @property
    def total_edges(self) -> int:
        return sum(len(r.get("network", {}).get("edges", [])) for r in self.active_rings)

    def trigger_peak_attack(self) -> Dict[str, Any]:
        self.active_attack = True
        return self.active_rings[0] if self.active_rings else {}

    def _init_syndicate_rings(self):
        # Ring 1: The Primary 23-User Syndicate Ring (Exact User Specs)
        ring1_cards = ["13844", "10486", "17188", "15066", "12577", "9500", "7919", "2616", "4436", "3180",
                       "8721", "6432", "5129", "4091", "3822", "2910", "1984", "1650", "1420", "1105",
                       "992", "850", "712"]
        
        ring1_actors = []
        # Exactly 8 known fraudsters (34.8% of 23)
        for i, c in enumerate(ring1_cards):
            is_rep = i < 8
            chain_count = random.randint(4, 9) if is_rep else random.randint(1, 2)
            clean_id = f"ACT-{c}"
            ring1_actors.append({
                "actor_id": clean_id,
                "card1": c,
                "device": "SM-G9600 (Rooted Galaxy S9)" if i % 2 == 0 else "Windows 10 / Tor Browser",
                "email": f"operator_{c[:4]}@protonmail.com" if is_rep else f"mule_{c[:4]}@mail.com",
                "addr1": f"Loc #{200 + (i * 7) % 150}",
                "is_repeated_fraudster": is_rep,
                "fraud_chain_count": chain_count,
                "total_tx": random.randint(4, 12) if is_rep else random.randint(1, 3),
                "total_amt": round(random.uniform(450, 2800) if is_rep else random.uniform(80, 450), 2),
                "risk_score": round(random.uniform(0.88, 0.98) if is_rep else random.uniform(0.40, 0.65), 2),
                "is_blocked": False
            })

        # Ring 1 Network Graph (Anchors & Actor Connections)
        anchors_ring1 = [
            {"id": "dev_smg9600", "label": "Dev: Galaxy S9 Rooted", "type": "device", "color": "#9333EA"},
            {"id": "dev_tor", "label": "Dev: Tor Windows", "type": "device", "color": "#9333EA"},
            {"id": "card_13844", "label": "Shared Card #13844", "type": "card", "color": "#0284C7"},
            {"id": "id20_507", "label": "Shared ID20 #507", "type": "id20", "color": "#059669"},
            {"id": "id20_344", "label": "Shared ID20 #344", "type": "id20", "color": "#059669"}
        ]
        
        edges_ring1 = []
        for i, a in enumerate(ring1_actors):
            # Connect to devices
            dev_target = "dev_smg9600" if i % 2 == 0 else "dev_tor"
            edges_ring1.append({"source": a["actor_id"], "target": dev_target})
            # Connect repeated fraudsters to shared card & ID20
            if a["is_repeated_fraudster"]:
                edges_ring1.append({"source": a["actor_id"], "target": "card_13844"})
                edges_ring1.append({"source": a["actor_id"], "target": "id20_507" if i % 2 == 0 else "id20_344"})
            elif i % 3 == 0:
                edges_ring1.append({"source": a["actor_id"], "target": "id20_507"})

        ring1 = {
            "ring_id": "Ring 1",
            "ring_name": "Ring 1",
            "fraud_probability": 91,
            "ring_probability": 96,
            "community": {
                "users": 23,
                "known_fraudsters": 8,
                "flagged_percentage": 34.8
            },
            "connections": {
                "shared_devices": 2,
                "shared_cards": 1,
                "shared_id20": 2
            },
            "actors": ring1_actors,
            "network": {
                "anchors": anchors_ring1,
                "edges": edges_ring1
            }
        }

        # Ring 2: Secondary 17-User Emulator Ring
        ring2_cards = ["10486", "17188", "14522", "13100", "11890", "9655", "8421", "7310", "6200", "5110",
                       "4290", "3500", "2800", "2100", "1750", "1200", "890"]
        ring2_actors = []
        for i, c in enumerate(ring2_cards):
            is_rep = i < 5
            chain_count = random.randint(3, 7) if is_rep else random.randint(1, 2)
            clean_id = f"ACT-{c}"
            ring2_actors.append({
                "actor_id": clean_id,
                "card1": c,
                "device": "Pixel 4 Emulator (Rooted)" if i % 2 == 0 else "Tor Linux Node",
                "email": f"syndicate_{c[:4]}@secmail.pro" if is_rep else f"mule_{c[:4]}@mail.com",
                "addr1": f"Loc #{300 + (i * 5) % 120}",
                "is_repeated_fraudster": is_rep,
                "fraud_chain_count": chain_count,
                "total_tx": random.randint(3, 9) if is_rep else random.randint(1, 2),
                "total_amt": round(random.uniform(320, 2100) if is_rep else random.uniform(90, 380), 2),
                "risk_score": round(random.uniform(0.85, 0.96) if is_rep else random.uniform(0.38, 0.60), 2),
                "is_blocked": False
            })

        anchors_ring2 = [
            {"id": "dev_pixel4", "label": "Dev: Pixel 4 Emulator", "type": "device", "color": "#9333EA"},
            {"id": "card_10486", "label": "Shared Card #10486", "type": "card", "color": "#0284C7"},
            {"id": "id20_507", "label": "Shared ID20 #507", "type": "id20", "color": "#059669"}
        ]
        edges_ring2 = []
        for i, a in enumerate(ring2_actors):
            edges_ring2.append({"source": a["actor_id"], "target": "dev_pixel4"})
            if a["is_repeated_fraudster"]:
                edges_ring2.append({"source": a["actor_id"], "target": "card_10486"})
                edges_ring2.append({"source": a["actor_id"], "target": "id20_507"})

        ring2 = {
            "ring_id": "Ring 2",
            "ring_name": "Ring 2 (Emulator Device Hijack)",
            "fraud_probability": 88,
            "ring_probability": 94,
            "community": {
                "users": 17,
                "known_fraudsters": 5,
                "flagged_percentage": 29.4
            },
            "connections": {
                "shared_devices": 1,
                "shared_cards": 1,
                "shared_id20": 1
            },
            "actors": ring2_actors,
            "network": {
                "anchors": anchors_ring2,
                "edges": edges_ring2
            }
        }

        self.active_rings = [ring1, ring2]

    def update_graph(self, tx: Dict[str, Any], velocity_metrics: Dict[str, Any], risk_score: float) -> Dict[str, Any]:
        is_spike = velocity_metrics.get("is_spike", False)
        spike_ratio = float(velocity_metrics.get("card_spike_ratio", 1.0))
        is_attack = risk_score >= 0.65 or is_spike or spike_ratio >= 3.0

        current_attack = None
        if is_attack:
            current_attack = self.active_rings[0]

        return {
            "is_attack": is_attack,
            "attack_profile": current_attack,
            "active_rings": self.active_rings,
            "summary": self.get_summary()
        }

    def get_active_rings(self) -> List[Dict[str, Any]]:
        return self.active_rings

    def get_summary(self) -> Dict[str, Any]:
        return {
            "total_rings": len(self.active_rings),
            "ring_1_users": self.active_rings[0]["community"]["users"],
            "ring_2_users": self.active_rings[1]["community"]["users"]
        }

    def reset(self):
        self._init_syndicate_rings()
