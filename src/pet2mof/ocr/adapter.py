"""Only entry point for configured OCR; no provider fallback or implicit spending."""

import base64
import logging
import re
from pathlib import Path

from .cache import RawCache, cache_key, sanitize, sha256_file
from .config import Config
from .ledger import Ledger
from .local import extract_local, selected_pdf
from .security import RedactingFilter

logger = logging.getLogger(__name__)


class ExternalDenied(RuntimeError):
    pass


class AuthorizationError(RuntimeError):
    pass


class ProviderError(RuntimeError):
    pass


class TransientError(ProviderError):
    pass


def _mistral(config, payload):
    import requests

    body = {
        "model": config.value("MISTRAL_OCR_MODEL"),
        "document": {"type": "document_url", "document_url": "data:application/pdf;base64," + base64.b64encode(payload).decode("ascii")},
    }
    try:
        with requests.Session() as session:
            session.trust_env = False
            response = session.post(
                "https://api.mistral.ai/v1/ocr", json=body,
                headers={"Authorization": "Bearer" + " " + config.value("MISTRAL_API_KEY")},
                timeout=60, allow_redirects=False,
            )
            if response.status_code in {401, 403}:
                raise AuthorizationError("OCR authorization failed")
            if response.status_code == 429 or response.status_code >= 500:
                raise TransientError("OCR temporarily unavailable")
            if response.status_code != 200:
                raise ProviderError("OCR request rejected")
            data = response.json()
            return data, data.get("model", "")
    except requests.RequestException:
        raise TransientError("OCR transport failed") from None


def _google(config, payload):
    from google.api_core import exceptions
    from google.auth.exceptions import RefreshError
    from google.cloud import documentai

    location = config.value("GOOGLE_DOCUMENT_AI_LOCATION")
    components = [config.value(key) for key in (
        "GOOGLE_CLOUD_PROJECT", "GOOGLE_DOCUMENT_AI_PROCESSOR_ID", "GOOGLE_DOCUMENT_AI_PROCESSOR_VERSION",
    )]
    if not re.fullmatch(r"[a-z][a-z0-9-]*", location) or any(not re.fullmatch(r"[A-Za-z0-9_.-]+", value) for value in components):
        raise ProviderError("invalid processor configuration")
    client = documentai.DocumentProcessorServiceClient(
        credentials=config.google_credentials(),
        client_options={"api_endpoint": f"{location}-documentai.googleapis.com"},
    )
    project, processor, version = components
    name = f"projects/{project}/locations/{location}/processors/{processor}/processorVersions/{version}"
    request = documentai.ProcessRequest(
        name=name, raw_document=documentai.RawDocument(content=payload, mime_type="application/pdf"),
        skip_human_review=True,
    )
    try:
        response = client.process_document(request=request, retry=None, timeout=60)
        return documentai.ProcessResponse.to_dict(response), version
    except (exceptions.Unauthenticated, exceptions.PermissionDenied, RefreshError):
        raise AuthorizationError("OCR authorization failed") from None
    except (exceptions.ServiceUnavailable, exceptions.DeadlineExceeded, exceptions.TooManyRequests):
        raise TransientError("OCR temporarily unavailable") from None
    except Exception:
        raise ProviderError("OCR request failed") from None
    finally:
        try:
            client.transport.close()
        except Exception:
            pass  # Preserve the request's error classification, especially authorization.


