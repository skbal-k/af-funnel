# partner_agent

CLI agent that generates AF Implementation Funnel visualizations from Salesforce data using natural language orders.

## Setup

```bash
cd partner_agent
pip install -r requirements.txt

# Optional: for PNG export
pip install playwright && playwright install chromium

cp .env.example .env
# Edit .env with your credentials
```

## Usage

```bash
python agent.py "show funnel for all partners"
python agent.py "show funnel for Globant, Salesforce Services and NTT Group"
python agent.py "generate funnel filtering by region LATAM"
python agent.py "show funnel for last 30 days, output as png"
python agent.py "funnel for partners Freeway and Gentrop, fiscal year 2025"
```

## Output

Files are saved to `./output/` as `.html` (always) and `.png` (if playwright is installed).

## Files

| File | Purpose |
|------|---------|
| `agent.py` | CLI entry point + Claude agentic loop |
| `funnel_data.py` | Salesforce SOQL queries per funnel step |
| `salesforce_client.py` | Salesforce OAuth connection |
| `renderer.py` | HTML/PNG visualization renderer |

## Adjusting Salesforce field names

Edit `funnel_data.py` → `_partner_col()` and the SOQL queries to match your org's actual field/object API names.
