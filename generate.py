#!/usr/bin/env python3
"""
generate.py — Fetch NZ electronic collections from the Alma API and write a
static index.html suitable for embedding as an iframe in LibAnswers.

Usage:
    python3 generate.py [output_path]

    output_path defaults to ./index.html

Environment variables (loaded from .env if present):
    NZ_API_KEY        Network Zone API key
    BIBS_NZ_API_KEY   Bibliographic NZ API key
"""

import html
import math
import os
import sys
import tempfile
import pytz
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

apikey1 = os.getenv("NZ_API_KEY")
apikey2 = os.getenv("BIBS_NZ_API_KEY")

URL_LIST = "https://api-na.hosted.exlibrisgroup.com/almaws/v1/electronic/e-collections?limit=100&offset={}&format=json&apikey={}"
URL_COLL = "https://api-na.hosted.exlibrisgroup.com/almaws/v1/electronic/e-collections/{}?apikey={}&format=json"
URL_BIBS = "https://api-na.hosted.exlibrisgroup.com/almaws/v1/bibs/{}?apikey={}&format=json"

NAME_FIXES = {
    "Manhattan Community College": "Borough of Manhattan Community College",
    "Fiorello H LaGuardia Community College Library": "LaGuardia Community College",
}

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NZ Electronic Collections</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      font-size: 14px;
      color: #222;
      margin: 0;
      padding: 16px;
      background: #fff;
    }}
    h1 {{
      font-size: 1.25rem;
      font-weight: 600;
      margin: 0 0 8px;
    }}
    p.summary {{
      margin: 0 0 16px;
      color: #555;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    tbody tr:nth-child(even) {{
      background: #f6f6f6;
    }}
    th {{
      font-weight: normal;
      text-align: left;
      padding: 8px 12px;
      border-bottom: 1px solid #e0e0e0;
      vertical-align: top;
    }}
    .name {{
      font-weight: 600;
    }}
    .id {{
      color: #555;
      margin-left: 6px;
      font-size: 13px;
    }}
    .meta {{
      margin: 3px 0 0 1.5em;
      font-size: 13px;
      color: #444;
    }}
    .meta em {{
      color: #888;
    }}
  </style>
</head>
<body>
  <h1>Network Zone Electronic Collections</h1>
  <p class="summary">There are currently {count} electronic collections in the NZ.
  This list is updated roughly once per hour. The last update was at {time}.</p>
  <table>
    <tbody>
{rows}
    </tbody>
  </table>
  <script src="https://cdn.jsdelivr.net/npm/iframe-resizer@4/js/iframeResizer.contentWindow.min.js"></script>
</body>
</html>
"""


def _get_json(url):
    """Fetch a URL and return parsed JSON, or exit with a clear message on failure."""
    try:
        resp = httpx.get(url, timeout=500)
        resp.raise_for_status()
        return resp.json()
    except httpx.TimeoutException:
        sys.exit(f"Error: request timed out: {url}")
    except httpx.HTTPStatusError as e:
        sys.exit(f"Error: API returned HTTP {e.response.status_code}: {url}")
    except httpx.RequestError as e:
        sys.exit(f"Error: network error: {e}")
    except Exception as e:
        sys.exit(f"Error: could not parse API response from {url}: {e}")


def _esc(value):
    return html.escape(str(value)) if value else ""


def render_row(item):
    name = _esc(item[0])
    groups = item[1]
    iface = item[2]
    vendor = item[3]
    id_val = _esc(item[4])
    id_type = _esc(item[5])
    override = item[6]

    lines = [
        "      <tr>",
        '        <th scope="row">',
        f'          <span class="name">{name}</span>',
        f'          <span class="id">({id_type}# {id_val})</span>',
    ]

    if override:
        lines.append(f'          <div class="meta">Public name override: {_esc(override)}</div>')
    else:
        lines.append('          <div class="meta">Public name override: <em>none</em></div>')

    if groups:
        group_str = ", ".join(_esc(g) for g in groups)
        lines.append(f'          <div class="meta">Groups: {group_str}</div>')
    else:
        lines.append('          <div class="meta">Groups: All CUNY Institutions</div>')

    if iface:
        lines.append(f'          <div class="meta">Interface name: {_esc(iface)}</div>')

    if vendor:
        lines.append(f'          <div class="meta">Vendor name: {_esc(vendor)}</div>')

    lines += ["        </th>", "      </tr>"]
    return "\n".join(lines)


def fetch_collection(coll_id):
    sub = _get_json(URL_COLL.format(coll_id, apikey1))

    try:
        groups = [g["group"]["desc"] for g in sub["group_setting"]]
    except KeyError:
        groups = []

    try:
        iface = sub["interface"]["name"]
    except KeyError:
        iface = None

    try:
        vendor = sub["interface"]["vendor"]["value"]
    except KeyError:
        vendor = None

    override = sub.get("public_name_override")

    try:
        nz_mms_id = sub["resource_metadata"]["mms_id"]["value"]
        bibs = _get_json(URL_BIBS.format(nz_mms_id, apikey2))
        for number in bibs.get("network_number", []):
            if "EXLCZ" in number:
                return groups, iface, vendor, number[7:], "MMS ID", override
    except KeyError:
        pass

    return groups, iface, vendor, sub["id"], "Collection ID", override


def fetch_all():
    first = _get_json(URL_LIST.format(0, apikey1))
    total = first.get("total_record_count")
    if total is None:
        sys.exit("Error: unexpected API response — 'total_record_count' missing. Check your API key.")
    pages = math.ceil(total / 100)

    records = []
    for page in range(pages):
        offset = page * 100
        page_data = _get_json(URL_LIST.format(offset, apikey1))
        for coll in page_data.get("electronic_collection", []):
            groups, iface, vendor, id_val, id_type, override = fetch_collection(coll["id"])
            fixed_groups = [NAME_FIXES.get(g, g) for g in groups]
            records.append((
                coll["public_name"],
                fixed_groups,
                iface,
                vendor,
                id_val,
                id_type,
                override,
            ))

    return sorted(records, key=lambda x: x[0].casefold())


def current_time_et():
    tz = pytz.timezone("America/New_York")
    now = datetime.now(pytz.utc).astimezone(tz)
    return now.strftime("%I:%M%p (%Z)").lstrip("0")


def main():
    if not apikey1 or not apikey2:
        sys.exit("Error: NZ_API_KEY and BIBS_NZ_API_KEY must be set (check your .env file).")

    output_path = sys.argv[1] if len(sys.argv) > 1 else "index.html"

    print("Fetching data from Alma API...", flush=True)
    data = fetch_all()

    if not data:
        sys.exit("Error: API returned 0 collections — aborting to avoid overwriting the live page.")

    rows_html = "\n".join(render_row(item) for item in data)
    content = HTML_TEMPLATE.format(
        count=len(data),
        time=current_time_et(),
        rows=rows_html,
    )

    # Write to a temp file in the same directory, then rename for an atomic swap.
    out = Path(output_path)
    try:
        fd, tmp_path = tempfile.mkstemp(dir=out.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            Path(tmp_path).replace(out)
        except Exception:
            os.unlink(tmp_path)
            raise
    except OSError as e:
        sys.exit(f"Error: could not write {output_path}: {e}")

    print(f"Generated: {output_path} ({len(data)} collections)")


if __name__ == "__main__":
    main()