class OCRAdapter:
    def __init__(self, root=None, *, env_path=None):
        self.config = Config(root, env_path=env_path)
        self.root = self.config.root
        self.cache = RawCache(self.root)
        self.log_filter = RedactingFilter(self.config.redactor)
        self.logger = logging.Logger(__name__ + ".session")
        self.logger.parent = logger
        self.logger.addFilter(self.log_filter)

    def readiness(self):
        return self.config.readiness()

    def extract(self, input_path, pages, mode="local", *, purpose, method="pymupdf", language="eng", retries=2):
        if not isinstance(purpose, str) or not purpose.strip():
            raise ValueError("extraction purpose required")
        if mode not in {"local", "external"}:
            raise ValueError("mode must be local or external")
        pages = list(pages)
        if mode == "local":
            input_digest = sha256_file(input_path)
            result = extract_local(input_path, pages, method=method, language=language, workdir=self.root)
            if sha256_file(input_path) != input_digest:
                raise ValueError("input changed during local extraction")
            key = cache_key(input_path, pages, engine=result["engine"], version=result["version"], params=result["params"], input_sha256=input_digest)
            try:
                raw_path = self.cache.write_once(key, result)
            except FileExistsError:
                raw_path = self.cache.path(key)
            self.logger.info("local OCR completed")
            return {**sanitize(result, redactor=self.config.redactor), "cache_key": key,
                    "input_sha256": input_digest, "raw_response_ref": str(raw_path.relative_to(self.root)),
                    "purpose": self.config.redactor.text(purpose)}
        if not self.readiness()["external_allowed"]:
            raise ExternalDenied("external OCR is not authorized")
        if type(retries) is not int or not 0 <= retries <= 2:
            raise ValueError("at most two retries allowed")
        config = self.config
        requested_version = config.value("MISTRAL_OCR_MODEL") if config.provider == "mistral" else config.value("GOOGLE_DOCUMENT_AI_PROCESSOR_VERSION")
        input_digest = sha256_file(input_path)
        payload, page_map = selected_pdf(input_path, pages)
        if sha256_file(input_path) != input_digest:
            raise ValueError("input changed during PDF selection")
        params = {"mime_type": "application/pdf", "selected_pages_only": True}
        # An alias cannot safely identify a cached engine version.
        alias = "latest" in requested_version.lower()
        key = cache_key(input_path, pages, engine=config.provider, version=requested_version, params=params, input_sha256=input_digest)
        if not alias and self.cache.path(key).exists():
            return self._public(self.cache.read(key), key, requested_version, page_map, purpose, input_digest)
        ledger = Ledger(self.root, budget=config.budget, page_limit=config.page_limit, price=config.price, provider=config.provider)
        provider = _mistral if config.provider == "mistral" else _google
        # Imports fail before budget reservation and before network use.
        try:
            if config.provider == "mistral":
                import requests  # noqa: F401
            else:
                from google.cloud import documentai  # noqa: F401
        except ImportError:
            raise ExternalDenied("install the ocr-cloud extra") from None
        for attempt in range(retries + 1):
            reservation = ledger.reserve(len(pages))
            try:
                raw, actual_version = provider(config, payload)
            except AuthorizationError:
                ledger.confirm(reservation)
                ledger.stop("authorization")
                raise AuthorizationError("OCR authorization failed; paid path stopped") from None
            except TransientError:
                ledger.confirm(reservation)
                if attempt == retries:
                    raise ProviderError("OCR retries exhausted") from None
                continue
            except Exception:
                ledger.confirm(reservation)
                raise ProviderError("OCR request failed; attempt charged") from None
            else:
                ledger.confirm(reservation)
                actual_version = actual_version or requested_version
                key = cache_key(input_path, pages, engine=config.provider, version=actual_version, params=params, input_sha256=input_digest)
                try:
                    self.cache.write_once(key, raw)
                except FileExistsError:
                    # Preserve the newly paid response as well, without overwriting the first.
                    alternate = cache_key(input_path, pages, engine=config.provider, version=actual_version,
                                          params={**params, "attempt": reservation}, input_sha256=input_digest)
                    self.cache.write_once(alternate, raw)
                    key = alternate
                if alias and (actual_version == requested_version or "latest" in actual_version.lower()):
                    raise ProviderError("actual engine version unavailable; raw retained, result unverified")
                return self._public(raw, key, actual_version, page_map, purpose, input_digest)

    def _public(self, raw, key, version, page_map, purpose, input_digest):
        return {"response": sanitize(raw, redactor=self.config.redactor), "cache_key": key,
                "input_sha256": input_digest,
                "engine": self.config.provider, "version": self.config.redactor.text(str(version)), "api_page_map": page_map,
                "raw_response_ref": str(self.cache.path(key).relative_to(self.root)),
                "purpose": self.config.redactor.text(purpose)}


def extract(input_path, pages, mode="local", *, purpose, root=None, **kwargs):
    return OCRAdapter(root).extract(input_path, pages, mode, purpose=purpose, **kwargs)


def readiness(root=None):
    return OCRAdapter(root).readiness()
