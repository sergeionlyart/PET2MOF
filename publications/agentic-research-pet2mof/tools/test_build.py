"""Offline behavioural tests, runnable under python -I -m pytest tools/test_build.py.

All temporary files stay under tools/; no repository-wide test setup is loaded.
"""
import csv
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


b = load("t051_build", "build.py")
c = load("t051_check", "check.py")
META = json.loads((HERE / "sample.metadata.json").read_text(encoding="utf-8"))


class BuildTests(unittest.TestCase):
    def render(self, source):
        return b.render(b.parse(source), META)

    def test_all_supported_elements(self):
        page = self.render((HERE / "sample.ru.md").read_text(encoding="utf-8"))
        for marker in ("<strong>", "<em>", "<code>", "<blockquote>", "<ul>", "<ol>",
                       "<thead>", "<tbody>", "<figure>", "<figcaption>", "<hr>", "<details", "<summary>"):
            self.assertIn(marker, page)
        self.assertIn('&lt;literal&gt; **не разбирать** [x](javascript:x)', page)
        parser = c.Page(); parser.feed(page)
        self.assertEqual(parser.h1, 1)
        self.assertFalse(parser.errors)
        self.assertFalse(parser.stack)
        self.assertEqual(len(parser.ids), len(set(parser.ids)))

    def test_unsupported_dialect_fails_with_line(self):
        bad = ["<div>x</div>", "текст <script>alert(1)</script>", "  - вложено", "- [x] task",
               "Термин\n: определение", "Заголовок\n===", "Заголовок\n---", "#### нет",
               "## Заголовок {#custom}", "+ item", "* item", "1) item", "~~~py\nx\n~~~",
               "| A | B |\n| --- | --- |\n| x |", "[x](javascript:alert)",
               "[x](http://example.org)", "[x](//example.org)", "![alt](https://example.org/a.png)\n*Рис. 1. x*",
               "![alt](assets/a.png)\n\n*Рис. 1. x*", "![ ](assets/a.png)\n*Рис. 1. x*",
               "![alt](assets/../a.png)\n*Рис. 1. x*", "[x](x \"title\")", "_italics_", "~~strike~~",
               "**unclosed", "`unclosed", "[^missing]", "`````\nx\n`````", "```\nx",
               "> ## вложенный блок", "- outer\n  - inner", "[reference][id]", "![inline](assets/a.png) text"]
        for text in bad:
            with self.subTest(text=text), self.assertRaisesRegex(b.MarkdownError, r"строка \d+:"):
                b.parse("# Title\n\n" + text)

    def test_yaml_unique_scalar_keys(self):
        good = b.parse("---\na: 'it''s scalar'\nb: 42\n---\n# Title")
        self.assertEqual(good.frontmatter["a"], "it's scalar")
        for bad in ("a: 1\na: 2", "a: [1,2]", "a:\n  b: x", "a: &alias x", "a: |", "a: 'unclosed"):
            with self.subTest(bad=bad), self.assertRaises(b.MarkdownError):
                b.parse("---\n" + bad + "\n---\n# Title")
        with self.assertRaisesRegex(b.MarkdownError, "незакрытый YAML"):
            b.parse("---\na: x\n# Title")

    def test_exactly_one_h1(self):
        for text in ("## Title", "# A\n\n# B", "before\n\n# Title"):
            with self.subTest(text=text), self.assertRaises(b.MarkdownError):
                b.parse(text)

    def test_deterministic_unicode_ids_and_collisions(self):
        text = "# T\n\n## Раздел\n\n## Раздел\n\n## Раздел-2\n\n## fn-1\n\nСноска[^1].\n\n[^1]: Текст"
        doc = b.parse(text)
        self.assertEqual([v.anchor for v in doc.blocks if v.kind == "heading"], ["t", "раздел", "раздел-2", "раздел-2-2", "fn-1-2"])
        self.assertEqual(b.render(doc, META), b.render(doc, META))

    def test_details_end_at_next_h2_and_main_count(self):
        text = "# Title\n\n## Main\n\nOne two.\n\n```\nnot counted words\n```\n\n| A |\n| --- |\n| excluded words |\n\n## Приложение A\n\n### Prompt\n\nHidden body.\n\n### More\n\nSecond.\n\n## End\n\nAfter."
        doc = b.parse(text)
        self.assertEqual(b.word_count(doc), 4)
        page = b.render(doc, META)
        self.assertEqual(page.count("<details "), 2)
        self.assertIn('</details>\n</section>\n<section><h2 id="end">', page)
        self.assertIn("beforeprint", page)
        self.assertIn("@media print", page)

    def test_repeated_footnotes_and_backlinks(self):
        page = self.render("# Title\n\nOne[^x], two[^x].\n\n[^x]: Note")
        self.assertIn('href="#fnref-x"', page)
        self.assertIn('href="#fnref-x-2"', page)
        with self.assertRaises(b.MarkdownError):
            b.parse("# T\n\n[^x]: one\n[^x]: two")

    def test_metadata_is_escaped_and_required(self):
        doc = b.parse("# T")
        meta = dict(META, subtitle='<script src="https://evil.invalid"></script>')
        page = b.render(doc, meta)
        self.assertIn("&lt;script src=", page)
        with self.assertRaisesRegex(ValueError, "author"):
            b.render(doc, dict(META, author=""))

    def test_plain_scientific_punctuation_and_precise_line_numbers(self):
        page = self.render("# T\n\n[S100], G_PET_value ∈ [1.063; 1.128], q < 1.10 и q>0.")
        self.assertIn("[1.063; 1.128]", page)
        self.assertIn("q &lt; 1.10", page)
        with self.assertRaisesRegex(b.MarkdownError, "строка 4:"):
            b.parse("# T\n\nnormal\n<script>bad</script>")

    def test_literal_code_does_not_count_as_css_loading(self):
        page = self.render('# T\n\n```css\n@import "example.css"; p{background:url(https://example.org/a)}\n```')
        parsed = c.Page(); parsed.feed(page)
        self.assertNotIn("@import", "".join(parsed.css))

    def test_nested_inline_emphasis(self):
        for text, expected in (("***both***", "<strong><em>both</em></strong>"),
                               ("**strong *em***", "<strong>strong <em>em</em></strong>"),
                               ("*em **strong***", "<em>em <strong>strong</strong></em>")):
            with self.subTest(text=text):
                self.assertIn(expected, self.render("# T\n\n" + text))


