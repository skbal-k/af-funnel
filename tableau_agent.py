#!/usr/bin/env python3
"""
LATAM AF Implementation Funnel — Tableau Agent
Uso: python3 tableau_agent.py

1. Entra a Tableau con cookies guardadas (sin login manual)
2. Aplica filtros:
   - Ac Region = LACA
   - Macro Segment: excluir ESMB
   - Implementation Type = TODOS
   - Grouping = Implementation Partner
3. Descarga el crosstab CSV de "Implementation Summary"
4. Genera la imagen del funnel en output/latam_funnel.png
5. Abre la imagen automáticamente
"""

import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).parent
OUTPUT = BASE / "output"
OUTPUT.mkdir(parents=True, exist_ok=True)


def run(script, label):
    print(f"\n{'='*60}")
    print(label)
    print('='*60)
    subprocess.run([sys.executable, str(script)], check=True)


def main():
    run(BASE / "find_and_download.py", "Paso 1/2 — Descargando CSV de Tableau...")
    run(BASE / "render_funnel.py",     "Paso 2/2 — Generando imagen del funnel...")

    img = OUTPUT / "latam_funnel.png"
    print(f"\n✓ Listo! Imagen guardada en: {img}")
    subprocess.run(["open", str(img)])


if __name__ == "__main__":
    main()
