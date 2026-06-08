"""
Genera imagen del MEXICO AF Implementation Funnel.
Bloques en forma de embudo (trapecio) + fila Scale desde Google Sheets.
"""
import json
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon
from pathlib import Path
from playwright.sync_api import sync_playwright

DOWNLOAD_DIR   = Path.home() / "partner_agent" / "output"
COOKIES_FILE   = Path("/Users/skbal/claude/tableau_agent/.google_cookies.json")
SCALE_CSV      = DOWNLOAD_DIR / "scale_clients.csv"
SCALE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1M5hPXCwHphDVUF7sMTnrUAUT0h8lxDppB4YlYUmPXQs/export?format=csv&gid=1623707669"


# ── Descargar Scale Clients desde Google Sheets ───────────────────────────────
def download_scale_sheet():
    print("Descargando Scale Clients de Google Sheets...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            args=["--no-sandbox"]
        )
        ctx = browser.new_context(accept_downloads=True)
        if COOKIES_FILE.exists():
            ctx.add_cookies(json.loads(COOKIES_FILE.read_text()))
        page = ctx.new_page()
        with page.expect_download(timeout=30000) as dl_info:
            page.evaluate(f"window.location.href = '{SCALE_SHEET_URL}'")
        dl_info.value.save_as(str(SCALE_CSV))
        browser.close()
    print(f"  Scale CSV guardado: {SCALE_CSV.stat().st_size} bytes")


# ── Cargar y cruzar Scale data ────────────────────────────────────────────────
def get_scale_counts(partners):
    """Devuelve dict {partner_name: count} con cuentas LATAM en Scale."""
    download_scale_sheet()
    df = pd.read_csv(SCALE_CSV, encoding="utf-8", on_bad_lines='skip')
    df = df.rename(columns={'Unnamed: 12': 'Impl Partner'})
    # Solo MEXICO (columna Unnamed: 13 = sub-región)
    latam = df[df['Unnamed: 13'].str.upper().str.contains('MEXICO', na=False)].copy()
    latam['Impl Partner'] = latam['Impl Partner'].fillna('No Partner')
    counts = latam.groupby('Impl Partner').size().to_dict()
    # Mapear a los partners que tenemos en el funnel
    result = {}
    for p in partners:
        # Buscar coincidencia parcial (el nombre puede estar truncado)
        match = 0
        for k, v in counts.items():
            if k != 'No Partner' and (p.upper() in k.upper() or k.upper() in p.upper()):
                match = v
                break
        result[p] = match
    return result


# ── Cargar CSV de Tableau ─────────────────────────────────────────────────────
csv_path = DOWNLOAD_DIR / "implementation_summary_mexico.csv"
df = pd.read_csv(csv_path, encoding="utf-16", sep="\t")
df = df.rename(columns={df.columns[0]: "Partner"})
df = df[df["Partner"].notna() & (df["Partner"].str.strip() != "")]
df = df[~df["Partner"].str.lower().isin(["total", "grand total", ""])]

def to_int(val):
    if pd.isna(val) or str(val).strip() in ["-", "", "–"]:
        return 0
    return int(str(val).replace(",", "").strip())

for col in [c for c in df.columns if c != "Partner"]:
    df[col] = df[col].apply(to_int)

col_map = {
    "Provisioned": "Provisioned",
    "Discovery":   "Discovery",
    "Created":     "Agent Created",
    "Activated":   "Agent in Prod",
    "Used":        "Used",
    "Consumed":    "Consumed",
}

phase_data = {}
for csv_col, phase_name in col_map.items():
    if csv_col in df.columns:
        phase_data[phase_name] = df[csv_col].values
    else:
        match = [c for c in df.columns if csv_col.lower() in c.lower()]
        phase_data[phase_name] = df[match[0]].values if match else [0]*len(df)

funnel_df = pd.DataFrame(phase_data, index=df["Partner"].values)
funnel_df = funnel_df[~funnel_df.index.str.strip().str.lower().isin(["no partner", ""])]
funnel_df = funnel_df.sort_values("Provisioned", ascending=False).head(11)
partners  = funnel_df.index.tolist()

# ── Obtener conteos de Scale ──────────────────────────────────────────────────
scale_counts = get_scale_counts(partners)
funnel_df["Scale"] = [scale_counts.get(p, 0) for p in partners]

phases = ["Provisioned", "Discovery", "Agent Created", "Agent in Prod",
          "Used", "Consumed", "Scale"]

# ── Estilos por fase ──────────────────────────────────────────────────────────
phase_style = {
    "Provisioned":   dict(bg="#4472C4", subtitle="Provisioned SKU"),
    "Discovery":     dict(bg="#2E75B6", subtitle="Project Submitted with OrgId\ntied to Closed/Won Oppty"),
    "Agent Created": dict(bg="#7030A0", subtitle="Build & Test"),
    "Agent in Prod": dict(bg="#375623", subtitle="Activated"),
    "Used":          dict(bg="#808080", subtitle="Conversations in\nProduction Org"),
    "Consumed":      dict(bg="#9C7A00", subtitle="50+ Conversations\nLast 7 days"),
    "Scale":         dict(bg="#C0504D", subtitle="100K+ Actions\nper Week"),
}

section_labels = {
    "Implementing": [0, 1, 2, 3],
    "Consuming":    [4, 5, 6],
}

