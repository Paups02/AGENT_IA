"""
Generador de gràfics per a informes de reg.

Utilitza matplotlib per crear visualitzacions tècniques:
- Evolució ETo
- Balanç hídric
- Temperatura i humitat
- Estat dels embassaments
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Patch
from matplotlib.figure import Figure
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import date, datetime
from pathlib import Path
import io

# Configuració d'estil professional
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['font.size'] = 10
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['axes.labelsize'] = 10

# Colors corporatius
COLORS = {
    'blau_aigua': '#1976D2',
    'verd_cultiu': '#388E3C',
    'taronja_alerta': '#F57C00',
    'vermell_emergencia': '#D32F2F',
    'gris_fons': '#F5F5F5',
    'blau_clar': '#BBDEFB',
    'verd_clar': '#C8E6C9',
}


class ChartGenerator:
    """Generador de gràfics per a informes de reg."""

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Inicialitza el generador.

        Args:
            output_dir: Directori de sortida per als gràfics
        """
        self.output_dir = output_dir or Path("output/charts")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _save_or_return(
        self,
        fig: Figure,
        filename: Optional[str] = None
    ) -> Tuple[Optional[Path], bytes]:
        """
        Guarda el gràfic o retorna els bytes.

        Args:
            fig: Figura matplotlib
            filename: Nom del fitxer (opcional)

        Returns:
            Tuple amb path (si es guarda) i bytes de la imatge
        """
        # Generar bytes
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        buffer.seek(0)
        img_bytes = buffer.getvalue()

        # Guardar si hi ha filename
        path = None
        if filename:
            path = self.output_dir / filename
            fig.savefig(path, dpi=150, bbox_inches='tight',
                       facecolor='white', edgecolor='none')

        plt.close(fig)
        return path, img_bytes

    def crear_grafic_eto(
        self,
        dies: List[Dict],
        filename: Optional[str] = None
    ) -> Tuple[Optional[Path], bytes]:
        """
        Crea un gràfic de l'evolució de l'ETo.

        Args:
            dies: Llista de dades diàries amb 'data' i 'eto_mm'
            filename: Nom del fitxer de sortida

        Returns:
            Path del fitxer i bytes de la imatge
        """
        fig, ax = plt.subplots(figsize=(10, 5))

        dates = [datetime.fromisoformat(d['data']) for d in dies]
        eto_values = [d['eto_mm'] for d in dies]
        etc_values = [d.get('etc_mm', d['eto_mm']) for d in dies]

        # Gràfic de barres per ETo
        x = np.arange(len(dates))
        width = 0.35

        bars1 = ax.bar(x - width/2, eto_values, width, label='ETo',
                      color=COLORS['blau_aigua'], alpha=0.8)
        bars2 = ax.bar(x + width/2, etc_values, width, label='ETc',
                      color=COLORS['verd_cultiu'], alpha=0.8)

        # Línia de mitjana
        mitjana_eto = np.mean(eto_values)
        ax.axhline(y=mitjana_eto, color=COLORS['taronja_alerta'],
                  linestyle='--', linewidth=1.5, label=f'Mitjana ETo: {mitjana_eto:.1f} mm')

        # Format
        ax.set_xlabel('Data')
        ax.set_ylabel('Evapotranspiració (mm/dia)')
        ax.set_title('Evolució de l\'Evapotranspiració (FAO-56)')
        ax.set_xticks(x)
        ax.set_xticklabels([d.strftime('%d/%m') for d in dates], rotation=45)
        ax.legend(loc='upper right')
        ax.set_ylim(bottom=0)

        # Afegir valors sobre les barres
        for bar in bars1:
            height = bar.get_height()
            ax.annotate(f'{height:.1f}',
                       xy=(bar.get_x() + bar.get_width()/2, height),
                       xytext=(0, 3), textcoords="offset points",
                       ha='center', va='bottom', fontsize=8)

        fig.tight_layout()
        return self._save_or_return(fig, filename)

    def crear_grafic_balanc_hidric(
        self,
        dies: List[Dict],
        filename: Optional[str] = None
    ) -> Tuple[Optional[Path], bytes]:
        """
        Crea un gràfic del balanç hídric.

        Args:
            dies: Llista de dades diàries amb ETc, pluja i reg
            filename: Nom del fitxer de sortida

        Returns:
            Path del fitxer i bytes de la imatge
        """
        fig, ax = plt.subplots(figsize=(12, 6))

        dates = [datetime.fromisoformat(d['data']) for d in dies]
        x = np.arange(len(dates))

        # Extreure dades
        etc = [d.get('etc_mm', 0) for d in dies]
        pluja = [d.get('pluja_mm', 0) for d in dies]
        reg = [d.get('dosi_bruta_mm', 0) if d.get('regar', False) else 0 for d in dies]
        deficit = [max(0, e - p) for e, p in zip(etc, pluja)]

        # Gràfic de barres apilades
        width = 0.8

        # ETc com a demanda (negatiu per visualització)
        ax.bar(x, [-e for e in etc], width, label='ETc (demanda)',
              color=COLORS['taronja_alerta'], alpha=0.7)

        # Pluja i reg com a aportacions (positiu)
        ax.bar(x, pluja, width, label='Pluja',
              color=COLORS['blau_clar'], alpha=0.9)
        ax.bar(x, reg, width, bottom=pluja, label='Reg',
              color=COLORS['blau_aigua'], alpha=0.8)

        # Línia de balanç
        balanc = [p + r - e for p, r, e in zip(pluja, reg, etc)]
        ax.plot(x, balanc, 'ko-', markersize=6, linewidth=2,
               label='Balanç net')

        # Zona d'equilibri
        ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
        ax.fill_between(x, 0, [min(0, b) for b in balanc],
                       color=COLORS['vermell_emergencia'], alpha=0.2)

        # Format
        ax.set_xlabel('Data')
        ax.set_ylabel('Aigua (mm)')
        ax.set_title('Balanç Hídric Diari')
        ax.set_xticks(x)
        ax.set_xticklabels([d.strftime('%d/%m') for d in dates], rotation=45)
        ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1))

        fig.tight_layout()
        return self._save_or_return(fig, filename)

    def crear_grafic_temperatura_humitat(
        self,
        dies: List[Dict],
        filename: Optional[str] = None
    ) -> Tuple[Optional[Path], bytes]:
        """
        Crea un gràfic combinat de temperatura i humitat.

        Args:
            dies: Llista de dades amb temperatura i humitat
            filename: Nom del fitxer de sortida

        Returns:
            Path del fitxer i bytes de la imatge
        """
        fig, ax1 = plt.subplots(figsize=(10, 5))

        dates = [datetime.fromisoformat(d['data']) for d in dies]
        x = np.arange(len(dates))

        # Temperatures
        temp_max = [d.get('temp_max', d.get('temperatura_max', 25)) for d in dies]
        temp_min = [d.get('temp_min', d.get('temperatura_min', 15)) for d in dies]
        temp_mitjana = [(tmax + tmin) / 2 for tmax, tmin in zip(temp_max, temp_min)]

        # Gràfic de temperatura
        ax1.fill_between(x, temp_min, temp_max, alpha=0.3, color=COLORS['vermell_emergencia'],
                        label='Rang tèrmic')
        ax1.plot(x, temp_mitjana, 'r-o', linewidth=2, markersize=6,
                label='T mitjana')
        ax1.set_xlabel('Data')
        ax1.set_ylabel('Temperatura (°C)', color='red')
        ax1.tick_params(axis='y', labelcolor='red')
        ax1.set_ylim(0, max(temp_max) + 5)

        # Línia de 35°C (onada de calor)
        ax1.axhline(y=35, color='red', linestyle='--', alpha=0.5, linewidth=1)
        ax1.text(len(x)-1, 36, 'Llindar onada calor', fontsize=8, color='red', ha='right')

        # Segon eix per humitat
        ax2 = ax1.twinx()
        humitat = [d.get('humitat', d.get('humitat_mitjana', 50)) for d in dies]
        ax2.plot(x, humitat, 'b-s', linewidth=2, markersize=6,
                label='Humitat relativa')
        ax2.set_ylabel('Humitat relativa (%)', color='blue')
        ax2.tick_params(axis='y', labelcolor='blue')
        ax2.set_ylim(0, 100)

        # Format
        ax1.set_title('Evolució de Temperatura i Humitat')
        ax1.set_xticks(x)
        ax1.set_xticklabels([d.strftime('%d/%m') for d in dates], rotation=45)

        # Llegenda combinada
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')

        fig.tight_layout()
        return self._save_or_return(fig, filename)

    def crear_grafic_embassaments(
        self,
        embassaments: List[Dict],
        llindars: Optional[Dict] = None,
        filename: Optional[str] = None
    ) -> Tuple[Optional[Path], bytes]:
        """
        Crea un gràfic de l'estat dels embassaments.

        Args:
            embassaments: Llista amb dades de cada embassament
            llindars: Llindars d'alerta (opcional)
            filename: Nom del fitxer de sortida

        Returns:
            Path del fitxer i bytes de la imatge
        """
        if llindars is None:
            llindars = {
                'normalitat': 50,
                'prealerta': 35,
                'alerta': 20,
            }

        fig, ax = plt.subplots(figsize=(10, 6))

        noms = [e['nom'] for e in embassaments]
        percentatges = [e['percentatge'] for e in embassaments]
        capacitats = [e['capacitat_hm3'] for e in embassaments]
        volums = [e['volum_hm3'] for e in embassaments]

        x = np.arange(len(noms))
        width = 0.6

        # Colors segons nivell
        colors = []
        for p in percentatges:
            if p >= llindars['normalitat']:
                colors.append(COLORS['verd_cultiu'])
            elif p >= llindars['prealerta']:
                colors.append(COLORS['taronja_alerta'])
            else:
                colors.append(COLORS['vermell_emergencia'])

        # Barres de percentatge
        bars = ax.bar(x, percentatges, width, color=colors, alpha=0.8, edgecolor='black')

        # Línies de llindar
        for llindar, valor in llindars.items():
            ax.axhline(y=valor, linestyle='--', linewidth=1.5, alpha=0.7,
                      label=f'{llindar.capitalize()}: {valor}%')

        # Etiquetes sobre les barres
        for bar, vol, cap in zip(bars, volums, capacitats):
            height = bar.get_height()
            ax.annotate(f'{height:.1f}%\n({vol:.0f}/{cap:.0f} hm³)',
                       xy=(bar.get_x() + bar.get_width()/2, height),
                       xytext=(0, 3), textcoords="offset points",
                       ha='center', va='bottom', fontsize=9, fontweight='bold')

        # Format
        ax.set_xlabel('Embassament')
        ax.set_ylabel('Nivell (%)')
        ax.set_title('Estat dels Embassaments - Conca del Segre')
        ax.set_xticks(x)
        ax.set_xticklabels(noms, fontsize=11, fontweight='bold')
        ax.set_ylim(0, 110)
        ax.legend(loc='upper right')

        # Llegenda de colors
        legend_elements = [
            Patch(facecolor=COLORS['verd_cultiu'], label='Normalitat'),
            Patch(facecolor=COLORS['taronja_alerta'], label='Prealerta'),
            Patch(facecolor=COLORS['vermell_emergencia'], label='Alerta/Emergència'),
        ]
        ax.legend(handles=legend_elements, loc='upper left')

        fig.tight_layout()
        return self._save_or_return(fig, filename)

    def crear_grafic_pla_setmanal(
        self,
        pla: Dict,
        filename: Optional[str] = None
    ) -> Tuple[Optional[Path], bytes]:
        """
        Crea un gràfic visual del pla de reg setmanal.

        Args:
            pla: Diccionari amb el pla de reg
            filename: Nom del fitxer de sortida

        Returns:
            Path del fitxer i bytes de la imatge
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), height_ratios=[2, 1])

        dies = pla['dies']
        dates = [datetime.fromisoformat(d['data']) for d in dies]
        x = np.arange(len(dates))

        # Gràfic superior: ETo, ETc i pluja
        etc = [d['etc_mm'] for d in dies]
        pluja = [d['pluja_mm'] for d in dies]
        dosi = [d['dosi_bruta_mm'] if d['regar'] else 0 for d in dies]

        ax1.bar(x - 0.2, etc, 0.4, label='ETc', color=COLORS['taronja_alerta'], alpha=0.7)
        ax1.bar(x + 0.2, pluja, 0.4, label='Pluja', color=COLORS['blau_clar'], alpha=0.9)
        ax1.bar(x + 0.2, dosi, 0.4, bottom=pluja, label='Reg', color=COLORS['blau_aigua'], alpha=0.8)

        ax1.set_ylabel('Aigua (mm)')
        ax1.set_title(f'Pla de Reg Setmanal - {pla.get("municipi", "")}')
        ax1.set_xticks(x)
        ax1.set_xticklabels([d.strftime('%a\n%d/%m') for d in dates])
        ax1.legend(loc='upper right')

        # Gràfic inferior: Indicadors de reg
        regar = [d['regar'] for d in dies]
        prioritats = [d['prioritat'] for d in dies]

        colors_prioritat = {
            'alta': COLORS['vermell_emergencia'],
            'mitjana': COLORS['taronja_alerta'],
            'baixa': COLORS['verd_cultiu'],
            'nul·la': COLORS['gris_fons'],
        }

        for i, (r, p) in enumerate(zip(regar, prioritats)):
            color = colors_prioritat.get(p, COLORS['gris_fons'])
            ax2.bar(i, 1, 0.8, color=color, alpha=0.8, edgecolor='black')

            if r:
                ax2.text(i, 0.5, f'{dosi[i]:.1f}\nmm', ha='center', va='center',
                        fontsize=10, fontweight='bold')
            else:
                ax2.text(i, 0.5, '—', ha='center', va='center',
                        fontsize=14, color='gray')

        ax2.set_ylabel('Recomanació')
        ax2.set_yticks([])
        ax2.set_xticks(x)
        ax2.set_xticklabels([d.strftime('%a\n%d/%m') for d in dates])

        # Llegenda
        legend_elements = [
            Patch(facecolor=colors_prioritat['alta'], label='Prioritat alta'),
            Patch(facecolor=colors_prioritat['mitjana'], label='Prioritat mitjana'),
            Patch(facecolor=colors_prioritat['baixa'], label='Prioritat baixa'),
            Patch(facecolor=colors_prioritat['nul·la'], label='Sense reg'),
        ]
        ax2.legend(handles=legend_elements, loc='upper right', ncol=4)

        fig.tight_layout()
        return self._save_or_return(fig, filename)

    def crear_tots_els_grafics(
        self,
        dades_completes: Dict,
        prefix: str = "informe"
    ) -> List[Path]:
        """
        Crea tots els gràfics necessaris per a un informe.

        Args:
            dades_completes: Diccionari amb totes les dades
            prefix: Prefix per als noms de fitxer

        Returns:
            Llista de paths dels fitxers creats
        """
        paths = []

        # Gràfic ETo
        if 'pla_setmanal' in dades_completes and 'dies' in dades_completes['pla_setmanal']:
            path, _ = self.crear_grafic_eto(
                dades_completes['pla_setmanal']['dies'],
                f"{prefix}_eto.png"
            )
            if path:
                paths.append(path)

            path, _ = self.crear_grafic_balanc_hidric(
                dades_completes['pla_setmanal']['dies'],
                f"{prefix}_balanc.png"
            )
            if path:
                paths.append(path)

            path, _ = self.crear_grafic_pla_setmanal(
                dades_completes['pla_setmanal'],
                f"{prefix}_pla.png"
            )
            if path:
                paths.append(path)

        # Gràfic embassaments
        if 'estat_hidrologic' in dades_completes and 'embassaments' in dades_completes['estat_hidrologic']:
            path, _ = self.crear_grafic_embassaments(
                dades_completes['estat_hidrologic']['embassaments'],
                filename=f"{prefix}_embassaments.png"
            )
            if path:
                paths.append(path)

        return paths
