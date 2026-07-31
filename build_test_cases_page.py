"""Generate the full test-case page and the combined CSV export.

Both outputs are committed and served as plain static files — nothing builds at
page load. They are generated rather than hand-written so they cannot drift
from the CSVs, the same reason the walkthrough page's quoted assertions are
checked against the suite.

Regenerate after changing a CSV or the coverage map::

    python build_test_cases_page.py

A unit test re-renders both in memory and fails if what is committed differs.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

from shopsmart.testcases import (
    AUTOMATED_WITHOUT_A_CASE,
    COMBINED_FILENAME,
    CSV_FILES,
    FEATURED_CASE,
    PENDING_MARKER,
    PREVIEW_CASES,
    SECTION_PREFIX,
    SECTION_TITLES,
    YES,
    all_cases,
    case_id,
    counts,
    coverage_for,
    find_case,
    is_spec_gap,
    is_traced,
    read_cases,
    write_combined_csv,
)

REPO_ROOT = Path(__file__).resolve().parent
OUTPUT = REPO_ROOT / "test-cases.html"

STEP_SPLIT = re.compile(r"(?=\b\d+\.\s)")
LEADING_NUMBER = re.compile(r"^\d+\.\s*")


def esc(value: str) -> str:
    return html.escape(value or "", quote=True)


def render_steps(raw: str) -> str:
    """Turn '1. Do this. 2. Do that.' into a real ordered list."""
    parts = [p.strip() for p in STEP_SPLIT.split(raw or "") if p.strip()]
    if len(parts) < 2:
        return f"<p>{esc(raw)}</p>"
    items = "".join(f"<li>{esc(LEADING_NUMBER.sub('', part))}</li>" for part in parts)
    return f'<ol class="steps-list">{items}</ol>'


def render_expected(raw: str) -> str:
    """Split a flagged expected result into the flag and the proposed outcome."""
    text = raw or ""
    if PENDING_MARKER not in text:
        return f"<p>{esc(text)}</p>"

    before, _, after = text.partition(PENDING_MARKER)
    after = after.lstrip(" —-–").strip()
    lead = f"<p>{esc(before.strip())}</p>" if before.strip() else ""
    return (
        f"{lead}"
        f'<p class="gapflag"><span class="pill gap">Spec gap — awaiting PM</span></p>'
        f'<p class="gaptext">{esc(after)}</p>'
    )


def automated_cell(filename: str, title: str) -> str:
    item = coverage_for(filename, title)
    if item is None:
        return '<span class="pill no">No</span>'
    pill_class = "yes" if item.state == YES else "partial"
    label = "Yes" if item.state == YES else "Partial"
    return (
        f'<span class="pill {pill_class}">{label}</span>'
        f'<a class="testlink" href="https://github.com/keonikaku/automation/tree/main/tests/ui">'
        f"<code>{esc(item.test)}</code></a>"
        f'<span class="covnote">{esc(item.note)}</span>'
    )


def render_row(filename: str, index: int, row: dict[str, str]) -> str:
    gap, traced = is_spec_gap(row), is_traced(row)
    classes = " ".join(
        filter(None, ["case", "is-gap" if gap else "", "is-traced" if traced else ""])
    )
    flags = ""
    if traced:
        flags += '<span class="pill trace">SMART-201</span>'
    if gap:
        flags += '<span class="pill gap">Spec gap</span>'
    priority = esc(row["Priority"])
    return f"""      <tr class="{classes}">
        <td class="cid"><code>{case_id(filename, index)}</code></td>
        <td class="ctitle">{esc(row["Title"])}{flags}</td>
        <td class="cpre">{esc(row["Preconditions"])}</td>
        <td class="csteps">{render_steps(row["Steps"])}</td>
        <td class="cexp">{render_expected(row["Expected Result"])}</td>
        <td class="cmeta"><span class="pri p-{priority.lower()}">{priority}</span>\
