import io
import json
import logging
import sys
import types
import uuid
from concurrent.futures import ProcessPoolExecutor
from decimal import Decimal

import pytest

from pet2mof.ocr import adapter
from pet2mof.ocr.cache import RawCache, cache_key, sanitize, sha256_file
from pet2mof.ocr.config import ALLOWLIST, Config
from pet2mof.ocr.ledger import BudgetStop, Ledger
from pet2mof.ocr.local import extract_local, quality_metrics, selected_pdf
from pet2mof.ocr.security import RedactingFilter, Redactor, Secret

pytestmark = pytest.mark.ocr


def configure(tmp_path, **changes):
    values = dict(OCR_PROVIDER="mistral", OCR_EXTERNAL_ENABLED="true", OCR_BUDGET_USD="10",
                  OCR_PAGE_LIMIT="10", OCR_PRICE_USD_PER_PAGE="0.1", MISTRAL_API_KEY="TESTSECRET-" + str(uuid.uuid4()),
                  MISTRAL_OCR_MODEL="fixed-2026")
    values.update(changes)
    (tmp_path / ".env").write_text("\n".join(f"{key}={value}" for key, value in values.items()))
    return values


def test_no_env_no_environment_import(tmp_path, monkeypatch, pdf):
    monkeypatch.setenv("OCR_PROVIDER", "mistral")
    monkeypatch.setenv("OCR_EXTERNAL_ENABLED", "true")
    client = adapter.OCRAdapter(tmp_path)
    assert client.readiness() == dict(env_file="absent", provider="local", external_allowed=False,
                                     reason="env_absent", mistral_key="absent", google_credentials="absent")
    result = client.extract(pdf, [2], purpose="offline check")
    assert len(result["pages"]) == 1 and "Second page" in result["pages"][0]["text"]
    assert result["pages"][0]["quality"]["signal_only"]
    with pytest.raises(adapter.ExternalDenied):
        client.extract(pdf, [1], mode="external", purpose="denied")
    assert "google.cloud.documentai" not in sys.modules


@pytest.mark.parametrize("changes", [
    {"OCR_BUDGET_USD": "0"}, {"OCR_PAGE_LIMIT": "0"}, {"OCR_PAGE_LIMIT": "1.5"},
    {"OCR_PRICE_USD_PER_PAGE": ""}, {"OCR_PRICE_USD_PER_PAGE": "0"},
    {"OCR_PRICE_USD_PER_PAGE": "NaN"}, {"OCR_BUDGET_USD": "Infinity"},
    {"OCR_EXTERNAL_ENABLED": "false"}, {"MISTRAL_API_KEY": ""}, {"MISTRAL_OCR_MODEL": ""},
    {"OCR_PROVIDER": "arbitrary-secret"}, {"OCR_PAGE_LIMIT": "-1"},
])
def test_closed_by_default(tmp_path, changes):
    configure(tmp_path, **changes)
    assert not Config(tmp_path).readiness()["external_allowed"]


def test_foreign_keys_discarded_and_secrets_wrapped(tmp_path, monkeypatch):
    marker = "TESTSECRET-" + str(uuid.uuid4())
    configure(tmp_path, OPENAI_API_KEY=marker, ANTHROPIC_API_KEY=marker, STRIPE_API_KEY=marker)
    monkeypatch.setenv("MISTRAL_API_KEY", marker)
    config = Config(tmp_path)
    assert set(config._values) <= ALLOWLIST
    assert marker not in repr(config._values) + repr(config) + json.dumps(config.readiness())
    assert marker not in config.redactor._secrets
    assert str(Secret(marker)) == repr(Secret(marker)) == "***"
    assert config.readiness()["external_allowed"]
    with pytest.raises(KeyError):
        config.value("OPENAI_API_KEY")


