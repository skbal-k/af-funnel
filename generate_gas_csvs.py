"""
Genera CSVs limpios en UTF-8 para que el GAS los lea desde GitHub.
Corre automáticamente desde update_dashboard.sh.
"""
import sys
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
OUTPUT = Path(__file__).parent / "output"

FUNNEL_TABS = {
    "LACA":           OUTPUT / "implementation_summary_LACA.csv",
    "BRAZIL":         OUTPUT / "implementation_summary_brazil.csv",
    "MEXICO":         OUTPUT / "implementation_summary_mexico.csv",
    "LATAM-GROWTH":   OUTPUT / "implementation_summary_growth.csv",
    "LATAM-EMERGING": OUTPUT / "implementation_summary_emg.csv",
}

STAGE_MAP = {
    "Provisioned":   ["provisioned"],
    "Discovery":     ["discovery"],
    "Agent Created": ["agent created", "created"],
    "Agent in Prod": ["agent in prod", "activated"],
    "Used":          ["used"],
    "Consumed 50+":  ["consumed 50+", "consumed"],
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


def find_col(df, keywords):
    for c in df.columns:
        cl = c.lower().strip()
        for kw in keywords:
            if kw in cl: return c
    return None


def generate_funnel_csvs():
    """Genera un CSV por región con el formato que espera el GAS."""
    for tab, path in FUNNEL_TABS.items():
        if not path.exists():
            print(f"  SKIP gas_{tab.lower()}.csv — CSV no encontrado")
            continue
        df = load_funnel_csv(path)
        # Detectar columnas de stages
        rows = []
        for _, row in df.iterrows():
            entry = {"Partner": row["Partner"]}
            for stage, keywords in STAGE_MAP.items():
                col = find_col(df, keywords)
                entry[stage] = int(row[col]) if col and col in df.columns else 0
            rows.append(entry)
        out = pd.DataFrame(rows)
        out = out.sort_values("Provisioned", ascending=False).head(11)
        out_path = OUTPUT / f"gas_{tab.lower().replace('-','_')}.csv"
        out.to_csv(out_path, index=False, encoding="utf-8")
        print(f"  ✓ {out_path.name} ({len(out)} partners)")


def generate_laca_overview():
    """Genera el CSV de LACA Overview con métricas por región."""
    try:
        from funnel_builder import load_csv, compute_metrics, compute_scale_metrics, COLS

        csv_path   = OUTPUT / "laca_raw_data.csv"
        scale_path = OUTPUT / "laca_scale_accounts.csv"
        if not csv_path.exists():
            print("  SKIP gas_laca_overview.csv — laca_raw_data.csv no encontrado")
            return

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

        STAGES   = ["Provisioned","Discovery","Agent Created","Agent in Prod","Used","Consumed","Scale"]
        COL_KEYS = ["LATAM","LATAM Prtns","Brazil","Brazil Prtns","Mexico","Mexico Prtns",
                    "Growth","Growth Prtns","Emerging","Emerg Prtns"]

        out_rows = []
        for stage in STAGES:
            row_data = metrics.get(stage, {})
            entry = {"Stage": stage}
            for k in COL_KEYS:
                entry[k] = int(row_data.get(k, 0))
            out_rows.append(entry)

        pd.DataFrame(out_rows).to_csv(OUTPUT / "gas_laca_overview.csv", index=False, encoding="utf-8")
        print(f"  ✓ gas_laca_overview.csv ({len(out_rows)} stages)")
    except Exception as e:
        print(f"  ERROR gas_laca_overview.csv: {e}")


def generate_scale_accounts():
    """Genera el CSV de scale accounts limpio."""
    laca_scale = OUTPUT / "laca_scale_accounts.csv"
    sc_csv     = OUTPUT / "scale_clients.csv"
    if not laca_scale.exists():
        print("  SKIP gas_scale_accounts.csv — laca_scale_accounts.csv no encontrado")
        return
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
            return str(p).replace(" TECNOLOGIA LTDA dba EVERYMIND","") \
                         .replace(" TECNOLOGIA LTDA","").replace(" LLC","").replace(" LTDA","").strip()

        def get_region(ou2):
            ou2 = str(ou2)
            if "- BR -" in ou2 or "PS - BR" in ou2: return "Brazil"
            if "- MX -" in ou2:                      return "Mexico"
            if "- GRW -" in ou2:                     return "Growth"
            if "- EMG -" in ou2 or "EMERG" in ou2:  return "Emerging"
            return "LATAM"

        def awu_val(v):
            try: return int(str(v).replace(",",""))
            except: return 0

        sdf["Impl Partner"] = sdf["Impl Partner"].apply(clean_partner)
        sdf["Region"]       = sdf["OU+2"].apply(get_region)
        sdf["AWUs"]         = sdf["Agent AWUs - Week Ending May 9"].apply(awu_val)
        sdf = sdf.sort_values("AWUs", ascending=False)

        out = sdf[["Account Name","Region","Impl Partner","AWUs"]].rename(columns={"Account Name":"Account"})
        out.to_csv(OUTPUT / "gas_scale_accounts.csv", index=False, encoding="utf-8")
        print(f"  ✓ gas_scale_accounts.csv ({len(out)} accounts)")
    except Exception as e:
        print(f"  ERROR gas_scale_accounts.csv: {e}")


def generate_metadata():
    meta = {"updated_at": datetime.now().strftime("%Y-%m-%d %H:%M")}
    with open(OUTPUT / "gas_metadata.json", "w") as f:
        json.dump(meta, f)
    print(f"  ✓ gas_metadata.json")


if __name__ == "__main__":
    print("Generando CSVs para GAS...")
    generate_funnel_csvs()
    generate_laca_overview()
    generate_scale_accounts()
    generate_metadata()
    print("Listo.")
