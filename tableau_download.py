"""
Descarga Implementation Summary CSV de Tableau y genera el funnel LATAM.
Reutiliza la lógica probada del tableau_agent.

Uso:
    python tableau_download.py
"""

import sys
sys.path.insert(0, "/Users/skbal/claude/tableau_agent")

from scraper import download_impl_summary
from pathlib import Path
import shutil

DOWNLOAD_DIR = Path(__file__).parent / "output"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


def main():
    print("[partner_agent] Descargando Implementation Summary de Tableau...")
    csv_path = download_impl_summary(headless=False)

    # Copiar al output del partner_agent
    dest = DOWNLOAD_DIR / "implementation_summary_LACA.csv"
    shutil.copy2(str(csv_path), str(dest))
    print(f"[partner_agent] CSV guardado en: {dest}")
    return dest


if __name__ == "__main__":
    main()
