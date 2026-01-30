"""
Interfície de línia de comandes per a l'Agent de Reg dels Canals d'Urgell.

Proporciona accés a totes les funcionalitats de l'agent:
- Consultes interactives
- Generació d'informes
- Càlcul de necessitats de reg
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich import print as rprint
from typing import Optional
import asyncio
from pathlib import Path

from .config import SistemaReg
from .cultius import TipusCultiu, NOMS_CULTIUS

app = typer.Typer(
    name="urgell-reg",
    help="Agent Expert en Hidràulica Agrícola per als Canals d'Urgell",
    add_completion=False
)

console = Console()


@app.command("consulta")
def consulta(
    text: str = typer.Argument(..., help="Text de la consulta"),
):
    """
    Realitza una consulta a l'agent de reg.

    Exemple:
        urgell-reg consulta "Quin és l'estat dels embassaments?"
    """
    from .agent import IrrigationAgent

    console.print("\n[bold blue]Agent de Reg dels Canals d'Urgell[/bold blue]\n")
    console.print(f"[dim]Consulta: {text}[/dim]\n")

    with console.status("[bold green]Processant consulta..."):
        agent = IrrigationAgent()
        resposta = asyncio.run(agent.processar_consulta(text))

    console.print(Panel(Markdown(resposta), title="Resposta", border_style="green"))


@app.command("informe")
def generar_informe(
    cultiu: str = typer.Argument(..., help="Tipus de cultiu (ex: panis, alfals, ametller)"),
    municipi: str = typer.Option("Mollerussa", "--municipi", "-m", help="Municipi"),
    sistema: str = typer.Option("aspersio", "--sistema", "-s", help="Sistema de reg"),
    format: str = typer.Option("markdown", "--format", "-f", help="Format de sortida (markdown, pdf, docx)"),
):
    """
    Genera un informe tècnic de reg.

    Exemple:
        urgell-reg informe panis -m Tàrrega -s degoteig -f pdf
    """
    from .agent import IrrigationAgent

    console.print("\n[bold blue]Generant informe tècnic...[/bold blue]\n")

    try:
        tipus_cultiu = TipusCultiu(cultiu)
        sistema_reg = SistemaReg(sistema)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    with console.status("[bold green]Calculant necessitats de reg i generant informe..."):
        agent = IrrigationAgent()
        resultat = asyncio.run(agent.generar_informe_automatic(
            tipus_cultiu, municipi, sistema_reg, format
        ))

    if "error" in resultat:
        console.print(f"[red]Error: {resultat['error']}[/red]")
        raise typer.Exit(1)

    if format == "markdown":
        console.print(Panel(Markdown(resultat["contingut"]), title="Informe de Reg", border_style="green"))
    else:
        console.print(f"[green]Informe generat: {resultat['path']}[/green]")

    if resultat.get("grafics"):
        console.print("\n[bold]Gràfics generats:[/bold]")
        for grafic in resultat["grafics"]:
            console.print(f"  • {grafic}")


@app.command("necessitat")
def calcular_necessitat(
    cultiu: str = typer.Argument(..., help="Tipus de cultiu"),
    municipi: str = typer.Option("Mollerussa", "--municipi", "-m", help="Municipi"),
    sistema: str = typer.Option("aspersio", "--sistema", "-s", help="Sistema de reg"),
):
    """
    Calcula la necessitat de reg per avui.

    Exemple:
        urgell-reg necessitat alfals -m Balaguer
    """
    from .engine import IrrigationEngine

    console.print("\n[bold blue]Calculant necessitat de reg...[/bold blue]\n")

    try:
        tipus_cultiu = TipusCultiu(cultiu)
        sistema_reg = SistemaReg(sistema)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    async def calcular():
        async with IrrigationEngine() as engine:
            return await engine.calcular_necessitat_diaria(
                tipus_cultiu, municipi, sistema_reg
            )

    with console.status("[bold green]Obtenint dades i calculant..."):
        necessitat = asyncio.run(calcular())

    # Mostrar resultats
    table = Table(title=f"Necessitat de Reg - {NOMS_CULTIUS[tipus_cultiu]}")
    table.add_column("Paràmetre", style="cyan")
    table.add_column("Valor", style="green")

    table.add_row("Data", str(necessitat.data))
    table.add_row("Municipi", necessitat.municipi)
    table.add_row("ETo (mm)", f"{necessitat.eto_mm:.2f}")
    table.add_row("Kc", f"{necessitat.kc:.2f}")
    table.add_row("ETc (mm)", f"{necessitat.etc_mm:.2f}")
    table.add_row("Pluja prevista (mm)", f"{necessitat.pluja_mm:.1f}")
    table.add_row("Pluja efectiva (mm)", f"{necessitat.pluja_efectiva_mm:.2f}")
    table.add_row("Dèficit (mm)", f"{necessitat.deficit_mm:.2f}")
    table.add_row("Dosi neta (mm)", f"{necessitat.dosi_neta_mm:.2f}")
    table.add_row("Dosi bruta (mm)", f"{necessitat.dosi_bruta_mm:.2f}")
    table.add_row("Dosi (m³/ha)", f"{necessitat.dosi_bruta_mm * 10:.0f}")

    console.print(table)

    # Recomanació
    if necessitat.regar:
        console.print(Panel(
            f"[bold green]✅ REGAR: {necessitat.dosi_bruta_mm:.1f} mm ({necessitat.dosi_bruta_mm * 10:.0f} m³/ha)[/bold green]\n\n"
            f"Prioritat: {necessitat.prioritat.upper()}\n"
            f"Motiu: {necessitat.motiu}",
            title="Recomanació",
            border_style="green"
        ))
    else:
        console.print(Panel(
            f"[bold yellow]❌ NO CAL REGAR AVUI[/bold yellow]\n\n"
            f"Motiu: {necessitat.motiu}",
            title="Recomanació",
            border_style="yellow"
        ))

    if necessitat.mode_sequera:
        console.print(Panel(
            f"[bold red]⚠️ MODE SEQUERA ACTIU[/bold red]\n"
            f"Factor de reducció: {necessitat.factor_sequera:.0%}",
            border_style="red"
        ))


@app.command("embassaments")
def estat_embassaments():
    """
    Mostra l'estat actual dels embassaments.
    """
    from .api_clients import HydrologyClient

    console.print("\n[bold blue]Estat dels Embassaments - Conca del Segre[/bold blue]\n")

    async def obtenir():
        async with HydrologyClient() as client:
            return await client.obtenir_resum_hidrologic()

    with console.status("[bold green]Obtenint dades..."):
        dades = asyncio.run(obtenir())

    table = Table(title="Embassaments")
    table.add_column("Nom", style="cyan")
    table.add_column("Volum (hm³)", justify="right")
    table.add_column("Capacitat (hm³)", justify="right")
    table.add_column("Nivell (%)", justify="right")

    for emb in dades.get("embassaments", []):
        # Color segons nivell
        nivell = emb["percentatge"]
        if nivell >= 50:
            style = "green"
        elif nivell >= 35:
            style = "yellow"
        else:
            style = "red"

        table.add_row(
            emb["nom"],
            f"{emb['volum_hm3']:.1f}",
            f"{emb['capacitat_hm3']:.1f}",
            f"[{style}]{nivell:.1f}%[/{style}]"
        )

    console.print(table)

    sistema = dades.get("sistema", {})
    console.print(f"\n[bold]Estat global:[/bold] {sistema.get('estat', '').upper()}")
    console.print(f"[dim]{sistema.get('estat_descripcio', '')}[/dim]")

    sequera = dades.get("sequera", {})
    if sequera.get("mode_actiu"):
        console.print(Panel(
            f"[bold red]⚠️ MODE SEQUERA ACTIU[/bold red]\n"
            f"Reducció del reg: {sequera.get('reduccio_percentatge', 0):.0f}%",
            border_style="red"
        ))


@app.command("meteo")
def meteo(
    municipi: str = typer.Argument("Mollerussa", help="Municipi"),
):
    """
    Mostra les dades meteorològiques d'un municipi.
    """
    from .api_clients import OpenWeatherClient

    console.print(f"\n[bold blue]Dades Meteorològiques - {municipi}[/bold blue]\n")

    async def obtenir():
        async with OpenWeatherClient() as client:
            return await client.obtenir_resum_meteo(municipi)

    with console.status("[bold green]Obtenint dades..."):
        dades = asyncio.run(obtenir())

    actual = dades.get("actual", {})
    table = Table(title="Condicions Actuals")
    table.add_column("Paràmetre", style="cyan")
    table.add_column("Valor", style="green")

    table.add_row("Temperatura", f"{actual.get('temperatura', 0):.1f} °C")
    table.add_row("Humitat", f"{actual.get('humitat', 0):.0f}%")
    table.add_row("Vent", f"{actual.get('vent_ms', 0):.1f} m/s")
    table.add_row("Nuvolositat", f"{actual.get('nuvolositat', 0):.0f}%")
    table.add_row("Descripció", actual.get("descripcio", ""))

    console.print(table)

    pluja = dades.get("pluja", {})
    console.print(f"\n[bold]Precipitació:[/bold]")
    console.print(f"  • Última hora: {pluja.get('ultima_hora_mm', 0):.1f} mm")
    console.print(f"  • Prevista 24h: {pluja.get('prevista_24h_mm', 0):.1f} mm")
    console.print(f"  • Prevista 48h: {pluja.get('prevista_48h_mm', 0):.1f} mm")

    if pluja.get("posposar_reg"):
        console.print(Panel(
            "[yellow]Es recomana posposar el reg per pluja prevista[/yellow]",
            border_style="yellow"
        ))

    alertes = dades.get("alertes", {})
    if alertes.get("onada_calor"):
        console.print(Panel(
            f"[red]🌡️ Onada de calor prevista: {alertes.get('dies_calor_extrema', 0)} dies >35°C[/red]\n"
            f"Temperatura màxima prevista: {alertes.get('temp_max_setmana', 0):.1f}°C",
            border_style="red"
        ))


@app.command("cultius")
def llistar_cultius():
    """
    Llista tots els cultius suportats.
    """
    from .cultius import COEFICIENTS_KC

    table = Table(title="Cultius Suportats")
    table.add_column("Codi", style="cyan")
    table.add_column("Nom", style="green")
    table.add_column("Kc inicial")
    table.add_column("Kc mitjà")
    table.add_column("Kc final")
    table.add_column("Prof. arrel (m)")

    for cultiu, coef in COEFICIENTS_KC.items():
        table.add_row(
            cultiu.value,
            NOMS_CULTIUS[cultiu],
            f"{coef.kc_ini:.2f}",
            f"{coef.kc_mid:.2f}",
            f"{coef.kc_end:.2f}",
            f"{coef.profunditat_arrel:.1f}"
        )

    console.print(table)


@app.command("municipis")
def llistar_municipis():
    """
    Llista tots els municipis de la zona regable.
    """
    from .config import MUNICIPIS_ZONA_REGABLE

    for comarca, municipis in MUNICIPIS_ZONA_REGABLE.items():
        console.print(f"\n[bold cyan]{comarca}[/bold cyan]")
        for m in municipis:
            console.print(f"  • {m}")


@app.command("interactiu")
def mode_interactiu():
    """
    Inicia el mode interactiu per a conversar amb l'agent.
    """
    from .agent import IrrigationAgent

    console.print(Panel(
        "[bold blue]Agent Expert en Hidràulica Agrícola[/bold blue]\n"
        "[dim]Canals d'Urgell - Lleida[/dim]\n\n"
        "Escriu les teves consultes sobre reg, embassaments, cultius...\n"
        "Escriu 'sortir' per acabar.",
        title="Mode Interactiu",
        border_style="blue"
    ))

    agent = IrrigationAgent()

    while True:
        try:
            consulta = console.input("\n[bold green]Tu>[/bold green] ")

            if consulta.lower() in ["sortir", "exit", "quit", "q"]:
                console.print("[dim]Adéu![/dim]")
                break

            if not consulta.strip():
                continue

            with console.status("[bold green]Pensant..."):
                resposta = asyncio.run(agent.processar_consulta(consulta))

            console.print(f"\n[bold blue]Agent>[/bold blue]")
            console.print(Markdown(resposta))

        except KeyboardInterrupt:
            console.print("\n[dim]Adéu![/dim]")
            break


def main():
    """Punt d'entrada principal."""
    app()


if __name__ == "__main__":
    main()
