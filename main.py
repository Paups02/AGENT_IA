#!/usr/bin/env python3
"""
Agent Expert en Hidràulica Agrícola - Canals d'Urgell

Punt d'entrada principal per executar l'agent de reg.
"""

import asyncio
import sys
from pathlib import Path

# Afegir src al path
sys.path.insert(0, str(Path(__file__).parent))

from src.cli import main

if __name__ == "__main__":
    main()