# ── Layout ────────────────────────────────────────────────────────────────────
COL_W    = 1.18
ROW_H    = 1.30
LABEL_W  = 2.8
SEC_W    = 0.45
LEFT_PAD = SEC_W + LABEL_W
TOP_PAD  = 2.2
n_rows   = len(phases)
n_cols   = len(partners)

fig_w = LEFT_PAD + n_cols * COL_W + 0.4
fig_h = TOP_PAD + n_rows * ROW_H + 0.6

fig, ax = plt.subplots(figsize=(fig_w, fig_h))
ax.set_xlim(0, fig_w)
ax.set_ylim(0, fig_h)
ax.axis("off")
BG = "#D6EAF8"
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

def row_y(i):
    return fig_h - TOP_PAD - (i + 1) * ROW_H

# Anchuras embudo: se estrechan linealmente
funnel_widths = [LABEL_W * (1.0 - 0.085 * i) for i in range(n_rows + 1)]
funnel_cx = SEC_W + LABEL_W / 2

# ── Título ────────────────────────────────────────────────────────────────────
ax.text(LEFT_PAD + (n_cols * COL_W) / 2, fig_h - 0.22,
        "MEXICO AF Implementation Funnel",
        fontsize=20, fontweight="bold", color="#1F3864",
        ha="center", va="top")

# ── Headers de partners ───────────────────────────────────────────────────────
for j, partner in enumerate(partners):
    label = partner
    label = label.replace(" TECNOLOGIA LTDA dba EVERYMIND", "\nEVERYMIND")
    label = label.replace(" TECNOLOGIA LTDA", "").replace(" dba ", "\n")
    label = label.replace(" LLC", "").replace(" LTDA", "")
    if len(label) > 14 and "\n" not in label:
        parts, w = [], label
        while len(w) > 14:
            sp = w[:15].rfind(" ")
            sp = sp if sp > 3 else 14
            parts.append(w[:sp]); w = w[sp:].strip()
        parts.append(w); label = "\n".join(parts)

    cx = LEFT_PAD + j * COL_W + COL_W / 2
    ax.text(cx, fig_h - TOP_PAD + 0.08, label,
            ha="center", va="bottom", fontsize=9, fontweight="bold",
            color="#1F3864", linespacing=1.3)

# ── Líneas verticales ─────────────────────────────────────────────────────────
for j in range(n_cols + 1):
    x = LEFT_PAD + j * COL_W
    ax.plot([x, x], [row_y(n_rows - 1), row_y(-1)],
            color="#A8C8DC", lw=0.5, zorder=1)

# ── Etiquetas sección ─────────────────────────────────────────────────────────
for sec_name, row_idxs in section_labels.items():
    top_y = row_y(row_idxs[0] - 1)
    bot_y = row_y(row_idxs[-1])
    mid_y = (top_y + bot_y) / 2
    ax.text(SEC_W / 2, mid_y, sec_name,
            ha="center", va="center", fontsize=9, color="#444",
            rotation=90, fontweight="bold", fontstyle="italic")

# ── Líneas punteadas Implementing/Consuming y Consuming/Scale ─────────────────
for sep_idx in [3, 5]:
    sep_y = row_y(sep_idx)
    ax.plot([0, fig_w - 0.1], [sep_y, sep_y],
            color="#555", lw=1.2, linestyle="--", zorder=5)

# ── Filas ─────────────────────────────────────────────────────────────────────
for i, phase in enumerate(phases):
    style  = phase_style[phase]
    y      = row_y(i)
    y_top  = y + ROW_H
    y_bot  = y

    # Fondo zona datos
    row_bg = "#C8DFEE" if i % 2 == 0 else "#B5D0E4"
    ax.add_patch(FancyBboxPatch(
        (LEFT_PAD, y_bot), n_cols * COL_W, ROW_H,
        boxstyle="square,pad=0", linewidth=0, facecolor=row_bg, zorder=0
    ))

    # Trapecio embudo
    w_top = funnel_widths[i]
    w_bot = funnel_widths[i + 1]
    tl = funnel_cx - w_top / 2
    tr = funnel_cx + w_top / 2
    bl = funnel_cx - w_bot / 2
    br = funnel_cx + w_bot / 2

    trap = Polygon(
        [[tl, y_top], [tr, y_top], [br, y_bot], [bl, y_bot]],
        closed=True, facecolor=style["bg"], edgecolor="none", zorder=2
    )
    ax.add_patch(trap)

    # Nombre de la fase
    ax.text(funnel_cx, y + ROW_H * 0.65, phase,
            ha="center", va="center",
            fontsize=12, fontweight="bold", color="white", zorder=3)

    # Subtítulo itálica
    ax.text(funnel_cx, y + ROW_H * 0.28, style["subtitle"],
            ha="center", va="center",
            fontsize=6.5, color="white", alpha=0.92,
            fontstyle="italic", zorder=3, linespacing=1.3)

    # Valores por partner
    for j, partner in enumerate(partners):
        val = funnel_df.loc[partner, phase] if partner in funnel_df.index else 0
        cx  = LEFT_PAD + j * COL_W + COL_W / 2
        cy  = y + ROW_H / 2
        txt = str(int(val)) if val > 0 else "–"
        ax.text(cx, cy, txt,
                ha="center", va="center",
                fontsize=13, fontweight="bold",
                color=style["bg"], zorder=4)

# ── Guardar ───────────────────────────────────────────────────────────────────
out = DOWNLOAD_DIR / "mexico_funnel.png"
plt.savefig(out, dpi=160, bbox_inches="tight", facecolor=fig.get_facecolor())
plt.close()
print(f"Imagen guardada: {out}")
