"""
partner_agent CLI — interprets natural language orders via Claude
and generates AF Implementation Funnel visualizations from Salesforce.

Usage:
    python agent.py "show funnel for partners Globant, Salesforce Services, NTT Group"
    python agent.py "show funnel filtering by region LATAM"
    python agent.py "generate funnel for all partners last 30 days"
"""

import sys
import os
import json
import re
from pathlib import Path
from dotenv import load_dotenv
import anthropic

load_dotenv()

TOOLS = [
    {
        "name": "generate_funnel",
        "description": (
            "Generate the AF Implementation Funnel table as HTML/PNG. "
            "Call this when the user wants to visualize the funnel. "
            "Extract partner filters and any Salesforce WHERE clause conditions from the user's request."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title shown at the top of the visualization, e.g. 'AF Implementation Funnel (LATAM Partners)'",
                },
                "partners": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "List of partner names to show as columns. "
                        "Use null or empty list to show all partners."
                    ),
                },
                "extra_filters": {
                    "type": "string",
                    "description": (
                        "Additional Salesforce SOQL WHERE clause fragment (without the word WHERE), "
                        "e.g. \"Region__c = 'LATAM'\" or \"CreatedDate = LAST_N_DAYS:30\". "
                        "Leave empty string if no extra filters."
                    ),
                },
                "output_format": {
                    "type": "string",
                    "enum": ["html", "png", "both"],
                    "description": "Output format. Default 'html'.",
                },
            },
            "required": ["title", "partners", "extra_filters", "output_format"],
        },
    }
]

SYSTEM_PROMPT = """You are partner_agent, a specialized assistant that generates
AF Implementation Funnel visualizations by querying Salesforce data.

When the user gives you an order, extract:
1. Which partners to show (or all)
2. Any filters to apply (date range, region, product, etc.)
3. A descriptive title for the chart

Always call the generate_funnel tool to fulfill the request.
Map user intent to valid Salesforce SOQL WHERE fragment for extra_filters.

Common field mappings:
- "region" → Region__c
- "last N days" → CreatedDate = LAST_N_DAYS:N
- "country" → Country__c
- "product" → Product__c
- "fiscal year" → Fiscal_Year__c
"""


def run_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == "generate_funnel":
        return _generate_funnel(**tool_input)
    return f"Unknown tool: {tool_name}"


def _generate_funnel(
    title: str,
    partners: list[str] | None,
    extra_filters: str,
    output_format: str,
) -> str:
    try:
        from funnel_data import build_dataframe
        from renderer import render_html, render_png
    except ImportError as e:
        return f"Import error: {e}. Make sure dependencies are installed."

    print(f"\n[partner_agent] Fetching data from Salesforce...")
    print(f"  Partners: {partners or 'all'}")
    print(f"  Filters: {extra_filters or 'none'}")

    try:
        df = build_dataframe(
            partners=partners if partners else None,
            extra_filters=extra_filters or "",
        )
    except Exception as e:
        return f"Salesforce query failed: {e}"

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    safe_title = re.sub(r"[^a-z0-9_]", "_", title.lower())[:40]
    html_path = str(output_dir / f"{safe_title}.html")

    print(f"[partner_agent] Rendering visualization...")
    render_html(df, title, html_path)
    result_files = [html_path]

    if output_format in ("png", "both"):
        png_path = html_path.replace(".html", ".png")
        actual = render_png(str(Path(html_path).resolve()), png_path)
        if actual != html_path:
            result_files.append(png_path)
        else:
            result_files.append("(PNG skipped — install playwright: pip install playwright && playwright install chromium)")

    return f"Done! Files generated:\n" + "\n".join(f"  • {f}" for f in result_files)


def main():
    if len(sys.argv) < 2:
        print("Usage: python agent.py \"<your order>\"")
        print("Example: python agent.py \"show funnel for Globant and Salesforce Services\"")
        sys.exit(1)

    user_order = " ".join(sys.argv[1:])
    print(f"\n[partner_agent] Processing: {user_order}\n")

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    messages = [{"role": "user", "content": user_order}]

    # Agentic loop
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Collect any text output
        for block in response.content:
            if hasattr(block, "text"):
                print(f"[Claude] {block.text}")

        if response.stop_reason == "end_turn":
            break

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"[partner_agent] Calling tool: {block.name}")
                    print(f"  Input: {json.dumps(block.input, indent=2)}")
                    result = run_tool(block.name, block.input)
                    print(f"  Result: {result}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    print("\n[partner_agent] Done.")


if __name__ == "__main__":
    main()
