"""
Sube los CSVs al Google Apps Script via POST.
No necesita credenciales GCP — usa el endpoint ya deployado.

Uso: python3 sync_to_sheets.py
"""
import json
import pandas as pd
import urllib.request
import urllib.parse
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

OUTPUT   = Path(__file__).parent / "output"

# Pegá acá el URL de tu Google Apps Script deployment
GAS_URL  = "https://script.google.com/a/macros/salesforce.com/s/AKfycby-WeueI_5ahmtLRXFX39OUMKqBat_BAoF8ZZMk-ct6Tbv3aajTP6noskHSs1idVZMM/exec"

TABS = {
    "LACA":           OUTPUT / "implementation_summary_LACA.csv",
    "BRAZIL":         OUTPUT / "implementation_summary_brazil.csv",
    "MEXICO":         OUTPUT / "implementation_summary_mexico.csv",
    "LATAM-GROWTH":   OUTPUT / "implementation_summary_growth.csv",
    "LATAM-EMERGING": OUTPUT / "implementation_summary_emg.csv",
}


def load_csv(path):
    df = pd.read_csv(path, encoding="utf-16", sep="\t")
    df = df.rename(columns={df.columns[0]: "Partner"})
    df = df[df["Partner"].notna() & (df["Partner"].str.strip() != "")]
    df = df[~df["Partner"].str.lower().isin(["no partner", "total", "grand total", ""])]

    def to_int(v):
        if pd.isna(v) or str(v).strip() in ["-", "", "–"]:
            return 0
        try:
            return int(str(v).replace(",", "").strip())
        except:
            return 0

    for col in [c for c in df.columns if c != "Partner"]:
        df[col] = df[col].apply(to_int)
    return df


def main():
    if GAS_URL == "PEGAR_URL_DEL_DEPLOYMENT_ACA":
        print("❌ Pegá el URL del deployment en la variable GAS_URL del script.")
        return

    all_data = {}
    for tab_name, csv_path in TABS.items():
        if not csv_path.exists():
            print(f"  SKIP {tab_name} — CSV no encontrado")
            continue
        print(f"  Cargando {tab_name}...", end=" ", flush=True)
        df = load_csv(csv_path)
        rows = [df.columns.tolist()] + [[str(v) for v in row] for row in df.values.tolist()]
        all_data[tab_name] = rows
        print(f"✓ {len(df)} filas")

    print("  Enviando al Apps Script...", end=" ", flush=True)

    token_path = Path(__file__).parent / "gas_token.json"
    creds_path = Path(__file__).parent.parent / "personal-assistant" / "credentials.json"
    if not token_path.exists():
        print("❌ No encontré gas_token.json — corré primero: python3 get_google_token.py")
        return

    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import AuthorizedSession, Request

    raw_creds = json.loads(creds_path.read_text())["installed"]
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
    result = resp.json()
    if result.get("ok"):
        print(f"✓ {result.get('msg', 'Sync completo')}")
    else:
        print(f"✗ Error: {result}")


if __name__ == "__main__":
    main()
