"""One-based PDF pages. Quality metrics are review signals, never acceptance."""

import shutil
import subprocess
import tempfile
from pathlib import Path


def validate_pages(pages, count):
    selected = list(pages)
    if not selected or len(set(selected)) != len(selected):
        raise ValueError("select distinct PDF pages")
    if any(type(page) is not int or page < 1 or page > count for page in selected):
        raise ValueError("PDF pages must be one-based and within document")
    return selected


def quality_metrics(text, blocks=()):
    count = max(1, len(text))
    columns = any(
        a[0] < b[0] and a[2] < b[0] and abs(a[1] - b[1]) < 20
        for a in blocks for b in blocks
    )
    return {
        "nonprintable_fraction": sum(not c.isprintable() and c not in "\n\t\r" for c in text) / count,
        "replacement_fraction": text.count("\ufffd") / count,
        "digit_fraction": sum(c.isdigit() for c in text) / count,
        "possible_mixed_columns": columns,
        "signal_only": True,
    }


def extract_local(input_path, pages, *, method="pymupdf", language="eng", workdir=None):
    import pymupdf

    if method not in {"pymupdf", "pdftotext", "tesseract"}:
        raise ValueError("unknown local engine")
    path = Path(input_path).resolve()
    with pymupdf.open(path) as document:
        selected = validate_pages(pages, len(document))
        result = []
        for number in selected:
            page = document[number - 1]
            original = page.get_text("text", sort=True)
            if method == "pymupdf":
                text = original
                version = pymupdf.VersionBind
            elif method == "pdftotext":
                binary = shutil.which("pdftotext")
                if not binary:
                    raise RuntimeError("pdftotext is not installed")
                run = subprocess.run([binary, "-layout", "-f", str(number), "-l", str(number), str(path), "-"], capture_output=True, check=True)
                text = run.stdout.decode("utf-8")
                version_run = subprocess.run([binary, "-v"], capture_output=True, check=True)
                version = (version_run.stderr or version_run.stdout).decode().splitlines()[0]
            else:
                binary = "/opt/homebrew/bin/tesseract"
                if not Path(binary).is_file():
                    binary = shutil.which("tesseract")
                if not binary:
                    raise RuntimeError("tesseract is not installed")
                with tempfile.TemporaryDirectory(dir=workdir) as directory:
                    image = Path(directory) / "page.png"
                    page.get_pixmap(dpi=300).save(image)
                    run = subprocess.run([binary, str(image), "stdout", "-l", language, "--dpi", "300"], capture_output=True, check=True)
                    text = run.stdout.decode("utf-8")
                version = subprocess.run([binary, "--version"], capture_output=True, check=True).stdout.decode().splitlines()[0]
            result.append({"pdf_page": number, "api_page": len(result) + 1, "text": text,
                           "quality": quality_metrics(original, page.get_text("blocks"))})
    return {"engine": method, "version": version, "pages": result,
            "params": {"dpi": 300, "language": language} if method == "tesseract" else {}}


def selected_pdf(input_path, pages):
    """Cloud payload contains ONLY the explicitly selected pages, in supplied order."""
    import pymupdf

    with pymupdf.open(input_path) as source, pymupdf.open() as target:
        selected = validate_pages(pages, len(source))
        for page in selected:
            target.insert_pdf(source, from_page=page - 1, to_page=page - 1)
        return target.tobytes(), {str(i + 1): page for i, page in enumerate(selected)}
