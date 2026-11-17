#!/usr/bin/env python3
"""Offline checks: python -I tools/check.py [index.html] [--source article.ru.md]."""
from __future__ import annotations

import argparse
from collections import Counter
from html.parser import HTMLParser
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

# python -I deliberately omits the script directory from sys.path.
spec = importlib.util.spec_from_file_location("article_build", Path(__file__).with_name("build.py"))
build = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = build
spec.loader.exec_module(build)

SHAS = (
    "66bae26af9970c3142b72d25031c844b5461708f",
    "1558433614619e04102989d6b6f1479c50f364ce",
    "70685dc686ce22505b303a60920980a02772f019",
)
REPO = Path(__file__).resolve().parents[3]
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids, self.links, self.errors = [], [], []
        self.stack, self.figures = [], []
        self.h1 = 0
        self.robots = False
        self.texts = []
        self.visible_texts = []
        self.css = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("style"):
            self.css.append(a["style"])
        if len(a) != len(attrs):
            self.errors.append(f"повторный атрибут {tag}")
        if a.get("id") is not None:
            self.ids.append(a["id"])
        self.h1 += tag == "h1"
        if tag == "meta" and a.get("name", "").lower() == "robots":
            self.robots |= {v.strip().lower() for v in a.get("content", "").split(",")} == {"noindex", "nofollow"}
        if tag in {"iframe", "form", "base", "object", "embed"}:
            self.errors.append(f"запрещённый элемент {tag}")
        if tag == "script" and "src" in a:
            self.errors.append("script src запрещён")
        for key in a:
            if key.lower().startswith("on") or key in {"srcset", "poster", "action", "formaction"}:
                self.errors.append(f"запрещённый атрибут {tag}.{key}")
        for key in ("src", "href"):
            if key not in a:
                continue
            value = a[key] or ""
            self.links.append((tag, key, value))
            parts = urlsplit(value)
            if (parts.scheme or parts.netloc) and not (tag == "a" and key == "href" and parts.scheme == "https"):
                self.errors.append(f"внешняя загрузка/схема {tag}.{key}")
            if key == "src" and not value.startswith("assets/"):
                self.errors.append(f"ресурс вне assets/: {value}")
        if tag == "figure":
            self.figures.append({"images": 0, "caption": ""})
        if tag == "img":
            if not a.get("alt", "").strip():
                self.errors.append("пустой alt изображения")
            if not self.figures:
                self.errors.append("img вне figure")
            else:
                self.figures[-1]["images"] += 1
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"нарушена вложенность HTML: </{tag}>")
            return
        self.stack.pop()
        if tag == "figure" and self.figures:
            figure = self.figures.pop()
            if figure["images"] and not figure["caption"].strip():
                self.errors.append("figure без непустого figcaption")

    def handle_data(self, data):
        self.texts.append(data)
        if "style" in self.stack:
            self.css.append(data)
        if not any(t in self.stack for t in ("script", "style", "title")):
            self.visible_texts.append(data)
        if self.figures and "figcaption" in self.stack:
            self.figures[-1]["caption"] += data


def github_error(value: str, repo: Path = REPO) -> str | None:
    parts = urlsplit(value)
    if parts.hostname != "github.com":
        return None
    prefix = "/sergeionlyart/PET2MOF/"
    if not parts.path.startswith(prefix):
        return None
    rest = parts.path[len(prefix):].split("/", 2)
    if not rest or rest[0] not in ("blob", "tree"):
        return None
    if len(rest) != 3 or rest[1] not in SHAS or not rest[2]:
        return "GitHub: нужен полный разрешённый SHA и путь"
    kind, sha, raw_path = rest
    path = unquote(raw_path).rstrip("/")
    if any(part in (".", "..", "") for part in path.split("/")):
        return "GitHub: некорректный путь"
    result = subprocess.run(["git", "ls-tree", "-z", sha, "--", f":(literal){path}"],
                            cwd=repo, capture_output=True, check=False)
    if result.returncode or not result.stdout:
        return "GitHub: путь не найден в git ls-tree"
    entries = [entry.split(b"\t", 1) for entry in result.stdout.rstrip(b"\0").split(b"\0")]
    expected = b"tree" if kind == "tree" else b"blob"
    if not any(len(e) == 2 and e[1].decode("utf-8") == path and e[0].split()[1] == expected for e in entries):
        return "GitHub: тип blob/tree не совпадает с git ls-tree"
    return None


def check(html_path: Path, source: Path, patterns: str | None = None) -> tuple[list[str], list[str], int]:
    errors, warnings, words = [], [], 0
    markdown = source.read_text(encoding="utf-8")
    try:
        doc = build.parse(markdown)
        words = build.word_count(doc)
        if not 4000 <= words <= 6000:
            warnings.append(f"основной текст: {words} слов, ориентир 4000–6000")
    except ValueError as exc:
        errors.append(f"Markdown: {exc}")
    content = html_path.read_text(encoding="utf-8")
    page = Page()
    try:
        page.feed(content)
        page.close()
    except ValueError as exc:
        errors.append(f"HTML: {exc}")
    errors.extend(page.errors)
    if page.stack:
        errors.append("HTML: незакрытые элементы")
    if page.h1 != 1:
        errors.append(f"должен быть один h1, найдено {page.h1}")
    if not page.robots:
        errors.append("нет noindex,nofollow")
    if "Черновик для согласования" not in " ".join(page.visible_texts):
        errors.append("нет метки черновика")
    if any(not identifier for identifier in page.ids) or any(n > 1 for n in Counter(page.ids).values()):
        errors.append("пустые или повторные id")
    if re.search(r"@import|url\(\s*['\"]?\s*(?:https?:|//)", "\n".join(page.css), re.I):
        errors.append("CSS: @import или внешний url()")
    for tag, key, value in page.links:
        parts = urlsplit(value)
        if value.startswith("#"):
            if unquote(value[1:]) not in page.ids:
                errors.append(f"якорь не найден: {value}")
        elif not parts.scheme and not parts.netloc:
            if not parts.path or not (html_path.parent / unquote(parts.path)).exists():
                errors.append(f"локальный путь не найден: {value}")
        failure = github_error(value)
        if failure:
            errors.append(failure + f": {value}")
    if patterns:
        try:
            # Do not echo matches, patterns or private values to logs.
            private = re.compile(patterns, re.I)
            if private.search(markdown) or private.search(content) or private.search(" ".join(page.texts)):
                errors.append("найдены персональные данные по ARTICLE_PRIVATE_PATTERNS (значения скрыты)")
        except re.error:
            errors.append("ARTICLE_PRIVATE_PATTERNS: неверное регулярное выражение")
    else:
        warnings.append("ARTICLE_PRIVATE_PATTERNS не задана: проверка персональных данных пропущена")
    return errors, warnings, words


def main() -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("html", nargs="?", type=Path, default=build.ROOT / "index.html")
    cli.add_argument("--source", type=Path)
    args = cli.parse_args()
    source = args.source or args.html.parent / "article.ru.md"
    try:
        errors, warnings, words = check(args.html, source, os.environ.get("ARTICLE_PRIVATE_PATTERNS"))
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Слов основного текста: {words}")
    for warning in warnings:
        print("WARNING: " + warning)
    for error in errors:
        print("ERROR: " + error, file=sys.stderr)
    print(f"Проверка: {'FAIL' if errors else 'OK'} ({len(errors)} ошибок)")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
