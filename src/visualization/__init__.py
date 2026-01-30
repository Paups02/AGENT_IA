"""
Mòdul de visualització per a l'Agent de Reg.

Inclou:
- Gràfics d'ETo i balanç hídric
- Visualització de l'estat dels embassaments
- Gràfics de temperatura i humitat
"""

from .charts import ChartGenerator

# ImageGenerator es carrega sota demanda per evitar problemes de dependències
ImageGenerator = None

def get_image_generator():
    """Obté ImageGenerator si està disponible."""
    global ImageGenerator
    if ImageGenerator is None:
        try:
            from .images import ImageGenerator as _ImageGenerator
            ImageGenerator = _ImageGenerator
        except Exception:
            pass
    return ImageGenerator

__all__ = ["ChartGenerator", "ImageGenerator", "get_image_generator"]
