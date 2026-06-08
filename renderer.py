"""
Renders the funnel DataFrame as an HTML file and optionally a PNG.
"""

import pandas as pd
from pathlib import Path
from jinja2 import Template

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body { font-family: 'Segoe UI', Arial, sans-serif; background: #b8d4f0; padding: 30px; }
  h1 { color: #1a2e5a; font-size: 2em; margin-bottom: 20px; }
  table { border-collapse: separate; border-spacing: 0; width: 100%; }
  th { background: transparent; color: #1a2e5a; font-weight: 600;
       font-size: 0.75em; text-align: center; padding: 8px 6px; vertical-align: bottom; }
  td { background: white; border-radius: 12px; padding: 12px 10px;
       text-align: center; font-weight: 700; font-size: 1.1em; margin: 4px; }
  tr td:first-child { text-align: left; padding-left: 0; background: transparent; }

  .label-cell { display: inline-block; border-radius: 12px; padding: 8px 14px;
                font-weight: 700; font-size: 0.95em; color: white; }

  .provisioned .label-cell { background: #2d6be4; }
  .discovery   .label-cell { background: #4a90d9; }
  .agent_created .label-cell { background: #7b5ea7; }
  .agent_in_prod .label-cell { background: #4caf6e; }
  .used        .label-cell { background: #6aab6a; }
  .consumed    .label-cell { background: #c8a840; }
  .scale       .label-cell { background: #d9534f; }

  .provisioned td:not(:first-child) { color: #2d6be4; }
  .discovery   td:not(:first-child) { color: #4a90d9; }
  .agent_created td:not(:first-child) { color: #7b5ea7; }
  .agent_in_prod td:not(:first-child) { color: #4caf6e; }
  .used        td:not(:first-child) { color: #4caf6e; }
  .consumed    td:not(:first-child) { color: #c8a840; }
  .scale       td:not(:first-child) { color: #d9534f; }

  tr { margin-bottom: 6px; }
  tr td { border: none; box-shadow: 0 2px 6px rgba(0,0,0,0.08); }

  .section-label { writing-mode: vertical-rl; transform: rotate(180deg);
                   color: #666; font-style: italic; font-size: 0.85em; }
  .divider td { border-top: 2px dashed #888; background: transparent;
                box-shadow: none; padding: 2px; }
</style>
</head>
<body>
<h1>{{ title }}</h1>
<table>
  <thead>
    <tr>
      <th></th>
      {% for col in columns %}
      <th>{{ col }}</th>
      {% endfor %}
    </tr>
  </thead>
  <tbody>
    {% for row in rows %}
    {% if row.divider %}
    <tr class="divider"><td colspan="{{ columns|length + 1 }}"></td></tr>
    {% else %}
    <tr class="{{ row.css_class }}">
      <td>
        <span class="label-cell">{{ row.label }}</span>
        {% if row.sublabel %}<div style="font-size:0.65em;color:#555;margin-top:2px;">{{ row.sublabel }}</div>{% endif %}
      </td>
      {% for val in row.values %}
      <td>{{ val if val != 0 else '-' }}</td>
      {% endfor %}
    </tr>
    {% endif %}
    {% endfor %}
  </tbody>
</table>
</body>
</html>
"""

STEP_META = {
    "Provisioned":    ("provisioned",   "Project Submitted with OrgID tied to Closed/Won Oppty"),
    "Discovery":      ("discovery",     "Project Submitted with OrgID tied to Closed/Won Oppty"),
    "Agent Created":  ("agent_created", "Build & Test"),
    "Agent in Prod":  ("agent_in_prod", "Activated"),
    "Used":           ("used",          "Conversations in Production Org"),
    "Consumed":       ("consumed",      "50+ Conversations Last 7 days"),
    "Scale":          ("scale",         "100K+ Actions per Week"),
}

DIVIDER_AFTER = "Agent in Prod"


def render_html(df: pd.DataFrame, title: str, output_path: str) -> str:
    columns = list(df.columns)
    rows = []

    for step in df.index:
        css_class, sublabel = STEP_META.get(step, (step.lower().replace(" ", "_"), ""))
        row = {
            "label": step,
            "sublabel": sublabel,
            "css_class": css_class,
            "values": [int(df.loc[step, c]) for c in columns],
            "divider": False,
        }
        rows.append(row)
        if step == DIVIDER_AFTER:
            rows.append({"divider": True})

    html = Template(TEMPLATE).render(title=title, columns=columns, rows=rows)
    Path(output_path).write_text(html, encoding="utf-8")
    return output_path


def render_png(html_path: str, png_path: str) -> str:
    """Requires kaleido + playwright or weasyprint. Falls back gracefully."""
    try:
        import subprocess
        subprocess.run(
            ["python", "-m", "playwright", "chromium", "--version"],
            capture_output=True, check=True
        )
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1600, "height": 900})
            page.goto(f"file://{html_path}")
            page.screenshot(path=png_path, full_page=True)
            browser.close()
        return png_path
    except Exception:
        # Fallback: just return the HTML path and inform caller
        return html_path
