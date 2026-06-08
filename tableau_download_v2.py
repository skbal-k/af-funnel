"""
Abre el dashboard de Tableau en el browser, PAUSA para que completes el SSO login,
aplica los filtros indicados y descarga el CSV de Implementation Summary.

Uso:
    python tableau_download_v2.py
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

TABLEAU_URL = (
    "https://prod-uswest-c.online.tableau.com/#/site/salesforce/views/"
    "AgentforceACForecast/AgentforceACForecast?:iid=1"
)

DOWNLOAD_DIR = Path.home() / "partner_agent" / "output"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


def click_filter(frame, filter_label: str, values_to_select: list,
                 deselect_values: list = None):
    print(f"  Aplicando filtro: {filter_label}")
    try:
        filter_btn = frame.locator(
            f"div.tab-filter-card:has-text('{filter_label}'), "
            f"div[data-tb-test-id*='filter']:has-text('{filter_label}')"
        ).first
        filter_btn.click(timeout=5000)
        time.sleep(1)

        if deselect_values:
            for val in deselect_values:
                checkbox = frame.locator(
                    f"div.tab-filter-item:has-text('{val}') input, "
                    f"li:has-text('{val}') input"
                ).first
                if checkbox.is_checked():
                    checkbox.click()
                    time.sleep(0.3)

        for val in values_to_select:
            checkbox = frame.locator(
                f"div.tab-filter-item:has-text('{val}') input, "
                f"li:has-text('{val}') input"
            ).first
            if not checkbox.is_checked():
                checkbox.click()
                time.sleep(0.3)

        frame.keyboard.press("Escape")
        time.sleep(0.5)

    except PWTimeout:
        print(f"  AVISO: No se pudo aplicar filtro '{filter_label}' automáticamente.")
        time.sleep(3)


def set_dropdown_filter(frame, filter_label: str, value: str):
    print(f"  Filtro dropdown: {filter_label} → {value}")
    try:
        filter_card = frame.locator(
            f"div.tab-filter-card:has-text('{filter_label}')"
        ).first
        filter_card.click(timeout=5000)
        time.sleep(1)

        option = frame.locator(
            f"div.tab-filter-item:has-text('{value}'), li:has-text('{value}')"
        ).first
        option.click(timeout=3000)
        time.sleep(0.5)
        frame.keyboard.press("Escape")
    except PWTimeout:
        print(f"  AVISO: No se pudo aplicar '{filter_label}={value}' automáticamente.")


def download_csv(page, frame, download_dir: Path) -> Path:
    print("  Abriendo menú de descarga...")

    try:
        download_btn = page.locator(
            "button[data-tb-test-id='download-button'], "
            "a[data-tb-test-id='download'], "
            "div.tab-toolbar button:has-text('Download'), "
            "button:has-text('Download')"
        ).first
        download_btn.click(timeout=8000)
        time.sleep(1)
    except PWTimeout:
        print("  AVISO: No se encontró botón Download automáticamente.")

    try:
        crosstab_option = page.locator(
            "a:has-text('Crosstab'), button:has-text('Crosstab'), "
            "div:has-text('Crosstab'):not(:has(div))"
        ).first
        crosstab_option.click(timeout=5000)
        time.sleep(1)
    except PWTimeout:
        print("  AVISO: No se encontró opción Crosstab automáticamente.")

    try:
        sheet_option = page.locator(
            "option:has-text('Implementation Summary'), "
            "div:has-text('Implementation Summary'):not(:has(div)), "
            "label:has-text('Implementation Summary')"
        ).first
        sheet_option.click(timeout=4000)
        time.sleep(0.5)
    except PWTimeout:
        print("  AVISO: No se encontró hoja 'Implementation Summary' automáticamente.")

    with page.expect_download(timeout=30000) as dl_info:
        try:
            confirm_btn = page.locator(
                "button:has-text('Download'), button[type='submit']"
            ).last
            confirm_btn.click(timeout=5000)
        except PWTimeout:
            print("  AVISO: No se encontró botón de confirmación de descarga.")

    download = dl_info.value
    dest = download_dir / "implementation_summary_LACA.csv"
    download.save_as(str(dest))
    return dest


def main():
    with sync_playwright() as p:
        print("\n[tableau_download] Abriendo browser...")
        browser = p.chromium.launch(headless=False, slow_mo=200)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        print(f"[tableau_download] Navegando a Tableau...")
        page.goto(TABLEAU_URL, wait_until="domcontentloaded", timeout=30000)

        print("\n" + "="*60)
        print("  ACCIÓN REQUERIDA: Completa el login SSO de Salesforce")
        print("  en el browser que se acaba de abrir.")
        print("="*60)
        input("\n  >>> Cuando el dashboard esté completamente cargado,\n  >>> presiona ENTER aquí para continuar: ")
        print("\n  Continuando...")
        time.sleep(3)

        # Intenta obtener el frame de Tableau (a veces está en un iframe)
        frames = page.frames
        tableau_frame = page
        for f in frames:
            if "tableau" in f.url.lower() or "vizql" in f.url.lower():
                tableau_frame = f
                break

        print("[tableau_download] Aplicando filtros...")

        set_dropdown_filter(tableau_frame, "Region", "LACA")
        click_filter(tableau_frame, "Macro Segment", values_to_select=[], deselect_values=["ESMB"])
        print("  Filtro Implementation Type: dejando en 'All' (sin cambios)")
        set_dropdown_filter(tableau_frame, "Explore Funnel Metrics By", "Implementation Partner")

        print("\n[tableau_download] Filtros aplicados. Descargando CSV...")
        time.sleep(2)

        csv_path = download_csv(page, tableau_frame, DOWNLOAD_DIR)
        print(f"\n[tableau_download] CSV guardado en: {csv_path}")

        browser.close()


if __name__ == "__main__":
    main()
