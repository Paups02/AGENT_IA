#!/usr/bin/env python3
"""
Exemple d'ús bàsic de l'Agent de Reg dels Canals d'Urgell.

Aquest exemple mostra com:
1. Obtenir l'estat dels embassaments
2. Calcular la necessitat de reg per a un cultiu
3. Generar un informe tècnic complet
"""

import asyncio
import sys
sys.path.insert(0, '..')

from src.agent import IrrigationAgent
from src.cultius import TipusCultiu
from src.config import SistemaReg


async def exemple_consulta_agent():
    """Exemple de consulta interactiva a l'agent."""
    print("=" * 60)
    print("EXEMPLE 1: Consulta a l'Agent")
    print("=" * 60)

    agent = IrrigationAgent()

    consulta = "Quin és l'estat actual dels embassaments de Rialb i Oliana?"
    print(f"\nConsulta: {consulta}\n")

    resposta = await agent.processar_consulta(consulta)
    print("Resposta:")
    print(resposta)


async def exemple_calcul_necessitat():
    """Exemple de càlcul de necessitat de reg."""
    print("\n" + "=" * 60)
    print("EXEMPLE 2: Càlcul de Necessitat de Reg")
    print("=" * 60)

    from src.engine import IrrigationEngine

    async with IrrigationEngine() as engine:
        necessitat = await engine.calcular_necessitat_diaria(
            cultiu=TipusCultiu.PANIS,
            municipi="Mollerussa",
            sistema_reg=SistemaReg.ASPERSIO
        )

    print(f"\nCultiu: Panís (Blat de moro)")
    print(f"Municipi: Mollerussa")
    print(f"Data: {necessitat.data}")
    print(f"\nDades agrometeorològiques:")
    print(f"  - ETo: {necessitat.eto_mm:.2f} mm")
    print(f"  - Kc: {necessitat.kc:.2f}")
    print(f"  - ETc: {necessitat.etc_mm:.2f} mm")
    print(f"\nBalanç hídric:")
    print(f"  - Pluja prevista: {necessitat.pluja_mm:.1f} mm")
    print(f"  - Pluja efectiva: {necessitat.pluja_efectiva_mm:.2f} mm")
    print(f"  - Dèficit: {necessitat.deficit_mm:.2f} mm")
    print(f"\nDosi de reg:")
    print(f"  - Dosi neta: {necessitat.dosi_neta_mm:.2f} mm")
    print(f"  - Dosi bruta: {necessitat.dosi_bruta_mm:.2f} mm")
    print(f"  - Equivalent: {necessitat.dosi_bruta_mm * 10:.0f} m³/ha")
    print(f"\nRecomanació:")
    print(f"  - Regar: {'Sí' if necessitat.regar else 'No'}")
    print(f"  - Prioritat: {necessitat.prioritat}")
    print(f"  - Motiu: {necessitat.motiu}")

    if necessitat.mode_sequera:
        print(f"\n⚠️ MODE SEQUERA ACTIU - Factor: {necessitat.factor_sequera:.0%}")


async def exemple_informe_complet():
    """Exemple de generació d'informe complet."""
    print("\n" + "=" * 60)
    print("EXEMPLE 3: Generació d'Informe Complet")
    print("=" * 60)

    agent = IrrigationAgent()

    resultat = await agent.generar_informe_automatic(
        cultiu=TipusCultiu.ALFALS,
        municipi="Tàrrega",
        sistema_reg=SistemaReg.DEGOTEIG,
        format_sortida="markdown"
    )

    print("\nInforme generat en format Markdown:")
    print("-" * 40)
    # Mostrar només les primeres línies
    linies = resultat["contingut"].split("\n")[:50]
    print("\n".join(linies))
    print("\n[... informe complet truncat ...]")

    if resultat.get("grafics"):
        print(f"\nGràfics generats: {len(resultat['grafics'])}")
        for grafic in resultat["grafics"]:
            print(f"  - {grafic}")


async def exemple_pla_setmanal():
    """Exemple de generació de pla setmanal."""
    print("\n" + "=" * 60)
    print("EXEMPLE 4: Pla de Reg Setmanal")
    print("=" * 60)

    from src.engine import IrrigationEngine

    async with IrrigationEngine() as engine:
        pla = await engine.calcular_pla_setmanal(
            cultiu=TipusCultiu.FRUITA_PINYOL,
            municipi="Les Borges Blanques",
            sistema_reg=SistemaReg.DEGOTEIG,
            dies=7
        )

    print(f"\nPla de reg per a Fruita de pinyol")
    print(f"Període: {pla.data_inici} - {pla.data_fi}")
    print(f"Municipi: {pla.municipi}")
    print(f"\nDia a dia:")
    print("-" * 70)
    print(f"{'Data':<12} {'ETo':>6} {'ETc':>6} {'Pluja':>7} {'Reg':>8} {'Prioritat':<10}")
    print("-" * 70)

    for dia in pla.dies:
        reg = f"{dia.dosi_bruta_mm:.1f} mm" if dia.regar else "—"
        print(f"{dia.data!s:<12} {dia.eto_mm:>6.2f} {dia.etc_mm:>6.2f} {dia.pluja_mm:>7.1f} {reg:>8} {dia.prioritat:<10}")

    print("-" * 70)
    print(f"\nTotal setmana: {pla.total_reg_mm:.1f} mm ({pla.total_reg_m3_ha:.0f} m³/ha)")

    if pla.alertes:
        print("\nAlertes:")
        for alerta in pla.alertes:
            print(f"  ⚠️ {alerta}")


async def main():
    """Executa tots els exemples."""
    print("=" * 60)
    print("AGENT DE REG DELS CANALS D'URGELL")
    print("Exemples d'ús")
    print("=" * 60)

    try:
        await exemple_consulta_agent()
        await exemple_calcul_necessitat()
        await exemple_informe_complet()
        await exemple_pla_setmanal()

        print("\n" + "=" * 60)
        print("Tots els exemples executats correctament!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