def test_redact_logs_exceptions_and_sanitize(tmp_path):
    values = configure(tmp_path)
    marker = values["MISTRAL_API_KEY"]
    config = Config(tmp_path)
    output = io.StringIO()
    handler = logging.StreamHandler(output)
    handler.addFilter(RedactingFilter(config.redactor))
    log = logging.Logger("offline-redaction")
    log.addHandler(handler)
    key_name = "private" + "_key"
    authorization = "Bearer" + " " + marker
    try:
        raise ValueError(marker)
    except ValueError:
        log.exception('payload %s %s "%s": "%s"', marker, authorization, key_name, marker)
    assert marker not in output.getvalue()
    raw = {"text": marker + " https://example.org/doc?signature=" + marker,
           "headers": {"Authorization": authorization}, key_name: marker,
           "nested": {"client_email": "test@example.org", "project_id": marker, "value": authorization}}
    cleaned = sanitize(raw, redactor=config.redactor)
    assert marker not in json.dumps(cleaned)
    assert "signature=" not in json.dumps(cleaned)
    assert "test@example.org" not in json.dumps(cleaned)
    assert raw[key_name] == marker
    client = adapter.OCRAdapter(tmp_path)
    output.truncate(0)
    output.seek(0)
    client.logger.addHandler(logging.StreamHandler(output))
    client.logger.error("credential %s", marker)
    assert marker not in output.getvalue()


def test_cache_key_complete_and_raw_write_once(tmp_path, pdf):
    key = cache_key(pdf, [1], engine="local", version="1")
    assert key != cache_key(pdf, [2], engine="local", version="1")
    assert key != cache_key(pdf, [1], engine="local", version="2")
    assert key != cache_key(pdf, [1], engine="local", version="1", regions=[[0, 0, 10, 10]])
    assert key != cache_key(pdf, [1], engine="local", version="1", transformations=["crop"])
    assert key != cache_key(pdf, [1], engine="local", version="1", params={"dpi": 300})
    cache = RawCache(tmp_path)
    path = cache.write_once(key, {"raw": "unchanged"})
    assert path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        cache.write_once(key, {"raw": "modified"})
    assert cache.read(key) == {"raw": "unchanged"}
    with pytest.raises(ValueError):
        cache.path("../escape")


def ledger(tmp_path, **kw):
    return Ledger(tmp_path, **(dict(budget="0.3", page_limit=3, price="0.1", provider="mistral") | kw))


def test_ledger_reserve_release_retry_limit(tmp_path):
    book = ledger(tmp_path)
    first = book.reserve(1)
    book.release(first)
    for _ in range(3):
        token = book.reserve(1)
        book.confirm(token)
    with pytest.raises(BudgetStop):
        book.reserve(1)
    assert book.snapshot()["blocked"] == "limit"
    assert sum(Decimal(a["cost"]) for a in book.snapshot()["attempts"].values() if a["status"] == "charged") == Decimal("0.3")
    with pytest.raises(BudgetStop):
        book.release(token)


def _reserve_worker(root):
    try:
        ledger(root, budget="0.1", page_limit=1).reserve(1)
        return 1
    except BudgetStop:
        return 0


def test_ledger_parallel_processes(tmp_path):
    with ProcessPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(_reserve_worker, [str(tmp_path)] * 4))
    assert sum(results) == 1


@pytest.mark.parametrize("bad", ["0", "-0.1", "", "NaN", "Infinity"])
def test_ledger_unknown_price(tmp_path, bad):
    with pytest.raises(BudgetStop):
        ledger(tmp_path, price=bad)


def test_ledger_auth_stop_and_corrupt_state(tmp_path):
    book = ledger(tmp_path)
    book.stop()
    with pytest.raises(BudgetStop):
        book.reserve(1)
    book.path.write_text("{}")
    with pytest.raises(BudgetStop):
        book.reserve(1)


def test_selected_pages_only(pdf):
    import pymupdf
    payload, mapping = selected_pdf(pdf, [2, 1])
    with pymupdf.open(stream=payload, filetype="pdf") as doc:
        assert len(doc) == 2
        assert "Second page" in doc[0].get_text()
        assert "Private unselected" not in "".join(p.get_text() for p in doc)
    assert mapping == {"1": 2, "2": 1}
    for pages in ([0], [4], [1, 1], [], [True]):
        with pytest.raises(ValueError):
            selected_pdf(pdf, pages)


def test_local_metrics_and_optional_layout(pdf):
    import shutil
    metrics = quality_metrics("12\ufffd\x001", [(0, 0, 10, 10), (20, 0, 30, 10)])
    assert metrics["replacement_fraction"] == 0.2
    assert metrics["nonprintable_fraction"] == 0.2
    assert metrics["possible_mixed_columns"]
    if shutil.which("pdftotext"):
        result = extract_local(pdf, [1], method="pdftotext")
        assert "First page" in result["pages"][0]["text"]


def fake_requests(monkeypatch):
    # Adapters are exercised without installing optional dependencies or allowing sockets.
    monkeypatch.setitem(sys.modules, "requests", types.ModuleType("requests"))


