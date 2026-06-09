#!/usr/bin/env python3
"""
Lee el CSV de Account Details de Tableau, filtra LATAM Implementation Partner,
calcula métricas con COUNTD por cuenta única y genera imagen del funnel.
Incluye etapa Scale (100K+ Actions/week) desde Google Sheets.
"""

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon

log = logging.getLogger(__name__)
OUTPUT_DIR = Path(__file__).parent / "outputs"


# ── parsing ────────────────────────────────────────────────────────────────────

def load_csv(csv_path: Path) -> list[dict]:
    content = ""
    for enc in ("utf-16", "utf-16-le", "utf-8-sig", "utf-8", "latin-1"):
        try:
            with open(csv_path, encoding=enc) as f:
                content = f.read()
            if content.strip():
                break
        except UnicodeDecodeError:
            continue

    delimiter = "\t" if "\t" in content.split("\n")[0] else ","
    lines = [l for l in content.splitlines() if l.strip()]
    reader = csv.DictReader(lines, delimiter=delimiter)
    rows = [{k.strip(): (v.strip() if v else "") for k, v in row.items()} for row in reader]
    log.info("CSV cargado: %d filas", len(rows))
    return rows


def is_true(val: str) -> bool:
    return val.strip().lower() == "true"

def is_partner(row: dict) -> bool:
    return row.get("Implementation Type", "").strip() == "Partner"

KNOWN_SUBREGIONS = {"BRAZIL", "MEXICO", "LATAM-GROWTH", "LATAM-EMERGING"}


def compute_metrics(rows: list[dict]) -> dict:
    # Si el CSV ya viene filtrado por LACA (descarga manual), Ac Region puede estar vacío
    has_region = any(r.get("Ac Region", "").strip() for r in rows[:10])
    latam = [r for r in rows
             if (not has_region or r.get("Ac Region", "").strip() == "LACA")
             and r.get("Account Drvd Macro Segment", "").strip() != "ESMB"]
    log.info("Filas LATAM (Partner): %d", len(latam))

    def seg(subregion=None, partners_only=False):
        s = latam
        if subregion:
            s = [r for r in s if r.get("Ac Sub Sub Region", "").strip() == subregion]
        elif partners_only:
            # LATAM Prtns total = only accounts assigned to a known sub-region (matches Tableau COUNTD)
            s = [r for r in s if r.get("Ac Sub Sub Region", "").strip() in KNOWN_SUBREGIONS]
        if partners_only:
            s = [r for r in s if is_partner(r)]
        return s

    segs = {
        "LATAM":        seg(),
        "LATAM Prtns":  seg(partners_only=True),
        "Brazil":       seg("BRAZIL"),
        "Brazil Prtns": seg("BRAZIL", True),
        "Mexico":       seg("MEXICO"),
        "Mexico Prtns": seg("MEXICO", True),
        "Growth":       seg("LATAM-GROWTH"),
        "Growth Prtns": seg("LATAM-GROWTH", True),
        "Emerging":     seg("LATAM-EMERGING"),
        "Emerg Prtns":  seg("LATAM-EMERGING", True),
    }

    phases = [
        ("Provisioned",   "Is Sku Provisioned"),
        ("Discovery",     "Discovery Phase"),
        ("Agent Created", "Created Phase"),
        ("Agent in Prod", "Activated Phase"),
        ("Used",          "Used Phase"),
        ("Consumed",      "Consumed Phase"),
    ]

    metrics = {}
    for label, col in phases:
        metrics[label] = {
            k: len(set(r.get("Acct Id 18", "") for r in v if is_true(r.get(col, ""))))
            for k, v in segs.items()
        }

    log.info("Métricas calculadas:")
    for label in metrics:
        log.info("  %-16s LATAM=%-5d Brazil=%-5d Mexico=%-5d Growth=%-5d Emerging=%-5d",
                 label,
                 metrics[label].get("LATAM", 0),
                 metrics[label].get("Brazil", 0),
                 metrics[label].get("Mexico", 0),
                 metrics[label].get("Growth", 0),
                 metrics[label].get("Emerging", 0))

    return metrics


