"""
Motor de càlcul de necessitats de reg segons metodologia FAO-56.

Implementa:
- Càlcul d'ETc (Evapotranspiració del cultiu)
- Balanç hídric diari
- Dosi de reg neta i bruta
- Moment òptim de reg
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import date, datetime
import asyncio

from ..config import settings, SistemaReg, EFICIENCIA_REG
from ..cultius import (
    TipusCultiu, COEFICIENTS_KC, calcular_kc_actual,
    obtenir_info_cultiu, NOMS_CULTIUS
)
from ..api_clients import OpenWeatherClient, HydrologyClient, AgrometeoClient


@dataclass
class NecessitatReg:
    """Resultat del càlcul de necessitat de reg."""
    data: date
    cultiu: TipusCultiu
    municipi: str

    # Dades agrometeorològiques
    eto_mm: float               # Evapotranspiració de referència
    kc: float                   # Coeficient de cultiu
    etc_mm: float               # Evapotranspiració del cultiu (ETo × Kc)

    # Balanç hídric
    pluja_mm: float             # Pluja prevista
    pluja_efectiva_mm: float    # Pluja efectiva
    deficit_mm: float           # ETc - Pluja efectiva

    # Dosi de reg
    dosi_neta_mm: float         # Aigua que ha d'arribar a les arrels
    dosi_bruta_mm: float        # Aigua a aplicar (considerant eficiència)
    sistema_reg: SistemaReg
    eficiencia: float

    # Factors d'ajust
    factor_sequera: float       # 1.0 si normal, <1 si sequera
    mode_sequera: bool

    # Recomanació
    regar: bool
    prioritat: str              # "alta", "mitjana", "baixa", "nul·la"
    motiu: str


@dataclass
class PlaReg:
    """Pla de reg per a múltiples dies."""
    municipi: str
    cultiu: TipusCultiu
    data_inici: date
    data_fi: date
    dies: List[NecessitatReg]
    total_reg_mm: float
    total_reg_m3_ha: float
    alertes: List[str]


class IrrigationEngine:
    """Motor principal de càlcul de reg."""

    def __init__(self):
        """Inicialitza el motor."""
        self._weather_client: Optional[OpenWeatherClient] = None
        self._hydro_client: Optional[HydrologyClient] = None
        self._agrometeo_client: Optional[AgrometeoClient] = None

    async def __aenter__(self):
        self._weather_client = OpenWeatherClient()
        self._hydro_client = HydrologyClient()
        self._agrometeo_client = AgrometeoClient()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._weather_client:
            await self._weather_client.close()
        if self._hydro_client:
            await self._hydro_client.close()
        if self._agrometeo_client:
            await self._agrometeo_client.close()

    def calcular_etc(self, eto: float, kc: float) -> float:
        """
        Calcula l'evapotranspiració del cultiu (ETc).

        ETc = ETo × Kc (FAO-56)

        Args:
            eto: Evapotranspiració de referència (mm/dia)
            kc: Coeficient de cultiu

        Returns:
            ETc en mm/dia
        """
        return round(eto * kc, 2)

    def calcular_dosi_neta(
        self,
        etc: float,
        pluja_efectiva: float,
        factor_sequera: float = 1.0
    ) -> float:
        """
        Calcula la dosi neta de reg.

        Dosi neta = (ETc - Pluja efectiva) × Factor sequera

        Args:
            etc: Evapotranspiració del cultiu (mm)
            pluja_efectiva: Pluja efectiva (mm)
            factor_sequera: Factor de reducció per sequera (0-1)

        Returns:
            Dosi neta en mm
        """
        deficit = max(0, etc - pluja_efectiva)
        return round(deficit * factor_sequera, 2)

    def calcular_dosi_bruta(
        self,
        dosi_neta: float,
        sistema: SistemaReg
    ) -> float:
        """
        Calcula la dosi bruta de reg considerant l'eficiència del sistema.

        Dosi bruta = Dosi neta / Eficiència

        Args:
            dosi_neta: Dosi neta (mm)
            sistema: Tipus de sistema de reg

        Returns:
            Dosi bruta en mm
        """
        eficiencia = EFICIENCIA_REG[sistema]
        if eficiencia <= 0:
            eficiencia = 0.70  # Valor per defecte

        return round(dosi_neta / eficiencia, 2)

    def mm_a_m3_ha(self, mm: float) -> float:
        """
        Converteix mm de reg a m³/ha.

        1 mm sobre 1 ha = 10 m³

        Args:
            mm: Làmina de reg en mm

        Returns:
            Volum en m³/ha
        """
        return round(mm * 10, 1)

    def determinar_prioritat(
        self,
        deficit_mm: float,
        etc_mm: float,
        mode_sequera: bool
    ) -> str:
        """
        Determina la prioritat del reg basant-se en el dèficit.

        Args:
            deficit_mm: Dèficit hídric (mm)
            etc_mm: ETc diària (mm)
            mode_sequera: Si estem en mode sequera

        Returns:
            Prioritat: "alta", "mitjana", "baixa", "nul·la"
        """
        if deficit_mm <= 0:
            return "nul·la"

        # Ràtio dèficit/ETc
        if etc_mm > 0:
            ratio = deficit_mm / etc_mm
        else:
            ratio = 0

        if mode_sequera:
            # En sequera, ser més conservador
            if ratio >= 1.0:
                return "alta"
            elif ratio >= 0.7:
                return "mitjana"
            elif ratio >= 0.5:
                return "baixa"
            else:
                return "nul·la"
        else:
            if ratio >= 0.8:
                return "alta"
            elif ratio >= 0.5:
                return "mitjana"
            elif ratio >= 0.3:
                return "baixa"
            else:
                return "nul·la"

    async def calcular_necessitat_diaria(
        self,
        cultiu: TipusCultiu,
        municipi: str = "Mollerussa",
        sistema_reg: SistemaReg = SistemaReg.ASPERSIO,
        data: Optional[date] = None
    ) -> NecessitatReg:
        """
        Calcula la necessitat de reg per a un dia concret.

        Args:
            cultiu: Tipus de cultiu
            municipi: Municipi de la parcel·la
            sistema_reg: Sistema de reg instal·lat
            data: Data de càlcul (per defecte avui)

        Returns:
            NecessitatReg amb tots els càlculs
        """
        if data is None:
            data = date.today()

        # Obtenir dades en paral·lel
        eto_task = self._agrometeo_client.obtenir_eto_diaria(municipi, data)
        meteo_task = self._weather_client.calcular_pluja_prevista(municipi, 24)
        hidro_task = self._hydro_client.obtenir_estat_sistema()

        eto_data, pluja_data, hidro_data = await asyncio.gather(
            eto_task, meteo_task, hidro_task
        )

        # Obtenir Kc del cultiu
        info_cultiu = obtenir_info_cultiu(cultiu, data)
        kc = info_cultiu["kc_actual"]

        # Calcular ETc
        eto = eto_data.eto_mm
        etc = self.calcular_etc(eto, kc)

        # Pluja efectiva
        pluja_mm = pluja_data["pluja_total_mm"]
        pluja_efectiva = self._agrometeo_client.calcular_pluja_efectiva(pluja_mm, etc)

        # Factor de sequera
        factor_sequera = hidro_data.factor_reduccio
        mode_sequera = hidro_data.mode_sequera

        # Calcular dosis
        dosi_neta = self.calcular_dosi_neta(etc, pluja_efectiva, factor_sequera)
        dosi_bruta = self.calcular_dosi_bruta(dosi_neta, sistema_reg)
        eficiencia = EFICIENCIA_REG[sistema_reg]

        # Determinar si regar
        deficit = max(0, etc - pluja_efectiva)
        regar = dosi_neta > 0.5  # Mínim 0.5 mm per justificar reg

        # Prioritat
        prioritat = self.determinar_prioritat(deficit, etc, mode_sequera)

        # Motiu de la recomanació
        if not regar:
            if pluja_data["pluja_significativa"]:
                motiu = f"Pluja prevista de {pluja_mm:.1f} mm cobreix les necessitats"
            else:
                motiu = "Necessitat de reg negligible"
        elif mode_sequera:
            motiu = f"Reg de supervivència (reducció {(1-factor_sequera)*100:.0f}%)"
        else:
            motiu = f"Reg normal per cobrir dèficit de {deficit:.1f} mm"

        return NecessitatReg(
            data=data,
            cultiu=cultiu,
            municipi=municipi,
            eto_mm=eto,
            kc=kc,
            etc_mm=etc,
            pluja_mm=pluja_mm,
            pluja_efectiva_mm=pluja_efectiva,
            deficit_mm=deficit,
            dosi_neta_mm=dosi_neta,
            dosi_bruta_mm=dosi_bruta,
            sistema_reg=sistema_reg,
            eficiencia=eficiencia,
            factor_sequera=factor_sequera,
            mode_sequera=mode_sequera,
            regar=regar,
            prioritat=prioritat,
            motiu=motiu
        )

    async def calcular_pla_setmanal(
        self,
        cultiu: TipusCultiu,
        municipi: str = "Mollerussa",
        sistema_reg: SistemaReg = SistemaReg.ASPERSIO,
        dies: int = 7
    ) -> PlaReg:
        """
        Calcula un pla de reg per als pròxims dies.

        Args:
            cultiu: Tipus de cultiu
            municipi: Municipi de la parcel·la
            sistema_reg: Sistema de reg instal·lat
            dies: Nombre de dies a planificar

        Returns:
            PlaReg amb la planificació completa
        """
        from datetime import timedelta

        avui = date.today()
        necessitats = []
        alertes = []

        # Obtenir estat hidrològic una vegada
        hidro = await self._hydro_client.obtenir_estat_sistema()

        if hidro.mode_sequera:
            alertes.append(f"⚠️ Mode sequera actiu: reducció del {(1-hidro.factor_reduccio)*100:.0f}%")

        # Obtenir ETo setmanal
        eto_setmana = await self._agrometeo_client.obtenir_eto_setmanal(municipi)

        # Obtenir temperatures extremes
        temps = await self._weather_client.obtenir_temperatures_extremes(municipi, dies)

        if temps["onada_calor_prevista"]:
            alertes.append(f"🌡️ Onada de calor prevista: {temps['dies_calor_extrema']} dies >35°C")

        # Calcular per a cada dia
        info_cultiu = obtenir_info_cultiu(cultiu, avui)
        kc = info_cultiu["kc_actual"]

        for i in range(min(dies, len(eto_setmana))):
            data_dia = avui + timedelta(days=i)
            eto_dia = eto_setmana[i]

            # Pluja prevista per a aquest dia
            pluja_mm = temps["temperatures"][i]["pluja_mm"] if i < len(temps["temperatures"]) else 0

            # Càlculs
            etc = self.calcular_etc(eto_dia.eto_mm, kc)
            pluja_efectiva = self._agrometeo_client.calcular_pluja_efectiva(pluja_mm, etc)
            deficit = max(0, etc - pluja_efectiva)
            dosi_neta = self.calcular_dosi_neta(etc, pluja_efectiva, hidro.factor_reduccio)
            dosi_bruta = self.calcular_dosi_bruta(dosi_neta, sistema_reg)

            regar = dosi_neta > 0.5
            prioritat = self.determinar_prioritat(deficit, etc, hidro.mode_sequera)

            if not regar:
                if pluja_mm > settings.llindar_pluja_posposar:
                    motiu = f"Pluja prevista ({pluja_mm:.1f} mm)"
                else:
                    motiu = "Sense necessitat"
            elif hidro.mode_sequera:
                motiu = "Reg de supervivència"
            else:
                motiu = "Reg normal"

            necessitats.append(NecessitatReg(
                data=data_dia,
                cultiu=cultiu,
                municipi=municipi,
                eto_mm=eto_dia.eto_mm,
                kc=kc,
                etc_mm=etc,
                pluja_mm=pluja_mm,
                pluja_efectiva_mm=pluja_efectiva,
                deficit_mm=deficit,
                dosi_neta_mm=dosi_neta,
                dosi_bruta_mm=dosi_bruta,
                sistema_reg=sistema_reg,
                eficiencia=EFICIENCIA_REG[sistema_reg],
                factor_sequera=hidro.factor_reduccio,
                mode_sequera=hidro.mode_sequera,
                regar=regar,
                prioritat=prioritat,
                motiu=motiu
            ))

        # Totals
        total_reg_mm = sum(n.dosi_bruta_mm for n in necessitats if n.regar)
        total_reg_m3 = self.mm_a_m3_ha(total_reg_mm)

        return PlaReg(
            municipi=municipi,
            cultiu=cultiu,
            data_inici=avui,
            data_fi=avui + timedelta(days=dies - 1),
            dies=necessitats,
            total_reg_mm=total_reg_mm,
            total_reg_m3_ha=total_reg_m3,
            alertes=alertes
        )

    async def obtenir_resum_complet(
        self,
        cultiu: TipusCultiu,
        municipi: str = "Mollerussa",
        sistema_reg: SistemaReg = SistemaReg.ASPERSIO
    ) -> Dict:
        """
        Obté un resum complet de la situació de reg.

        Inclou:
        - Estat hidrològic
        - Anàlisi agrometeorològica
        - Necessitat hídrica
        - Recomanació operativa
        - Pla setmanal

        Args:
            cultiu: Tipus de cultiu
            municipi: Municipi
            sistema_reg: Sistema de reg

        Returns:
            Diccionari amb tota la informació
        """
        # Obtenir dades en paral·lel
        necessitat_avui = await self.calcular_necessitat_diaria(cultiu, municipi, sistema_reg)
        pla_setmanal = await self.calcular_pla_setmanal(cultiu, municipi, sistema_reg)
        hidro = await self._hydro_client.obtenir_resum_hidrologic()
        meteo = await self._weather_client.obtenir_resum_meteo(municipi)
        eto = await self._agrometeo_client.obtenir_eto_diaria(municipi)

        info_cultiu = obtenir_info_cultiu(cultiu)

        return {
            "data_informe": datetime.now().isoformat(),
            "municipi": municipi,
            "cultiu": {
                "tipus": cultiu.value,
                "nom": NOMS_CULTIUS[cultiu],
                "fase_fenologica": info_cultiu["fase_fenologica"],
                "kc_actual": info_cultiu["kc_actual"],
                "dies_desde_sembra": info_cultiu["dies_desde_sembra"],
            },
            "sistema_reg": {
                "tipus": sistema_reg.value,
                "eficiencia": EFICIENCIA_REG[sistema_reg],
            },
            "estat_hidrologic": hidro,
            "agrometeo": {
                "temperatura_actual": meteo["actual"]["temperatura"],
                "humitat": meteo["actual"]["humitat"],
                "vent_ms": meteo["actual"]["vent_ms"],
                "eto_mm": eto.eto_mm,
                "radiacio_solar": eto.radiacio_solar,
            },
            "pluja": meteo["pluja"],
            "alertes": meteo["alertes"],
            "necessitat_avui": {
                "etc_mm": necessitat_avui.etc_mm,
                "pluja_efectiva_mm": necessitat_avui.pluja_efectiva_mm,
                "deficit_mm": necessitat_avui.deficit_mm,
                "dosi_neta_mm": necessitat_avui.dosi_neta_mm,
                "dosi_bruta_mm": necessitat_avui.dosi_bruta_mm,
                "dosi_m3_ha": self.mm_a_m3_ha(necessitat_avui.dosi_bruta_mm),
                "regar": necessitat_avui.regar,
                "prioritat": necessitat_avui.prioritat,
                "motiu": necessitat_avui.motiu,
                "mode_sequera": necessitat_avui.mode_sequera,
                "factor_sequera": necessitat_avui.factor_sequera,
            },
            "pla_setmanal": {
                "dies": [
                    {
                        "data": n.data.isoformat(),
                        "eto_mm": n.eto_mm,
                        "etc_mm": n.etc_mm,
                        "pluja_mm": n.pluja_mm,
                        "dosi_bruta_mm": n.dosi_bruta_mm,
                        "regar": n.regar,
                        "prioritat": n.prioritat,
                    }
                    for n in pla_setmanal.dies
                ],
                "total_reg_mm": pla_setmanal.total_reg_mm,
                "total_reg_m3_ha": pla_setmanal.total_reg_m3_ha,
                "alertes": pla_setmanal.alertes,
            },
        }


# Funcions síncrones per a ús des de la CLI
def calcular_reg_sync(
    cultiu: str,
    municipi: str = "Mollerussa",
    sistema: str = "aspersio"
) -> Dict:
    """Versió síncrona de calcular necessitat de reg."""
    async def _calc():
        async with IrrigationEngine() as engine:
            tipus_cultiu = TipusCultiu(cultiu)
            sistema_reg = SistemaReg(sistema)
            return await engine.obtenir_resum_complet(tipus_cultiu, municipi, sistema_reg)
    return asyncio.run(_calc())
