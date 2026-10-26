import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("resq_ai.knowledge")


class EmergencyKnowledgeService:
    """Provides grounded retrieval of verified emergency Standard Operating Procedures (SOPs).
    Ensures multi-agent decisions are anchored in real safety protocols.
    """

    def __init__(self, sops_path: Optional[str] = None):
        if sops_path is None:
            sops_path = str(Path(__file__).parent / "emergency_sops.json")
        self.sops_path = Path(sops_path)
        self.sops: List[Dict[str, Any]] = []
        self._load_sops()

    def _load_sops(self) -> None:
        if self.sops_path.exists():
            try:
                with open(self.sops_path, "r", encoding="utf-8") as f:
                    self.sops = json.load(f)
            except Exception as exc:
                logger.error(f"Failed to load emergency SOPs: {exc}")
                self.sops = []

    def query_sops(self, incident_type: str, query_text: str = "") -> List[Dict[str, Any]]:
        """Finds matching verified SOPs by incident type and keyword relevance."""
        results = []
        type_norm = incident_type.lower()
        query_norm = query_text.lower()

        for sop in self.sops:
            sop_hazard = sop.get("hazard_type", "").lower()
            sop_title = sop.get("title", "").lower()

            match_score = 0
            if sop_hazard in type_norm or type_norm in sop_hazard:
                match_score += 10
            if any(term in query_norm for term in [sop_hazard, sop_title]):
                match_score += 5

            if match_score > 0:
                results.append((match_score, sop))

        results.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in results] if results else self.sops[:2]


# Global singleton
knowledge_service = EmergencyKnowledgeService()
