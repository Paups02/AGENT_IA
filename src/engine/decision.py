"""
Motor de decisió de reg.

Implementa la lògica avançada de decisió:
- Restriccions per sequera
- Optimització per pluja
- Coherència agronòmica
- Generació de recomanacions
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import date, datetime
from enum import Enum

from ..config import settings, EstatHidrologic
from ..cultius import TipusCultiu, FaseFenologica, NOMS_CULTIUS
from .irrigation import NecessitatReg, PlaReg


class TipusRecomanacio(str, Enum):
    """Tipus de recomanació de reg."""
    REGAR_NORMAL = "regar_normal"
    REGAR_SUPERVIVENCIA = "regar_supervivencia"
    POSPOSAR = "posposar"
    CANCEL_LAR = "cancelar"
    REGAR_URGENT = "regar_urgent"


class NivellRisc(str, Enum):
    """Nivell de risc per al cultiu."""
    BAIX = "baix"
    MODERAT = "moderat"
    ALT = "alt"
    CRITIC = "critic"


@dataclass
class Recomanacio:
    """Recomanació de reg estructurada."""
    tipus: TipusRecomanacio
    data: date
    cultiu: TipusCultiu
    municipi: str

    # Dosi recomanada
    dosi_mm: float
    dosi_m3_ha: float

    # Context
    estat_hidrologic: EstatHidrologic
    mode_sequera: bool
    pluja_prevista_mm: float

    # Detalls
    missatge_principal: str
    justificacio: str
    accions: List[str]
    riscos: List[str]
    nivell_risc: NivellRisc


@dataclass
class AnalisiRisc:
    """Anàlisi de riscos per al cultiu."""
    nivell: NivellRisc
    factors: List[Dict]
    recomanacions_preventives: List[str]


class DecisionEngine:
    """Motor de decisió de reg."""

    def __init__(self):
        """Inicialitza el motor."""
        pass

    def avaluar_restriccions_sequera(
        self,
        estat_hidrologic: EstatHidrologic,
        percentatge_embassaments: float
    ) -> Dict:
        """
        Avalua les restriccions per sequera.

        Regla: Si Rialb < 20% → Mode Reg de Supervivència

        Args:
            estat_hidrologic: Estat actual del sistema
            percentatge_embassaments: Percentatge d'ocupació

        Returns:
            Diccionari amb restriccions aplicables
        """
        restriccions = {
            "mode_sequera": False,
            "factor_reduccio": 1.0,
            "tipus_reg": "normal",
            "limitacions": [],
        }

        if estat_hidrologic == EstatHidrologic.EMERGENCIA:
            restriccions.update({
                "mode_sequera": True,
                "factor_reduccio": 0.40,  # Reducció del 60%
                "tipus_reg": "emergencia",
                "limitacions": [
                    "Només reg d'emergència per evitar mort del cultiu",
                    "Prioritzar cultius perennes i fruiters",
                    "Suspendre reg de cultius anuals en fase final",
                ],
            })
        elif estat_hidrologic == EstatHidrologic.ALERTA:
            restriccions.update({
                "mode_sequera": True,
                "factor_reduccio": settings.factor_sequera,  # 0.60
                "tipus_reg": "supervivencia",
                "limitacions": [
                    f"Reducció del {(1-settings.factor_sequera)*100:.0f}% en la dosi",
                    "Prioritzar manteniment del cultiu sobre màxim rendiment",
                    "Evitar regs nocturns innecessaris",
                ],
            })
        elif estat_hidrologic == EstatHidrologic.PREALERTA:
            restriccions.update({
                "mode_sequera": False,
                "factor_reduccio": 0.85,  # Reducció del 15%
                "tipus_reg": "eficient",
                "limitacions": [
                    "Es recomana màxima eficiència en el reg",
                    "Evitar pèrdues per escorrentia",
                ],
            })

        return restriccions

    def avaluar_pluja_prevista(
        self,
        pluja_24h_mm: float,
        pluja_48h_mm: float,
        etc_mm: float
    ) -> Dict:
        """
        Avalua si la pluja prevista justifica posposar el reg.

        Regla: Si >5 mm en 24h → Cancel·la o posposa el reg

        Args:
            pluja_24h_mm: Pluja prevista en 24h
            pluja_48h_mm: Pluja prevista en 48h
            etc_mm: ETc diària

        Returns:
            Diccionari amb la decisió sobre pluja
        """
        decisio = {
            "posposar": False,
            "cancelar": False,
            "motiu": None,
            "estalvi_mm": 0,
        }

        if pluja_24h_mm >= settings.llindar_pluja_posposar:
            if pluja_24h_mm >= etc_mm * 0.8:
                decisio.update({
                    "cancelar": True,
                    "motiu": f"Pluja prevista ({pluja_24h_mm:.1f} mm) cobreix la major part de l'ETc ({etc_mm:.1f} mm)",
                    "estalvi_mm": pluja_24h_mm,
                })
            else:
                decisio.update({
                    "posposar": True,
                    "motiu": f"Pluja significativa prevista ({pluja_24h_mm:.1f} mm), recomanem posposar 24-48h",
                    "estalvi_mm": pluja_24h_mm * 0.7,  # Pluja efectiva estimada
                })
        elif pluja_48h_mm >= settings.llindar_pluja_posposar * 2:
            decisio.update({
                "posposar": True,
                "motiu": f"Pluja acumulada significativa prevista en 48h ({pluja_48h_mm:.1f} mm)",
                "estalvi_mm": pluja_48h_mm * 0.5,
            })

        return decisio

    def generar_recomanacio(
        self,
        necessitat: NecessitatReg,
        estat_hidrologic: EstatHidrologic,
        pluja_24h: float,
        pluja_48h: float
    ) -> Recomanacio:
        """
        Genera una recomanació de reg completa.

        Args:
            necessitat: Càlcul de necessitat de reg
            estat_hidrologic: Estat del sistema hidrològic
            pluja_24h: Pluja prevista en 24h
            pluja_48h: Pluja prevista en 48h

        Returns:
            Recomanacio estructurada
        """
        # Avaluar restriccions
        restriccions = self.avaluar_restriccions_sequera(
            estat_hidrologic,
            0  # El percentatge ja està considerat a NecessitatReg
        )

        avaluacio_pluja = self.avaluar_pluja_prevista(
            pluja_24h,
            pluja_48h,
            necessitat.etc_mm
        )

        # Determinar tipus de recomanació
        accions = []
        riscos = []
        nivell_risc = NivellRisc.BAIX

        if avaluacio_pluja["cancelar"]:
            tipus = TipusRecomanacio.CANCEL_LAR
            dosi = 0
            missatge = "Cancel·lar el reg programat"
            justificacio = avaluacio_pluja["motiu"]
            accions = [
                "No aplicar reg avui",
                f"Estalvi estimat: {avaluacio_pluja['estalvi_mm']:.1f} mm",
                "Reavaluar demà segons pluja real",
            ]

        elif avaluacio_pluja["posposar"]:
            tipus = TipusRecomanacio.POSPOSAR
            dosi = 0
            missatge = "Posposar el reg 24-48 hores"
            justificacio = avaluacio_pluja["motiu"]
            accions = [
                "Esperar la precipitació prevista",
                "Reavaluar necessitats després de la pluja",
                f"Estalvi potencial: {avaluacio_pluja['estalvi_mm']:.1f} mm",
            ]

        elif restriccions["mode_sequera"]:
            if estat_hidrologic == EstatHidrologic.EMERGENCIA:
                tipus = TipusRecomanacio.REGAR_URGENT
                nivell_risc = NivellRisc.CRITIC
            else:
                tipus = TipusRecomanacio.REGAR_SUPERVIVENCIA
                nivell_risc = NivellRisc.ALT

            dosi = necessitat.dosi_bruta_mm * restriccions["factor_reduccio"]
            missatge = f"Aplicar reg de supervivència: {dosi:.1f} mm"
            justificacio = (
                f"Mode sequera actiu. Reducció del {(1-restriccions['factor_reduccio'])*100:.0f}% "
                f"respecte a la dosi òptima ({necessitat.dosi_bruta_mm:.1f} mm). "
                f"Referència FAO-56: ETc = {necessitat.etc_mm:.1f} mm, Kc = {necessitat.kc:.2f}"
            )
            accions = restriccions["limitacions"] + [
                f"Aplicar {dosi:.1f} mm ({dosi*10:.0f} m³/ha)",
                "Regar preferiblement a primera hora del matí",
            ]
            riscos = [
                "Estrès hídric moderat esperat",
                "Possible reducció del rendiment",
            ]

        elif necessitat.regar:
            tipus = TipusRecomanacio.REGAR_NORMAL
            dosi = necessitat.dosi_bruta_mm
            missatge = f"Regar avui: {dosi:.1f} mm ({dosi*10:.0f} m³/ha)"
            justificacio = (
                f"Balanç hídric segons FAO-56: ETc = {necessitat.etc_mm:.1f} mm "
                f"(ETo {necessitat.eto_mm:.1f} mm × Kc {necessitat.kc:.2f}). "
                f"Dèficit net: {necessitat.deficit_mm:.1f} mm. "
                f"Eficiència sistema {necessitat.sistema_reg.value}: {necessitat.eficiencia*100:.0f}%"
            )
            accions = [
                f"Aplicar {dosi:.1f} mm de reg",
                f"Equivalent a {dosi*10:.0f} m³/ha",
                "Horari recomanat: matinada o vespre",
            ]

        else:
            tipus = TipusRecomanacio.CANCEL_LAR
            dosi = 0
            missatge = "No cal regar avui"
            justificacio = necessitat.motiu
            accions = [
                "Mantenir vigilància de les condicions",
                "Reavaluar demà",
            ]

        return Recomanacio(
            tipus=tipus,
            data=necessitat.data,
            cultiu=necessitat.cultiu,
            municipi=necessitat.municipi,
            dosi_mm=round(dosi, 1),
            dosi_m3_ha=round(dosi * 10, 0),
            estat_hidrologic=estat_hidrologic,
            mode_sequera=necessitat.mode_sequera,
            pluja_prevista_mm=pluja_24h,
            missatge_principal=missatge,
            justificacio=justificacio,
            accions=accions,
            riscos=riscos,
            nivell_risc=nivell_risc,
        )

    def analitzar_riscos(
        self,
        pla: PlaReg,
        temperatures_extremes: Dict
    ) -> AnalisiRisc:
        """
        Analitza els riscos per al cultiu en el període planificat.

        Args:
            pla: Pla de reg setmanal
            temperatures_extremes: Dades de temperatures

        Returns:
            AnalisiRisc amb l'anàlisi completa
        """
        factors = []
        recomanacions = []
        nivell_maxim = NivellRisc.BAIX

        # Risc per sequera
        if any(n.mode_sequera for n in pla.dies):
            factors.append({
                "tipus": "sequera",
                "descripcio": "Mode sequera actiu en el període",
                "impacte": "alt",
            })
            recomanacions.append("Prioritzar eficiència màxima del sistema de reg")
            nivell_maxim = NivellRisc.ALT

        # Risc per onada de calor
        if temperatures_extremes.get("onada_calor_prevista"):
            dies_calor = temperatures_extremes.get("dies_calor_extrema", 0)
            factors.append({
                "tipus": "calor_extrema",
                "descripcio": f"Onada de calor prevista ({dies_calor} dies >35°C)",
                "impacte": "alt",
            })
            recomanacions.extend([
                "Incrementar freqüència de reg durant l'onada de calor",
                "Considerar reg per aspersió per refredar el cultiu",
                "Evitar reg durant les hores centrals del dia",
            ])
            if nivell_maxim != NivellRisc.CRITIC:
                nivell_maxim = NivellRisc.ALT

        # Risc per dèficit acumulat
        deficit_acumulat = sum(n.deficit_mm for n in pla.dies)
        if deficit_acumulat > 30:
            factors.append({
                "tipus": "deficit_acumulat",
                "descripcio": f"Dèficit hídric acumulat elevat ({deficit_acumulat:.0f} mm)",
                "impacte": "moderat",
            })
            recomanacions.append("Mantenir el programa de reg per evitar estrès crònic")
            if nivell_maxim == NivellRisc.BAIX:
                nivell_maxim = NivellRisc.MODERAT

        # Risc per excés de pluja
        pluja_total = sum(n.pluja_mm for n in pla.dies)
        if pluja_total > 50:
            factors.append({
                "tipus": "exces_pluja",
                "descripcio": f"Precipitació abundant prevista ({pluja_total:.0f} mm)",
                "impacte": "moderat",
            })
            recomanacions.extend([
                "Vigilar drenatge de la parcel·la",
                "Ajustar el reg segons la pluja real",
            ])

        if not factors:
            factors.append({
                "tipus": "sense_risc",
                "descripcio": "No s'identifiquen riscos significatius",
                "impacte": "baix",
            })

        return AnalisiRisc(
            nivell=nivell_maxim,
            factors=factors,
            recomanacions_preventives=recomanacions,
        )

    def generar_informe_decisio(
        self,
        recomanacio: Recomanacio,
        analisi_risc: AnalisiRisc
    ) -> str:
        """
        Genera un informe textual de la decisió de reg.

        Format per a ús en informes tècnics.

        Args:
            recomanacio: Recomanació generada
            analisi_risc: Anàlisi de riscos

        Returns:
            Text formatat de l'informe
        """
        nom_cultiu = NOMS_CULTIUS.get(recomanacio.cultiu, recomanacio.cultiu.value)

        informe = []
        informe.append("=" * 60)
        informe.append("RECOMANACIÓ DE REG")
        informe.append("=" * 60)
        informe.append("")
        informe.append(f"📅 Data: {recomanacio.data.isoformat()}")
        informe.append(f"📍 Municipi: {recomanacio.municipi}")
        informe.append(f"🌱 Cultiu: {nom_cultiu}")
        informe.append("")
        informe.append("-" * 60)
        informe.append(f"🎯 RECOMANACIÓ: {recomanacio.missatge_principal}")
        informe.append("-" * 60)
        informe.append("")

        if recomanacio.dosi_mm > 0:
            informe.append(f"💧 Dosi recomanada: {recomanacio.dosi_mm} mm ({recomanacio.dosi_m3_ha:.0f} m³/ha)")
            informe.append("")

        informe.append("📋 JUSTIFICACIÓ TÈCNICA (FAO-56):")
        informe.append(recomanacio.justificacio)
        informe.append("")

        informe.append("✅ ACCIONS:")
        for accio in recomanacio.accions:
            informe.append(f"   • {accio}")
        informe.append("")

        if recomanacio.riscos:
            informe.append("⚠️ RISCOS:")
            for risc in recomanacio.riscos:
                informe.append(f"   • {risc}")
            informe.append("")

        if recomanacio.mode_sequera:
            informe.append(f"🚨 ESTAT: Mode sequera actiu ({recomanacio.estat_hidrologic.value})")
            informe.append("")

        if analisi_risc.recomanacions_preventives:
            informe.append("🛡️ MESURES PREVENTIVES:")
            for rec in analisi_risc.recomanacions_preventives:
                informe.append(f"   • {rec}")
            informe.append("")

        informe.append("=" * 60)

        return "\n".join(informe)