<br /><span class="ctype">{esc(row["Type"])}</span></td>
        <td class="cauto">{automated_cell(filename, row["Title"])}</td>
      </tr>"""


def build() -> str:
    total = counts()
    sections = []

    for filename in CSV_FILES:
        rows = read_cases(filename)
        body = "\n".join(
            render_row(filename, index, row) for index, row in enumerate(rows, start=1)
        )
        plural = "s" if len(rows) != 1 else ""
        sections.append(f"""  <div class="section-head" id="{SECTION_PREFIX[filename].lower()}">
    <h2>{SECTION_TITLES[filename]}</h2>
    <span>{len(rows)} case{plural} ·
      <a href="test-cases/{filename}" download><code>{filename}</code></a></span>
  </div>

  <div class="tablewrap">
    <table class="cases">
      <thead>
        <tr>
          <th>ID</th><th>Title</th><th>Preconditions</th><th>Steps</th>
          <th>Expected result</th><th>Priority</th><th>Automated</th>
        </tr>
      </thead>
      <tbody>
{body}
      </tbody>
    </table>
  </div>
""")

    downloads = "\n".join(
        f'      <a class="dl" href="test-cases/{name}" download><code>{name}</code></a>'
        for name in CSV_FILES
    )
    orphans = "\n".join(
        f"        <li><code>{esc(name)}</code> — {esc(reason)}</li>"
        for name, reason in sorted(AUTOMATED_WITHOUT_A_CASE.items())
    )

    return TEMPLATE.format(
        combined=COMBINED_FILENAME,
        downloads=downloads,
        orphans=orphans,
        sections="\n".join(sections),
        not_automated=total["cases"] - total["automated"],
        **total,
    )


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>ShopSmart — All {cases} test cases</title>
<meta name="description" content="All {cases} manually designed test cases for the ShopSmart practice \
exercise, with spec gaps flagged, defect traceability, and the automated subset marked." />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&\
family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet" />
<style>
  :root{{
    --bg:#0a0e14; --panel:#111826; --panel2:#161f2e; --line:#232e40; --line-soft:#1a2434;
    --txt:#eef2f7; --muted:#8b9bb0; --muted-dim:#5c6c81;
    --accent:#4fd1ff; --accent-2:#7c9cff; --green:#34d399; --red:#f87171; --amber:#fbbf24;
    --sans:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
    --mono:'JetBrains Mono',ui-monospace,Menlo,Consolas,monospace;
  }}
  *{{box-sizing:border-box;}}
  body{{
    margin:0;background:
      radial-gradient(1100px 520px at 10% -10%, rgba(79,209,255,.10), transparent 60%),
      radial-gradient(900px 500px at 100% 0%, rgba(124,156,255,.07), transparent 55%),
      var(--bg);
    color:var(--txt);font-family:var(--sans);line-height:1.6;-webkit-font-smoothing:antialiased;
    min-height:100vh;
  }}
  a{{color:var(--accent);text-decoration:none;}}
  a:hover{{color:#fff;}}
  code{{font-family:var(--mono);}}
  .wrap{{max-width:1500px;margin:0 auto;padding:26px 22px 60px;}}
  header{{display:flex;justify-content:space-between;align-items:flex-start;gap:20px;
    flex-wrap:wrap;margin-bottom:22px;}}
  h1{{font-size:clamp(21px,2.6vw,27px);font-weight:800;letter-spacing:-.02em;margin:0 0 8px;}}
  .sub{{color:var(--muted);font-size:14.5px;max-width:820px;margin:0;}}
  .sub b{{color:var(--txt);}}
  .head-links{{display:flex;gap:10px;flex-wrap:wrap;}}
  .head-links a{{font-size:13.5px;font-weight:600;color:var(--txt);background:var(--panel);
    border:1px solid var(--line);padding:8px 14px;border-radius:9px;}}
  .head-links a:hover{{border-color:var(--accent);background:var(--panel2);}}
  .runbar{{display:flex;align-items:center;gap:26px;flex-wrap:wrap;background:var(--panel);
    border:1px solid var(--line);border-radius:14px;padding:15px 20px;margin:16px 0;}}
  .stat{{display:flex;flex-direction:column;gap:1px;}}
  .stat .k{{font-family:var(--mono);font-size:10.5px;text-transform:uppercase;
    letter-spacing:.09em;color:var(--muted-dim);font-weight:700;}}
  .stat .v{{font-family:var(--mono);font-size:14px;font-weight:700;color:var(--txt);}}
  .stat .v.amber{{color:var(--amber);}} .stat .v.ok{{color:var(--green);}}
  .note-panel{{background:var(--panel);border:1px solid var(--line);border-radius:14px;
    padding:18px 20px;margin-bottom:16px;}}
  .note-panel.amber{{border-left:2px solid var(--amber);}}
  .note-panel h2{{font-size:14px;font-weight:700;margin:0 0 9px;}}
  .note-panel p{{margin:0 0 9px;color:var(--muted);font-size:13.5px;max-width:900px;}}
  .note-panel p:last-child{{margin-bottom:0;}}
  .note-panel b{{color:var(--txt);}}
  .note-panel ul{{margin:0;padding-left:19px;color:var(--muted);font-size:13.5px;}}
  .note-panel li{{margin-bottom:6px;}}
  .dl-row{{display:flex;gap:9px;flex-wrap:wrap;margin-top:11px;}}
  .dl{{font-size:12.5px;background:var(--panel2);border:1px solid var(--line);
    border-radius:8px;padding:7px 12px;color:var(--accent);}}
  .dl:hover{{border-color:var(--accent);}}
  .dl.primary{{border-color:rgba(52,211,153,.4);color:var(--green);
    background:rgba(52,211,153,.08);}}
  .section-head{{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin:30px 0 12px;}}
  .section-head h2{{font-size:16px;font-weight:700;margin:0;letter-spacing:-.01em;}}
  .section-head span{{font-size:13px;color:var(--muted-dim);}}
  .tablewrap{{background:var(--panel);border:1px solid var(--line);border-radius:14px;
    overflow-x:auto;}}
  table.cases{{border-collapse:collapse;width:100%;font-size:13px;min-width:1100px;}}
  table.cases th{{text-align:left;font-family:var(--mono);font-size:10.5px;font-weight:700;
    text-transform:uppercase;letter-spacing:.07em;color:var(--muted-dim);
    padding:11px 13px;border-bottom:1px solid var(--line);background:var(--panel2);}}
  table.cases td{{padding:13px;border-bottom:1px solid var(--line-soft);
    vertical-align:top;color:var(--muted);}}
  table.cases tr:last-child td{{border-bottom:none;}}
  .case.is-gap{{background:rgba(251,191,36,.035);}}
  .case.is-traced{{background:rgba(79,209,255,.045);}}
  .case.is-gap td:first-child{{box-shadow:inset 2px 0 0 var(--amber);}}
  .case.is-traced td:first-child{{box-shadow:inset 2px 0 0 var(--accent);}}
  .cid{{width:74px;}} .cid code{{font-size:11px;color:var(--muted-dim);}}
  .ctitle{{width:230px;color:var(--txt);font-weight:600;}}
  .cpre{{width:150px;}} .csteps{{width:290px;}} .cexp{{width:300px;}}
  .cmeta{{width:96px;}} .cauto{{width:200px;}}
  .steps-list{{margin:0;padding-left:16px;}}
  .steps-list li{{margin-bottom:3px;}}
  .cexp p{{margin:0 0 6px;}} .cexp p:last-child{{margin-bottom:0;}}
  .gaptext{{color:var(--muted-dim);font-style:italic;}}
  .gapflag{{margin:5px 0 !important;}}
  .pill{{display:inline-block;font-family:var(--mono);font-size:9.5px;font-weight:700;
    letter-spacing:.05em;text-transform:uppercase;padding:2px 8px;border-radius:6px;
    margin:5px 6px 0 0;white-space:nowrap;}}
  .pill.gap{{color:var(--amber);background:rgba(251,191,36,.1);
    border:1px solid rgba(251,191,36,.32);}}
  .pill.trace{{color:var(--accent);background:rgba(79,209,255,.1);
    border:1px solid rgba(79,209,255,.32);}}
  .pill.yes{{color:var(--green);background:rgba(52,211,153,.1);
    border:1px solid rgba(52,211,153,.32);}}
  .pill.partial{{color:var(--accent-2);background:rgba(124,156,255,.1);
    border:1px solid rgba(124,156,255,.32);}}
  .pill.no{{color:var(--muted-dim);background:var(--panel2);border:1px solid var(--line);}}
  .testlink{{display:block;font-size:11px;margin-top:3px;}}
  .covnote{{display:block;font-size:11.5px;color:var(--muted-dim);margin-top:5px;}}
  .pri{{font-family:var(--mono);font-size:10.5px;font-weight:700;}}
  .p-critical{{color:var(--red);}} .p-high{{color:var(--amber);}} .p-medium{{color:var(--muted);}}
  .ctype{{font-size:11px;color:var(--muted-dim);}}
  footer{{margin-top:38px;padding-top:20px;border-top:1px solid var(--line-soft);
    color:var(--muted);font-size:13px;}}
  footer .note{{font-size:12.5px;color:var(--muted-dim);max-width:900px;margin-top:8px;}}
</style>
</head>
<body>
<div class="wrap">

  <header>
    <div>
      <h1>ShopSmart — all {cases} test cases</h1>
      <p class="sub">
        Every case, exactly as authored, with a derived column showing which ones the automated suite
        covers. The summary and the featured defect trace are on the
        <a href="index.html">project page</a>.
      </p>
      <p class="sub" style="margin-top:8px;">
        These {cases} cases were written by hand in <b>TestRail</b> during the exercise, one at a
        time, with the steps, preconditions and expected results filled in there. The CSVs below are
        the export. That TestRail instance is no longer active, so the export is what remains of it.
      </p>
      <p class="sub" style="margin-top:8px;">
        <b>&ldquo;ShopSmart&rdquo; is the name of this practice exercise</b> — not a company, a client,
        or a shipped product. The cases describe a fictional storefront; the automation runs against
        <a href="https://www.automationexercise.com">automationexercise.com</a>, a public practice site.
      </p>
    </div>
    <div class="head-links">
      <a href="index.html">← Project page</a>
      <a href="https://github.com/keonikaku/automation">View source</a>
      <a href="https://keonikaku.github.io">Portfolio</a>
    </div>
  </header>

  <div class="runbar">
    <div class="stat"><span class="k">Cases designed</span><span class="v">{cases}</span></div>
    <div class="stat"><span class="k">Automated</span><span class="v ok">{automated} \
({yes} full · {partial} partial)</span></div>
    <div class="stat"><span class="k">Spec gaps flagged</span><span class="v amber">{gaps}</span></div>
    <div class="stat"><span class="k">Traced to SMART-201</span><span class="v">{traced}</span></div>
  </div>

  <div class="note-panel amber">
    <h2>{gaps} cases say &ldquo;spec gap — awaiting PM&rdquo; instead of an expected result</h2>
    <p>
      That is the finished state of those cases, not an unfinished one. Where the specification did
      not define a behaviour — what happens on an empty search, what the error is for an already
      registered email, what the empty-cart screen says — the case <b>records that the spec is silent
      and proposes an expectation</b>, rather than inventing an expected result and quietly turning
      one person's guess into the standard the build gets measured against.
    </p>
    <p>
      Every one of these rows still carries full steps and a proposed outcome, so it is executable
      today and becomes final the moment a product owner answers.
    </p>
  </div>

  <div class="note-panel">
    <h2>What &ldquo;Automated&rdquo; means here, and what it does not</h2>
    <p>
      <b>{automated} of {cases} cases have automated coverage</b> — {yes} fully, {partial} partially.
      The other {not_automated} are designed and run manually. That ratio is the point rather than a
      shortfall: test design and test automation are different activities, and which cases get
      automated is a risk decision. Automating all {cases} against a practice site would cost more
      than it could return.
    </p>
    <p>
      The column is <b>derived, not asserted</b>. Each entry names the test that covers it, and a unit
      test fails the build if a named test stops existing. <b>Partial</b> means an automated test
      exercises the scenario but asserts something weaker than the case specifies — marking those
      &ldquo;Yes&rdquo; would overclaim and &ldquo;No&rdquo; would hide real coverage.
    </p>
    <p>Four automated tests have no matching case in these files:</p>
    <ul>
{orphans}
    </ul>
  </div>

  <div class="note-panel">
    <h2>Download</h2>
    <p>
      The combined file is all {cases} cases in one CSV with a <code>Suite</code> column, ready to
      import into TestRail, Xray, Zephyr, or a spreadsheet. It also carries the derived
      <code>ID</code>, <code>Automated</code> and <code>Automated Test</code> columns.
    </p>
    <div class="dl-row">
      <a class="dl primary" href="test-cases/{combined}" download><code>{combined}</code> \
— all {cases} cases</a>
    </div>
    <p style="margin-top:13px;">
      The four originals, unmodified and with their original six columns — what you download is what
      was authored:
    </p>
    <div class="dl-row">
{downloads}
    </div>
  </div>

{sections}

  <footer>
    <strong style="color:var(--txt)">Keoni Kakugawa</strong> · QA &amp; Release Management Leader ·
    <a href="https://github.com/keonikaku/automation">github.com/keonikaku/automation</a> ·
    <a href="https://keonikaku.github.io">Portfolio</a>
    <p class="note">
      This page and the combined CSV are generated from the four original files by
      <a href="https://github.com/keonikaku/automation/blob/main/build_test_cases_page.py"><code>\
build_test_cases_page.py</code></a>, so they cannot drift from them; a unit test re-renders both and
      fails the build if what is committed disagrees with the data. The automated-coverage mapping is
      in <a href="https://github.com/keonikaku/automation/blob/main/shopsmart/testcases.py"><code>\
shopsmart/testcases.py</code></a>.
    </p>
  </footer>

</div>
</body>
</html>
"""


