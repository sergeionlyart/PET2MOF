#!/usr/bin/env python3
"""Build the Russian report locally using the locked PyMuPDF and bundled font."""
from html import escape
from pathlib import Path
import re
import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / 'reports'


def inline(s):
    s = escape(s)
    s = re.sub(r'!\[([^]]*)\]\(([^)]+)\)', r'<div style="page-break-before: always"></div><img alt="\1" src="\2" width="500">', s)
    s = re.sub(r'\[([^]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    return s


def render(source):
    lines = source.splitlines()
    out = []
    paragraph = []
    table = []
    def close_table():
        if table:
            out.append('<table>' + ''.join(table) + '</table>')
            table.clear()
    def flush():
        if paragraph:
            out.append('<p>' + inline(' '.join(paragraph)) + '</p>')
            paragraph.clear()
    for line in lines:
        if not line.strip():
            close_table()
            flush()
        elif line.startswith('#'):
            close_table()
            flush()
            n = min(len(line) - len(line.lstrip('#')), 6)
            out.append(f'<h{n}>' + inline(line[n:].strip()) + f'</h{n}>')
        elif line.startswith('|'):
            flush()
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if all(re.fullmatch(r'[:\- ]+', c) for c in cells):
                continue
            if not table:
                table.append('<tr>' + ''.join('<th>' + inline(c) + '</th>' for c in cells) + '</tr>')
            else:
                table.append('<tr>' + ''.join('<td>' + inline(c) + '</td>' for c in cells) + '</tr>')
            continue
        else:
            paragraph.append(line.strip())
        close_table()
    flush()
    close_table()
    return '<html><body>' + '\n'.join(out) + '</body></html>'


def main():
    css = '''@font-face {font-family: dejavu; src: url(assets/DejaVuSans.ttf);}
    body {font-family: dejavu; font-size: 9pt; line-height: 1.3;}
    h1 {font-size: 19pt;} h2 {font-size: 13pt; margin-top: 14pt;}
    p {margin: 6pt 0;}
    table {border-collapse: collapse; width: 100%; margin: 6pt 0;}
    th, td {border: 0.5pt solid #888; padding: 2pt 3pt; font-size: 7.5pt; vertical-align: top;}
    th {background-color: #eeeeee;}
    img {width: 480px; height: 309px;} a {color: #175080;} code {font-family: dejavu; font-size: 8pt;}
    '''
    story = fitz.Story(html=render((REPORTS / 'final_report.md').read_text(encoding='utf-8')),
                       user_css=css, archive=fitz.Archive(str(REPORTS)))
    output = REPORTS / 'final_report.pdf'
    writer = fitz.DocumentWriter(str(output))
    page = fitz.paper_rect('a4')
    content = page + (42, 42, -42, -42)
    more = True
    while more:
        device = writer.begin_page(page)
        more, _ = story.place(content)
        story.draw(device)
        writer.end_page()
    writer.close()
    print(f'Built {output.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
