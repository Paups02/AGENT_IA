"""
Coeficients de cultiu (Kc) segons FAO-56 per als cultius de la zona dels Canals d'Urgell.

Els valors Kc s'ajusten segons:
- Tipus de cultiu
- Fase fenològica
- Condicions climàtiques locals

Referències:
- FAO Irrigation and Drainage Paper No. 56 (Allen et al., 1998)
- Adaptacions locals IRTA/SIGPAC
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum
from datetime import date


class FaseFenologica(str, Enum):
    """Fases fenològiques segons FAO-56."""
    INICIAL = "inicial"           # Germinació - 10% cobertura
    DESENVOLUPAMENT = "desenvolupament"  # 10% - 80% cobertura
    MITJA_TEMPORADA = "mitja_temporada"  # 80% - inici senescència
    FINAL = "final"               # Maduració - collita


class TipusCultiu(str, Enum):
    """Cultius principals de la zona regable dels Canals d'Urgell."""
    PANIS = "panis"                    # Blat de moro
    ALFALS = "alfals"                  # Alfals
    FRUITA_PINYOL = "fruita_pinyol"    # Préssec, nectarina, cirera
    FRUITA_LLAVOR = "fruita_llavor"    # Poma, pera
    CEREAL_HIVERN = "cereal_hivern"    # Blat, ordi
    AMETLLER = "ametller"
    OLIVERA = "olivera"
    HORTICOLES = "horticoles"          # Hortícoles extensives
    VINYA = "vinya"
    GIRA_SOL = "gira_sol"
    COLZA = "colza"
    SORGO = "sorgo"


@dataclass
class CoeficientKc:
    """
    Coeficients Kc per a cada fase fenològica d'un cultiu.

    Attributes:
        kc_ini: Kc fase inicial
        kc_mid: Kc fase de mitja temporada (màxim)
        kc_end: Kc fase final
        profunditat_arrel: Profunditat radicular efectiva (m)
        altura_maxima: Altura màxima del cultiu (m)
    """
    kc_ini: float
    kc_mid: float
    kc_end: float
    profunditat_arrel: float
    altura_maxima: float
    durada_fases: Dict[FaseFenologica, int]  # Dies per fase


