"""
Agent Expert en Hidràulica Agrícola per als Canals d'Urgell.

Integra tots els components del sistema:
- APIs externes (meteorologia, hidrologia)
- Càlculs FAO-56
- Motor de decisió
- Visualització
- Generació d'informes
"""

from .irrigation_agent import IrrigationAgent

__all__ = ["IrrigationAgent"]
