"""
Sube los CSVs al Google Apps Script via POST y los escribe en Google Sheets.
Uso: python3 sync_to_sheets.py
"""
import json
import sys
import pandas as pd
import urllib.request
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

OUTPUT  = Path(__file__).parent / "output"
GAS_URL = "https://script.google.com/a/macros/salesforce.com/s/AKfycby-WeueI_5ahmtLRXFX39OUMKqBat_BAoF8ZZMk-ct6Tbv3aajTP6noskHSs1idVZMM/exec"

# ── Tabs de funnel por región ─────────────────────────────────────────────────
FUNNEL_TABS = {
    "LACA":           OUTPUT / "implementation_summary_LACA.csv",
    "BRAZIL":         OUTPUT / "implementation_summary_brazil.csv",
    "MEXICO":         OUTPUT / "implementation_summary_mexico.csv",
    "LATAM-GROWTH":   OUTPUT / "implementation_summary_growth.csv",
    "LATAM-EMERGING": OUTPUT / "implementation_summary_emg.csv",
}


def load_funnel_csv(path):
    df = pd.read_csv(path, encoding="utf-16", sep="\t")
    df = df.rename(columns={df.columns[0]: "Partner"})
    df = df[df["Partner"].notna() & (df["Partner"].str.strip() != "")]
    df = df[~df["Partner"].str.lower().isin(["no partner", "total", "grand total", ""])]
    def to_int(v):
        if pd.isna(v) or str(v).strip() in ["-", "", "–"]: return 0
        try: return int(str(v).replace(",", "").strip())
        except: return 0
    for col in [c for c in df.columns if c != "Partner"]:
        df[col] = df[col].apply(to_int)
    return df


def build_laca_overview():
    """Construye la tabla de LACA Overview usando funnel_builder."""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from funnel_builder import load_csv, compute_metrics, compute_scale_metrics, COLS

        csv_path   = OUTPUT / "laca_raw_data.csv"
        scale_path = OUTPUT / "laca_scale_accounts.csv"

        if not csv_path.exists():
            print("  SKIP LACA_OVERVIEW — laca_raw_data.csv no encontrado")
            return None

        rows    = load_csv(csv_path)
        metrics = compute_metrics(rows)

        scale_ids = []
        if scale_path.exists():
            sdf = pd.read_csv(scale_path, encoding="utf-8", on_bad_lines="skip")
            id_col = next((c for c in sdf.columns if "ACCT_ID_18" in c.upper()), None)
            if id_col:
                scale_ids = sdf[id_col].dropna().tolist()

        scale_m = compute_scale_metrics(rows, scale_ids) if scale_ids else {k: 0 for k in COLS}
        metrics["Scale"] = scale_m

        STAGES = ["Provisioned","Discovery","Agent Created","Agent in Prod","Used","Consumed","Scale"]
        COL_KEYS = ["LATAM","LATAM Prtns","Brazil","Brazil Prtns","Mexico","Mexico Prtns",
                    "Growth","Growth Prtns","Emerging","Emerg Prtns"]

        headers = ["Stage"] + COL_KEYS
        table   = [headers]
        for stage in STAGES:
            row_data = metrics.get(stage, {})
            row = [stage] + [int(row_data.get(k, 0)) for k in COL_KEYS]
            table.append(row)
        return table

    except Exception as e:
        print(f"  ERROR buildando LACA Overview: {e}")
        return None


