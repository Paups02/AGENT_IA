"""
Generador d'imatges conceptuals amb Gemini Pro.

Genera imatges educatives i tècniques:
- Esquema sòl-arrel-atmosfera
- Impacte de la sequera
- Comparativa reg òptim vs dèficit
"""

import google.generativeai as genai
from typing import Optional, Dict
from pathlib import Path
import base64
import io
from PIL import Image

from ..config import settings


class ImageGenerator:
    """
    Generador d'imatges conceptuals per a informes de reg.

    Utilitza Gemini Pro per generar descripcions detallades
    que es poden convertir en imatges o infografies.
    """

    def __init__(self):
        """Inicialitza el generador amb l'API de Gemini."""
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-pro')

    def generar_descripcio_esquema_sol_arrel(
        self,
        cultiu: str,
        profunditat_arrel: float,
        humitat_sol: float
    ) -> str:
        """
        Genera una descripció detallada de l'esquema sòl-arrel-atmosfera.

        Args:
            cultiu: Nom del cultiu
            profunditat_arrel: Profunditat radicular en metres
            humitat_sol: Percentatge d'humitat del sòl

        Returns:
            Descripció textual detallada
        """
        prompt = f"""
        Com a expert en agronomia, descriu un diagrama tècnic del sistema
        sòl-arrel-atmosfera per a un cultiu de {cultiu} amb les següents
        característiques:

        - Profunditat radicular: {profunditat_arrel} metres
        - Humitat del sòl: {humitat_sol}%

        El diagrama ha de mostrar:
        1. Capes del sòl (horitzons A, B, C)
        2. Sistema radicular del cultiu
        3. Moviment de l'aigua (capil·laritat, percolació)
        4. Evapotranspiració
        5. Zona d'absorció radicular

        Proporciona una descripció detallada en català, adequada per a un
        informe tècnic agrícola.
        """

        response = self.model.generate_content(prompt)
        return response.text

    def generar_descripcio_impacte_sequera(
        self,
        cultiu: str,
        nivell_sequera: str,
        reducció_reg: float
    ) -> str:
        """
        Genera una descripció de l'impacte de la sequera sobre el cultiu.

        Args:
            cultiu: Nom del cultiu
            nivell_sequera: Nivell de sequera (moderat, sever, extrem)
            reducció_reg: Percentatge de reducció en el reg

        Returns:
            Descripció de l'impacte i mesures
        """
        prompt = f"""
        Com a expert en fisiologia vegetal i gestió de l'aigua, descriu
        l'impacte de la sequera sobre un cultiu de {cultiu} en les següents
        condicions:

        - Nivell de sequera: {nivell_sequera}
        - Reducció del reg: {reducció_reg}%

        Descriu:
        1. Simptomes visibles d'estrès hídric
        2. Impacte fisiològic (tancament estomàtic, reducció fotosíntesi)
        3. Impacte sobre el rendiment esperat
        4. Mesures de mitigació recomanades
        5. Criteris per prioritzar el reg limitat

        Proporciona informació tècnica rigorosa en català.
        """

        response = self.model.generate_content(prompt)
        return response.text

    def generar_comparativa_reg(
        self,
        cultiu: str,
        etc_optim: float,
        reg_aplicat: float,
        fase_fenologica: str
    ) -> str:
        """
        Genera una comparativa entre reg òptim i reg aplicat.

        Args:
            cultiu: Nom del cultiu
            etc_optim: ETc òptima en mm
            reg_aplicat: Reg realment aplicat en mm
            fase_fenologica: Fase del cultiu

        Returns:
            Anàlisi comparativa
        """
        deficit = etc_optim - reg_aplicat
        percentatge_cobert = (reg_aplicat / etc_optim * 100) if etc_optim > 0 else 100

        prompt = f"""
        Com a enginyer agrònom especialista en reg, analitza la següent
        situació per a un cultiu de {cultiu} en fase {fase_fenologica}:

        - ETc òptima (FAO-56): {etc_optim:.1f} mm
        - Reg aplicat: {reg_aplicat:.1f} mm
        - Dèficit: {deficit:.1f} mm
        - Cobertura: {percentatge_cobert:.0f}%

        Proporciona:
        1. Valoració tècnica de la situació
        2. Impacte esperat sobre el cultiu
        3. Recomanacions per als propers dies
        4. Conseqüències a mitjà termini si continua el dèficit

        Utilitza terminologia tècnica adequada per a professionals agrícoles.
        Respon en català.
        """

        response = self.model.generate_content(prompt)
        return response.text

    def generar_infografia_balanc_hidric(
        self,
        etc: float,
        pluja: float,
        reg: float,
        evaporacio: float
    ) -> str:
        """
        Genera una descripció per a una infografia de balanç hídric.

        Args:
            etc: Evapotranspiració del cultiu (mm)
            pluja: Precipitació (mm)
            reg: Reg aplicat (mm)
            evaporacio: Evaporació directa (mm)

        Returns:
            Descripció per a infografia
        """
        entrades = pluja + reg
        sortides = etc + evaporacio
        balanc = entrades - sortides

        prompt = f"""
        Crea una descripció detallada per a una infografia de balanç hídric
        d'una parcel·la agrícola amb les següents dades:

        ENTRADES D'AIGUA:
        - Precipitació: {pluja:.1f} mm
        - Reg: {reg:.1f} mm
        - Total entrades: {entrades:.1f} mm

        SORTIDES D'AIGUA:
        - Evapotranspiració cultiu (ETc): {etc:.1f} mm
        - Evaporació directa: {evaporacio:.1f} mm
        - Total sortides: {sortides:.1f} mm

        BALANÇ NET: {balanc:+.1f} mm

        Descriu els elements visuals que hauria de tenir la infografia
        i la interpretació del balanç per a un agricultor professional.
        Respon en català amb terminologia tècnica.
        """

        response = self.model.generate_content(prompt)
        return response.text

    def generar_consells_personalitzats(
        self,
        cultiu: str,
        fase: str,
        situacio_hidrica: str,
        temperatures: Dict
    ) -> str:
        """
        Genera consells personalitzats per al maneig del reg.

        Args:
            cultiu: Tipus de cultiu
            fase: Fase fenològica
            situacio_hidrica: Situació dels embassaments
            temperatures: Dades de temperatura

        Returns:
            Consells personalitzats
        """
        temp_max = temperatures.get('temp_max', 30)
        temp_min = temperatures.get('temp_min', 15)
        onada_calor = temperatures.get('onada_calor', False)

        prompt = f"""
        Com a assessor agronòmic dels Canals d'Urgell, proporciona consells
        personalitzats per a un agricultor amb les següents condicions:

        CULTIU: {cultiu}
        FASE FENOLÒGICA: {fase}
        SITUACIÓ HÍDRICA: {situacio_hidrica}
        TEMPERATURES: Màxima {temp_max}°C, Mínima {temp_min}°C
        ONADA DE CALOR: {"Sí" if onada_calor else "No"}

        Proporciona:
        1. Recomanació principal de reg per als propers 3 dies
        2. Ajustos de maneig del cultiu
        3. Precaucions específiques
        4. Perspectives a 7 dies vista

        Els consells han de ser pràctics, directes i aplicables per un
        agricultor professional de la zona de Lleida.
        Respon en català.
        """

        response = self.model.generate_content(prompt)
        return response.text

    def generar_explicacio_metodologia_fao56(self) -> str:
        """
        Genera una explicació didàctica de la metodologia FAO-56.

        Returns:
            Explicació de la metodologia
        """
        prompt = """
        Explica de forma clara i tècnica la metodologia FAO-56 per al càlcul
        de necessitats de reg. L'explicació ha d'incloure:

        1. Què és l'ETo (evapotranspiració de referència) i com es calcula
           amb Penman-Monteith
        2. Què és el Kc (coeficient de cultiu) i com varia segons la fase
        3. Com es calcula l'ETc (ETc = ETo × Kc)
        4. Com es determina la dosi de reg considerant:
           - Pluja efectiva
           - Eficiència del sistema de reg
           - Reserves del sòl

        L'explicació ha de ser adequada per a un informe tècnic dirigit
        a agricultors professionals.
        Respon en català amb fórmules i exemples pràctics.
        """

        response = self.model.generate_content(prompt)
        return response.text
