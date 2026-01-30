"""
Servidor API REST per a l'Agent de Reg dels Canals d'Urgell.

Endpoints disponibles:
- GET /health - Estat del servidor
- GET /embassaments - Estat dels embassaments
- GET /cultius - Llistat de cultius
- GET /municipis - Llistat de municipis
- POST /consulta - Consulta a l'agent
- POST /calcular - Calcular necessitat de reg
- POST /informe - Generar informe
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import asyncio
import uvicorn

from src.agent import IrrigationAgent
from src.api_clients import HydrologyClient
from src.cultius import TipusCultiu, NOMS_CULTIUS, COEFICIENTS_KC
from src.config import MUNICIPIS_ZONA_REGABLE, SistemaReg

app = FastAPI(
    title="Agent de Reg dels Canals d'Urgell",
    description="API per a l'optimització del reg agrícola a la zona dels Canals d'Urgell",
    version="1.0.0"
)

# CORS per permetre accés des de qualsevol origen
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicialitzar agent
agent = IrrigationAgent()


class ConsultaRequest(BaseModel):
    text: str


class CalculRequest(BaseModel):
    cultiu: str
    municipi: str = "Mollerussa"
    sistema_reg: str = "aspersio"


class InformeRequest(BaseModel):
    cultiu: str
    municipi: str = "Mollerussa"
    sistema_reg: str = "aspersio"
    format: str = "markdown"


@app.get("/")
async def root():
    """Pàgina principal."""
    return {
        "nom": "Agent de Reg dels Canals d'Urgell",
        "versio": "1.0.0",
        "descripcio": "API per a l'optimització del reg agrícola",
        "endpoints": {
            "GET /health": "Estat del servidor",
            "GET /embassaments": "Estat dels embassaments",
            "GET /cultius": "Llistat de cultius suportats",
            "GET /municipis": "Llistat de municipis",
            "POST /consulta": "Consulta a l'agent (body: {text: string})",
            "POST /calcular": "Calcular necessitat de reg",
            "POST /informe": "Generar informe tècnic"
        }
    }


@app.get("/health")
async def health():
    """Verifica l'estat del servidor."""
    return {"status": "ok", "agent": "operatiu"}


@app.get("/embassaments")
async def obtenir_embassaments():
    """Obté l'estat actual dels embassaments."""
    try:
        async with HydrologyClient() as client:
            dades = await client.obtenir_resum_hidrologic()
        return dades
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cultius")
async def llistar_cultius():
    """Llista tots els cultius suportats."""
    cultius = {}
    for cultiu, coef in COEFICIENTS_KC.items():
        cultius[cultiu.value] = {
            "nom": NOMS_CULTIUS[cultiu],
            "kc_ini": coef.kc_ini,
            "kc_mid": coef.kc_mid,
            "kc_end": coef.kc_end,
            "profunditat_arrel_m": coef.profunditat_arrel,
            "altura_maxima_m": coef.altura_maxima
        }
    return {"cultius": cultius}


@app.get("/municipis")
async def llistar_municipis():
    """Llista tots els municipis de la zona regable."""
    return {"municipis": MUNICIPIS_ZONA_REGABLE}


@app.post("/consulta")
async def processar_consulta(request: ConsultaRequest):
    """Processa una consulta a l'agent."""
    try:
        resposta = await agent.processar_consulta(request.text)
        return {"resposta": resposta}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/calcular")
async def calcular_necessitat(request: CalculRequest):
    """Calcula la necessitat de reg per a un cultiu."""
    try:
        # Validar cultiu
        try:
            cultiu = TipusCultiu(request.cultiu)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Cultiu no vàlid. Opcions: {[c.value for c in TipusCultiu]}"
            )

        # Validar sistema de reg
        try:
            sistema = SistemaReg(request.sistema_reg)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Sistema de reg no vàlid. Opcions: {[s.value for s in SistemaReg]}"
            )

        consulta = f"Calcula la necessitat de reg per a {request.cultiu} a {request.municipi} amb sistema de reg per {request.sistema_reg}"
        resposta = await agent.processar_consulta(consulta)
        return {"resposta": resposta}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/informe")
async def generar_informe(request: InformeRequest):
    """Genera un informe tècnic complet."""
    try:
        consulta = f"""Genera un informe tècnic complet de reg per a {request.cultiu}
        a {request.municipi} amb sistema de reg per {request.sistema_reg}.
        Inclou estat dels embassaments, recomanació de reg i alertes."""

        resposta = await agent.processar_consulta(consulta)
        return {
            "format": request.format,
            "informe": resposta
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """Inicia el servidor."""
    print("\n" + "=" * 60)
    print("🌾 AGENT DE REG DELS CANALS D'URGELL")
    print("=" * 60)
    print("\n📡 Servidor API iniciant...")
    print("🌐 URL: http://localhost:8000")
    print("📖 Documentació: http://localhost:8000/docs")
    print("\n" + "-" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