def build_scale_accounts():
    """Construye la tabla de Scale Accounts cruzando los dos CSVs."""
    laca_scale = OUTPUT / "laca_scale_accounts.csv"
    sc_csv     = OUTPUT / "scale_clients.csv"

    if not laca_scale.exists():
        print("  SKIP SCALE_ACCOUNTS — laca_scale_accounts.csv no encontrado")
        return None

    try:
        sdf = pd.read_csv(laca_scale, encoding="utf-8", on_bad_lines="skip")
        sdf = sdf[sdf["OU"].str.contains("LATAM", na=False)].copy()

        # Cruzar con scale_clients para obtener el partner
        if sc_csv.exists():
            sc = pd.read_csv(sc_csv, encoding="utf-8", on_bad_lines="skip")
            sc = sc.rename(columns={"Unnamed: 12": "Impl Partner"})
            sc_p = sc[["ACCT_ID_18","Impl Partner"]].dropna(subset=["Impl Partner"])
            sdf = sdf.merge(sc_p, on="ACCT_ID_18", how="left")
        else:
            sdf["Impl Partner"] = None

        def clean_partner(p):
            if pd.isna(p): return "Direct"
            return str(p).replace(" TECNOLOGIA LTDA dba EVERYMIND","") \
                         .replace(" TECNOLOGIA LTDA","").replace(" LLC","") \
                         .replace(" LTDA","").strip()

        def get_region(ou2):
            ou2 = str(ou2)
            if "- BR -" in ou2 or "PS - BR" in ou2: return "🇧🇷 Brazil"
            if "- MX -" in ou2:                       return "🇲🇽 Mexico"
            if "- GRW -" in ou2:                      return "📈 Growth"
            if "- EMG -" in ou2 or "EMERG" in ou2:   return "🌱 Emerging"
            return "🌎 LATAM"

        sdf["Impl Partner"] = sdf["Impl Partner"].apply(clean_partner)
        sdf["Region"]       = sdf["OU+2"].apply(get_region)

        # Ordenar por AWUs desc
        def awu_val(v):
            try: return int(str(v).replace(",",""))
            except: return 0
        sdf["_awu_num"] = sdf["Agent AWUs - Week Ending May 9"].apply(awu_val)
        sdf = sdf.sort_values("_awu_num", ascending=False)

        headers = ["Account","Region","Impl Partner","AWUs"]
        table   = [headers]
        for _, row in sdf.iterrows():
            table.append([
                str(row["Account Name"]),
                str(row["Region"]),
                str(row["Impl Partner"]),
                int(row["_awu_num"])
            ])
        return table

    except Exception as e:
        print(f"  ERROR buildando Scale Accounts: {e}")
        return None


def send_to_gas(all_data, token_path, creds_path):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import AuthorizedSession, Request

    raw_creds  = json.loads(creds_path.read_text())["installed"]
    token_data = json.loads(token_path.read_text())

    creds = Credentials(
        token=token_data.get("access_token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=raw_creds["token_uri"],
        client_id=raw_creds["client_id"],
        client_secret=raw_creds["client_secret"],
    )
    if not creds.valid:
        creds.refresh(Request())

    session = AuthorizedSession(creds)
    payload = json.dumps({"action": "syncData", "data": all_data})
    resp = session.post(GAS_URL, data=payload, headers={"Content-Type": "application/json"})
    resp.raise_for_status()
    return resp.json()


def main():
    all_data = {}

    # ── Funnel tabs ──────────────────────────────────────────────────────────
    for tab_name, csv_path in FUNNEL_TABS.items():
        if not csv_path.exists():
            print(f"  SKIP {tab_name} — CSV no encontrado")
            continue
        print(f"  Cargando {tab_name}...", end=" ", flush=True)
        df   = load_funnel_csv(csv_path)
        rows = [df.columns.tolist()] + [[str(v) for v in row] for row in df.values.tolist()]
        all_data[tab_name] = rows
        print(f"✓ {len(df)} filas")

    # ── LACA Overview ────────────────────────────────────────────────────────
    print("  Buildando LACA Overview...", end=" ", flush=True)
    laca_table = build_laca_overview()
    if laca_table:
        all_data["LACA_OVERVIEW"] = laca_table
        print(f"✓ {len(laca_table)-1} filas")

    # ── Scale Accounts ───────────────────────────────────────────────────────
    print("  Buildando Scale Accounts...", end=" ", flush=True)
    scale_table = build_scale_accounts()
    if scale_table:
        all_data["SCALE_ACCOUNTS"] = scale_table
        print(f"✓ {len(scale_table)-1} cuentas")

    # ── Enviar al GAS ────────────────────────────────────────────────────────
    print("  Enviando al Apps Script...", end=" ", flush=True)
    token_path = Path(__file__).parent / "gas_token.json"
    creds_path = Path(__file__).parent.parent / "personal-assistant" / "credentials.json"

    if not token_path.exists():
        print("❌ No encontré gas_token.json — corré: python3 get_google_token.py")
        return
    if not creds_path.exists():
        print("❌ No encontré credentials.json")
        return

    result = send_to_gas(all_data, token_path, creds_path)
    if result.get("ok"):
        print(f"✓ {result.get('msg', 'Sync completo')}")
    else:
        print(f"✗ Error: {result}")


if __name__ == "__main__":
    main()