# Coeficients Kc segons FAO-56 adaptats a la zona dels Canals d'Urgell
COEFICIENTS_KC: Dict[TipusCultiu, CoeficientKc] = {
    TipusCultiu.PANIS: CoeficientKc(
        kc_ini=0.30,
        kc_mid=1.20,
        kc_end=0.60,
        profunditat_arrel=1.0,
        altura_maxima=2.5,
        durada_fases={
            FaseFenologica.INICIAL: 25,
            FaseFenologica.DESENVOLUPAMENT: 40,
            FaseFenologica.MITJA_TEMPORADA: 45,
            FaseFenologica.FINAL: 30
        }
    ),
    TipusCultiu.ALFALS: CoeficientKc(
        kc_ini=0.40,
        kc_mid=1.20,
        kc_end=1.15,
        profunditat_arrel=1.5,
        altura_maxima=0.7,
        durada_fases={
            FaseFenologica.INICIAL: 10,
            FaseFenologica.DESENVOLUPAMENT: 20,
            FaseFenologica.MITJA_TEMPORADA: 20,
            FaseFenologica.FINAL: 10
        }
    ),
    TipusCultiu.FRUITA_PINYOL: CoeficientKc(
        kc_ini=0.45,
        kc_mid=1.15,
        kc_end=0.90,
        profunditat_arrel=1.5,
        altura_maxima=4.0,
        durada_fases={
            FaseFenologica.INICIAL: 30,
            FaseFenologica.DESENVOLUPAMENT: 50,
            FaseFenologica.MITJA_TEMPORADA: 90,
            FaseFenologica.FINAL: 30
        }
    ),
    TipusCultiu.FRUITA_LLAVOR: CoeficientKc(
        kc_ini=0.45,
        kc_mid=1.20,
        kc_end=0.95,
        profunditat_arrel=1.5,
        altura_maxima=4.0,
        durada_fases={
            FaseFenologica.INICIAL: 30,
            FaseFenologica.DESENVOLUPAMENT: 50,
            FaseFenologica.MITJA_TEMPORADA: 100,
            FaseFenologica.FINAL: 30
        }
    ),
    TipusCultiu.CEREAL_HIVERN: CoeficientKc(
        kc_ini=0.30,
        kc_mid=1.15,
        kc_end=0.40,
        profunditat_arrel=1.0,
        altura_maxima=1.0,
        durada_fases={
            FaseFenologica.INICIAL: 30,
            FaseFenologica.DESENVOLUPAMENT: 140,
            FaseFenologica.MITJA_TEMPORADA: 40,
            FaseFenologica.FINAL: 30
        }
    ),
    TipusCultiu.AMETLLER: CoeficientKc(
        kc_ini=0.40,
        kc_mid=1.10,
        kc_end=0.85,
        profunditat_arrel=2.0,
        altura_maxima=5.0,
        durada_fases={
            FaseFenologica.INICIAL: 30,
            FaseFenologica.DESENVOLUPAMENT: 60,
            FaseFenologica.MITJA_TEMPORADA: 90,
            FaseFenologica.FINAL: 30
        }
    ),
    TipusCultiu.OLIVERA: CoeficientKc(
        kc_ini=0.65,
        kc_mid=0.70,
        kc_end=0.70,
        profunditat_arrel=1.5,
        altura_maxima=5.0,
        durada_fases={
            FaseFenologica.INICIAL: 30,
            FaseFenologica.DESENVOLUPAMENT: 90,
            FaseFenologica.MITJA_TEMPORADA: 60,
            FaseFenologica.FINAL: 90
        }
    ),
    TipusCultiu.HORTICOLES: CoeficientKc(
        kc_ini=0.50,
        kc_mid=1.05,
        kc_end=0.90,
        profunditat_arrel=0.6,
        altura_maxima=0.6,
        durada_fases={
            FaseFenologica.INICIAL: 25,
            FaseFenologica.DESENVOLUPAMENT: 35,
            FaseFenologica.MITJA_TEMPORADA: 40,
            FaseFenologica.FINAL: 20
        }
    ),
    TipusCultiu.VINYA: CoeficientKc(
        kc_ini=0.30,
        kc_mid=0.85,
        kc_end=0.45,
        profunditat_arrel=1.5,
        altura_maxima=2.0,
        durada_fases={
            FaseFenologica.INICIAL: 30,
            FaseFenologica.DESENVOLUPAMENT: 60,
            FaseFenologica.MITJA_TEMPORADA: 70,
            FaseFenologica.FINAL: 40
        }
    ),
    TipusCultiu.GIRA_SOL: CoeficientKc(
        kc_ini=0.35,
        kc_mid=1.15,
        kc_end=0.35,
        profunditat_arrel=1.5,
        altura_maxima=2.0,
        durada_fases={
            FaseFenologica.INICIAL: 25,
            FaseFenologica.DESENVOLUPAMENT: 35,
            FaseFenologica.MITJA_TEMPORADA: 45,
            FaseFenologica.FINAL: 25
        }
    ),
    TipusCultiu.COLZA: CoeficientKc(
        kc_ini=0.35,
        kc_mid=1.15,
        kc_end=0.35,
        profunditat_arrel=1.0,
        altura_maxima=1.5,
        durada_fases={
            FaseFenologica.INICIAL: 30,
            FaseFenologica.DESENVOLUPAMENT: 60,
            FaseFenologica.MITJA_TEMPORADA: 40,
            FaseFenologica.FINAL: 30
        }
    ),
    TipusCultiu.SORGO: CoeficientKc(
        kc_ini=0.30,
        kc_mid=1.10,
        kc_end=0.55,
        profunditat_arrel=1.2,
        altura_maxima=2.0,
        durada_fases={
            FaseFenologica.INICIAL: 20,
            FaseFenologica.DESENVOLUPAMENT: 35,
            FaseFenologica.MITJA_TEMPORADA: 40,
            FaseFenologica.FINAL: 30
        }
    ),
}


# Dates de sembra/plantació típiques a la zona
DATES_SEMBRA: Dict[TipusCultiu, tuple] = {
    TipusCultiu.PANIS: (4, 15),          # 15 abril
    TipusCultiu.ALFALS: (3, 1),           # 1 març (primera dall)
    TipusCultiu.FRUITA_PINYOL: (3, 1),    # Brotació març
    TipusCultiu.FRUITA_LLAVOR: (3, 15),   # Brotació març
    TipusCultiu.CEREAL_HIVERN: (11, 15),  # 15 novembre
    TipusCultiu.AMETLLER: (2, 15),        # Floració febrer
    TipusCultiu.OLIVERA: (3, 1),          # Brotació març
    TipusCultiu.HORTICOLES: (4, 1),       # Variable
    TipusCultiu.VINYA: (4, 1),            # Brotació abril
    TipusCultiu.GIRA_SOL: (5, 1),         # 1 maig
    TipusCultiu.COLZA: (9, 15),           # 15 setembre
    TipusCultiu.SORGO: (5, 15),           # 15 maig
}


def calcular_dies_desde_sembra(cultiu: TipusCultiu, data_actual: Optional[date] = None) -> int:
    """
    Calcula els dies transcorreguts des de la sembra/brotació.

    Args:
        cultiu: Tipus de cultiu
        data_actual: Data actual (per defecte avui)

    Returns:
        Nombre de dies des de la sembra
    """
    if data_actual is None:
        data_actual = date.today()

    mes_sembra, dia_sembra = DATES_SEMBRA[cultiu]
    any_sembra = data_actual.year

    # Si la data de sembra és posterior a la data actual, és de l'any anterior
    data_sembra = date(any_sembra, mes_sembra, dia_sembra)
    if data_sembra > data_actual:
        data_sembra = date(any_sembra - 1, mes_sembra, dia_sembra)

    return (data_actual - data_sembra).days