def main() -> int:
    combined = write_combined_csv()
    OUTPUT.write_text(build(), encoding="utf-8")
    print(f"Wrote {combined}")
    print(f"Wrote {OUTPUT}")
    update_index()
    return 0


# ── the preview section embedded in index.html ────────────────────────
# index.html is hand-maintained everywhere except the region between these
# markers, which is generated from the CSVs like the full page. That keeps the
# numbers on the project page derived rather than typed.

PREVIEW_START = "<!-- TEST-CASE-PREVIEW:START — generated by build_test_cases_page.py -->"
PREVIEW_END = "<!-- TEST-CASE-PREVIEW:END -->"

INDEX = REPO_ROOT / "index.html"


def preview_row(filename: str, title: str) -> str:
    case_ref, row = find_case(filename, title)
    gap, traced = is_spec_gap(row), is_traced(row)
    classes = " ".join(
        filter(None, ["case", "is-gap" if gap else "", "is-traced" if traced else ""])
    )
    flags = '<span class="pill gap">Spec gap</span>' if gap else ""
    priority = esc(row["Priority"])
    return f"""        <tr class="{classes}">
          <td class="cid"><code>{case_ref}</code></td>
          <td class="ctitle">{esc(row["Title"])}{flags}</td>
          <td class="cexp">{render_expected(row["Expected Result"])}</td>
          <td class="cmeta"><span class="pri p-{priority.lower()}">{priority}</span></td>
          <td class="cauto">{automated_cell(filename, row["Title"])}</td>
        </tr>"""