class CheckTests(unittest.TestCase):
    def check_page(self, content=None, source="# Title\n\n## Main\n\nText.", patterns=None):
        with tempfile.TemporaryDirectory(prefix="test-", dir=HERE) as dirname:
            root = Path(dirname)
            md = root / "article.ru.md"; md.write_text(source, encoding="utf-8")
            page = root / "index.html"
            page.write_text(content if content is not None else b.render(b.parse(source), META), encoding="utf-8")
            return c.check(page, md, patterns)

    def test_good_page_warns_about_length_and_privacy(self):
        errors,warnings,words = self.check_page()
        self.assertFalse(errors)
        self.assertEqual(words, 3)
        self.assertEqual(len(warnings), 2)

    def test_broken_dom_resources_anchors(self):
        base = b.render(b.parse("# T\n\n## Main\n\nText."), META)
        mutations = [base.replace("</article>", '<a href="#missing">x</a></article>'),
                     base.replace("</article>", '<a href="missing.txt">x</a></article>'),
                     base.replace("</article>", '<p id="main">duplicate</p></article>'),
                     base.replace("<h1 ", "<h2 ").replace("</h1>", "</h2>"),
                     base.replace("noindex,nofollow", "index,follow"),
                     base.replace("Черновик для согласования", "Final"),
                     base.replace("</article>", '<img src="assets/missing.png" alt=""></article>'),
                     base.replace("</article>", '<figure><img src="assets/a.png" alt="x"></figure></article>')]
        for content in mutations:
            with self.subTest(content=content[:30]):
                self.assertTrue(self.check_page(content)[0])

    def test_external_loads_and_embeds_fail(self):
        base = b.render(b.parse("# T"), META)
        for injection in ('<script src="assets/a.js"></script>', '<link rel="stylesheet" href="https://evil.invalid/a.css">',
                          '<img src="https://evil.invalid/a.png" alt="x">', '<iframe></iframe>', '<form></form>',
                          '<style>@import "evil.css";</style>', '<style>p{background:url(https://evil.invalid/a)}</style>',
                          '<style>p{background:url(//evil.invalid/a)}</style>', '<base href="https://evil.invalid/">',
                          '<img src="assets/a.png" srcset="https://evil.invalid/a.png" alt="x">'):
            with self.subTest(injection=injection):
                self.assertTrue(self.check_page(base.replace("</article>", injection + "</article>"))[0])

    def test_markdown_checked_even_if_html_valid(self):
        page = b.render(b.parse("# T"), META)
        self.assertTrue(any("Markdown" in e for e in self.check_page(page, "# T\n\n<raw>")[0]))

    def test_private_patterns_no_value_leak(self):
        errors,_,_ = self.check_page(source="# Title\n\nprivate-example-123", patterns="private-example-123|another")
        self.assertTrue(errors)
        self.assertNotIn("private-example-123", " ".join(errors))
        self.assertTrue(self.check_page(patterns="(")[0])

    def test_fixed_github_shas_and_paths(self):
        base = "https://github.com/sergeionlyart/PET2MOF/"
        for sha in c.SHAS:
            self.assertIsNone(c.github_error(base + f"blob/{sha}/AGENTS.md"))
            self.assertIsNone(c.github_error(base + f"tree/{sha}/docs"))
        for suffix in ("blob/main/AGENTS.md", f"blob/{c.SHAS[0][:7]}/AGENTS.md", f"blob/{c.SHAS[0]}/missing.txt",
                       f"tree/{c.SHAS[0]}/AGENTS.md", f"blob/{c.SHAS[0]}/docs", f"blob/{c.SHAS[0]}/../AGENTS.md"):
            with self.subTest(suffix=suffix):
                self.assertIsNotNone(c.github_error(base + suffix))


