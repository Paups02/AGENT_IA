"""
Motor de càlcul de reg.

Mòduls:
- irrigation: Càlcul de necessitats de reg segons FAO-56
- decision: Lògica de decisió de reg
"""

from .irrigation import IrrigationEngine
from .decision import DecisionEngine

__all__ = ["IrrigationEngine", "DecisionEngine"]