def build_preview() -> str:
    total = counts()
    featured_ref, featured = find_case(*FEATURED_CASE)
    traced_refs = [
        f"<code>{find_case(f, r['Title'])[0]}</code>"
        for f, _, r in all_cases()
        if is_traced(r) and f != FEATURED_CASE[0]
    ]
    rows = "\n".join(preview_row(f, t) for f, t in PREVIEW_CASES)

    return f"""{PREVIEW_START}
  <div class="section-head" style="margin-top:34px;">
    <h2>Test design</h2>
    <span>{total["cases"]} cases written before and alongside the automation</span>
  </div>

  <div class="runbar">
    <div class="stat"><span class="k">Cases designed</span><span class="v">{total["cases"]}</span></div>
    <div class="stat"><span class="k">Automated</span><span class="v ok">{total["automated"]} of {total["cases"]}</span></div>
    <div class="stat"><span class="k">Spec gaps flagged</span><span class="v amber">{total["gaps"]}</span></div>
  </div>

  <div class="scope" style="border-left:2px solid var(--accent);">
    <h2>SMART-201 — one defect, traced through {total["traced"]} cases into the smoke suite</h2>
    <p class="tc-lead">
      Search ignored the active category filter: filter to Women, search, and results came back from
      every category. Rather than log it and move on, the issue was traced into coverage —
      {" and ".join([", ".join(traced_refs[:-1]), traced_refs[-1]]) if len(traced_refs) > 1 else traced_refs[0]}
      pin the behaviour from different angles, and <b>the smoke suite is this one case</b>.
      A one-case smoke suite is a decision, not a thin result: smoke exists to answer
      &ldquo;is this build worth testing?&rdquo;, and the fastest honest answer here was the
      regression most likely to make the catalog useless.
    </p>

    <div class="featured">
      <div class="featured-head">
        <code>{featured_ref}</code>
        <span class="pill trace">SMART-201</span>
        <span class="pill no">Automated: No</span>
      </div>
      <h3>{esc(featured["Title"])}</h3>
      <dl class="fdl">
        <dt>Preconditions</dt><dd>{esc(featured["Preconditions"])}</dd>
        <dt>Steps</dt><dd>{render_steps(featured["Steps"])}</dd>
        <dt>Expected result</dt><dd>{render_expected(featured["Expected Result"])}</dd>
        <dt>Priority / Type</dt><dd><span class="pri p-{esc(featured["Priority"]).lower()}">{esc(featured["Priority"])}</span> · {esc(featured["Type"])}</dd>
      </dl>
      <p class="vnote">Designed, prioritised Critical, and <b>not automated</b>. Nothing in the suite
      yet combines a category filter with a search. It sits in the backlog — an ordinary state for
      real work, and more useful published honestly than quietly closed.</p>
    </div>
  </div>

  <div class="section-head">
    <h2>A sample of the cases</h2>
    <span>four of {total["cases"]} · showing the shape, not the size</span>
  </div>

  <div class="tablewrap">
    <table class="cases">
      <thead>
        <tr><th>ID</th><th>Title</th><th>Expected result</th><th>Priority</th><th>Automated</th></tr>
      </thead>
      <tbody>
{rows}
      </tbody>
    </table>
  </div>

  <div class="scope" style="margin-top:16px;">
    <h2>All {total["cases"]} cases, and the files</h2>
    <p class="tc-lead">
      <b>{total["automated"]} of {total["cases"]} cases have automated coverage</b> — {total["yes"]} fully,
      {total["partial"]} partially. The other {total["cases"] - total["automated"]} are designed and run
      manually, which is the point rather than a shortfall: test design and automation are different
      activities, and which cases get automated is a risk decision. The
      <b>{total["gaps"]} &ldquo;spec gap&rdquo; rows</b> are finished cases, not blank ones — where the
      specification was silent, the case records that and proposes an expectation instead of inventing
      one and turning a guess into the standard the build gets measured against.
    </p>
    <div class="dl-row">
      <a class="dl primary" href="test-cases.html">Browse all {total["cases"]} cases →</a>
      <a class="dl" href="test-cases/{COMBINED_FILENAME}" download><code>{COMBINED_FILENAME}</code> — one file, all {total["cases"]}</a>
    </div>
    <p class="tc-lead" style="margin-top:11px;font-size:12.5px;">
      The four original files are published unmodified with their original columns and are linked from
      the full list. <code>Suite</code>, <code>ID</code> and <code>Automated</code> are derived for
      publication and were not written back into them.
    </p>
  </div>
{PREVIEW_END}"""


def update_index() -> None:
    text = INDEX.read_text(encoding="utf-8")
    start, end = text.index(PREVIEW_START), text.index(PREVIEW_END) + len(PREVIEW_END)
    INDEX.write_text(text[:start] + build_preview() + text[end:], encoding="utf-8")
    print(f"Updated {INDEX}")


if __name__ == "__main__":
    raise SystemExit(main())
