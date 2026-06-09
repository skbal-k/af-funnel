"""
Genera los CSVs para el GAS y los sube a GitHub.
El GAS los lee directamente desde GitHub raw.
Uso: python3 sync_to_sheets.py
"""
import json
import subprocess
import sys
import pandas as pd
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

OUTPUT  = Path(__file__).parent / "output"

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
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from funnel_builder import load_csv, compute_metrics, compute_scale_metrics, COLS
        csv_path   = OUTPUT / "laca_raw_data.csv"
        scale_path = OUTPUT / "laca_scale_accounts.csv"
        if not csv_path.exists(): return None
        rows    = load_csv(csv_path)
        metrics = compute_metrics(rows)
        scale_ids = []
        if scale_path.exists():
            sdf = pd.read_csv(scale_path, encoding="utf-8", on_bad_lines="skip")
            id_col = next((c for c in sdf.columns if "ACCT_ID_18" in c.upper()), None)
            if id_col: scale_ids = sdf[id_col].dropna().tolist()
        scale_m = compute_scale_metrics(rows, scale_ids) if scale_ids else {k: 0 for k in COLS}
        metrics["Scale"] = scale_m
        STAGES   = ["Provisioned","Discovery","Agent Created","Agent in Prod","Used","Consumed","Scale"]
        COL_KEYS = ["LATAM","LATAM Prtns","Brazil","Brazil Prtns","Mexico","Mexico Prtns",
                    "Growth","Growth Prtns","Emerging","Emerg Prtns"]
        table = [["Stage"] + COL_KEYS]
        for stage in STAGES:
            row_data = metrics.get(stage, {})
            table.append([stage] + [int(row_data.get(k, 0)) for k in COL_KEYS])
        return table
    except Exception as e:
        print(f"  ERROR LACA Overview: {e}")
        return None


def build_scale_accounts():
    laca_scale = OUTPUT / "laca_scale_accounts.csv"
    sc_csv     = OUTPUT / "scale_clients.csv"
    if not laca_scale.exists(): return None
    try:
        sdf = pd.read_csv(laca_scale, encoding="utf-8", on_bad_lines="skip")
        sdf = sdf[sdf["OU"].str.contains("LATAM", na=False)].copy()
        if sc_csv.exists():
            sc  = pd.read_csv(sc_csv, encoding="utf-8", on_bad_lines="skip")
            sc  = sc.rename(columns={"Unnamed: 12": "Impl Partner"})
            sc_p = sc[["ACCT_ID_18","Impl Partner"]].dropna(subset=["Impl Partner"])
            sdf = sdf.merge(sc_p, on="ACCT_ID_18", how="left")
        else:
            sdf["Impl Partner"] = None
        def clean_partner(p):
            if pd.isna(p): return "Direct"
            return str(p).replace(" TECNOLOGIA LTDA dba EVERYMIND","").replace(" TECNOLOGIA LTDA","") \
                         .replace(" LLC","").replace(" LTDA","").strip()
        def get_region(ou2):
            ou2 = str(ou2)
            if "- BR -" in ou2 or "PS - BR" in ou2: return "Brazil"
            if "- MX -" in ou2: return "Mexico"
            if "- GRW -" in ou2: return "Growth"
            return "LATAM"
        def awu_val(v):
            try: return int(str(v).replace(",",""))
            except: return 0
        sdf["Impl Partner"] = sdf["Impl Partner"].apply(clean_partner)
        sdf["Region"]       = sdf["OU+2"].apply(get_region)
        sdf["AWUs"]         = sdf["Agent AWUs - Week Ending May 9"].apply(awu_val)
        sdf = sdf.sort_values("AWUs", ascending=False)
        table = [["Account","Region","Impl Partner","AWUs"]]
        for _, row in sdf.iterrows():
            table.append([str(row["Account Name"]), str(row["Region"]),
                          str(row["Impl Partner"]), int(row["AWUs"])])
        return table
    except Exception as e:
        print(f"  ERROR Scale Accounts: {e}")
        return None


def push_to_github(files):
    """Hace git add + commit + push de los archivos indicados."""
    repo = Path(__file__).parent
    subprocess.run(["git", "add"] + [str(f) for f in files], cwd=repo, check=True)
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=repo
    )
    if result.returncode == 0:
        print("Sin cambios nuevos.")
        return
    subprocess.run(
        ["git", "commit", "-m", f"Sync data {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}"],
        cwd=repo, check=True
    )
    subprocess.run(["git", "pull", "--rebase", "origin", "main"], cwd=repo, check=True)
    subprocess.run(["git", "push"], cwd=repo, check=True)


def main():
    all_data = {}

    for tab_name, csv_path in FUNNEL_TABS.items():
        if not csv_path.exists():
            print(f"  SKIP {tab_name}")
            continue
        print(f"  Cargando {tab_name}...", end=" ", flush=True)
        df   = load_funnel_csv(csv_path)
        rows = [df.columns.tolist()] + [[str(v) for v in row] for row in df.values.tolist()]
        all_data[tab_name] = rows
        print(f"✓ {len(df)} filas")

    print("  Buildando LACA Overview...", end=" ", flush=True)
    laca = build_laca_overview()
    if laca:
        all_data["LACA_OVERVIEW"] = laca
        print(f"✓")

    print("  Buildando Scale Accounts...", end=" ", flush=True)
    scale = build_scale_accounts()
    if scale:
        all_data["SCALE_ACCOUNTS"] = scale
        print(f"✓")

    # Generar los gas_*.csv desde los datos procesados
    print("  Generando CSVs para GAS...", end=" ", flush=True)
    sys.path.insert(0, str(Path(__file__).parent))
    from generate_gas_csvs import generate_funnel_csvs, generate_laca_overview, generate_scale_accounts, generate_metadata
    generate_funnel_csvs()
    generate_laca_overview()
    generate_scale_accounts()
    generate_metadata()
    print("✓")

    gas_files = list(OUTPUT.glob("gas_*.csv")) + [OUTPUT / "gas_metadata.json"]
    print(f"  Subiendo {len(gas_files)} archivos a GitHub...", end=" ", flush=True)
    push_to_github(gas_files)
    print("✓ Listo — el GAS se actualiza en ~30 segundos.")


if __name__ == "__main__":
    main()
