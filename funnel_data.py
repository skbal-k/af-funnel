"""
Fetches AF Implementation Funnel data from Salesforce.
Each function returns a dict: { partner_name: count, ... }
"""

import pandas as pd
from salesforce_client import query


def _partner_col() -> str:
    # Adjust this field name to match your Salesforce schema
    return "Partner_Name__c"


def get_provisioned(extra_filters: str = "") -> dict:
    """Projects submitted with OrgID tied to Closed/Won Oppty."""
    where = "WHERE Project_Status__c != NULL AND Closed_Won_Oppty__c = true"
    if extra_filters:
        where += f" AND {extra_filters}"
    records = query(
        f"SELECT {_partner_col()}, COUNT(Id) cnt "
        f"FROM AF_Implementation_Project__c "
        f"{where} "
        f"GROUP BY {_partner_col()}"
    )
    return {r[_partner_col()] or "No Partner": r["cnt"] for r in records}


def get_discovery(extra_filters: str = "") -> dict:
    where = "WHERE Stage__c = 'Discovery' AND Closed_Won_Oppty__c = true"
    if extra_filters:
        where += f" AND {extra_filters}"
    records = query(
        f"SELECT {_partner_col()}, COUNT(Id) cnt "
        f"FROM AF_Implementation_Project__c "
        f"{where} "
        f"GROUP BY {_partner_col()}"
    )
    return {r[_partner_col()] or "No Partner": r["cnt"] for r in records}


def get_agent_created(extra_filters: str = "") -> dict:
    where = "WHERE Stage__c = 'Build & Test' AND Agent_Created__c = true"
    if extra_filters:
        where += f" AND {extra_filters}"
    records = query(
        f"SELECT {_partner_col()}, COUNT(Id) cnt "
        f"FROM AF_Implementation_Project__c "
        f"{where} "
        f"GROUP BY {_partner_col()}"
    )
    return {r[_partner_col()] or "No Partner": r["cnt"] for r in records}


def get_agent_in_prod(extra_filters: str = "") -> dict:
    where = "WHERE Agent_Activated__c = true"
    if extra_filters:
        where += f" AND {extra_filters}"
    records = query(
        f"SELECT {_partner_col()}, COUNT(Id) cnt "
        f"FROM AF_Implementation_Project__c "
        f"{where} "
        f"GROUP BY {_partner_col()}"
    )
    return {r[_partner_col()] or "No Partner": r["cnt"] for r in records}


def get_used(extra_filters: str = "") -> dict:
    """Conversations in Production Org."""
    where = "WHERE Conversations__c > 0 AND Org_Type__c = 'Production'"
    if extra_filters:
        where += f" AND {extra_filters}"
    records = query(
        f"SELECT {_partner_col()}, COUNT(Id) cnt "
        f"FROM AF_Usage__c "
        f"{where} "
        f"GROUP BY {_partner_col()}"
    )
    return {r[_partner_col()] or "No Partner": r["cnt"] for r in records}


def get_consumed(extra_filters: str = "") -> dict:
    """50+ Conversations Last 7 days."""
    where = "WHERE Conversations_Last_7_Days__c >= 50"
    if extra_filters:
        where += f" AND {extra_filters}"
    records = query(
        f"SELECT {_partner_col()}, COUNT(Id) cnt "
        f"FROM AF_Usage__c "
        f"{where} "
        f"GROUP BY {_partner_col()}"
    )
    return {r[_partner_col()] or "No Partner": r["cnt"] for r in records}


def get_scale(extra_filters: str = "") -> dict:
    """100K+ Actions per Week."""
    where = "WHERE Actions_Per_Week__c >= 100000"
    if extra_filters:
        where += f" AND {extra_filters}"
    records = query(
        f"SELECT {_partner_col()}, COUNT(Id) cnt "
        f"FROM AF_Usage__c "
        f"{where} "
        f"GROUP BY {_partner_col()}"
    )
    return {r[_partner_col()] or "No Partner": r["cnt"] for r in records}


FUNNEL_STEPS = [
    ("Provisioned", get_provisioned),
    ("Discovery", get_discovery),
    ("Agent Created", get_agent_created),
    ("Agent in Prod", get_agent_in_prod),
    ("Used", get_used),
    ("Consumed", get_consumed),
    ("Scale", get_scale),
]


def build_dataframe(partners: list[str] | None = None, extra_filters: str = "") -> pd.DataFrame:
    """
    Returns a DataFrame with rows = funnel steps, columns = partners.
    If partners is None, uses all partners found across all steps.
    """
    data = {}
    all_partners: set[str] = set()

    for step_name, fetch_fn in FUNNEL_STEPS:
        counts = fetch_fn(extra_filters)
        data[step_name] = counts
        all_partners.update(counts.keys())

    if partners:
        cols = partners
    else:
        # Sort: No Partner first, then alphabetically
        others = sorted(p for p in all_partners if p != "No Partner")
        cols = ["No Partner"] + others

    rows = []
    for step_name, _ in FUNNEL_STEPS:
        row = {p: data[step_name].get(p, 0) for p in cols}
        rows.append(row)

    df = pd.DataFrame(rows, index=[s for s, _ in FUNNEL_STEPS], columns=cols)
    return df
