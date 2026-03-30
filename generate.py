#!/usr/bin/env python3
"""
generate.py — Fetch NZ electronic collections from the Alma API and write a
static index.html suitable for embedding as an iframe in LibAnswers.

Usage:
    python3 generate.py [output_path]

    output_path defaults to ./index.html

Environment variables (loaded from .env if present):
    NZ_API_KEY   Alma API key (requires Electronic Collections read permission)
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

apikey = os.getenv("NZ_API_KEY")

URL_LIST = "https://api-na.hosted.exlibrisgroup.com/almaws/v1/electronic/e-collections?limit=100&offset={}&format=json&apikey={}"
URL_COLL = "https://api-na.hosted.exlibrisgroup.com/almaws/v1/electronic/e-collections/{}?apikey={}&format=json"

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
  <link rel="stylesheet" href="https://cdn.datatables.net/1.13.8/css/jquery.dataTables.min.css">
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
    .filters {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 14px;
      align-items: flex-end;
    }}
    .filters label {{
      display: flex;
      flex-direction: column;
      gap: 3px;
      font-size: 12px;
      font-weight: 600;
      color: #555;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .filters select {{
      font-size: 13px;
      padding: 5px 8px;
      border: 1px solid #767676;
      border-radius: 4px;
      background: #fff;
      cursor: pointer;
      min-width: 180px;
    }}
    .filters select:focus {{
      outline: 2px solid #4a90d9;
      outline-offset: 1px;
    }}
    .table-wrapper {{
      width: 100%;
      overflow-x: auto;
    }}
    #collections {{
      width: 100% !important;
    }}
    #collections thead th {{
      white-space: nowrap;
    }}
    #collections tbody td {{
      vertical-align: top;
      line-height: 1.4;
    }}
    .override {{
      font-size: 12px;
      color: #888;
      margin-top: 3px;
    }}
    .dataTables_wrapper .dataTables_filter input {{
      border: 1px solid #767676;
      border-radius: 4px;
      padding: 4px 8px;
    }}
  </style>
</head>
<body>
  <h1>Network Zone Electronic Collections</h1>
  <p class="summary">There are currently {count} electronic collections in the NZ.
  This list is updated roughly once per hour. The last update was at {time}.</p>
  <div class="filters">
{filter_selects}
  </div>
  <div class="table-wrapper">
    <table id="collections" class="display" style="width:100%">
      <thead>
        <tr>
          <th>Collection Name</th>
          <th>Collection ID</th>
          <th>Groups</th>
          <th>Interface</th>
          <th>Vendor</th>
        </tr>
      </thead>
      <tbody>
{rows}
      </tbody>
    </table>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/iframe-resizer@4/js/iframeResizer.contentWindow.min.js"></script>
  <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
  <script src="https://cdn.datatables.net/1.13.8/js/jquery.dataTables.min.js"></script>
  <script>
  $(function () {{
    var table = $('#collections').DataTable({{
      pageLength: 25,
      lengthMenu: [10, 25, 50, 100],
      order: [[0, 'asc']],
      columnDefs: [{{ targets: '_all', defaultContent: '' }}]
    }});

    // Institution filter — rows marked "All CUNY Institutions" always pass
    $.fn.dataTable.ext.search.push(function (settings, data) {{
      var selected = $('#filter-institution').val();
      if (!selected) return true;
      var groups = data[2];
      if (groups === 'All CUNY Institutions') return true;
      return groups.split(', ').indexOf(selected) !== -1;
    }});

    // Interface filter
    $.fn.dataTable.ext.search.push(function (settings, data) {{
      var selected = $('#filter-interface').val();
      return !selected || data[3] === selected;
    }});

    // Vendor filter
    $.fn.dataTable.ext.search.push(function (settings, data) {{
      var selected = $('#filter-vendor').val();
      return !selected || data[4] === selected;
    }});

    $('.filters select').on('change', function () {{
      table.draw();
    }});
  }});
  </script>
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


def make_select(label, select_id, options):
    opt_tags = [f'      <option value="">All {label}</option>']
    for opt in sorted(options):
        esc = html.escape(str(opt), quote=True)
        opt_tags.append(f'      <option value="{esc}">{esc}</option>')
    return (
        f'    <label>{label}\n'
        f'      <select id="{select_id}">\n'
        + "\n".join(opt_tags) + "\n"
        + f'      </select>\n'
        + f'    </label>'
    )


def render_row(item):
    name = _esc(item[0])
    groups = item[1]
    iface = item[2]
    vendor = item[3]
    coll_id = _esc(item[4])
    override = item[5]

    name_cell = f"<td>{name}"
    if override:
        name_cell += f'<div class="override">Public name override: {_esc(override)}</div>'
    name_cell += "</td>"

    groups_str = ", ".join(_esc(g) for g in groups) if groups else "All CUNY Institutions"

    return (
        "      <tr>\n"
        f"        {name_cell}\n"
        f"        <td>{coll_id}</td>\n"
        f"        <td>{groups_str}</td>\n"
        f"        <td>{_esc(iface)}</td>\n"
        f"        <td>{_esc(vendor)}</td>\n"
        "      </tr>"
    )


def fetch_collection(coll_id):
    sub = _get_json(URL_COLL.format(coll_id, apikey))

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

    return groups, iface, vendor, sub["id"], override


def fetch_all():
    first = _get_json(URL_LIST.format(0, apikey))
    total = first.get("total_record_count")
    if total is None:
        sys.exit("Error: unexpected API response — 'total_record_count' missing. Check your API key.")
    pages = math.ceil(total / 100)

    records = []
    for page in range(pages):
        offset = page * 100
        page_data = _get_json(URL_LIST.format(offset, apikey))
        for coll in page_data.get("electronic_collection", []):
            groups, iface, vendor, coll_id, override = fetch_collection(coll["id"])
            fixed_groups = [NAME_FIXES.get(g, g) for g in groups]
            records.append((
                coll["public_name"],
                fixed_groups,
                iface,
                vendor,
                coll_id,
                override,
            ))

    return sorted(records, key=lambda x: x[0].casefold())


def current_time_et():
    tz = pytz.timezone("America/New_York")
    now = datetime.now(pytz.utc).astimezone(tz)
    return now.strftime("%I:%M%p (%Z)").lstrip("0")


def main():
    if not apikey:
        sys.exit("Error: NZ_API_KEY must be set (check your .env file).")

    output_path = sys.argv[1] if len(sys.argv) > 1 else "index.html"

    print("Fetching data from Alma API...", flush=True)
    data = fetch_all()

    if not data:
        sys.exit("Error: API returned 0 collections — aborting to avoid overwriting the live page.")

    # Collect unique values for filter dropdowns
    all_institutions = set()
    all_interfaces = set()
    all_vendors = set()
    for item in data:
        for g in item[1]:
            all_institutions.add(g)
        if item[2]:
            all_interfaces.add(item[2])
        if item[3]:
            all_vendors.add(item[3])

    filter_selects = "\n".join([
        make_select("Institution", "filter-institution", all_institutions),
        make_select("Interface", "filter-interface", all_interfaces),
        make_select("Vendor", "filter-vendor", all_vendors),
    ])

    rows_html = "\n".join(render_row(item) for item in data)
    content = HTML_TEMPLATE.format(
        count=len(data),
        time=current_time_et(),
        filter_selects=filter_selects,
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
