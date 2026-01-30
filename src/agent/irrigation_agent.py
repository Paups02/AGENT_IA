"""
Agent Expert en Hidràulica Agrícola per als Canals d'Urgell.

Implementa un agent intel·ligent que:
1. Recull dades meteorològiques i hidrològiques
2. Calcula necessitats de reg segons FAO-56
3. Genera recomanacions de reg
4. Produeix informes tècnics professionals
"""

import anthropic
import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import date, datetime
from pathlib import Path

from ..config import settings, EstatHidrologic, SistemaReg, MUNICIPIS_ZONA_REGABLE
from ..cultius import TipusCultiu, NOMS_CULTIUS, obtenir_info_cultiu
from ..api_clients import OpenWeatherClient, HydrologyClient, AgrometeoClient
from ..engine import IrrigationEngine, DecisionEngine
from ..engine.decision import TipusRecomanacio, Recomanacio, AnalisiRisc
from ..visualization import ChartGenerator, ImageGenerator
from ..reports import ReportGenerator


class IrrigationAgent:
    """
    Agent Expert en Hidràulica Agrícola.

    Especialitzat exclusivament en la zona regable dels Canals d'Urgell (Lleida).
    Optimitza l'ús de l'aigua de reg calculant la dosi exacta i el moment òptim
    de reg per a qualsevol cultiu i municipi de la zona.
    """

    SYSTEM_PROMPT = """Ets un Agent Expert en Hidràulica Agrícola, Agrometeorologia i Ciència de Dades,
especialitzat exclusivament en la zona regable dels Canals d'Urgell (Lleida).

La teva missió és optimitzar l'ús de l'aigua de reg calculant la dosi exacta i el moment òptim
de reg per a qualsevol cultiu i municipi de la zona, amb criteris tècnics rigorosos i orientació
a agricultors professionals.

Treballes sota el principi de gestió eficient de l'aigua en un context d'escassetat estructural
a la conca de l'Ebre.

ÀMBIT GEOGRÀFIC:
- Zona regable dels Canals d'Urgell
- Comarques: Segrià, Noguera, Urgell, Pla d'Urgell, Garrigues
- Fonts d'aigua: Embassaments de Rialb i Oliana (Conca del Segre)

CULTIUS COBERTS:
- Panís (blat de moro), Alfals, Fruita dolça (pinyol i llavor)
- Cereal d'hivern, Ametller, Olivera, Hortícoles extensives

METODOLOGIA:
- Apliques estrictament la metodologia FAO-56
- ETc = ETo × Kc
- Necessitat de Reg = ETc - Pluja Efectiva
- Consideres eficiència del sistema de reg

REGLES DE DECISIÓ:
1. Si Rialb < 20% → Mode Reg de Supervivència (reducció 40%)
2. Si pluja prevista >5 mm en 24h → Cancel·la o posposa el reg
3. Mai recomanar regs excessius
4. Justificar sempre decisions conservatives

PERSONALITAT:
- Tècnic, precís, preventiu
- Orientat a professionals
- Conscient del valor estratègic de l'aigua
- Parles com un enginyer agrònom expert en regadius dels Canals d'Urgell
- No utilitzes llenguatge comercial ni divulgatiu bàsic"""

    def __init__(self):
        """Inicialitza l'agent."""
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.irrigation_engine: Optional[IrrigationEngine] = None
        self.decision_engine = DecisionEngine()
        self.chart_generator = ChartGenerator()
        self.image_generator = ImageGenerator()
        self.report_generator = ReportGenerator()

        # Definir les eines disponibles
        self.tools = self._definir_eines()

    def _definir_eines(self) -> List[Dict]:
        """Defineix les eines disponibles per a l'agent."""
        return [
            {
                "name": "obtenir_estat_hidrologic",
                "description": "Obté l'estat actual dels embassaments de Rialb i Oliana, incloent volum, percentatge i si hi ha mode sequera actiu.",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "obtenir_meteo",
                "description": "Obté les dades meteorològiques actuals i previsions per a un municipi de la zona dels Canals d'Urgell.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "municipi": {
                            "type": "string",
                            "description": "Nom del municipi (ex: Mollerussa, Tàrrega, Lleida)"
                        }
                    },
                    "required": ["municipi"]
                }
            },
            {
                "name": "calcular_necessitat_reg",
                "description": "Calcula la necessitat de reg per a un cultiu específic en un municipi, aplicant la metodologia FAO-56.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "cultiu": {
                            "type": "string",
                            "enum": [c.value for c in TipusCultiu],
                            "description": "Tipus de cultiu"
                        },
                        "municipi": {
                            "type": "string",
                            "description": "Nom del municipi"
                        },
                        "sistema_reg": {
                            "type": "string",
                            "enum": [s.value for s in SistemaReg],
                            "description": "Sistema de reg (gravetat, aspersio, degoteig, pivot)"
                        }
                    },
                    "required": ["cultiu", "municipi"]
                }
            },
            {
                "name": "generar_pla_setmanal",
                "description": "Genera un pla de reg complet per als propers 7 dies.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "cultiu": {
                            "type": "string",
                            "enum": [c.value for c in TipusCultiu],
                            "description": "Tipus de cultiu"
                        },
                        "municipi": {
                            "type": "string",
                            "description": "Nom del municipi"
                        },
                        "sistema_reg": {
                            "type": "string",
                            "enum": [s.value for s in SistemaReg],
                            "description": "Sistema de reg"
                        }
                    },
                    "required": ["cultiu", "municipi"]
                }
            },
            {
                "name": "generar_informe_complet",
                "description": "Genera un informe tècnic complet amb totes les dades, gràfics i recomanacions.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "cultiu": {
                            "type": "string",
                            "enum": [c.value for c in TipusCultiu],
                            "description": "Tipus de cultiu"
                        },
                        "municipi": {
                            "type": "string",
                            "description": "Nom del municipi"
                        },
                        "sistema_reg": {
                            "type": "string",
                            "enum": [s.value for s in SistemaReg],
                            "description": "Sistema de reg"
                        },
                        "format": {
                            "type": "string",
                            "enum": ["markdown", "pdf", "docx"],
                            "description": "Format de l'informe"
                        }
                    },
                    "required": ["cultiu", "municipi"]
                }
            },
            {
                "name": "obtenir_info_cultiu",
                "description": "Obté informació detallada sobre un cultiu: fase fenològica, Kc actual, etc.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "cultiu": {
                            "type": "string",
                            "enum": [c.value for c in TipusCultiu],
                            "description": "Tipus de cultiu"
                        }
                    },
                    "required": ["cultiu"]
                }
            },
            {
                "name": "llistar_municipis",
                "description": "Llista tots els municipis de la zona regable dels Canals d'Urgell, organitzats per comarca.",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "llistar_cultius",
                "description": "Llista tots els cultius suportats amb els seus coeficients Kc.",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        ]

    async def _executar_eina(self, nom_eina: str, arguments: Dict) -> Any:
        """
        Executa una eina i retorna el resultat.

        Args:
            nom_eina: Nom de l'eina
            arguments: Arguments de l'eina

        Returns:
            Resultat de l'execució
        """
        if nom_eina == "obtenir_estat_hidrologic":
            async with HydrologyClient() as client:
                return await client.obtenir_resum_hidrologic()

        elif nom_eina == "obtenir_meteo":
            municipi = arguments.get("municipi", "Mollerussa")
            async with OpenWeatherClient() as client:
                return await client.obtenir_resum_meteo(municipi)

        elif nom_eina == "calcular_necessitat_reg":
            cultiu = TipusCultiu(arguments["cultiu"])
            municipi = arguments.get("municipi", "Mollerussa")
            sistema = SistemaReg(arguments.get("sistema_reg", "aspersio"))

            async with IrrigationEngine() as engine:
                necessitat = await engine.calcular_necessitat_diaria(cultiu, municipi, sistema)
                return {
                    "data": necessitat.data.isoformat(),
                    "cultiu": necessitat.cultiu.value,
                    "municipi": necessitat.municipi,
                    "eto_mm": necessitat.eto_mm,
                    "kc": necessitat.kc,
                    "etc_mm": necessitat.etc_mm,
                    "pluja_mm": necessitat.pluja_mm,
                    "pluja_efectiva_mm": necessitat.pluja_efectiva_mm,
                    "deficit_mm": necessitat.deficit_mm,
                    "dosi_neta_mm": necessitat.dosi_neta_mm,
                    "dosi_bruta_mm": necessitat.dosi_bruta_mm,
                    "dosi_m3_ha": necessitat.dosi_bruta_mm * 10,
                    "sistema_reg": necessitat.sistema_reg.value,
                    "eficiencia": necessitat.eficiencia,
                    "regar": necessitat.regar,
                    "prioritat": necessitat.prioritat,
                    "motiu": necessitat.motiu,
                    "mode_sequera": necessitat.mode_sequera,
                    "factor_sequera": necessitat.factor_sequera,
                }

        elif nom_eina == "generar_pla_setmanal":
            cultiu = TipusCultiu(arguments["cultiu"])
            municipi = arguments.get("municipi", "Mollerussa")
            sistema = SistemaReg(arguments.get("sistema_reg", "aspersio"))

            async with IrrigationEngine() as engine:
                pla = await engine.calcular_pla_setmanal(cultiu, municipi, sistema)
                return {
                    "municipi": pla.municipi,
                    "cultiu": pla.cultiu.value,
                    "data_inici": pla.data_inici.isoformat(),
                    "data_fi": pla.data_fi.isoformat(),
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
                        for n in pla.dies
                    ],
                    "total_reg_mm": pla.total_reg_mm,
                    "total_reg_m3_ha": pla.total_reg_m3_ha,
                    "alertes": pla.alertes,
                }

        elif nom_eina == "generar_informe_complet":
            cultiu = TipusCultiu(arguments["cultiu"])
            municipi = arguments.get("municipi", "Mollerussa")
            sistema = SistemaReg(arguments.get("sistema_reg", "aspersio"))
            format_informe = arguments.get("format", "markdown")

            async with IrrigationEngine() as engine:
                dades = await engine.obtenir_resum_complet(cultiu, municipi, sistema)

            # Generar gràfics
            grafics = self.chart_generator.crear_tots_els_grafics(dades)

            # Generar informe
            if format_informe == "markdown":
                contingut = self.report_generator.generar_markdown(dades)
                return {"format": "markdown", "contingut": contingut}

            elif format_informe == "pdf":
                path = self.report_generator.generar_pdf(dades, grafics)
                return {"format": "pdf", "path": str(path)}

            elif format_informe == "docx":
                path = self.report_generator.generar_docx(dades, grafics)
                return {"format": "docx", "path": str(path)}

        elif nom_eina == "obtenir_info_cultiu":
            cultiu = TipusCultiu(arguments["cultiu"])
            info = obtenir_info_cultiu(cultiu)
            info["nom"] = NOMS_CULTIUS[cultiu]
            return info

        elif nom_eina == "llistar_municipis":
            return MUNICIPIS_ZONA_REGABLE

        elif nom_eina == "llistar_cultius":
            from ..cultius import COEFICIENTS_KC
            return {
                cultiu.value: {
                    "nom": NOMS_CULTIUS[cultiu],
                    "kc_ini": coef.kc_ini,
                    "kc_mid": coef.kc_mid,
                    "kc_end": coef.kc_end,
                    "profunditat_arrel_m": coef.profunditat_arrel,
                }
                for cultiu, coef in COEFICIENTS_KC.items()
            }

        return {"error": f"Eina desconeguda: {nom_eina}"}

    async def processar_consulta(self, consulta: str) -> str:
        """
        Processa una consulta de l'usuari.

        Args:
            consulta: Text de la consulta

        Returns:
            Resposta de l'agent
        """
        messages = [
            {"role": "user", "content": consulta}
        ]

        # Primera crida a l'API
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=self.SYSTEM_PROMPT,
            tools=self.tools,
            messages=messages
        )

        # Bucle per gestionar crides a eines
        while response.stop_reason == "tool_use":
            tool_uses = [block for block in response.content if block.type == "tool_use"]

            tool_results = []
            for tool_use in tool_uses:
                try:
                    result = await self._executar_eina(tool_use.name, tool_use.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": json.dumps(result, ensure_ascii=False, default=str)
                    })
                except Exception as e:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": json.dumps({"error": str(e)}),
                        "is_error": True
                    })

            # Afegir els missatges
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            # Següent crida
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=self.SYSTEM_PROMPT,
                tools=self.tools,
                messages=messages
            )

        # Extreure resposta final
        resposta_final = ""
        for block in response.content:
            if hasattr(block, "text"):
                resposta_final += block.text

        return resposta_final

    async def generar_informe_automatic(
        self,
        cultiu: TipusCultiu,
        municipi: str = "Mollerussa",
        sistema_reg: SistemaReg = SistemaReg.ASPERSIO,
        format_sortida: str = "markdown"
    ) -> Dict:
        """
        Genera un informe complet automàticament.

        Args:
            cultiu: Tipus de cultiu
            municipi: Municipi
            sistema_reg: Sistema de reg
            format_sortida: Format de l'informe (markdown, pdf, docx)

        Returns:
            Diccionari amb l'informe generat
        """
        # Obtenir dades
        async with IrrigationEngine() as engine:
            dades = await engine.obtenir_resum_complet(cultiu, municipi, sistema_reg)

        # Generar gràfics
        grafics = self.chart_generator.crear_tots_els_grafics(dades)

        # Generar anàlisi de riscos
        async with OpenWeatherClient() as weather:
            temps = await weather.obtenir_temperatures_extremes(municipi)

        from ..engine.irrigation import PlaReg
        from datetime import timedelta

        # Crear objecte PlaReg per a l'anàlisi
        pla_dies = []
        for dia in dades['pla_setmanal']['dies']:
            from ..engine.irrigation import NecessitatReg
            pla_dies.append(type('obj', (object,), dia)())

        analisi = self.decision_engine.analitzar_riscos(
            type('obj', (object,), {
                'dies': pla_dies,
                'municipi': municipi,
                'cultiu': cultiu,
            })(),
            temps
        )

        # Generar informe en el format sol·licitat
        if format_sortida == "markdown":
            contingut = self.report_generator.generar_markdown(dades)
            return {
                "format": "markdown",
                "contingut": contingut,
                "grafics": [str(g) for g in grafics],
                "riscos": {
                    "nivell": analisi.nivell.value,
                    "factors": analisi.factors,
                    "recomanacions": analisi.recomanacions_preventives,
                }
            }

        elif format_sortida == "pdf":
            path = self.report_generator.generar_pdf(dades, grafics)
            return {
                "format": "pdf",
                "path": str(path),
                "grafics": [str(g) for g in grafics],
            }

        elif format_sortida == "docx":
            path = self.report_generator.generar_docx(dades, grafics)
            return {
                "format": "docx",
                "path": str(path),
                "grafics": [str(g) for g in grafics],
            }

        return {"error": f"Format desconegut: {format_sortida}"}


# Funció síncrona per a ús des de la CLI
def consultar_agent_sync(consulta: str) -> str:
    """
    Versió síncrona de processar_consulta.

    Args:
        consulta: Text de la consulta

    Returns:
        Resposta de l'agent
    """
    agent = IrrigationAgent()
    return asyncio.run(agent.processar_consulta(consulta))


def generar_informe_sync(
    cultiu: str,
    municipi: str = "Mollerussa",
    sistema: str = "aspersio",
    format: str = "markdown"
) -> Dict:
    """
    Versió síncrona de generar_informe_automatic.

    Args:
        cultiu: Nom del cultiu
        municipi: Nom del municipi
        sistema: Sistema de reg
        format: Format de sortida

    Returns:
        Diccionari amb l'informe
    """
    agent = IrrigationAgent()
    return asyncio.run(agent.generar_informe_automatic(
        TipusCultiu(cultiu),
        municipi,
        SistemaReg(sistema),
        format
    ))