class AssetTests(unittest.TestCase):
    def test_complete_manifest_and_formats(self):
        pub = HERE.parent
        path = pub / "evidence/assets_manifest.csv"
        if not path.exists():
            self.skipTest("Run make_figures.py before asset checks")
        with path.open(encoding="utf-8") as handle:
            records = list(csv.DictReader(handle))
        self.assertEqual(len(records), 14)
        self.assertEqual({int(r["figure_no"]) for r in records}, set(range(1,8)))
        self.assertEqual(len({r["asset_id"] for r in records}), 14)
        for row in records:
            with self.subTest(file=row["file"]):
                self.assertTrue(all(row.values()))
                asset = pub / row["file"]
                raw = asset.read_bytes()
                if asset.suffix == ".png":
                    self.assertGreaterEqual(struct.unpack(">II", raw[16:24])[0], 1600)
                    self.assertLessEqual(len(raw), 10 * 1024**2)
                else:
                    self.assertIn("<text", raw.decode("utf-8"))
                    self.assertNotIn("<image", raw.decode("utf-8"))

    def test_numeric_evidence_saved(self):
        path = HERE / "figure_checks.json"
        if not path.exists():
            self.skipTest("Run make_figures.py first")
        checks = json.loads(path.read_text(encoding="utf-8"))["figures"]
        self.assertAlmostEqual(checks["fig04_task002_dry"]["evidence"]["S2-C72"]["q"], 3.26)
        item = checks["fig07_before_after"]["evidence"]
        self.assertAlmostEqual(item["before"]["G_PET_at_k095"], 1.0666284983362404)
        self.assertEqual(item["after"]["outward_interval"], [1.063, 1.128])
        self.assertLess(item["after"]["A"], 1.10)
        self.assertGreater(item["after"]["B"], 1.10)


if __name__ == "__main__":
    unittest.main()
