"""
Client per a dades agrometeorològiques.

Fonts:
- RuralCat (Xarxa Agroclimàtica de Catalunya)
- Meteocat (Servei Meteorològic de Catalunya)

Proporciona:
- ETo (Evapotranspiració de referència) calculada segons Penman-Monteith
- Dades climàtiques de les estacions agrometeo
"""

import httpx
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, date, timedelta
import math
import asyncio

from ..config import settings, ESTACIONS_METEO, COORDENADES_MUNICIPIS


@dataclass
class DadesETo:
    """Dades d'evapotranspiració de referència."""
    data: date
    estacio: str
    eto_mm: float               # ETo diària en mm
    temperatura_mitjana: float  # °C
    temperatura_max: float      # °C
    temperatura_min: float      # °C
    humitat_mitjana: float      # %
    radiacio_solar: float       # MJ/m²/dia
    velocitat_vent: float       # m/s a 2m


@dataclass
class BalancHidric:
    """Balanç hídric diari."""
    data: date
    eto_mm: float
    pluja_mm: float
    pluja_efectiva_mm: float
    deficit_mm: float           # ETc - Pluja efectiva


class AgrometeoClient:
    """Client per a dades agrometeorològiques."""

    # Constants per al càlcul de Penman-Monteith
    STEFAN_BOLTZMANN = 4.903e-9  # MJ/K⁴/m²/dia
    ALBEDO = 0.23               # Coeficient d'albedo per cultius
    GSC = 0.0820                # Constant solar (MJ/m²/min)

    def __init__(self):
        """Inicialitza el client."""
        self._client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Tanca el client HTTP."""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def _obtenir_estacio_propera(self, municipi: str) -> str:
        """
        Troba l'estació meteorològica més propera a un municipi.

        Args:
            municipi: Nom del municipi

        Returns:
            Nom de l'estació més propera
        """
        if municipi not in COORDENADES_MUNICIPIS:
            return "Mollerussa"

        lat_m, lon_m = COORDENADES_MUNICIPIS[municipi]

        distancia_min = float("inf")
        estacio_propera = "Mollerussa"

        for estacio, info in ESTACIONS_METEO.items():
            lat_e, lon_e = info["lat"], info["lon"]
            # Distància euclidiana simple (aproximació)
            dist = math.sqrt((lat_m - lat_e) ** 2 + (lon_m - lon_e) ** 2)
            if dist < distancia_min:
                distancia_min = dist
                estacio_propera = estacio

        return estacio_propera

    def calcular_eto_penman_monteith(
        self,
        temp_max: float,
        temp_min: float,
        humitat: float,
        velocitat_vent: float,
        radiacio_solar: float,
        latitud: float,
        dia_julia: int,
        altitud: float = 250
    ) -> float:
        """
        Calcula l'ETo segons el mètode FAO Penman-Monteith.

        Referència: FAO Irrigation and Drainage Paper No. 56

        Args:
            temp_max: Temperatura màxima (°C)
            temp_min: Temperatura mínima (°C)
            humitat: Humitat relativa mitjana (%)
            velocitat_vent: Velocitat del vent a 2m (m/s)
            radiacio_solar: Radiació solar (MJ/m²/dia)
            latitud: Latitud en graus
            dia_julia: Dia de l'any (1-365)
            altitud: Altitud en metres

        Returns:
            ETo en mm/dia
        """
        # Temperatura mitjana
        t_mean = (temp_max + temp_min) / 2

        # Pressió atmosfèrica (kPa)
        P = 101.3 * ((293 - 0.0065 * altitud) / 293) ** 5.26

        # Constant psicomètrica (kPa/°C)
        gamma = 0.000665 * P

        # Pendent de la corba de pressió de vapor (kPa/°C)
        delta = (4098 * (0.6108 * math.exp((17.27 * t_mean) / (t_mean + 237.3)))) / \
                ((t_mean + 237.3) ** 2)

        # Pressió de vapor de saturació (kPa)
        es_max = 0.6108 * math.exp((17.27 * temp_max) / (temp_max + 237.3))
        es_min = 0.6108 * math.exp((17.27 * temp_min) / (temp_min + 237.3))
        es = (es_max + es_min) / 2

        # Pressió de vapor real (kPa)
        ea = es * (humitat / 100)

        # Dèficit de pressió de vapor
        vpd = es - ea

        # Radiació extraterrestre (Ra)
        lat_rad = latitud * math.pi / 180
        dr = 1 + 0.033 * math.cos(2 * math.pi * dia_julia / 365)
        delta_sol = 0.409 * math.sin(2 * math.pi * dia_julia / 365 - 1.39)
        ws = math.acos(-math.tan(lat_rad) * math.tan(delta_sol))
        Ra = (24 * 60 / math.pi) * self.GSC * dr * \
             (ws * math.sin(lat_rad) * math.sin(delta_sol) +
              math.cos(lat_rad) * math.cos(delta_sol) * math.sin(ws))

        # Radiació neta de ona curta
        Rns = (1 - self.ALBEDO) * radiacio_solar

        # Radiació neta de ona llarga
        Rso = (0.75 + 2e-5 * altitud) * Ra
        ratio = radiacio_solar / Rso if Rso > 0 else 0.5
        ratio = min(1.0, max(0.25, ratio))

        Rnl = self.STEFAN_BOLTZMANN * \
              (((temp_max + 273.16) ** 4 + (temp_min + 273.16) ** 4) / 2) * \
              (0.34 - 0.14 * math.sqrt(ea)) * \
              (1.35 * ratio - 0.35)

        # Radiació neta
        Rn = Rns - Rnl

        # Flux de calor del sòl (G) - negligible per a càlculs diaris
        G = 0

        # Equació FAO Penman-Monteith
        numerador = 0.408 * delta * (Rn - G) + gamma * (900 / (t_mean + 273)) * velocitat_vent * vpd
        denominador = delta + gamma * (1 + 0.34 * velocitat_vent)

        eto = numerador / denominador

        return max(0, round(eto, 2))

    async def obtenir_eto_diaria(
        self,
        municipi: str = "Mollerussa",
        data: Optional[date] = None
    ) -> DadesETo:
        """
        Obté l'ETo diària per a un municipi.

        Args:
            municipi: Nom del municipi
            data: Data (per defecte avui)

        Returns:
            DadesETo amb l'evapotranspiració calculada
        """
        if data is None:
            data = date.today()

        estacio = self._obtenir_estacio_propera(municipi)
        info_estacio = ESTACIONS_METEO.get(estacio, ESTACIONS_METEO["Mollerussa"])

        # Obtenir dades meteorològiques d'OpenWeatherMap
        from .weather import OpenWeatherClient

        async with OpenWeatherClient() as weather:
            meteo = await weather.obtenir_resum_meteo(municipi)
            temps = await weather.obtenir_temperatures_extremes(municipi, 1)

        # Extreure dades
        temp_actual = meteo["actual"]["temperatura"]
        humitat = meteo["actual"]["humitat"]
        vent = meteo["actual"]["vent_ms"]
        nuvolositat = meteo["actual"]["nuvolositat"]

        # Estimar temperatures extremes
        if temps["temperatures"]:
            t_avui = temps["temperatures"][0]
            temp_max = t_avui["temp_max"]
            temp_min = t_avui["temp_min"]
        else:
            # Estimació basada en temperatura actual
            temp_max = temp_actual + 5
            temp_min = temp_actual - 5

        # Estimar radiació solar a partir de nuvolositat
        # Radiació màxima teòrica per a la latitud i època
        dia_julia = data.timetuple().tm_yday
        lat = info_estacio["lat"]

        # Radiació extraterrestre aproximada
        Ra = 37.6 * (1 + 0.033 * math.cos(2 * math.pi * dia_julia / 365))

        # Factor de nuvolositat (0-1)
        factor_nuvols = 1 - (nuvolositat / 100) * 0.75
        radiacio_solar = Ra * factor_nuvols * 0.7  # 0.7 és transmissivitat atmosfèrica

        # Calcular ETo
        eto = self.calcular_eto_penman_monteith(
            temp_max=temp_max,
            temp_min=temp_min,
            humitat=humitat,
            velocitat_vent=vent,
            radiacio_solar=radiacio_solar,
            latitud=lat,
            dia_julia=dia_julia,
            altitud=info_estacio["altitud"]
        )

        return DadesETo(
            data=data,
            estacio=estacio,
            eto_mm=eto,
            temperatura_mitjana=(temp_max + temp_min) / 2,
            temperatura_max=temp_max,
            temperatura_min=temp_min,
            humitat_mitjana=humitat,
            radiacio_solar=round(radiacio_solar, 2),
            velocitat_vent=vent
        )

    async def obtenir_eto_setmanal(
        self,
        municipi: str = "Mollerussa"
    ) -> List[DadesETo]:
        """
        Obté l'ETo prevista per als pròxims 7 dies.

        Args:
            municipi: Nom del municipi

        Returns:
            Llista de DadesETo per a cada dia
        """
        from .weather import OpenWeatherClient

        estacio = self._obtenir_estacio_propera(municipi)
        info_estacio = ESTACIONS_METEO.get(estacio, ESTACIONS_METEO["Mollerussa"])

        async with OpenWeatherClient() as weather:
            temps = await weather.obtenir_temperatures_extremes(municipi, 7)

        resultats = []
        avui = date.today()

        for i, dia in enumerate(temps["temperatures"]):
            data_dia = avui + timedelta(days=i)
            dia_julia = data_dia.timetuple().tm_yday

            # Estimar radiació solar
            Ra = 37.6 * (1 + 0.033 * math.cos(2 * math.pi * dia_julia / 365))
            # Assumir nuvolositat mitjana basada en prob. pluja
            factor_nuvols = 1 - dia["prob_pluja"] * 0.6
            radiacio_solar = Ra * factor_nuvols * 0.7

            eto = self.calcular_eto_penman_monteith(
                temp_max=dia["temp_max"],
                temp_min=dia["temp_min"],
                humitat=dia["humitat"],
                velocitat_vent=2.0,  # Valor típic
                radiacio_solar=radiacio_solar,
                latitud=info_estacio["lat"],
                dia_julia=dia_julia,
                altitud=info_estacio["altitud"]
            )

            resultats.append(DadesETo(
                data=data_dia,
                estacio=estacio,
                eto_mm=eto,
                temperatura_mitjana=(dia["temp_max"] + dia["temp_min"]) / 2,
                temperatura_max=dia["temp_max"],
                temperatura_min=dia["temp_min"],
                humitat_mitjana=dia["humitat"],
                radiacio_solar=round(radiacio_solar, 2),
                velocitat_vent=2.0
            ))

        return resultats

    def calcular_pluja_efectiva(self, pluja_mm: float, eto_mm: float) -> float:
        """
        Calcula la pluja efectiva segons mètode USDA SCS.

        La pluja efectiva és la part de la precipitació que és
        realment utilitzable pel cultiu (descomptant escorrentia,
        percolació profunda, etc.).

        Args:
            pluja_mm: Precipitació total (mm)
            eto_mm: ETo del dia (mm)

        Returns:
            Pluja efectiva en mm
        """
        if pluja_mm <= 0:
            return 0

        # Mètode USDA SCS modificat
        if pluja_mm <= 250:
            pef = pluja_mm * (125 - 0.2 * pluja_mm) / 125
        else:
            pef = 125 + 0.1 * pluja_mm

        # Limitar al màxim que el cultiu pot aprofitar
        pef = min(pef, pluja_mm * 0.8)
        pef = min(pef, eto_mm * 1.2)  # Màxim 120% de l'ETo

        return round(max(0, pef), 2)

    async def obtenir_balanc_hidric(
        self,
        municipi: str = "Mollerussa",
        kc: float = 1.0,
        dies: int = 7
    ) -> List[BalancHidric]:
        """
        Calcula el balanç hídric per als pròxims dies.

        Args:
            municipi: Nom del municipi
            kc: Coeficient de cultiu
            dies: Nombre de dies a calcular

        Returns:
            Llista de BalancHidric per a cada dia
        """
        from .weather import OpenWeatherClient

        eto_setmana = await self.obtenir_eto_setmanal(municipi)

        async with OpenWeatherClient() as weather:
            temps = await weather.obtenir_temperatures_extremes(municipi, dies)

        resultats = []

        for i, eto_dia in enumerate(eto_setmana[:dies]):
            pluja_mm = temps["temperatures"][i]["pluja_mm"] if i < len(temps["temperatures"]) else 0
            etc = eto_dia.eto_mm * kc
            pluja_ef = self.calcular_pluja_efectiva(pluja_mm, etc)
            deficit = max(0, etc - pluja_ef)

            resultats.append(BalancHidric(
                data=eto_dia.data,
                eto_mm=eto_dia.eto_mm,
                pluja_mm=pluja_mm,
                pluja_efectiva_mm=pluja_ef,
                deficit_mm=round(deficit, 2)
            ))

        return resultats


# Funcions síncrones per a ús des de la CLI
def obtenir_eto_sync(municipi: str = "Mollerussa") -> Dict:
    """Versió síncrona d'obtenir ETo diària."""
    async def _get():
        async with AgrometeoClient() as client:
            eto = await client.obtenir_eto_diaria(municipi)
            return {
                "data": eto.data.isoformat(),
                "estacio": eto.estacio,
                "eto_mm": eto.eto_mm,
                "temperatura_mitjana": eto.temperatura_mitjana,
                "temperatura_max": eto.temperatura_max,
                "temperatura_min": eto.temperatura_min,
                "humitat": eto.humitat_mitjana,
                "radiacio_solar": eto.radiacio_solar,
            }
    return asyncio.run(_get())


def obtenir_balanc_sync(municipi: str = "Mollerussa", kc: float = 1.0) -> List[Dict]:
    """Versió síncrona d'obtenir balanç hídric."""
    async def _get():
        async with AgrometeoClient() as client:
            balanc = await client.obtenir_balanc_hidric(municipi, kc)
            return [
                {
                    "data": b.data.isoformat(),
                    "eto_mm": b.eto_mm,
                    "pluja_mm": b.pluja_mm,
                    "pluja_efectiva_mm": b.pluja_efectiva_mm,
                    "deficit_mm": b.deficit_mm,
                }
                for b in balanc
            ]
    return asyncio.run(_get())
