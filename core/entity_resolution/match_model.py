from typing import Dict, Any
from core.entity_resolution.confidence_scorer import score_match, explain_match

class MatchModel:
    """Interface for entity resolution matching models."""
    def predict(self, record_a: dict, record_b: dict) -> Dict[str, Any]:
        raise NotImplementedError

class RuleBasedMatchModel(MatchModel):
    """Deterministic matching abstraction / future ML interface"""
    
    def __init__(self):
        pass
        
    def predict(self, record_a: dict, record_b: dict) -> Dict[str, Any]:
        """Predicts the match deterministically."""
        if not record_a or not record_b:
            return {
                "decision": "REJECTED",
                "confidence": 0.0,
                "reasons": [],
                "risk_level": "Low Risk",
                "merge_reason": "Invalid input"
            }
            
        explanation = explain_match(record_a, record_b)
        
        return {
            "decision": explanation["decision"],
            "confidence": explanation.get("confidence", 0.0),
            "reasons": explanation["reasons"],
            "risk_level": explanation["risk_level"],
            "merge_reason": explanation["merge_reason"]
        }