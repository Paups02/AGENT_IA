"""
Configuració central de l'Agent de Reg dels Canals d'Urgell.

Conté les credencials d'API, paràmetres hidrològics i constants agronòmiques.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Dict, List
from enum import Enum


class EstatHidrologic(str, Enum):
    """Estat del sistema hidrològic segons nivell dels embassaments."""
    NORMALITAT = "normalitat"
    PREALERTA = "prealerta"
    ALERTA = "alerta"
    EMERGENCIA = "emergencia"


class SistemaReg(str, Enum):
    """Tipus de sistema de reg amb les seves eficiències."""
    GRAVETAT = "gravetat"
    ASPERSIO = "aspersio"
    DEGOTEIG = "degoteig"
    PIVOT = "pivot"


# Eficiències dels sistemes de reg (%)
EFICIENCIA_REG: Dict[SistemaReg, float] = {
    SistemaReg.GRAVETAT: 0.55,
    SistemaReg.ASPERSIO: 0.75,
    SistemaReg.DEGOTEIG: 0.90,
    SistemaReg.PIVOT: 0.80,
}


class Settings(BaseSettings):
    """Configuració principal de l'aplicació."""

    # API Keys - Configura mitjançant variables d'entorn o fitxer .env
    anthropic_api_key: str = Field(
        default="",
        description="Clau API d'Anthropic per a Claude"
    )
    openweather_api_key: str = Field(
        default="",
        description="Clau API d'OpenWeatherMap 3.0"
    )
    gemini_api_key: str = Field(
        default="",
        description="Clau API de Google Gemini Pro"
    )

    # URLs de les APIs
    openweather_base_url: str = "https://api.openweathermap.org/data/3.0"
    saih_ebro_url: str = "https://www.saihebro.com/tiempo-real/mapa-embalses-H7-segre"
    saih_estado_url: str = "https://www.saihebro.com/homepage/estado-cuenca-ebro"
    canals_urgell_url: str = "https://regs.canalsurgell.cat/"
    dades_obertes_url: str = "https://analisi.transparenciacatalunya.cat/api/views"

    # Embassaments de referència
    embassaments: List[str] = ["Rialb", "Oliana"]

    # Llindars hidrològics (%)
    llindar_normalitat: float = 50.0
    llindar_prealerta: float = 35.0
    llindar_alerta: float = 20.0
    llindar_emergencia: float = 10.0

    # Factor de reducció en mode sequera
    factor_sequera: float = 0.60  # Redueix 40%

    # Llindar de pluja per posposar reg (mm en 24h)
    llindar_pluja_posposar: float = 5.0

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


# Municipis de la zona regable dels Canals d'Urgell per comarca
MUNICIPIS_ZONA_REGABLE: Dict[str, List[str]] = {
    "Segrià": [
        "Alcarràs", "Almacelles", "Almenar", "Benavent de Segrià",
        "Gimenells i el Pla de la Font", "Lleida", "Rosselló", "Torrefarrera",
        "Torres de Segre", "Vilanova de Segrià"
    ],
    "Noguera": [
        "Balaguer", "Bellcaire d'Urgell", "Bellmunt d'Urgell", "Castelló de Farfanya",
        "La Sentiu de Sió", "Linyola", "Menàrguens", "Os de Balaguer",
        "Penelles", "Térmens", "Vallfogona de Balaguer"
    ],
    "Urgell": [
        "Agramunt", "Anglesola", "Bellpuig", "Castellserà", "Preixana",
        "Puigverd d'Agramunt", "Sant Martí de Riucorb", "Tàrrega",
        "Tornabous", "Verdú", "Vilagrassa"
    ],
    "Pla d'Urgell": [
        "Barbens", "Bell-lloc d'Urgell", "Bellvís", "Castellnou de Seana",
        "Fondarella", "Golmés", "Ivars d'Urgell", "Linyola", "Miralcamp",
        "Mollerussa", "El Palau d'Anglesola", "El Poal", "Sidamon",
        "Torregrossa", "Vila-sana"
    ],
    "Garrigues": [
        "Arbeca", "Les Borges Blanques", "Castelldans", "Juneda",
        "La Floresta", "Puiggròs", "Torrebesses"
    ]
}


# Coordenades dels municipis principals (latitud, longitud)
COORDENADES_MUNICIPIS: Dict[str, tuple] = {
    "Mollerussa": (41.6300, 0.8950),
    "Tàrrega": (41.6472, 1.1397),
    "Lleida": (41.6176, 0.6200),
    "Balaguer": (41.7900, 0.8050),
    "Bellpuig": (41.6250, 1.0000),
    "Les Borges Blanques": (41.5167, 0.8667),
    "Agramunt": (41.7878, 1.1003),
    "Almacelles": (41.7300, 0.4400),
    "Bell-lloc d'Urgell": (41.6350, 0.7850),
    "Golmés": (41.6100, 0.8600),
    "Juneda": (41.5500, 0.8200),
    "Arbeca": (41.5400, 0.9300),
    "Anglesola": (41.6400, 1.0800),
    "Linyola": (41.6800, 0.9000),
    "Bellvís": (41.6700, 0.7900),
}


# Estacions agrometeorològiques de referència (RuralCat/Meteocat)
ESTACIONS_METEO: Dict[str, Dict] = {
    "Mollerussa": {
        "codi": "XN",
        "lat": 41.63,
        "lon": 0.89,
        "altitud": 250
    },
    "Tàrrega": {
        "codi": "XG",
        "lat": 41.65,
        "lon": 1.14,
        "altitud": 373
    },
    "Lleida": {
        "codi": "XL",
        "lat": 41.62,
        "lon": 0.60,
        "altitud": 192
    },
    "Gimenells": {
        "codi": "WK",
        "lat": 41.65,
        "lon": 0.39,
        "altitud": 264
    },
    "Raïmat": {
        "codi": "WR",
        "lat": 41.67,
        "lon": 0.50,
        "altitud": 296
    }
}


settings = Settings()
