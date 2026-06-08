#!/usr/bin/env python3
"""
AGENTE 3 — MEXICO AF Implementation Funnel
Uso: python3 mexico_agent.py

Igual al Agente 2 pero filtra por Ac Sub Sub Region = MEXICO.
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
    run(BASE / "find_and_download_mexico.py", "Paso 1/2 — Descargando CSV de Tableau (MEXICO)...")
    run(BASE / "render_funnel_mexico.py",     "Paso 2/2 — Generando imagen del funnel MEXICO...")

    img = OUTPUT / "mexico_funnel.png"
    print(f"\n✓ Listo! Imagen guardada en: {img}")
    subprocess.run(["open", str(img)])


if __name__ == "__main__":
    main()
