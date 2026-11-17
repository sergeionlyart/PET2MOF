#!/usr/bin/env python3
"""Offline, deliberately small Markdown dialect. No third-party imports.

Usage: python -I tools/build.py [article.ru.md] [--metadata PATH] [--output PATH]
Defaults are relative to this script, not the current working directory.
Unsupported syntax is an error; no raw HTML is ever passed through.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import html
import json
from pathlib import Path
import re
import sys
import unicodedata
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent


class MarkdownError(ValueError):
    def __init__(self, line: int, message: str):
        super().__init__(f"строка {line}: {message}")


def safe_url(value: str, line: int, image: bool = False) -> str:
    if not value or re.search(r'[\s<>"\\\x00-\x1f\x7f]', value):
        raise MarkdownError(line, "недопустимый URL")
    parts = urlsplit(value)
    if parts.scheme:
        if image or parts.scheme != "https" or not parts.netloc or parts.username:
            raise MarkdownError(line, "разрешены только ссылки https и относительные пути")
    elif parts.netloc or value.startswith("/") or ":" in parts.path:
        raise MarkdownError(line, "нужен относительный путь")
    if image and (not value.startswith("assets/") or ".." in parts.path.split("/")):
        raise MarkdownError(line, "изображения должны находиться в assets/")
    return html.escape(value, quote=True)


@dataclass
class Block:
    kind: str
    text: str
    line: int
    extra: object = None
    anchor: str = ""


@dataclass
class Document:
    blocks: list[Block]
    frontmatter: dict
    footnotes: dict[str, tuple[str, int]]
    used_ids: set[str] = field(default_factory=set)
    refs: dict[str, list[str]] = field(default_factory=dict)
    footnote_anchor: str = ""

    def unique_id(self, base: str) -> str:
        candidate, n = base, 1
        while candidate in self.used_ids:
            n += 1
            candidate = f"{base}-{n}"
        self.used_ids.add(candidate)
        return candidate

    def inline(self, text: str, line: int, *, allow_refs: bool = True) -> str:
        result, pos = [], 0
        while pos < len(text):
            tail = text[pos:]
            current_line = line + text[:pos].count("\n")
            if tail.startswith("`"):
                end = text.find("`", pos + 1)
                if end < 0 or end == pos + 1:
                    raise MarkdownError(current_line, "незакрытый или пустой inline code")
                result.append("<code>" + html.escape(text[pos + 1:end]) + "</code>")
                pos = end + 1
                continue
            foot = re.match(r"\[\^([\w-]+)\]", tail)
            if foot:
                key = foot[1]
                if not allow_refs or key not in self.footnotes:
                    raise MarkdownError(current_line, f"неизвестная или вложенная сноска {key}")
                ref = self.unique_id(f"fnref-{key}")
                self.refs.setdefault(key, []).append(ref)
                result.append(f'<sup id="{ref}"><a href="#fn-{key}">{html.escape(key)}</a></sup>')
                pos += len(foot[0])
                continue
            link = re.match(r"\[([^\[\]\n]+)\]\(([^()\n]+)\)", tail)
            if link:
                label = self.inline(link[1], current_line, allow_refs=False)
                if "<a " in label:
                    raise MarkdownError(current_line, "вложенная ссылка")
                result.append(f'<a href="{safe_url(link[2], current_line)}">{label}</a>')
                pos += len(link[0])
                continue
            if tail.startswith("*"):
                delimiter = "***" if tail.startswith("***") else "**" if tail.startswith("**") else "*"
                end = text.find(delimiter, pos + len(delimiter))
                if delimiter == "*":
                    # A run of two stars belongs to nested strong, not to em.
                    for run in re.finditer(r"\*+", text[pos + 1:]):
                        if len(run[0]) == 1 or len(run[0]) == 3:
                            end = pos + 1 + run.start() + (2 if len(run[0]) == 3 else 0)
                            break
                    else:
                        end = -1
                elif delimiter == "**" and end >= 0 and text[end:end + 3] == "***":
                    singles = re.findall(r"(?<!\*)\*(?!\*)", text[pos + 2:end])
                    if len(singles) % 2:
                        end += 1
                if end < 0 or end == pos + len(delimiter):
                    raise MarkdownError(current_line, "незакрытое или пустое выделение")
                opening, closing = (("<strong><em>", "</em></strong>") if delimiter == "***"
                                    else ("<strong>", "</strong>") if delimiter == "**" else ("<em>", "</em>"))
                result.append(opening + self.inline(text[pos + len(delimiter):end], current_line,
                                                   allow_refs=allow_refs) + closing)
                pos = end + len(delimiter)
                continue
            if (text[pos] == "\\" or tail.startswith("![")
                    or re.match(r"<(?:/?[A-Za-z]|!|\?)", tail)
                    or re.match(r"\[(?:\^|[^\]]+\](?:\[|\(|:))", tail)):
                raise MarkdownError(current_line, "HTML или неподдерживаемая inline-разметка")
            if tail.startswith("~~") or ((pos == 0 or not text[pos - 1].isalnum())
                                           and re.match(r"(?:__|_[^_\s]+_)", tail)):
                raise MarkdownError(current_line, "неподдерживаемое выделение")
            result.append(html.escape(text[pos]))
            pos += 1
        return "".join(result)


def scalar(value: str, line: int):
    if not value:
        raise MarkdownError(line, "ожидается скаляр YAML")
    if value.startswith('"'):
        try:
            answer = json.loads(value)
        except ValueError as exc:
            raise MarkdownError(line, "неверная строка YAML (двойные кавычки: JSON escapes)") from exc
        if not isinstance(answer, str):
            raise MarkdownError(line, "ожидается строка")
        return answer
    if value.startswith("'"):
        if not re.fullmatch(r"'(?:[^']|'')*'", value):
            raise MarkdownError(line, "неверная строка YAML")
        return value[1:-1].replace("''", "'")
    if value[0] in "[{&*!|>@`" or re.search(r"\s+#|:\s", value):
        raise MarkdownError(line, "поддерживаются только простые скаляры YAML")
    return value


def parse(source: str) -> Document:
    lines = source.splitlines()
    blocks, notes, front = [], {}, {}
    i = 0
    if lines and lines[0] == "---":
        if "---" not in lines[1:]:
            raise MarkdownError(1, "незакрытый YAML-блок")
        i = 1
        while i < len(lines) and lines[i] != "---":
            if lines[i].strip():
                match = re.fullmatch(r"([\w-]+):\s*(.*)", lines[i])
                if not match or match[1] in front:
                    raise MarkdownError(i + 1, "неверный или повторный ключ YAML")
                front[match[1]] = scalar(match[2], i + 1)
            i += 1
        if i == len(lines):
            raise MarkdownError(1, "незакрытый YAML-блок")
        i += 1

    def special(value: str) -> bool:
        return bool(re.match(r"^(?:#|---$|`{3,}|\||- |\d+\. |> |!\[|\[\^)", value))

    while i < len(lines):
        text, number = lines[i], i + 1
        if not text.strip():
            i += 1
            continue
        if text[0].isspace():
            raise MarkdownError(number, "отступы и вложенные блоки запрещены")
        fence = re.fullmatch(r"(`{3,4})([\w+-]*)", text)
        if fence:
            end = i + 1
            while end < len(lines) and lines[end] != fence[1]:
                end += 1
            if end == len(lines):
                raise MarkdownError(number, "незакрытый code fence")
            blocks.append(Block("code", "\n".join(lines[i + 1:end]) + ("\n" if end > i + 1 else ""),
                                number, fence[2]))
            i = end + 1
            continue
        heading = re.fullmatch(r"(#{1,3}) (\S.*)", text)
        if heading:
            if "{#" in heading[2] or re.search(r"\s+#+$", heading[2]):
                raise MarkdownError(number, "явные id и закрывающие # не поддерживаются")
            blocks.append(Block("heading", heading[2], number, len(heading[1])))
            i += 1
            continue
        if text == "---":
            if i and lines[i - 1].strip() and blocks and blocks[-1].kind == "paragraph":
                raise MarkdownError(number, "Setext запрещён; отделите разделитель пустой строкой")
            blocks.append(Block("hr", "", number))
            i += 1
            continue
        note = re.fullmatch(r"\[\^([\w-]+)\]: (\S.*)", text)
        if note:
            if note[1] in notes:
                raise MarkdownError(number, "повторное определение сноски")
            notes[note[1]] = (note[2], number)
            i += 1
            continue
        picture = re.fullmatch(r"!\[([^\[\]]+)\]\(([^()]+)\)", text)
        if picture:
            if not picture[1].strip():
                raise MarkdownError(number, "пустой alt")
            safe_url(picture[2], number, image=True)
            if i + 1 >= len(lines) or not re.fullmatch(r"\*Рис\. \d+\. .+\*", lines[i + 1]):
                raise MarkdownError(number, "следующая строка должна быть *Рис. N. подпись*")
            blocks.append(Block("figure", lines[i + 1][1:-1], number, (picture[1], picture[2])))
            i += 2
            continue
        if text.startswith("|"):
            def cells(row: str, lineno: int) -> list[str]:
                if not row.endswith("|") or "\\|" in row:
                    raise MarkdownError(lineno, "нужна простая pipe-таблица с крайними |")
                return [cell.strip() for cell in row[1:-1].split("|")]
            header = cells(text, number)
            if i + 1 >= len(lines):
                raise MarkdownError(number, "нет разделителя таблицы")
            divider = cells(lines[i + 1], number + 1)
            if len(header) != len(divider) or not all(re.fullmatch(r":?-{3,}:?", c) for c in divider):
                raise MarkdownError(number + 1, "неверный разделитель таблицы")
            rows = [header]
            i += 2
            while i < len(lines) and lines[i].startswith("|"):
                row = cells(lines[i], i + 1)
                if len(row) != len(header):
                    raise MarkdownError(i + 1, "разное число столбцов")
                rows.append(row)
                i += 1
            blocks.append(Block("table", "", number, rows))
            continue
        listing = re.match(r"^(- |\d+\. )(.*)", text)
        if listing:
            ordered = listing[1] != "- "
            items = []
            while i < len(lines):
                item = re.match(r"^(\d+\. |\- )(\S.*)", lines[i])
                if not item or (item[1] != "- ") != ordered:
                    break
                if re.match(r"\[[ xX]\]", item[2]):
                    raise MarkdownError(i + 1, "task lists запрещены")
                items.append((item[2], i + 1))
                i += 1
            if not items:
                raise MarkdownError(number, "пустой список")
            blocks.append(Block("ol" if ordered else "ul", "", number, items))
            continue
        if text.startswith("> "):
            items = []
            while i < len(lines) and lines[i].startswith("> "):
                if special(lines[i][2:]):
                    raise MarkdownError(i + 1, "в цитате поддерживается только inline-текст")
                items.append(lines[i][2:])
                i += 1
            blocks.append(Block("quote", "\n".join(items), number))
            continue
        if re.match(r"^(?:#|`{3,}|~~~|\+ |\* |\d+\) |: |={2,}\s*$|-{2,}\s*$)", text):
            raise MarkdownError(number, "неподдерживаемый блок Markdown")
        paragraph = [text]
        i += 1
        while i < len(lines) and lines[i].strip() and not special(lines[i]):
            if lines[i][0].isspace() or re.match(r"^(?:={2,}\s*$|: |\+ |\* |~~~|\d+\) )", lines[i]):
                raise MarkdownError(i + 1, "вложенность, Setext или неподдерживаемый блок")
            paragraph.append(lines[i])
            i += 1
        blocks.append(Block("paragraph", "\n".join(paragraph), number))
    titles = [b for b in blocks if b.kind == "heading" and b.extra == 1]
    if len(titles) != 1:
        raise MarkdownError(1, "требуется ровно один # H1")
    if not blocks or blocks[0] is not titles[0]:
        raise MarkdownError(titles[0].line, "H1 должен начинать статью после YAML")
    doc = Document(blocks, front, notes)
    doc.used_ids.add("toc-title")
    doc.used_ids.update(f"fn-{key}" for key in notes)
    # Validate inline syntax before rendering; reserve all anchors first.
    for block in blocks:
        if block.kind == "heading":
            plain = re.sub(r"<[^>]+>", "", doc.inline(block.text, block.line, allow_refs=False))
            slug = "".join(c if c.isalnum() else "-" for c in unicodedata.normalize("NFC", html.unescape(plain)).casefold())
            block.anchor = doc.unique_id(re.sub("-+", "-", slug).strip("-") or "section")
    if notes:
        doc.footnote_anchor = doc.unique_id("сноски")
    for block in blocks:
        if block.kind in ("paragraph", "quote", "figure"):
            doc.inline(block.text, block.line)
        elif block.kind in ("ul", "ol"):
            for item, line in block.extra:
                doc.inline(item, line)
        elif block.kind == "table":
            for j, row in enumerate(block.extra):
                for cell in row:
                    doc.inline(cell, block.line + j + (1 if j else 0))
    for value, line in notes.values():
        doc.inline(value, line, allow_refs=False)
    # Validation does not consume footnote reference ids.
    for refs in doc.refs.values():
        doc.used_ids.difference_update(refs)
    doc.refs.clear()
    return doc


def word_count(doc: Document) -> int:
    """Main narrative only, stopping before the first appendix H2."""
    texts = []
    for b in doc.blocks:
        if b.kind == "heading" and b.extra == 2 and b.text.startswith("Приложение"):
            break
        if b.kind in ("code", "table", "hr"):
            continue
        if b.kind in ("ol", "ul"):
            texts.extend(item for item, _ in b.extra)
        else:
            texts.append(b.text)
    text = " ".join(texts)
    text = re.sub(r"!?\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[\^[^\]]+\]", "", text)
    return len(re.findall(r"\w+(?:[’'-]\w+)*", text, flags=re.UNICODE))


CSS = r"""
:root{--bg:#f8f7f3;--ink:#121212;--muted:#5c5c59;--line:#9d9d98;--thin:#d5d4ce;--blue:#0755dc;--darkblue:#003fae;--red:#d91922;--ui:"Helvetica Neue",Arial,sans-serif;--mono:ui-monospace,"SFMono-Regular",Menlo,Consolas,monospace}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;min-width:320px;background:var(--bg);color:var(--ink);font-family:Georgia,"Times New Roman",serif;line-height:1.5}
.page{width:min(1380px,calc(100vw - 64px));margin:0 auto}header{max-width:1000px;border-bottom:1px solid var(--ink);padding:60px 0 32px;margin-bottom:60px}
.eyebrow{font:11px var(--mono);text-transform:uppercase;letter-spacing:.08em}header{overflow-wrap:anywhere}h1{font-size:clamp(40px,8vw,96px);font-weight:500;letter-spacing:-.035em;line-height:.92;margin:28px 0}.subtitle{font-size:21px;max-width:740px}.meta{font:10px/1.6 var(--mono);text-transform:uppercase}.draft{display:inline-block;border:1px solid var(--red);color:var(--red);font:12px/1.5 var(--mono);padding:8px 12px;margin-top:16px}
.layout{display:grid;grid-template-columns:220px minmax(0,740px);gap:clamp(48px,9vw,130px);align-items:start;padding-bottom:80px}.toc{position:sticky;top:24px;font-family:var(--ui);max-height:calc(100vh - 48px);overflow-y:auto}.toc h2{font:12px var(--mono);text-transform:uppercase;margin:0 0 16px}.toc ul{list-style:none;padding:0;margin:0}.toc a{display:block;border-top:1px solid var(--line);padding:9px 0;font-size:12px;text-decoration:none}.toc .sub a{padding-left:14px;font-size:11px;color:var(--muted)}.toc a:hover,.toc a:focus-visible{color:var(--blue)}
article{min-width:0;font-size:19px;line-height:1.55;overflow-wrap:anywhere}article h2{font-size:clamp(31px,4vw,43px);font-weight:500;line-height:1.03;margin:52px 0 24px}article h3{font:500 18px/1.4 var(--ui);margin-top:32px}p{margin:0 0 1.2em}a{color:inherit;text-decoration-thickness:1px;text-underline-offset:.18em}a:hover{color:var(--blue)}a:active{color:var(--darkblue)}:focus-visible{outline:3px solid var(--blue);outline-offset:3px}[id]{scroll-margin-top:24px}.brief{border-top:1px solid var(--ink);border-bottom:1px solid var(--ink);margin:32px 0;padding:20px 0}.brief h2{font:12px var(--mono);text-transform:uppercase;margin:0 0 20px}code{font-family:var(--mono);font-size:.8em}pre{border:1px solid var(--line);padding:18px;white-space:pre-wrap;overflow-wrap:anywhere;max-width:100%;background:#fff}pre code{font-size:13px}blockquote{margin:24px 0;border-left:2px solid var(--line);padding-left:22px;color:var(--muted)}hr{border:0;border-top:1px solid var(--line);margin:36px 0}
.table-scroll{overflow-x:auto;max-width:100%;margin:24px 0}table{border-collapse:collapse;font:14px/1.5 var(--ui);width:100%}th,td{text-align:left;border-bottom:1px solid var(--thin);padding:12px;min-width:110px}th{font:10px var(--mono);text-transform:uppercase;background:#fff}figure{margin:32px 0}figure img{display:block;width:100%;height:auto;border:1px solid var(--line)}figcaption{font:11px/1.6 var(--mono);color:var(--muted);margin-top:12px}details{margin:16px 0}summary{cursor:pointer;font:600 16px/1.5 var(--ui);min-height:52px;padding:14px 0;border-top:1px solid var(--line)}details[open]>summary{margin-bottom:20px}.footnotes{font-size:15px;border-top:1px solid var(--line);margin-top:48px;padding-top:16px}.footnotes h2{font:12px var(--mono);text-transform:uppercase}.backref{font-family:var(--ui)}
@media(max-width:900px){.layout{grid-template-columns:minmax(0,1fr);gap:32px}.toc{position:static;max-height:none}.toc li.sub{display:none}.toc ul{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 24px}header{padding-top:36px;margin-bottom:32px}}
@media(max-width:620px){.page{width:calc(100vw - 32px)}.toc ul{grid-template-columns:1fr}article{font-size:18px}h1{line-height:1}header{padding-top:24px}}
@media print{body{background:#fff}.page,header{width:100%;max-width:none}.toc{display:none}.layout{display:block}article{font-size:12pt}details>*,details:not([open])>*{display:block!important}details::details-content{content-visibility:visible!important;display:block!important}summary{display:list-item!important}.table-scroll{overflow:visible}table{table-layout:fixed;width:100%}th,td{min-width:0;overflow-wrap:anywhere;padding:5px}pre{overflow:visible;white-space:pre-wrap}figure{break-inside:avoid}a[href^="https://"]::after{content:" (" attr(href) ")";font-size:9pt;overflow-wrap:anywhere}h1{font-size:40pt}header{padding-top:0}*{scroll-behavior:auto!important}}
"""

SCRIPT = """(() => {
  function reveal() {
    let node;
    try { node = document.getElementById(decodeURIComponent(location.hash.slice(1))); }
    catch (_) { return; }
    if (!node) return;
    for (let p = node; p; p = p.parentElement) if (p.tagName === 'DETAILS') p.open = true;
    node.scrollIntoView();
  }
  addEventListener('hashchange', reveal); if (location.hash) reveal();
  let closed = [];
  addEventListener('beforeprint', () => {
    closed = [...document.querySelectorAll('details:not([open])')];
    closed.forEach(d => d.open = true);
  });
  addEventListener('afterprint', () => closed.forEach(d => d.open = false));
})();"""


def render(doc: Document, metadata: dict) -> str:
    required = ("eyebrow", "subtitle", "author", "date", "version", "reading_time")
    for key in required:
        if not isinstance(metadata.get(key), str) or not metadata[key].strip():
            raise ValueError(f"metadata: требуется непустая строка {key}")
    if doc.refs:
        for refs in doc.refs.values():
            doc.used_ids.difference_update(refs)
        doc.refs.clear()
    title = doc.blocks[0]
    title_html = doc.inline(title.text, title.line, allow_refs=False)
    body, toc = [], []
    section_open = detail_open = appendix = brief_seen = False
    for b in doc.blocks[1:]:
        if b.kind == "heading":
            level = b.extra
            if level == 2:
                appendix = b.text.startswith("Приложение")
            label = doc.inline(b.text, b.line, allow_refs=False)
            if not (level == 3 and appendix):
                toc.append(f'<li class="{"sub" if level == 3 else "top"}"><a href="#{b.anchor}">{label}</a></li>')
            if level == 2:
                if detail_open:
                    body.append("</details>")
                    detail_open = False
                if section_open:
                    body.append("</section>")
                appendix = b.text.startswith("Приложение")
                brief = b.text == "Кратко" and not brief_seen
                brief_seen |= brief
                body.append(f'<section{" class=\"brief\"" if brief else ""}><h2 id="{b.anchor}">{label}</h2>')
                section_open = True
            elif appendix:
                if detail_open:
                    body.append("</details>")
                body.append(f'<details id="{b.anchor}"><summary>{label}</summary>')
                detail_open = True
            else:
                body.append(f'<h3 id="{b.anchor}">{label}</h3>')
        elif b.kind == "paragraph":
            body.append("<p>" + doc.inline(b.text, b.line) + "</p>")
        elif b.kind == "quote":
            body.append("<blockquote><p>" + doc.inline(b.text, b.line) + "</p></blockquote>")
        elif b.kind == "code":
            language = f' class="language-{b.extra}"' if b.extra else ""
            body.append(f"<pre><code{language}>{html.escape(b.text)}</code></pre>")
        elif b.kind in ("ol", "ul"):
            body.append(f"<{b.kind}>" + "".join("<li>" + doc.inline(t, n) + "</li>" for t, n in b.extra) + f"</{b.kind}>")
        elif b.kind == "hr":
            body.append("<hr>")
        elif b.kind == "figure":
            alt, src = b.extra
            body.append(f'<figure><img src="{safe_url(src, b.line, image=True)}" alt="{html.escape(alt, quote=True)}"><figcaption>'
                        + doc.inline(b.text, b.line + 1) + "</figcaption></figure>")
        elif b.kind == "table":
            rows = []
            for j, row in enumerate(b.extra):
                tag = "th" if j == 0 else "td"
                rows.append("<tr>" + "".join(f"<{tag}{' scope=\"col\"' if j == 0 else ''}>" + doc.inline(c, b.line + j + (1 if j else 0)) + f"</{tag}>" for c in row) + "</tr>")
            body.append('<div class="table-scroll" role="region" aria-label="Таблица" tabindex="0"><table><thead>'
                        + rows[0] + "</thead><tbody>" + "".join(rows[1:]) + "</tbody></table></div>")
    if detail_open:
        body.append("</details>")
    if section_open:
        body.append("</section>")
    if doc.footnotes:
        body.append(f'<section class="footnotes" aria-label="Сноски"><h2 id="{doc.footnote_anchor}">Сноски</h2><ol>')
        for key, (text, line) in doc.footnotes.items():
            backs = " ".join(f'<a class="backref" href="#{ref}" aria-label="Назад к сноске {html.escape(key)} ({j})">↩{j}</a>'
                             for j, ref in enumerate(doc.refs.get(key, []), 1))
            body.append(f'<li id="fn-{key}">' + doc.inline(text, line, allow_refs=False) + " " + backs + "</li>")
        body.append("</ol></section>")
    meta = " · ".join(html.escape(metadata[k]) for k in required[2:])
    plain_title = html.escape(re.sub(r"<[^>]+>", "", html.unescape(title_html)))
    return (f'<!doctype html>\n<html lang="ru"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<meta name="robots" content="noindex,nofollow"><title>{plain_title}</title><style>{CSS}</style></head>'
            f'<body><div class="page"><header><p class="eyebrow">{html.escape(metadata["eyebrow"])}</p>'
            f'<h1 id="{title.anchor}">{title_html}</h1><p class="subtitle">{html.escape(metadata["subtitle"])}</p>'
            f'<p class="meta">{meta}</p><p class="draft">Черновик для согласования</p></header>'
            '<div class="layout"><nav class="toc" aria-label="На этой странице"><h2 id="toc-title">На этой странице</h2><ul>'
            + "".join(toc) + '</ul></nav><article>' + "\n".join(body)
            + f'</article></div></div><script>{SCRIPT}</script></body></html>\n')


def build(source: Path, metadata: Path, output: Path) -> None:
    doc = parse(source.read_text(encoding="utf-8"))
    meta = json.loads(metadata.read_text(encoding="utf-8"))
    output.write_text(render(doc, meta), encoding="utf-8")


def main() -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("source", nargs="?", type=Path, default=ROOT / "article.ru.md")
    cli.add_argument("--metadata", type=Path)
    cli.add_argument("--output", type=Path)
    args = cli.parse_args()
    metadata = args.metadata or args.source.with_name(args.source.name.replace(".ru.md", ".metadata.json"))
    output = args.output or args.source.parent / "index.html"
    try:
        build(args.source, metadata, output)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Собрано: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
