#!/usr/bin/env python3
"""
Descarga Implementation Summary CSV de Tableau con:
- Ac Sub Sub Region = BRAZIL
- Implementation Type = TODOS
- Explore Funnel Metrics By = Implementation Partner
"""

import json
import time
import logging
from pathlib import Path
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

TABLEAU_URL = "https://prod-uswest-c.online.tableau.com/#/site/salesforce/views/AgentforceACForecast/AgentforceACForecast"
COOKIES_FILE = Path("/Users/skbal/claude/tableau_agent/.session_cookies.json")
OUTPUT_DIR = Path("/Users/skbal/partner_agent/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            args=["--no-sandbox", "--disable-dev-shm-usage",
                  "--disable-blink-features=AutomationControlled"]
        )
        ctx = browser.new_context(
            accept_downloads=True,
            viewport={"width": 1440, "height": 900},
        )
        page = ctx.new_page()

        # Cargar cookies
        if COOKIES_FILE.exists():
            cookies = json.loads(COOKIES_FILE.read_text())
            ctx.add_cookies(cookies)
            log.info("Cookies cargadas: %d", len(cookies))

        # Navegar
        page.goto(TABLEAU_URL, wait_until="domcontentloaded", timeout=60000)
        page.bring_to_front()
        time.sleep(5)

        # Login si hace falta
        if "sso" in page.url or "okta" in page.url or "login" in page.url:
            print("\n" + "="*60)
            print("ACCIÓN REQUERIDA: Completá el login en el browser")
            print("El agente continuará automáticamente")
            print("="*60 + "\n")
            page.wait_for_url("**/tableau.com/**", timeout=300000)
            time.sleep(2)
            page.goto(TABLEAU_URL, wait_until="domcontentloaded", timeout=60000)
            time.sleep(5)

        log.info("URL: %s", page.url[:80])

        # Esperar iframe
        page.wait_for_selector("iframe", timeout=60000)
        fl = page.frame_locator("iframe").first

        # Esperar toolbar
        log.info("Esperando toolbar...")
        fl.locator("[data-tb-test-id='viz-viewer-toolbar-button-download']").wait_for(
            state="visible", timeout=120000
        )
        log.info("Viz listo — estabilizando...")
        time.sleep(8)

        # Guardar cookies
        COOKIES_FILE.write_text(json.dumps(ctx.cookies()))
        log.info("Cookies guardadas")

        # ── Paso 1: Cambiar Grouping = Implementation Partner ─────────────────
        r = page.evaluate("""
            async () => {
                try {
                    await tableau.VizManager.getVizs()[0].getWorkbook()
                        .changeParameterValueAsync('Grouping', 'Implementation Partner');
                    return 'ok';
                } catch(e) { return 'error: ' + e.toString(); }
            }
        """)
        log.info("Grouping=Implementation Partner: %s", r)
        time.sleep(4)

        # ── Paso 2: Implementation Type = TODOS ───────────────────────────────
        r = page.evaluate("""
            async () => {
                try {
                    const wb = tableau.VizManager.getVizs()[0].getWorkbook();
                    const sheet = wb.getActiveSheet();
                    const wss = sheet.getSheetType() === 'dashboard'
                        ? sheet.getWorksheets() : [sheet];
                    const res = [];
                    for (const ws of wss) {
                        try {
                            await ws.applyFilterAsync('Implementation Type', [], tableau.FilterUpdateType.ALL);
                            res.push(ws.getName() + ':ok');
                        } catch(e) { res.push(ws.getName() + ':skip'); }
                    }
                    return res;
                } catch(e) { return ['error:'+e.toString()]; }
            }
        """)
        log.info("Implementation Type=ALL: %s", r)
        time.sleep(3)

        # ── Paso 3: Filtro Ac Sub Sub Region = BRAZIL ────────────────────────
        r = page.evaluate("""
            async () => {
                try {
                    const wb = tableau.VizManager.getVizs()[0].getWorkbook();
                    const sheet = wb.getActiveSheet();
                    const wss = sheet.getSheetType() === 'dashboard'
                        ? sheet.getWorksheets() : [sheet];
                    const res = [];
                    for (const ws of wss) {
                        try {
                            await ws.applyFilterAsync('Ac Sub Sub Region', ['BRAZIL'], tableau.FilterUpdateType.REPLACE);
                            res.push(ws.getName() + ':ok');
                        } catch(e) { res.push(ws.getName() + ':' + e.toString().substring(0,60)); }
                    }
                    return res;
                } catch(e) { return ['error:'+e.toString()]; }
            }
        """)
        log.info("Ac Sub Sub Region=BRAZIL: %s", r)
        time.sleep(4)

        # ── Paso 3b: Macro Segment — excluir ESMB ────────────────────────────
        r = page.evaluate("""
            async () => {
                try {
                    const wb = tableau.VizManager.getVizs()[0].getWorkbook();
                    const sheet = wb.getActiveSheet();
                    const wss = sheet.getSheetType() === 'dashboard'
                        ? sheet.getWorksheets() : [sheet];
                    const res = [];
                    for (const ws of wss) {
                        try {
                            await ws.applyFilterAsync('Account Drvd Macro Segment', ['ESMB'], tableau.FilterUpdateType.REMOVE);
                            res.push(ws.getName() + ':ok');
                        } catch(e) { res.push(ws.getName() + ':skip'); }
                    }
                    return res;
                } catch(e) { return ['error:'+e.toString()]; }
            }
        """)
        log.info("Macro Segment excluir ESMB: %s", r)
        time.sleep(3)

        # Screenshot para verificar
        page.screenshot(path=str(OUTPUT_DIR / "before_download.png"))
        log.info("Screenshot guardado")

        # ── Paso 4: Download crosstab ─────────────────────────────────────────
        log.info("Abriendo menú de descarga...")
        fl.locator("[data-tb-test-id='viz-viewer-toolbar-button-download']").click()
        time.sleep(2)

        fl.locator("[data-tb-test-id='download-flyout-download-crosstab-MenuItem']").wait_for(
            state="visible", timeout=10000
        )
        fl.locator("[data-tb-test-id='download-flyout-download-crosstab-MenuItem']").click()
        time.sleep(2)

        fl.locator("[data-tb-test-id='thumbnail-picker-list']").wait_for(
            state="visible", timeout=15000
        )
        time.sleep(1)

        # Log thumbnails disponibles
        thumbs = fl.locator("[data-tb-test-id^='sheet-thumbnail-']").all()
        log.info("Thumbnails: %d", len(thumbs))
        for t in thumbs:
            try:
                log.info("  %s: %s", t.get_attribute("data-tb-test-id"),
                         t.inner_text()[:50].replace('\n', ' | '))
            except Exception:
                pass

        download_btn = fl.locator("[data-tb-test-id='export-crosstab-export-Button']").first

        # Buscar "Implementation Summary" por texto (independiente del índice)
        impl_summary_thumb = None
        for t in thumbs:
            try:
                txt = t.inner_text().strip()
                if "Implementation Summary" in txt:
                    impl_summary_thumb = t
                    log.info("Encontrado 'Implementation Summary': %s", t.get_attribute("data-tb-test-id"))
                    break
            except Exception:
                pass

        if impl_summary_thumb is None:
            log.warning("No se encontró 'Implementation Summary', usando Funnel-Partner")
            for t in thumbs:
                try:
                    if "Funnel" in t.inner_text():
                        impl_summary_thumb = t
                        break
                except Exception:
                    pass

        # Deseleccionar si hay uno activo
        if not download_btn.is_disabled():
            try:
                fl.locator("[data-tb-test-id='sheet-thumbnail-0']").click()
                time.sleep(0.5)
            except Exception:
                pass

        if impl_summary_thumb:
            impl_summary_thumb.click()
            log.info("Thumbnail seleccionado: Implementation Summary")
            time.sleep(1)
        elif len(thumbs) > 1:
            thumbs[1].click()
            log.info("Seleccionado thumbnail índice 1 como fallback")

        # CSV format
        fl.locator("[data-tb-test-id='crosstab-options-dialog-radio-csv-Label']").click()
        time.sleep(1)

        # Esperar botón
        for _ in range(30):
            if not download_btn.is_disabled():
                break
            time.sleep(0.5)

        log.info("Botón disabled: %s — descargando...", download_btn.is_disabled())

        with page.expect_download(timeout=120000) as dl_info:
            download_btn.click()

        download = dl_info.value
        out_path = OUTPUT_DIR / "implementation_summary_brazil.csv"
        download.save_as(str(out_path))
        size_kb = out_path.stat().st_size // 1024
        log.info("✓ CSV guardado: %s (%d KB)", out_path, size_kb)

        # Preview
        with open(out_path, encoding="utf-16") as f:
            lines = f.readlines()
        print("\n--- Primeras 8 líneas ---")
        for line in lines[:8]:
            print(line.rstrip())
        print(f"--- Total: {len(lines)} líneas ---")

        # Verificar LACA
        content = "".join(lines[:100])
        brazil_partners = ["COMPASS", "Accenture", "Deloitte", "Capgemini", "IBM",
                           "EVERYMIND", "C-Tech", "Wipro"]
        found = [p for p in brazil_partners if p.upper() in content.upper()]
        if found:
            log.info("✓ Partners Brazil encontrados: %s", found)
        else:
            log.info("Partners en primeras líneas — verificar manualmente")

        browser.close()
        return out_path


if __name__ == "__main__":
    result = main()
    print(f"\nCSV: {result}")
