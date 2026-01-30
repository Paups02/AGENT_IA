"""
Clients per a les APIs externes de l'Agent de Reg.

Mòduls:
- weather: Client OpenWeatherMap
- hydrology: Client SAIH Ebro i embassaments
- agrometeo: Client RuralCat/Meteocat
"""

from .weather import OpenWeatherClient
from .hydrology import HydrologyClient
from .agrometeo import AgrometeoClient

__all__ = ["OpenWeatherClient", "HydrologyClient", "AgrometeoClient"]
