import streamlit as st
import subprocess
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime
st.set_page_config(
    page_title="AF Implementation Funnel",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Login — email @salesforce.com + contraseña ────────────────────────────────
_APP_PASSWORD = "agentforce"

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown("## ⚡ AF Implementation Funnel")
    st.markdown("**Ingresá tus datos para acceder:**")
    email_input = st.text_input("Email (@salesforce.com)", key="login_email")
    pwd_input   = st.text_input("Contraseña", type="password", key="login_pwd")
    if st.button("Ingresar"):
        if not email_input.endswith("@salesforce.com"):
            st.error("Solo se permite acceso con cuentas @salesforce.com.")
        elif pwd_input != _APP_PASSWORD:
            st.error("Contraseña incorrecta.")
        else:
            st.session_state["authenticated"] = True
            st.session_state["user_email"] = email_input
            st.rerun()
    st.stop()

BASE   = Path(__file__).parent
OUTPUT = BASE / "output"
is_admin = st.session_state.get("user_email", "") == "skbal@salesforce.com"

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp { background: #f4f7fb; }

/* Top bar */
.top-bar {
    background: #1a2e4a;
    border-radius: 12px;
    padding: 18px 28px;
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 24px;
}
.top-bar-title {
    color: white;
    font-size: 1.35rem;
    font-weight: 800;
    letter-spacing: -0.3px;
    margin: 0;
}
.top-bar-sub {
    color: #8eaecf;
    font-size: 0.82rem;
    margin: 0;
}

/* KPI cards */
.kpi-card {
    background: white;
    border-radius: 14px;
    padding: 22px 24px;
    box-shadow: 0 1px 8px rgba(0,0,0,0.07);
    border-top: 4px solid var(--kpi-color, #2E75B6);
    text-align: center;
}
.kpi-value {
    font-size: 2.6rem;
    font-weight: 800;
    color: var(--kpi-color, #2E75B6);
    line-height: 1;
    margin-bottom: 4px;
}
.kpi-label {
    font-size: 0.78rem;
    font-weight: 700;
    color: #8899aa;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}

/* Filter bar */
.filter-bar {
    background: white;
    border-radius: 12px;
    padding: 14px 24px;
    box-shadow: 0 1px 6px rgba(0,0,0,0.06);
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 24px;
}

/* Table */
.funnel-table {
    background: white;
    border-radius: 14px;
    padding: 0;
    box-shadow: 0 1px 8px rgba(0,0,0,0.07);
    overflow: hidden;
    width: 100%;
    border-collapse: collapse;
}
.funnel-table th {
    background: #1a2e4a;
    color: white;
    font-size: 0.8rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    padding: 12px 16px;
    text-align: center;
}
.funnel-table th:first-child { text-align: left; }
.funnel-table td {
    padding: 12px 16px;
    text-align: center;
    font-size: 0.92rem;
    border-bottom: 1px solid #f0f4f8;
}
.funnel-table td:first-child {
    text-align: left;
    font-weight: 700;
    color: #1a2e4a;
    font-size: 0.9rem;
}
.funnel-table tr:last-child td { border-bottom: none; }
.funnel-table tr:nth-child(even) td { background: #fafcff; }
.funnel-table tr:hover td { background: #eef4fb; }

.cell-val { font-weight: 700; color: #1a2e4a; font-size: 1rem; }
.cell-dash { color: #ccc; font-size: 1rem; }

/* Stage badges */
.stage-badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 700;
    color: white;
    margin-right: 8px;
}

/* Refresh button */
div[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #1a2e4a 0%, #2E75B6 100%);
    color: white !important;
    border: none;
    border-radius: 8px;
    padding: 0.5rem 1.6rem;
    font-size: 0.88rem;
    font-weight: 700;
    transition: opacity 0.2s;
    box-shadow: 0 3px 10px rgba(26,46,74,0.25);
}
div[data-testid="stButton"] > button:hover { opacity: 0.85; }

/* Download button */
div[data-testid="stDownloadButton"] > button {
    background: white;
    color: #1a2e4a !important;
    border: 2px solid #1a2e4a !important;
    border-radius: 8px;
    font-weight: 700;
}

/* Selectbox */
div[data-baseweb="select"] > div {
    border-radius: 8px !important;
    border-color: #d0dce8 !important;
    background: white !important;
}

/* Section title */
.section-title {
    font-size: 1rem;
    font-weight: 700;
    color: #1a2e4a;
    margin-bottom: 12px;
    padding-bottom: 6px;
    border-bottom: 2px solid #e8f0f8;
}
</style>
""", unsafe_allow_html=True)

# ── Config regiones ───────────────────────────────────────────────────────────
REGIONS = {
    "🌎  LACA (All)":      dict(script="tableau_agent.py",  csv="implementation_summary_LACA.csv",   img="latam_funnel.png",  color="#1a2e4a", scale_filter="LATAM"),
    "🇧🇷  Brazil":         dict(script="brazil_agent.py",   csv="implementation_summary_brazil.csv", img="brazil_funnel.png", color="#009c3b", scale_filter="BRAZIL"),
    "🇲🇽  Mexico":         dict(script="mexico_agent.py",   csv="implementation_summary_mexico.csv", img="mexico_funnel.png", color="#ce1126", scale_filter="MEXICO"),
    "📈  LATAM-Growth":   dict(script="growth_agent.py",   csv="implementation_summary_growth.csv", img="growth_funnel.png", color="#7030A0", scale_filter="GROWTH"),
    "🌱  LATAM-Emerging": dict(script="emg_agent.py",      csv="implementation_summary_emg.csv",    img="emg_funnel.png",    color="#375623", scale_filter="EMERG"),
}

STAGES = [
    ("Provisioned",  "Provisioned", "#4472C4"),
    ("Discovery",    "Discovery",   "#2E75B6"),
    ("Agent Created","Created",     "#7030A0"),
    ("Agent in Prod","Activated",   "#375623"),
    ("Used",         "Used",        "#808080"),
    ("Consumed 50+", "Consumed",    "#9C7A00"),
    ("Scale",        None,          "#C0504D"),
]

def load_csv(csv_path):
    if not csv_path.exists():
        return None
    df = pd.read_csv(csv_path, encoding="utf-16", sep="\t")
    df = df.rename(columns={df.columns[0]: "Partner"})
    df = df[df["Partner"].notna() & (df["Partner"].str.strip() != "")]
    df = df[~df["Partner"].str.lower().isin(["no partner", ""])]
    def to_int(v):
        if pd.isna(v) or str(v).strip() in ["-","","–"]: return 0
        return int(str(v).replace(",","").strip())
    for col in [c for c in df.columns if c != "Partner"]:
        df[col] = df[col].apply(to_int)
    return df

def get_col(df, keyword):
    for c in df.columns:
        if keyword.lower() in c.lower():
            return c
    return None

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="top-bar">
  <div>
    <div class="top-bar-title">⚡ AF Implementation Funnel</div>
    <div class="top-bar-sub">Agentforce Cumulative Go-Live · LATAM Partner Team</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Filter bar ────────────────────────────────────────────────────────────────
top_n = 11

col_f1, col_f3 = st.columns([3, 1])

with col_f1:
    selected = st.selectbox("Sub Sub Region", list(REGIONS.keys()), label_visibility="visible")

with col_f3:
    st.markdown("<br>", unsafe_allow_html=True)
    refresh = st.button("🔄  Refresh from Tableau") if is_admin else False

cfg = REGIONS[selected]
img_path = OUTPUT / cfg["img"]

# ── Refresh ───────────────────────────────────────────────────────────────────
if refresh:
    with st.spinner(f"Connecting to Tableau..."):
        result = subprocess.run(
            [sys.executable, str(BASE / cfg["script"])],
            capture_output=True, text=True
        )
    if result.returncode == 0:
        st.success("✅ Data refreshed!")
        st.rerun()
    else:
        st.error("❌ Error. Check Tableau session.")
        with st.expander("Error log"):
            st.code(result.stderr[-2000:])

st.markdown("---")

# ── Load data ─────────────────────────────────────────────────────────────────
csv_path = OUTPUT / cfg["csv"]
df = load_csv(csv_path)

if df is None:
    st.info(f"No data for **{selected}** yet. Click **Refresh from Tableau**.")
    st.stop()

# Top N partners — ordenar por Provisioned descendente
sort_col = get_col(df, "Provisioned") or (df.columns[1] if len(df.columns) > 1 else df.columns[0])
df = df.sort_values(sort_col, ascending=False).head(top_n)
partners = df["Partner"].tolist()

# ── KPI cards ─────────────────────────────────────────────────────────────────
prov_col  = get_col(df, "Provisioned")
activ_col = get_col(df, "Activated")
used_col  = get_col(df, "Used")
cons_col  = get_col(df, "Consumed")

prov  = int(df[prov_col].sum())  if prov_col  else 0
activ = int(df[activ_col].sum()) if activ_col else 0
used  = int(df[used_col].sum())  if used_col  else 0
cons  = int(df[cons_col].sum())  if cons_col  else 0

kpi_cols = st.columns(5)
kpis = [
    ("Partners",     len(partners),  "#1a2e4a"),
    ("Provisioned",  prov,           "#4472C4"),
    ("Agent in Prod",activ,          "#375623"),
    ("Used",         used,           "#808080"),
    ("Consumed 50+", cons,           "#9C7A00"),
]
for col, (label, val, color) in zip(kpi_cols, kpis):
    top_tag = "<div style='font-size:0.7rem;font-weight:700;color:#8899aa;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:2px'>Top</div>" if label == "Partners" else ""
    html = (
        f"<div class='kpi-card' style='--kpi-color:{color}'>"
        + top_tag
        + f"<div class='kpi-value'>{val:,}</div>"
        + f"<div class='kpi-label'>{label}</div>"
        + "</div>"
    )
    col.markdown(html, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Tabla interactiva ─────────────────────────────────────────────────────────
AGENT1_OUTPUT = BASE / "output"
AGENT1_SCRIPT = Path("/Users/skbal/claude/tableau_agent/agent.py")

tab1, tab3 = st.tabs(["📊  Funnel Table", "🌎  LACA Overview"])

with tab1:
    st.markdown('<div class="section-title">Funnel by Implementation Partner</div>', unsafe_allow_html=True)

    # Construir tabla
    short_names = []
    for p in partners:
        s = p.replace(" TECNOLOGIA LTDA dba EVERYMIND", "").replace(" TECNOLOGIA LTDA", "")
        s = s.replace(" LLC", "").replace(" LTDA", "").replace(" S.A.", "").strip()
        if len(s) > 18:
            s = s[:16] + "…"
        short_names.append(s)

    # Header
    header_html = "<table class='funnel-table'><thead><tr><th>Stage</th>"
    for sn in short_names:
        header_html += f"<th>{sn}</th>"
    header_html += "<th>TOTAL</th></tr></thead><tbody>"

    # Cargar scale
    scale_counts = {}
    try:
        import json
        scale_csv = OUTPUT / "scale_clients.csv"
        if scale_csv.exists():
            sdf = pd.read_csv(scale_csv, encoding="utf-8", on_bad_lines='skip')
            sdf = sdf.rename(columns={'Unnamed: 12': 'Impl Partner'})
            region_filter = cfg["csv"]
            if "brazil" in region_filter:
                sdf = sdf[sdf.get('Unnamed: 13', pd.Series(dtype=str)).str.upper().str.contains('BRAZIL', na=False)]
            elif "mexico" in region_filter:
                sdf = sdf[sdf.get('Unnamed: 13', pd.Series(dtype=str)).str.upper().str.contains('MEXICO', na=False)]
            elif "growth" in region_filter:
                sdf = sdf[sdf.get('Unnamed: 13', pd.Series(dtype=str)).str.upper().str.contains('GROWTH', na=False)]
            elif "emg" in region_filter:
                sdf = sdf[sdf.get('Unnamed: 13', pd.Series(dtype=str)).str.upper().str.contains('EMERG', na=False)]
            else:
                sdf = sdf[sdf['OU'].str.contains('LATAM', na=False)]
            sdf['Impl Partner'] = sdf['Impl Partner'].fillna('No Partner')
            scale_counts = sdf.groupby('Impl Partner').size().to_dict()
    except Exception:
        pass

    rows_html = ""
    for stage_label, csv_keyword, color in STAGES:
        rows_html += f"<tr><td><span class='stage-badge' style='background:{color}'>&nbsp;</span>{stage_label}</td>"
        total = 0
        for partner in partners:
            if csv_keyword is None:
                # Scale — cruzar con sheet
                val = 0
                for k, v in scale_counts.items():
                    if k != 'No Partner' and (partner.upper() in k.upper() or k.upper() in partner.upper()):
                        val = v
                        break
            else:
                col_name = get_col(df, csv_keyword)
                if col_name and partner in df["Partner"].values:
                    val = int(df[df["Partner"] == partner][col_name].values[0])
                else:
                    val = 0
            total += val
            if val > 0:
                rows_html += f"<td><span class='cell-val' style='color:{color}'>{val}</span></td>"
            else:
                rows_html += f"<td><span class='cell-dash'>–</span></td>"
        rows_html += f"<td><b style='color:{color}'>{total}</b></td></tr>"

    st.markdown(header_html + rows_html + "</tbody></table>", unsafe_allow_html=True)

    # Última actualización
    if csv_path.exists():
        mtime = datetime.fromtimestamp(csv_path.stat().st_mtime)
        st.markdown(f"<br><span style='font-size:0.72rem;color:#aaa'>Last updated: {mtime.strftime('%Y-%m-%d %H:%M')}</span>",
                    unsafe_allow_html=True)

    # ── Funnel Chart debajo de la tabla ──────────────────────────────────────
    if img_path.exists():
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-title">Funnel Chart</div>', unsafe_allow_html=True)
        col_chart, col_dl_chart = st.columns([5, 1])
        with col_chart:
            st.image(str(img_path), use_container_width=True)
        with col_dl_chart:
            st.markdown("<br><br><br>", unsafe_allow_html=True)
            with open(img_path, "rb") as f:
                st.download_button("⬇️  Download PNG", f, file_name=cfg["img"], mime="image/png", key="dl_funnel_chart")

with tab3:
    st.markdown('<div class="section-title">LACA Agentforce Funnel — All Accounts (excl. ESMB)</div>', unsafe_allow_html=True)

    laca_json = AGENT1_OUTPUT / "laca_latest.json"

    col_a1, col_a2 = st.columns([1, 5])
    with col_a1:
        refresh_laca = st.button("🔄  Refresh LACA") if is_admin else False

    with col_a2:
        laca_csv = AGENT1_OUTPUT / "laca_raw_data.csv"
        if laca_csv.exists():
            mtime_laca = datetime.fromtimestamp(laca_csv.stat().st_mtime)
            st.markdown(f"<span style='font-size:0.78rem;color:#aaa'>Last updated: {mtime_laca.strftime('%Y-%m-%d %H:%M')}</span>", unsafe_allow_html=True)

    if refresh_laca:
        with st.spinner("Regenerating LACA funnel..."):
            csv_candidates = [
                AGENT1_OUTPUT / "laca_raw_data.csv",
                AGENT1_OUTPUT / "laca_raw_data.csv",
                AGENT1_OUTPUT / "laca_raw_data.csv",
            ]
            csv_found = next((str(p) for p in csv_candidates if p.exists()), None)
            if csv_found:
                result = subprocess.run(
                    [sys.executable, "-c",
                     f"import sys; sys.path.insert(0,'{AGENT1_OUTPUT.parent}'); "
                     f"from funnel_builder import run; from pathlib import Path; "
                     f"run(Path('{csv_found}'))"],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    st.success("✅ LACA funnel refreshed!")
                    st.rerun()
                else:
                    st.error("❌ Error regenerating funnel.")
                    with st.expander("Error log"):
                        st.code(result.stderr[-2000:])
            else:
                st.error("❌ No CSV data found. Run the LACA agent first: `python3 agent.py`")

    # ── Build table from raw data ──────────────────────────────────────────
    import sys as _sys
    _sys.path.insert(0, str(AGENT1_OUTPUT.parent))

    _csv_candidates = [
        AGENT1_OUTPUT / "laca_raw_data.csv",
        AGENT1_OUTPUT / "laca_raw_data.csv",
        AGENT1_OUTPUT / "laca_raw_data.csv",
    ]
    _csv_path = next((p for p in _csv_candidates if p.exists()), None)

    if _csv_path:
        try:
            from funnel_builder import load_csv as _load_csv, compute_metrics as _compute_metrics, compute_scale_metrics as _compute_scale_metrics, COLS as _COLS

            _rows = _load_csv(_csv_path)
            _metrics = _compute_metrics(_rows)

            # Load scale IDs if available
            _scale_csv = AGENT1_OUTPUT / "laca_scale_accounts.csv"
            _scale_ids = []
            if _scale_csv.exists():
                _sdf = pd.read_csv(_scale_csv, encoding="utf-8", on_bad_lines="skip")
                _id_col = next((c for c in _sdf.columns if "ACCT_ID_18" in c.upper() or "18" in c), None)
                if _id_col:
                    _scale_ids = _sdf[_id_col].dropna().tolist()
            _scale_m = _compute_scale_metrics(_rows, _scale_ids) if _scale_ids else {k: 0 for k in _COLS}
            _metrics["Scale"] = _scale_m

            LACA_STAGES = [
                ("Provisioned",   "#4472C4"),
                ("Discovery",     "#2E75B6"),
                ("Agent Created", "#7030A0"),
                ("Agent in Prod", "#2E7D5E"),
                ("Used",          "#6C757D"),
                ("Consumed",      "#C4A82A"),
                ("Scale",         "#E57373"),
            ]

            LACA_COLS = [
                ("LATAM",         "LATAM"),
                ("LATAM\nPrtns",  "LATAM Prtns"),
                ("Brazil",        "Brazil"),
                ("Brazil\nPrtns", "Brazil Prtns"),
                ("Mexico",        "Mexico"),
                ("Mexico\nPrtns", "Mexico Prtns"),
                ("Growth",        "Growth"),
                ("Growth\nPrtns", "Growth Prtns"),
                ("Emerging",      "Emerging"),
                ("Emerg\nPrtns",  "Emerg Prtns"),
            ]

            PCT_BASES = {
                "LATAM Prtns":  "LATAM",
                "Brazil Prtns": "Brazil",
                "Mexico Prtns": "Mexico",
                "Growth Prtns": "Growth",
                "Emerg Prtns":  "Emerging",
            }

            def _pct(a, b):
                return f"{round(a/b*100)}%" if b else "–"

            # Header
            hdr = "<table class='funnel-table'><thead><tr><th>Stage</th>"
            for col_label, _ in LACA_COLS:
                hdr += f"<th>{col_label.replace(chr(10), '<br>')}</th>"
            hdr += "</tr></thead><tbody>"

            rows_laca = ""
            for stage, color in LACA_STAGES:
                rows_laca += f"<tr><td><span class='stage-badge' style='background:{color}'>&nbsp;</span>{stage}</td>"
                row_data = _metrics.get(stage, {})
                for _, col_key in LACA_COLS:
                    val = row_data.get(col_key, 0)
                    base_key = PCT_BASES.get(col_key)
                    if base_key:
                        base_val = row_data.get(base_key, 0)
                        pct_str = _pct(val, base_val)
                        rows_laca += (
                            f"<td><span class='cell-val' style='color:{color}'>{val}</span>"
                            f"<br><span style='font-size:0.75rem;color:#888'>{pct_str}</span></td>"
                        )
                    else:
                        if val:
                            rows_laca += f"<td><span class='cell-val' style='color:{color}'>{val}</span></td>"
                        else:
                            rows_laca += "<td><span class='cell-dash'>–</span></td>"
                rows_laca += "</tr>"

            st.markdown(hdr + rows_laca + "</tbody></table>", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error loading LACA data: {e}")
    else:
        st.info("No LACA data yet. Click **Refresh LACA**.")

    # ── Funnel Chart image ─────────────────────────────────────────────────
    laca_img = OUTPUT / "laca_funnel.png"
    if laca_img.exists():
        st.markdown("<br>", unsafe_allow_html=True)
        col_img, col_dl = st.columns([5, 1])
        with col_img:
            st.image(str(laca_img), use_container_width=True)
        with col_dl:
            st.markdown("<br><br><br>", unsafe_allow_html=True)
            with open(laca_img, "rb") as f:
                st.download_button("⬇️  Download PNG", f, file_name="laca_funnel.png", mime="image/png", key="dl_laca_overview")
