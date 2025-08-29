import os
from typing import Optional, Tuple


ML_MODE = os.environ.get("ML_MODE", "HYBRID").upper() # RULES_ONLY | HYBRID | ML_ONLY
ML_THRESHOLD = float(os.environ.get("ML_THRESHOLD", "0.75"))

class HybridDecider:
    def __init__(self, threshold: float = ML_THRESHOLD, mode: str = ML_MODE):
        self.threshold = threshold
        self.mode = mode

    def decide(self, rules_label: Optional[str], ml_label: Optional[str], ml_conf: float) -> Tuple[str, str]:
        """Return (final_label, source). source in {rules, ml, rules_low_conf}.
        In HYBRID: if ML >= threshold -> ML; else fall back to rules.
        In ML_ONLY: always ML.
        In RULES_ONLY: always rules.
        """

        mode = self.mode
        if mode == "ML_ONLY":
            return (ml_label or rules_label or "Unknown"), "ml"
        if mode == "RULES_ONLY":
            return (rules_label or ml_label or "Unknown"), "rules"
        # HYBRID
        if ml_label and ml_conf >= self.threshold:
            return ml_label, "ml"
        if rules_label:
            return rules_label, "rules_low_conf" if ml_label else "rules"
        return (ml_label or "Unknown"), "ml"