def test_external_retries_charged_and_cache(tmp_path, pdf, monkeypatch):
    values = configure(tmp_path)
    fake_requests(monkeypatch)
    calls = []
    def provider(config, payload):
        calls.append(payload)
        if len(calls) <= 2:
            raise adapter.TransientError("not logged")
        return {"text": values["MISTRAL_API_KEY"] + " recognized"}, "fixed-2026"
    monkeypatch.setattr(adapter, "_mistral", provider)
    client = adapter.OCRAdapter(tmp_path)
    result = client.extract(pdf, [2], mode="external", purpose="test")
    assert len(calls) == 3 and values["MISTRAL_API_KEY"] not in json.dumps(result)
    assert len(ledger(tmp_path).snapshot()["attempts"]) == 3
    assert client.extract(pdf, [2], mode="external", purpose="repeat")["cache_key"] == result["cache_key"]
    assert len(calls) == 3


def test_external_auth_no_retry_no_fallback(tmp_path, pdf, monkeypatch):
    configure(tmp_path)
    fake_requests(monkeypatch)
    calls = []
    def provider(*args):
        calls.append(1)
        raise adapter.AuthorizationError("do not echo")
    monkeypatch.setattr(adapter, "_mistral", provider)
    client = adapter.OCRAdapter(tmp_path)
    with pytest.raises(adapter.AuthorizationError):
        client.extract(pdf, [1], mode="external", purpose="test")
    with pytest.raises(BudgetStop):
        client.extract(pdf, [1], mode="external", purpose="test")
    assert len(calls) == 1


def test_latest_must_resolve_and_retain_raw(tmp_path, pdf, monkeypatch):
    configure(tmp_path, MISTRAL_OCR_MODEL="ocr-latest")
    fake_requests(monkeypatch)
    monkeypatch.setattr(adapter, "_mistral", lambda *args: ({"text": "unversioned"}, ""))
    with pytest.raises(adapter.ProviderError, match="actual engine version"):
        adapter.OCRAdapter(tmp_path).extract(pdf, [1], mode="external", purpose="test")
    assert len(list((tmp_path / "private/ocr_cache/raw").glob("*.json"))) == 1


def test_retry_cap_budget_before_network(tmp_path, pdf, monkeypatch):
    configure(tmp_path, OCR_BUDGET_USD="0.2")
    fake_requests(monkeypatch)
    calls = []
    def failing(*args):
        calls.append(1)
        raise adapter.TransientError("timeout")
    monkeypatch.setattr(adapter, "_mistral", failing)
    client = adapter.OCRAdapter(tmp_path)
    with pytest.raises(BudgetStop):
        client.extract(pdf, [1], mode="external", purpose="test")
    assert len(calls) == 2
    state = ledger(tmp_path).snapshot()
    assert all(a["status"] == "charged" for a in state["attempts"].values())
    with pytest.raises(ValueError):
        client.extract(pdf, [1], mode="external", purpose="test", retries=3)


def test_retries_exhausted_exactly_three_attempts(tmp_path, pdf, monkeypatch):
    configure(tmp_path)
    fake_requests(monkeypatch)
    def failing(*args):
        raise adapter.TransientError("timeout")
    monkeypatch.setattr(adapter, "_mistral", failing)
    with pytest.raises(adapter.ProviderError, match="retries exhausted"):
        adapter.OCRAdapter(tmp_path).extract(pdf, [1], mode="external", purpose="test")
    assert len(ledger(tmp_path).snapshot()["attempts"]) == 3


def test_external_key_keeps_submitted_input_hash(tmp_path, pdf, monkeypatch):
    configure(tmp_path)
    fake_requests(monkeypatch)
    original_digest = sha256_file(pdf)
    def provider(*args):
        pdf.write_bytes(b"changed after transmission")
        return {"text": "recognized"}, "fixed-2026"
    monkeypatch.setattr(adapter, "_mistral", provider)
    result = adapter.OCRAdapter(tmp_path).extract(pdf, [1], mode="external", purpose="test")
    assert result["cache_key"] == cache_key(pdf, [1], engine="mistral", version="fixed-2026",
        params={"mime_type": "application/pdf", "selected_pages_only": True}, input_sha256=original_digest)


