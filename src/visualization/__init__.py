"""
Mòdul de visualització per a l'Agent de Reg.

Inclou:
- Gràfics d'ETo i balanç hídric
- Visualització de l'estat dels embassaments
- Gràfics de temperatura i humitat
"""

from .charts import ChartGenerator
from .images import ImageGenerator

__all__ = ["ChartGenerator", "ImageGenerator"]
