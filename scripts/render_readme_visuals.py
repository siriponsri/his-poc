"""Render self-contained README diagrams and an evidence-backed trial figure.

Uses the Python standard library for SVG. Optional --png uses an already installed
CairoSVG renderer; it never installs packages, fetches assets or calls a service.
The chart reads the retained six-call synthetic acceptance receipt, not live data.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/branding'
EVIDENCE = ROOT / 'evidence/ai-driven-root-20261114/application-acceptance.json'
BLUE = '#1c4286'
BURGUNDY = '#861c42'
GREEN = '#42861c'
INK = '#202b3a'
MUTED = '#667386'
LINE = '#dbe2eb'
PAPER = '#ffffff'
TINT = '#f5f7fa'


def esc(value):
    return html.escape(str(value), quote=True)


class Drawing:
    def __init__(self, width, height, title, description):
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{esc(title)}</title><desc id="desc">{esc(description)}</desc>',
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M1 1 L9 5 L1 9" fill="none" stroke="#8090a5" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></marker></defs>',
            f'<rect width="{width}" height="{height}" fill="{PAPER}"/>',
            '<g font-family="Arial, Helvetica, sans-serif">',
        ]

    def rect(self, x, y, w, h, fill=PAPER, stroke=LINE, radius=12, dashed=False):
        dash = ' stroke-dasharray="6 6"' if dashed else ''
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"{dash}/>')

    def text(self, x, y, value, size=18, fill=INK, weight=400, anchor='start'):
        self.parts.append(f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}">{esc(value)}</text>')

    def lines(self, x, y, values, size=18, fill=MUTED, step=26, weight=400):
        for offset, value in enumerate(values):
            self.text(x, y + offset * step, value, size, fill, weight)

    def path(self, points, arrow=True, dashed=False, color='#8090a5', width=2):
        end = ' marker-end="url(#arrow)"' if arrow else ''
        dash = ' stroke-dasharray="6 6"' if dashed else ''
        self.parts.append(f'<path d="{esc(points)}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"{dash}{end}/>')

    def circle(self, x, y, radius, fill, stroke='none', width=1):
        self.parts.append(f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')

    def box(self, x, y, w, title, body, accent=BLUE, height=104):
        self.rect(x, y, w, height)
        self.circle(x + 25, y + 31, 4, accent)
        self.text(x + 40, y + 38, title, 23, INK, 600)
        self.lines(x + 24, y + 69, body, 17, MUTED, 24)

    def finish(self):
        return '\n'.join(self.parts + ['</g></svg>']) + '\n'


def architecture():
    d = Drawing(1440, 850, 'CareBalance deployed architecture',
                'Staff reach the same-origin React and FastAPI application through Cloudflare Access. On dr-train, PostgreSQL and file storage retain records and evidence. A separate guarded worker reads the durable queue and calls a private Typhoon service. Server-only specialist gateways reach isolated LabClear and DR services. Model and database endpoints have no public route. This is a simplified logical diagram, not a network topology or high-availability claim.')
    d.text(60, 58, 'ONE PATIENT CONTEXT. SEPARATE EXECUTION BOUNDARIES.', 15, BLUE, 700)
    d.text(60, 104, 'How CareBalance connects the work', 36, INK, 600)
    d.box(80, 155, 420, 'Staff browser', ['Clinical workspace · patient record', 'Existing HIS account and care assignment'])
    d.box(820, 155, 500, 'Cloudflare Access + Tunnel', ['Allowed-email access to his.ai-cie.com', 'HTTPS traffic to the protected HIS origin'])
    d.path('M500 207 H820')
    d.text(660, 193, 'HTTPS', 16, MUTED, anchor='middle')

    d.rect(44, 317, 1352, 470, TINT, LINE, 18)
    d.text(72, 348, 'dr-train · application and private services', 18, MUTED, 600)
    d.path('M1070 259 V285 H350 V390')
    d.text(700, 278, 'Exact-host origin', 16, MUTED, anchor='middle')
    d.box(80, 390, 540, 'CareBalance application', ['React + FastAPI /api/v2 · shared clinical / ERP core', 'Session · CSRF · role, facility and patient scope'])
    d.box(750, 390, 260, 'PostgreSQL 18', ['Records · durable queue', 'Versions · effects · audit'])
    d.box(1060, 390, 260, 'File storage', ['Source bytes', 'Checksums and ownership'])
    d.path('M620 430 H750')
    d.text(685, 455, 'SQL', 16, MUTED, anchor='middle')
    d.path('M620 406 H720 V368 H1190 V390')

    d.box(80, 635, 390, 'LabClear + DR Screening', ['Server-only scoped gateways', 'Separate services and databases'], BURGUNDY)
    d.box(650, 635, 300, 'Guarded worker', ['Same immutable app image', 'One queued preparation at a time'])
    d.box(1020, 635, 300, 'Private Typhoon', ['Dedicated GPU0 · pinned identity', 'Bounded source view and output'])
    d.path('M880 494 V560 H800 V635')
    d.text(1010, 585, 'Queue + source-change watches', 17, MUTED, anchor='middle')
    d.path('M950 687 H1020')
    d.text(985, 672, 'HTTP', 15, MUTED, anchor='middle')
    d.path('M275 494 V635')
    d.text(310, 565, 'Explicit transfer / review', 17, MUTED)
    d.text(80, 768, 'No open database transaction during model or specialist HTTP calls.', 17, INK)
    d.text(60, 824, 'Private services have no public model/database route. Legacy document review uses its separate existing private provider route.', 16, MUTED)
    return d.finish()


def workflow():
    d = Drawing(1440, 570, 'CareBalance source-bound AI workflow',
                'An authenticated staff member selects a visit. Role-authorized sources are collected with omissions disclosed. AI prepares a source-linked artifact. A person reviews evidence and edits a draft, then explicitly applies permitted draft or follow-up effects. Version checks, audit and idempotency bind the save. An opt-in bounded watch triggers only on eligible source changes. Invalid or unknown work remains recorded, without automatic retries.')
    d.text(60, 58, 'AI PREPARES. STAFF REVIEW AND DECIDE.', 15, BLUE, 700)
    d.text(60, 104, 'From source record to the next piece of work', 35, INK, 600)
    columns = [60, 337, 614, 891, 1168]
    steps = [
        ('Choose context', ['One patient and visit', 'Current role and care scope'], BLUE),
        ('Collect sources', ['Authorized fields and notes', 'Visible omissions and citations'], BLUE),
        ('Prepare with AI', ['Source-linked facts and draft', 'Private, bounded inference'], BLUE),
        ('Review the draft', ['Open evidence and full record', 'Edit and select follow-ups'], BURGUNDY),
        ('Save the work', ['New draft or follow-up', 'Link an existing open review'], GREEN),
    ]
    for index, (x, (title, body, color)) in enumerate(zip(columns, steps), 1):
        d.circle(x + 20, 173, 20, color)
        d.text(x + 20, 180, str(index), 20, PAPER, 600, 'middle')
        d.text(x, 232, title, 23, INK, 600)
        d.lines(x, 268, body, 17, MUTED, 27)
        if index < 5:
            d.path(f'M{x + 235} 174 H{x + 265}')
    d.path('M60 335 H1380', False, color=LINE, width=1)
    d.text(60, 374, 'Every save rechecks current permissions, source versions and selected actions.', 21, INK, 500)
    d.text(60, 407, 'Immutable revisions + audit + idempotency preserve the original evidence and prevent duplicate effects.', 18, MUTED)
    d.rect(60, 447, 1320, 78, TINT, LINE, 10)
    d.text(84, 478, 'Optional watch', 18, BLUE, 600)
    d.text(262, 478, 'Eligible source change', 18, INK)
    d.path('M465 473 H520', dashed=True)
    d.text(540, 478, 'One new preparation', 18, INK)
    d.text(84, 507, 'Up to 30 minutes · at most 3 automatic runs · pristine AI-created drafts/tasks do not trigger a feedback loop', 16, MUTED)
    d.text(60, 555, 'No assistant action signs, prescribes, places an order or releases a laboratory result. Unknown / invalid outcomes remain recorded.', 16, MUTED)
    return d.finish()


def trial_chart(receipt):
    labels = {
        'visit': 'Visit preparation',
        'nursing_original': 'Nursing · original source',
        'nursing_corrected': 'Nursing · corrected source',
        'records': 'Records readiness',
        'laboratory': 'Laboratory handoff',
        'watch': 'Records · changed-source watch',
    }
    runs = receipt['runs']
    assert [r['case'] for r in runs] == list(labels)
    assert receipt['application_call_budget']['actual'] == 6
    description = ['Six retained synthetic application calls; no clinical performance or latency-SLA claim.']
    for run in runs:
        c = run['coverage']
        assert c['included_sources'] + c['omitted_sources'] == c['eligible_sources']
        assert run['elapsed_ms'] / 1000 <= run['queue_to_completion_seconds']
        description.append(f"{labels[run['case']]}: provider {run['elapsed_ms']/1000:.3f}s; queue record to completion {run['queue_to_completion_seconds']:.3f}s; included {c['included_sources']} of {c['eligible_sources']} eligible sources.")
    d = Drawing(1440, 740, 'Observed AI trial timing and source coverage', ' '.join(description))
    d.text(60, 58, 'MEASURED IN THE SYNTHETIC POC · 14 NOV 2026 UTC', 15, BLUE, 700)
    d.text(60, 104, 'Six calls, with timing and source coverage visible', 35, INK, 600)
    d.text(60, 139, 'One visit, two distinct nursing inputs, records, laboratory and one changed-source watch.', 19, MUTED)
    d.text(340, 191, 'Observed duration', 19, INK, 600)
    d.rect(340, 211, 28, 10, BLUE, BLUE, 3)
    d.text(378, 222, 'Provider', 16, MUTED)
    d.circle(481, 216, 5, INK)
    d.text(495, 222, 'Queue record → completion', 16, MUTED)
    d.text(870, 191, 'Provider / total', 17, MUTED)
    d.text(1100, 191, 'Source coverage', 19, INK, 600)
    d.text(1100, 222, 'Included / eligible', 16, MUTED)
    plot_x, plot_w = 340, 485
    for value in (0, 20, 40, 60, 80):
        x = plot_x + value / 80 * plot_w
        d.path(f'M{x} 249 V603', False, color=LINE, width=1)
        d.text(x, 628, f'{value}s', 15, MUTED, anchor='middle')
    d.path('M1070 175 V638', False, color=LINE, width=1)
    for i, run in enumerate(runs):
        y = 280 + i * 60
        provider = run['elapsed_ms'] / 1000
        total = run['queue_to_completion_seconds']
        d.text(60, y + 6, labels[run['case']], 18, INK, 500)
        px = plot_x + provider / 80 * plot_w
        tx = plot_x + total / 80 * plot_w
        d.rect(plot_x, y - 6, px - plot_x, 12, BLUE, BLUE, 4)
        d.path(f'M{px} {y} H{tx}', False, color=INK, width=1.5)
        d.circle(tx, y, 5, INK)
        d.text(870, y + 6, f'{provider:.1f} / {total:.1f}s', 18, INK)
        c = run['coverage']
        scale = 220 / 12
        d.rect(1100, y - 8, c['eligible_sources'] * scale, 16, '#e6ebf1', '#e6ebf1', 3)
        d.rect(1100, y - 8, c['included_sources'] * scale, 16, BLUE, BLUE, 3)
        d.text(1340, y + 6, f"{c['included_sources']} / {c['eligible_sources']}", 18, INK)
    d.rect(1100, 659, 16, 10, BLUE, BLUE, 2)
    d.text(1125, 670, 'Included', 15, MUTED)
    d.rect(1230, 659, 16, 10, '#e6ebf1', '#e6ebf1', 2)
    d.text(1255, 670, 'Omitted', 15, MUTED)
    d.text(60, 677, 'Original nursing output was retained unapplied. The corrected source produced a separate reviewed call.', 17, INK)
    d.text(60, 710, 'Small authored-data trial; not a benchmark or staff-time-savings estimate. Total time includes scheduling and persistence.', 16, MUTED)
    return d.finish()


def validate_svg(raw):
    root = ET.fromstring(raw)
    ns = {'s': 'http://www.w3.org/2000/svg'}
    assert root.get('role') == 'img' and root.get('aria-labelledby') == 'title desc'
    assert root.find('s:title', ns).text and root.find('s:desc', ns).text
    ids = [node.get('id') for node in root.iter() if node.get('id')]
    assert len(ids) == len(set(ids))
    assert all(node.tag.split('}')[-1] not in ('script', 'foreignObject') for node in root.iter())
    assert all(not key.endswith('href') for node in root.iter() for key in node.attrib)


def validate_document_links():
    pattern = r'!?\[[^\]]*\]\(([^)\s]+)\)|(?:href|src)="([^"]+)"'
    checked = 0
    for path in [ROOT / 'README.md', ROOT / 'docs/README_VISUALS.md']:
        for groups in re.findall(pattern, path.read_text(encoding='utf-8')):
            value = next(part for part in groups if part)
            if value.startswith(('https://', 'http://', '#')):
                continue
            target = (path.parent / value.split('#')[0]).resolve()
            assert target.is_relative_to(ROOT) and target.exists(), f'Broken local link in {path.name}: {value}'
            checked += 1
    return checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--png', action='store_true', help='Also render PNG using installed CairoSVG')
    parser.add_argument('--check', action='store_true', help='Verify SVGs match current evidence without writing')
    args = parser.parse_args()
    receipt = json.loads(EVIDENCE.read_text(encoding='utf-8'))
    assert receipt['status'] == 'PASS_BOUNDED_PRODUCTION_ASSISTANT_WORKFLOWS'
    visuals = {'readme-architecture': architecture(), 'readme-workflow': workflow(), 'readme-trial': trial_chart(receipt)}
    renderer = None
    if args.png:
        import cairosvg
        renderer = cairosvg
    for stem, raw in visuals.items():
        validate_svg(raw)
        path = OUT / f'{stem}.svg'
        if args.check:
            assert path.read_bytes() == raw.encode('utf-8'), f'Regenerate stale visual: {path.name}'
        else:
            path.write_bytes(raw.encode('utf-8'))
        if renderer is not None and not args.check:
            renderer.svg2png(bytestring=raw.encode('utf-8'), write_to=str(OUT / f'{stem}.png'))
    checked_links = validate_document_links() if args.check else None
    print(json.dumps({'status': 'PASS', 'visuals': len(visuals), 'mode': 'check' if args.check else 'render', 'png_rendered': bool(renderer) and not args.check, 'local_links_checked': checked_links, 'evidence_sha256': hashlib.sha256(EVIDENCE.read_bytes()).hexdigest(), 'external_requests': 0}))


if __name__ == '__main__':
    main()