def determinar_fase_fenologica(cultiu: TipusCultiu, dies_desde_sembra: int) -> FaseFenologica:
    """
    Determina la fase fenològica actual del cultiu.

    Args:
        cultiu: Tipus de cultiu
        dies_desde_sembra: Dies des de la sembra

    Returns:
        Fase fenològica actual
    """
    coef = COEFICIENTS_KC[cultiu]
    fases = coef.durada_fases

    acumulat = 0
    for fase in FaseFenologica:
        acumulat += fases[fase]
        if dies_desde_sembra <= acumulat:
            return fase

    return FaseFenologica.FINAL


def calcular_kc_actual(
    cultiu: TipusCultiu,
    data_actual: Optional[date] = None,
    dies_desde_sembra: Optional[int] = None
) -> float:
    """
    Calcula el coeficient Kc actual segons la fase fenològica.

    Utilitza interpolació lineal entre fases segons FAO-56.

    Args:
        cultiu: Tipus de cultiu
        data_actual: Data actual (opcional)
        dies_desde_sembra: Dies des de la sembra (opcional, si no es calcula)

    Returns:
        Valor Kc interpolat
    """
    if dies_desde_sembra is None:
        dies_desde_sembra = calcular_dies_desde_sembra(cultiu, data_actual)

    coef = COEFICIENTS_KC[cultiu]
    fases = coef.durada_fases

    # Calcular posició dins del cicle
    fase_actual = determinar_fase_fenologica(cultiu, dies_desde_sembra)

    # Acumular dies fins a la fase actual
    dies_acumulats = 0
    for fase in FaseFenologica:
        if fase == fase_actual:
            break
        dies_acumulats += fases[fase]

    dies_en_fase = dies_desde_sembra - dies_acumulats
    durada_fase = fases[fase_actual]

    # Interpolació segons fase
    if fase_actual == FaseFenologica.INICIAL:
        return coef.kc_ini

    elif fase_actual == FaseFenologica.DESENVOLUPAMENT:
        # Interpolació lineal de kc_ini a kc_mid
        progres = dies_en_fase / durada_fase
        return coef.kc_ini + (coef.kc_mid - coef.kc_ini) * progres

    elif fase_actual == FaseFenologica.MITJA_TEMPORADA:
        return coef.kc_mid

    else:  # FINAL
        # Interpolació lineal de kc_mid a kc_end
        progres = dies_en_fase / durada_fase
        return coef.kc_mid + (coef.kc_end - coef.kc_mid) * progres


def obtenir_info_cultiu(cultiu: TipusCultiu, data_actual: Optional[date] = None) -> Dict:
    """
    Obté informació completa del cultiu per a la data especificada.

    Args:
        cultiu: Tipus de cultiu
        data_actual: Data actual

    Returns:
        Diccionari amb informació del cultiu
    """
    if data_actual is None:
        data_actual = date.today()

    dies = calcular_dies_desde_sembra(cultiu, data_actual)
    fase = determinar_fase_fenologica(cultiu, dies)
    kc = calcular_kc_actual(cultiu, data_actual)
    coef = COEFICIENTS_KC[cultiu]

    return {
        "cultiu": cultiu.value,
        "data": data_actual.isoformat(),
        "dies_desde_sembra": dies,
        "fase_fenologica": fase.value,
        "kc_actual": round(kc, 2),
        "kc_ini": coef.kc_ini,
        "kc_mid": coef.kc_mid,
        "kc_end": coef.kc_end,
        "profunditat_arrel_m": coef.profunditat_arrel,
        "altura_maxima_m": coef.altura_maxima
    }


# Noms en català dels cultius
NOMS_CULTIUS: Dict[TipusCultiu, str] = {
    TipusCultiu.PANIS: "Panís (Blat de moro)",
    TipusCultiu.ALFALS: "Alfals",
    TipusCultiu.FRUITA_PINYOL: "Fruita de pinyol",
    TipusCultiu.FRUITA_LLAVOR: "Fruita de llavor",
    TipusCultiu.CEREAL_HIVERN: "Cereal d'hivern",
    TipusCultiu.AMETLLER: "Ametller",
    TipusCultiu.OLIVERA: "Olivera",
    TipusCultiu.HORTICOLES: "Hortícoles extensives",
    TipusCultiu.VINYA: "Vinya",
    TipusCultiu.GIRA_SOL: "Gira-sol",
    TipusCultiu.COLZA: "Colza",
    TipusCultiu.SORGO: "Sorgo",
}