def compute_scale_metrics(rows: list[dict], scale_ids: list[str]) -> dict:
    """
    Calcula la etapa Scale cruzando los Account IDs del Google Sheet
    con los rows de Tableau (para saber sub-región de cada cuenta).
    """
    # Normalizar IDs a uppercase para match case-insensitive
    scale_set = set(i.upper() for i in scale_ids if i)

    # Construir lookup: Acct Id 18 (uppercase) → sub-región
    id_to_subregion = {}
    id_to_is_partner = {}
    for r in rows:
        acct_id = r.get("Acct Id 18", "").strip().upper()
        subregion = r.get("Ac Sub Sub Region", "").strip()
        macro_seg = r.get("Account Drvd Macro Segment", "").strip()
        if acct_id and macro_seg != "ESMB":
            id_to_subregion[acct_id] = subregion
            id_to_is_partner[acct_id] = is_partner(r)

    # Contar Scale accounts por sub-región
    scale_latam = 0
    scale_latam_prtns = 0
    brazil = 0; brazil_prtns = 0
    mexico = 0; mexico_prtns = 0
    growth = 0; growth_prtns = 0
    emerging = 0; emerg_prtns = 0

    for acct_id in scale_set:
        if acct_id not in id_to_subregion:
            continue
        sub = id_to_subregion[acct_id]

        if sub in KNOWN_SUBREGIONS:
            scale_latam += 1
            partner = id_to_is_partner.get(acct_id, False)
            scale_latam_prtns += int(partner)
            if sub == "BRAZIL":
                brazil += 1
                brazil_prtns += int(partner)
            elif sub == "MEXICO":
                mexico += 1
                mexico_prtns += int(partner)
            elif sub == "LATAM-GROWTH":
                growth += 1
                growth_prtns += int(partner)
            elif sub == "LATAM-EMERGING":
                emerging += 1
                emerg_prtns += int(partner)

    result = {
        "LATAM":        scale_latam,
        "LATAM Prtns":  scale_latam_prtns,
        "Brazil":       brazil,
        "Brazil Prtns": brazil_prtns,
        "Mexico":       mexico,
        "Mexico Prtns": mexico_prtns,
        "Growth":       growth,
        "Growth Prtns": growth_prtns,
        "Emerging":     emerging,
        "Emerg Prtns":  emerg_prtns,
    }
    log.info("  %-16s LATAM=%-5d Brazil=%-5d Mexico=%-5d Growth=%-5d Emerging=%-5d",
             "Scale", scale_latam, brazil, mexico, growth, emerging)
    return result


# ── rendering ──────────────────────────────────────────────────────────────────

COLS = ["LATAM", "LATAM Prtns", "Brazil", "Brazil Prtns",
        "Mexico", "Mexico Prtns", "Growth", "Growth Prtns",
        "Emerging", "Emerg Prtns"]

COL_HEADERS = ["LATAM", "LATAM\nPrtns", "Brazil", "Brazil\nPrtns",
               "Mexico", "Mexico\nPrtns", "Growth", "Growth\nPrtns",
               "Emerging", "Emerging\nPrtns"]

# phase name, bg color, fg color, section, subtitle
PHASE_CONFIG = [
    ("Provisioned",   "#4472C4", "white", "Implementing", "Provisioned SKU"),
    ("Discovery",     "#2E75B6", "white", "Implementing", "Project Submitted with OrgId\ntied to Closed/Won Oppty"),
    ("Agent Created", "#7030A0", "white", "Implementing", "Build & Test"),
    ("Agent in Prod", "#2E7D5E", "white", "Implementing", "Activated"),
    ("Used",          "#6C757D", "white", "Consuming",    "Conversations in\nProduction Org"),
    ("Consumed",      "#C4A82A", "white", "Consuming",    "50+ Conversations\nLast 7 days"),
    ("Scale",         "#E57373", "white", "Consuming",    "100K+\nActions per Week"),
]

PCT_COLS = {"LATAM Prtns", "Brazil Prtns", "Mexico Prtns", "Growth Prtns", "Emerg Prtns"}

