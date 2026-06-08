#!/usr/bin/env python3
"""
AGENTE 3 — LATAM-GROWTH AF Implementation Funnel
Uso: python3 growth_agent.py

Igual al Agente 2 pero filtra por Ac Sub Sub Region = LATAM-GROWTH.
"""

import subprocess
import sys
from pathlib import Path

BASE   = Path(__file__).parent
OUTPUT = BASE / "output"
OUTPUT.mkdir(parents=True, exist_ok=True)


def run(script, label):
    print(f"\n{'='*60}")
    print(label)
    print('='*60)
    subprocess.run([sys.executable, str(script)], check=True)


def main():
    run(BASE / "find_and_download_growth.py", "Paso 1/2 — Descargando CSV de Tableau (LATAM-GROWTH)...")
    run(BASE / "render_funnel_growth.py",     "Paso 2/2 — Generando imagen del funnel LATAM-GROWTH...")

    img = OUTPUT / "growth_funnel.png"
    print(f"\n✓ Listo! Imagen guardada en: {img}")
    subprocess.run(["open", str(img)])


if __name__ == "__main__":
    main()
