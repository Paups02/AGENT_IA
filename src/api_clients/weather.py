"""
Client per a l'API OpenWeatherMap 3.0.

Proporciona:
- Dades meteorològiques actuals
- Predicció a 48 hores
- Pluja acumulada i prevista
"""

import httpx
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio

from ..config import settings, COORDENADES_MUNICIPIS


@dataclass
class DadesMeteo:
    """Dades meteorològiques per a un moment donat."""
    timestamp: datetime
    temperatura: float          # °C
    humitat: float              # %
    pressio: float              # hPa
    velocitat_vent: float       # m/s
    direccio_vent: float        # graus
    nuvolositat: float          # %
    pluja_1h: float             # mm
    pluja_3h: float             # mm
    descripcio: str
    icona: str


@dataclass
class PrevisioPluvia:
    """Previsió de pluja."""
    inici: datetime
    fi: datetime
    pluja_total_mm: float
    probabilitat: float         # 0-1


class OpenWeatherClient:
    """Client per a OpenWeatherMap API 3.0."""

    BASE_URL = "https://api.openweathermap.org/data/3.0"
    ONECALL_URL = f"{BASE_URL}/onecall"

    def __init__(self, api_key: Optional[str] = None):
        """
        Inicialitza el client.

        Args:
            api_key: Clau API d'OpenWeatherMap (per defecte usa la configuració)
        """
        self.api_key = api_key or settings.openweather_api_key
        self._client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Tanca el client HTTP."""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def _get_coords(self, municipi: str) -> tuple:
        """Obté coordenades d'un municipi."""
        if municipi in COORDENADES_MUNICIPIS:
            return COORDENADES_MUNICIPIS[municipi]
        # Per defecte, Mollerussa (centre de la zona regable)
        return COORDENADES_MUNICIPIS["Mollerussa"]

    async def obtenir_dades_actuals(self, municipi: str = "Mollerussa") -> DadesMeteo:
        """
        Obté les dades meteorològiques actuals.

        Args:
            municipi: Nom del municipi

        Returns:
            DadesMeteo amb les condicions actuals
        """
        lat, lon = self._get_coords(municipi)

        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.api_key,
            "units": "metric",
            "lang": "ca"
        }

        response = await self._client.get(self.ONECALL_URL, params=params)
        response.raise_for_status()
        data = response.json()

        current = data["current"]

        return DadesMeteo(
            timestamp=datetime.fromtimestamp(current["dt"]),
            temperatura=current["temp"],
            humitat=current["humidity"],
            pressio=current["pressure"],
            velocitat_vent=current["wind_speed"],
            direccio_vent=current.get("wind_deg", 0),
            nuvolositat=current["clouds"],
            pluja_1h=current.get("rain", {}).get("1h", 0),
            pluja_3h=current.get("rain", {}).get("3h", 0),
            descripcio=current["weather"][0]["description"],
            icona=current["weather"][0]["icon"]
        )

    async def obtenir_previsio_48h(self, municipi: str = "Mollerussa") -> List[DadesMeteo]:
        """
        Obté la previsió horària per a les pròximes 48 hores.

        Args:
            municipi: Nom del municipi

        Returns:
            Llista de DadesMeteo amb la previsió horària
        """
        lat, lon = self._get_coords(municipi)

        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.api_key,
            "units": "metric",
            "lang": "ca",
            "exclude": "minutely,daily,alerts"
        }

        response = await self._client.get(self.ONECALL_URL, params=params)
        response.raise_for_status()
        data = response.json()

        previsio = []
        for hour_data in data.get("hourly", [])[:48]:
            previsio.append(DadesMeteo(
                timestamp=datetime.fromtimestamp(hour_data["dt"]),
                temperatura=hour_data["temp"],
                humitat=hour_data["humidity"],
                pressio=hour_data["pressure"],
                velocitat_vent=hour_data["wind_speed"],
                direccio_vent=hour_data.get("wind_deg", 0),
                nuvolositat=hour_data["clouds"],
                pluja_1h=hour_data.get("rain", {}).get("1h", 0),
                pluja_3h=0,  # No disponible en previsió horària
                descripcio=hour_data["weather"][0]["description"],
                icona=hour_data["weather"][0]["icon"]
            ))

        return previsio

    async def calcular_pluja_prevista(
        self,
        municipi: str = "Mollerussa",
        hores: int = 24
    ) -> Dict:
        """
        Calcula la pluja prevista per a les pròximes hores.

        Args:
            municipi: Nom del municipi
            hores: Nombre d'hores a considerar

        Returns:
            Diccionari amb pluja total i per intervals
        """
        previsio = await self.obtenir_previsio_48h(municipi)

        pluja_total = 0
        pluja_per_interval = []
        interval_actual = {"inici": None, "fi": None, "pluja_mm": 0}

        for i, hora in enumerate(previsio[:hores]):
            pluja_hora = hora.pluja_1h

            if pluja_hora > 0:
                pluja_total += pluja_hora

                if interval_actual["inici"] is None:
                    interval_actual["inici"] = hora.timestamp

                interval_actual["fi"] = hora.timestamp
                interval_actual["pluja_mm"] += pluja_hora
            else:
                if interval_actual["inici"] is not None:
                    pluja_per_interval.append(interval_actual.copy())
                    interval_actual = {"inici": None, "fi": None, "pluja_mm": 0}

        # Afegir l'últim interval si existeix
        if interval_actual["inici"] is not None:
            pluja_per_interval.append(interval_actual)

        return {
            "municipi": municipi,
            "hores_analitzades": hores,
            "pluja_total_mm": round(pluja_total, 1),
            "intervals_pluja": pluja_per_interval,
            "hi_haura_pluja": pluja_total > 0,
            "pluja_significativa": pluja_total >= settings.llindar_pluja_posposar
        }

    async def obtenir_temperatures_extremes(
        self,
        municipi: str = "Mollerussa",
        dies: int = 7
    ) -> Dict:
        """
        Obté les temperatures màximes i mínimes previstes.

        Args:
            municipi: Nom del municipi
            dies: Nombre de dies a analitzar

        Returns:
            Diccionari amb temperatures extremes
        """
        lat, lon = self._get_coords(municipi)

        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.api_key,
            "units": "metric",
            "lang": "ca",
            "exclude": "current,minutely,hourly,alerts"
        }

        response = await self._client.get(self.ONECALL_URL, params=params)
        response.raise_for_status()
        data = response.json()

        temperatures = []
        for day_data in data.get("daily", [])[:dies]:
            temperatures.append({
                "data": datetime.fromtimestamp(day_data["dt"]).date().isoformat(),
                "temp_min": day_data["temp"]["min"],
                "temp_max": day_data["temp"]["max"],
                "temp_dia": day_data["temp"]["day"],
                "humitat": day_data["humidity"],
                "pluja_mm": day_data.get("rain", 0),
                "prob_pluja": day_data.get("pop", 0)
            })

        # Detectar onada de calor (>35°C durant 3+ dies)
        dies_calor = sum(1 for t in temperatures if t["temp_max"] > 35)
        onada_calor = dies_calor >= 3

        return {
            "municipi": municipi,
            "temperatures": temperatures,
            "temp_max_periode": max(t["temp_max"] for t in temperatures),
            "temp_min_periode": min(t["temp_min"] for t in temperatures),
            "onada_calor_prevista": onada_calor,
            "dies_calor_extrema": dies_calor
        }

    async def obtenir_resum_meteo(self, municipi: str = "Mollerussa") -> Dict:
        """
        Obté un resum complet de la situació meteorològica.

        Args:
            municipi: Nom del municipi

        Returns:
            Diccionari amb resum meteorològic
        """
        actual = await self.obtenir_dades_actuals(municipi)
        pluja_24h = await self.calcular_pluja_prevista(municipi, 24)
        pluja_48h = await self.calcular_pluja_prevista(municipi, 48)
        temperatures = await self.obtenir_temperatures_extremes(municipi, 7)

        return {
            "municipi": municipi,
            "timestamp": datetime.now().isoformat(),
            "actual": {
                "temperatura": actual.temperatura,
                "humitat": actual.humitat,
                "vent_ms": actual.velocitat_vent,
                "nuvolositat": actual.nuvolositat,
                "descripcio": actual.descripcio
            },
            "pluja": {
                "ultima_hora_mm": actual.pluja_1h,
                "prevista_24h_mm": pluja_24h["pluja_total_mm"],
                "prevista_48h_mm": pluja_48h["pluja_total_mm"],
                "posposar_reg": pluja_24h["pluja_significativa"]
            },
            "alertes": {
                "onada_calor": temperatures["onada_calor_prevista"],
                "dies_calor_extrema": temperatures["dies_calor_extrema"],
                "temp_max_setmana": temperatures["temp_max_periode"]
            }
        }


# Funcions síncrones per a ús des de la CLI
def obtenir_meteo_sync(municipi: str = "Mollerussa") -> Dict:
    """Versió síncrona d'obtenir resum meteorològic."""
    async def _get():
        async with OpenWeatherClient() as client:
            return await client.obtenir_resum_meteo(municipi)
    return asyncio.run(_get())


def obtenir_pluja_prevista_sync(municipi: str = "Mollerussa", hores: int = 24) -> Dict:
    """Versió síncrona d'obtenir pluja prevista."""
    async def _get():
        async with OpenWeatherClient() as client:
            return await client.calcular_pluja_prevista(municipi, hores)
    return asyncio.run(_get())
