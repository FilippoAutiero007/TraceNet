from pydantic import BaseModel
from typing import List

class CableRule(BaseModel):
    endA: str  # categoria device
    endB: str
    cable: str  # "straight", "cross", "serial"

# Tabella delle regole cavi
CABLE_RULES: List[CableRule] = [
    CableRule(endA="pc", endB="switch", cable="straight"),
    CableRule(endA="router", endB="switch", cable="straight"),
    CableRule(endA="switch", endB="switch", cable="cross"),
    CableRule(endA="pc", endB="pc", cable="cross"),
    CableRule(endA="router", endB="router", cable="serial"),
]

def get_cable_type(categoryA: str, categoryB: str) -> str:
    for rule in CABLE_RULES:
        if (rule.endA == categoryA and rule.endB == categoryB) or \
           (rule.endA == categoryB and rule.endB == categoryA):
            return rule.cable
    return "straight"  # default