def test_changed_input_before_transmission_never_spends(tmp_path, pdf, monkeypatch):
    configure(tmp_path)
    original = adapter.selected_pdf
    def selection(path, pages):
        result = original(path, pages)
        pdf.write_bytes(b"changed during selection")
        return result
    monkeypatch.setattr(adapter, "selected_pdf", selection)
    with pytest.raises(ValueError, match="input changed"):
        adapter.OCRAdapter(tmp_path).extract(pdf, [1], mode="external", purpose="test")
    assert not (tmp_path / "private/ocr_cache/ledger.json").exists()


def test_latest_actual_version_and_no_alias_cache(tmp_path, pdf, monkeypatch):
    configure(tmp_path, MISTRAL_OCR_MODEL="ocr-latest")
    fake_requests(monkeypatch)
    calls = []
    def provider(*args):
        calls.append(1)
        return {"text": "recognized", "model": "fixed-2026"}, "fixed-2026"
    monkeypatch.setattr(adapter, "_mistral", provider)
    client = adapter.OCRAdapter(tmp_path)
    first = client.extract(pdf, [1], mode="external", purpose="test")
    second = client.extract(pdf, [1], mode="external", purpose="test")
    assert first["version"] == second["version"] == "fixed-2026"
    assert first["cache_key"] != second["cache_key"]
    assert len(calls) == 2


@pytest.mark.parametrize("status,error", [(200, None), (302, adapter.ProviderError),
    (401, adapter.AuthorizationError), (403, adapter.AuthorizationError), (429, adapter.TransientError), (500, adapter.TransientError)])
def test_mistral_transport_contract(tmp_path, monkeypatch, status, error):
    configure(tmp_path)
    captured = {}
    class RequestException(Exception):
        pass
    class Session:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            captured["trust_env"] = self.trust_env
        def post(self, url, **kwargs):
            captured.update(url=url, **kwargs)
            return types.SimpleNamespace(status_code=status, json=lambda: {"model": "fixed-2026", "text": "recognized"})
    fake = types.SimpleNamespace(Session=Session, RequestException=RequestException)
    monkeypatch.setitem(sys.modules, "requests", fake)
    if error:
        with pytest.raises(error):
            adapter._mistral(Config(tmp_path), b"selected-pdf")
    else:
        assert adapter._mistral(Config(tmp_path), b"selected-pdf")[1] == "fixed-2026"
    assert captured["trust_env"] is False
    assert captured["allow_redirects"] is False
    assert captured["timeout"] == 60
    assert captured["url"] == "https://api.mistral.ai/v1/ocr"


def test_tesseract_selected_page_300dpi(pdf, tmp_path):
    import shutil
    if not shutil.which("tesseract"):
        pytest.skip("optional local executable not installed")
    result = extract_local(pdf, [1], method="tesseract", workdir=tmp_path)
    assert len(result["pages"]) == 1
    assert result["params"]["dpi"] == 300
    assert "12.5" in result["pages"][0]["text"]


def fake_google(monkeypatch, captured):
    google = types.ModuleType("google")
    auth = types.ModuleType("google.auth")
    oauth = types.ModuleType("google.oauth2")
    service = types.ModuleType("google.oauth2.service_account")
    class Credentials:
        @staticmethod
        def from_service_account_info(info, scopes):
            captured.update(info=info, scopes=scopes)
            return object()
    service.Credentials = Credentials
    def default(**kwargs):
        captured.update(kwargs)
        return object(), "demo-project"
    auth.default = default
    google.auth = auth
    for name, module in (("google", google), ("google.auth", auth), ("google.oauth2", oauth), ("google.oauth2.service_account", service)):
        monkeypatch.setitem(sys.modules, name, module)


def test_google_credentials_in_memory_and_adc(tmp_path, monkeypatch):
    captured = {}
    fake_google(monkeypatch, captured)
    key = "private" + "_key"
    marker = "TESTSECRET-" + str(uuid.uuid4())
    info = dict(type="service_account", project_id="demo-project", token_uri="https://oauth2.googleapis.com/token")
    info[key] = marker
    changes = dict(OCR_PROVIDER="google_docai", GOOGLE_CLOUD_PROJECT="demo-project",
                   GOOGLE_DOCUMENT_AI_LOCATION="eu", GOOGLE_DOCUMENT_AI_PROCESSOR_ID="demo",
                   GOOGLE_DOCUMENT_AI_PROCESSOR_VERSION="fixed", GOOGLE_SERVICE_ACCOUNT_JSON=json.dumps(info))
    configure(tmp_path, **changes)
    config = Config(tmp_path)
    assert config.readiness()["google_credentials"] == "service_account_json"
    assert captured["scopes"] == ["https://www.googleapis.com/auth/cloud-platform"]
    assert marker not in json.dumps(sanitize({"text": marker}, redactor=config.redactor))
    assert list(tmp_path.iterdir()) == [tmp_path / ".env"]
    configure(tmp_path, **(changes | {"GOOGLE_SERVICE_ACCOUNT_JSON": ""}))
    assert Config(tmp_path).readiness()["google_credentials"] == "adc"
    with pytest.raises(RuntimeError):
        captured["request"]()