# For each Prtns column, its corresponding base column
BASE_COL = {
    "LATAM Prtns":  "LATAM",
    "Brazil Prtns": "Brazil",
    "Mexico Prtns": "Mexico",
    "Growth Prtns": "Growth",
    "Emerg Prtns":  "Emerging",
}


def pct(a, b):
    return f"{round(a / b * 100)}%" if b else "-"


def generate_image(metrics: dict, output_dir: Path, scale_metrics: Optional[dict] = None) -> Path:
    # Merge scale_metrics into metrics dict
    all_metrics = dict(metrics)
    if scale_metrics is not None:
        all_metrics["Scale"] = scale_metrics
    else:
        all_metrics["Scale"] = {k: 0 for k in COLS}

    output_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%m/%d/%Y")

    fig_w, fig_h = 34, 18
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    ax.axis("off")
    fig.patch.set_facecolor("#D6EAF8")
    ax.set_facecolor("#D6EAF8")

    # Layout
    left        = 0.3
    sec_w       = 0.55
    pill_w      = 4.5
    table_x     = left + sec_w + pill_w + 0.2
    table_w     = fig_w - table_x - 0.35
    latam_col_w = table_w * 0.138
    other_col_w = (table_w - latam_col_w) / 9

    header_y = fig_h - 2.0
    n_rows   = len(PHASE_CONFIG)
    row_h    = (header_y - 0.5) / n_rows
    start_y  = header_y - 0.65

    # ── Title ───────────────────────────────────────────────────────────────
    ax.text(fig_w / 2, fig_h - 0.35,
            "AF Implementation Funnel (Cumulative Go-Live)",
            ha="center", va="top", fontsize=30, fontweight="bold", color="#1A3A5C")
    ax.text(fig_w - 0.35, fig_h - 0.4, f"Updated on    {today}",
            ha="right", va="top", fontsize=13, color="#555")

    # ── Column headers ──────────────────────────────────────────────────────
    col_xs = []

    # LATAM (wider)
    cx = table_x + latam_col_w / 2
    col_xs.append(cx)
    ax.text(cx, header_y, "LATAM", ha="center", va="center",
            fontsize=26, fontweight="bold", color="#1A3A5C")

    # Remaining 9 columns
    for i, hdr in enumerate(COL_HEADERS[1:]):
        cx = table_x + latam_col_w + (i + 0.5) * other_col_w
        col_xs.append(cx)
        is_bold = COLS[i + 1] == "LATAM Prtns"
        ax.text(cx, header_y, hdr, ha="center", va="center",
                fontsize=22, fontweight="bold" if is_bold else "normal",
                color="#1A3A5C")

    ax.plot([table_x - 0.06, fig_w - 0.25],
            [header_y - 0.3, header_y - 0.3],
            color="#1A3A5C", linewidth=1.5)

    # ── Rows ────────────────────────────────────────────────────────────────
    section_drawn = {}

    for pi, (phase, bg, fg, section, subtitle) in enumerate(PHASE_CONFIG):
        row_y = start_y - pi * row_h

        # Alternating row background
        row_bg = "white" if pi % 2 == 0 else "#E6F2FA"
        ax.add_patch(FancyBboxPatch(
            (table_x - 0.06, row_y - row_h + 0.1),
            fig_w - table_x - 0.19, row_h - 0.08,
            boxstyle="round,pad=0.04",
            facecolor=row_bg, edgecolor="#C5D9E8", linewidth=0.4
        ))

        # Section label
        if section not in section_drawn:
            section_drawn[section] = True
            count_in = sum(1 for _, _, _, s, _ in PHASE_CONFIG if s == section)
            first_i  = next(i for i, (_, _, _, s, _) in enumerate(PHASE_CONFIG) if s == section)
            sec_cy   = start_y - (first_i + (count_in - 1) / 2) * row_h
            ax.text(left + sec_w / 2, sec_cy, section,
                    ha="center", va="center",
                    fontsize=22, color="#555", rotation=90, style="italic")

        # Phase pill — trapezoid funnel shape (widens toward top)
        # pi=0 is widest (Provisioned), pi=5 is narrowest (Consumed)
        max_shrink = pill_w * 0.30          # total side shrink across all rows
        shrink = pi * (max_shrink / (n_rows - 1))
        px_full = left + sec_w + 0.06
        pill_h  = row_h - 0.18
        pill_y0 = row_y - row_h + 0.12     # bottom edge
        pill_y1 = pill_y0 + pill_h         # top edge

        # Next row's shrink for the bottom edge
        next_shrink = (pi + 1) * (max_shrink / (n_rows - 1)) if pi < n_rows - 1 else shrink + (max_shrink / (n_rows - 1))

        top_left  = px_full + shrink / 2
        top_right = px_full + pill_w - 0.12 - shrink / 2
        bot_left  = px_full + next_shrink / 2
        bot_right = px_full + pill_w - 0.12 - next_shrink / 2

        trap = Polygon(
            [[top_left, pill_y1], [top_right, pill_y1],
             [bot_right, pill_y0], [bot_left, pill_y0]],
            closed=True, facecolor=bg, edgecolor="none"
        )
        ax.add_patch(trap)

        pill_cx = (top_left + top_right) / 2
        # Phase name
        ax.text(pill_cx, row_y - row_h * 0.28,
                phase, ha="center", va="center",
                fontsize=22, fontweight="bold", color=fg)
        # Subtitle
        ax.text(pill_cx, row_y - row_h * 0.66,
                subtitle, ha="center", va="center",
                fontsize=13, color=fg, style="italic",
                multialignment="center")

        # ── Data cells ──────────────────────────────────────────────────────
        row_data = all_metrics[phase]

        for ci, col in enumerate(COLS):
            cx  = col_xs[ci]
            val = row_data.get(col, 0)

            if col == "LATAM":
                ax.text(cx, row_y - row_h * 0.42, str(val),
                        ha="center", va="center",
                        fontsize=44, fontweight="bold", color="#1A3A5C")

            elif col == "LATAM Prtns":
                base_val = row_data.get(BASE_COL[col], 0)
                ax.text(cx, row_y - row_h * 0.28, str(val),
                        ha="center", va="center",
                        fontsize=34, fontweight="bold", color="#1A5276")
                ax.text(cx, row_y - row_h * 0.65, pct(val, base_val),
                        ha="center", va="center",
                        fontsize=26, color="#2E86C1")

            elif col in PCT_COLS:
                base_val = row_data.get(BASE_COL[col], 0)
                ax.text(cx, row_y - row_h * 0.28, str(val),
                        ha="center", va="center",
                        fontsize=30, color="#2C3E50")
                ax.text(cx, row_y - row_h * 0.65, pct(val, base_val),
                        ha="center", va="center",
                        fontsize=24, color="#5D6D7E")

            else:
                ax.text(cx, row_y - row_h * 0.42, str(val),
                        ha="center", va="center",
                        fontsize=34, color="#2C3E50")

    # ── Dashed separator Implementing / Consuming ────────────────────────────
    dash_y = start_y - 4 * row_h - 0.08
    ax.plot([left, fig_w - 0.25], [dash_y, dash_y],
            color="#555", linewidth=1.2, linestyle="--")

    # ── Save ─────────────────────────────────────────────────────────────────
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path  = output_dir / f"af_funnel_{timestamp}.png"
    plt.tight_layout(pad=0.5)
    plt.savefig(str(out_path), dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()

    latest = output_dir / "latest_funnel.png"
    if latest.exists() or latest.is_symlink():
        latest.unlink()
    latest.symlink_to(out_path.name)
    log.info("Imagen generada: %s", out_path)
    return out_path


def run(csv_path: Path, scale_ids: Optional[list] = None) -> Path:
    rows = load_csv(csv_path)
    metrics = compute_metrics(rows)
    scale_metrics = compute_scale_metrics(rows, scale_ids) if scale_ids else None
    return generate_image(metrics, OUTPUT_DIR, scale_metrics)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    csv_file = Path(sys.argv[1]) if len(sys.argv) > 1 else OUTPUT_DIR / "raw_data.csv"
    out = run(csv_file)
    print(f"Imagen: {out}")