@pytest.mark.parametrize("change", [{"type": "authorized_user"}, {"project_id": "other"}, {"token_uri": "https://evil.invalid/token"}])
def test_google_invalid_account_never_constructed(tmp_path, monkeypatch, change):
    captured = {}
    fake_google(monkeypatch, captured)
    info = dict(type="service_account", project_id="demo-project", token_uri="https://oauth2.googleapis.com/token") | change
    configure(tmp_path, OCR_PROVIDER="google_docai", GOOGLE_CLOUD_PROJECT="demo-project",
              GOOGLE_DOCUMENT_AI_LOCATION="eu", GOOGLE_DOCUMENT_AI_PROCESSOR_ID="demo",
              GOOGLE_DOCUMENT_AI_PROCESSOR_VERSION="fixed", GOOGLE_SERVICE_ACCOUNT_JSON=json.dumps(info))
    assert not Config(tmp_path).readiness()["external_allowed"]
    assert not captured


@pytest.mark.parametrize("auth_failure", [False, True])
def test_google_transport_pinned_endpoint_no_sdk_retry(tmp_path, monkeypatch, auth_failure):
    configure(tmp_path, OCR_PROVIDER="google_docai", GOOGLE_CLOUD_PROJECT="demo-project",
              GOOGLE_DOCUMENT_AI_LOCATION="eu", GOOGLE_DOCUMENT_AI_PROCESSOR_ID="demo",
              GOOGLE_DOCUMENT_AI_PROCESSOR_VERSION="fixed")
    config = Config(tmp_path)
    monkeypatch.setattr(config, "google_credentials", lambda: object())
    captured = {}
    exceptions = types.SimpleNamespace(**{
        name: type(name, (Exception,), {}) for name in
        ("Unauthenticated", "PermissionDenied", "ServiceUnavailable", "DeadlineExceeded", "TooManyRequests")
    })
    class RefreshError(Exception):
        pass
    class Client:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.transport = types.SimpleNamespace(close=lambda: captured.update(closed=True))
        def process_document(self, **kwargs):
            captured.update(kwargs)
            if auth_failure:
                raise RefreshError("not logged")
            return {"document": {"text": "recognized"}}
    docai = types.SimpleNamespace(DocumentProcessorServiceClient=Client,
        RawDocument=lambda **kwargs: kwargs, ProcessRequest=lambda **kwargs: kwargs,
        ProcessResponse=types.SimpleNamespace(to_dict=lambda value: value))
    cloud = types.ModuleType("google.cloud")
    cloud.documentai = docai
    api_core = types.ModuleType("google.api_core")
    api_core.exceptions = exceptions
    auth_exceptions = types.ModuleType("google.auth.exceptions")
    auth_exceptions.RefreshError = RefreshError
    monkeypatch.setitem(sys.modules, "google", types.ModuleType("google"))
    monkeypatch.setitem(sys.modules, "google.cloud", cloud)
    monkeypatch.setitem(sys.modules, "google.api_core", api_core)
    monkeypatch.setitem(sys.modules, "google.auth", types.ModuleType("google.auth"))
    monkeypatch.setitem(sys.modules, "google.auth.exceptions", auth_exceptions)
    if auth_failure:
        with pytest.raises(adapter.AuthorizationError):
            adapter._google(config, b"only-selected-pages")
    else:
        response, version = adapter._google(config, b"only-selected-pages")
        assert version == "fixed" and response["document"]["text"] == "recognized"
    assert captured["client_options"]["api_endpoint"] == "eu-documentai.googleapis.com"
    assert captured["retry"] is None and captured["timeout"] == 60
    assert captured["request"]["raw_document"]["content"] == b"only-selected-pages"
    assert captured["request"]["name"].endswith("/processorVersions/fixed")
    assert captured["closed"]
