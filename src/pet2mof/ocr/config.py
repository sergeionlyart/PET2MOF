"""Root dotenv parser used by the adapter, without environment import/export."""

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .security import Redactor, Secret

ALLOWLIST = frozenset({
    "OCR_PROVIDER", "OCR_EXTERNAL_ENABLED", "OCR_BUDGET_USD", "OCR_PAGE_LIMIT",
    "OCR_PRICE_USD_PER_PAGE", "MISTRAL_API_KEY", "MISTRAL_OCR_MODEL",
    "GOOGLE_CLOUD_PROJECT", "GOOGLE_DOCUMENT_AI_LOCATION",
    "GOOGLE_DOCUMENT_AI_PROCESSOR_ID", "GOOGLE_DOCUMENT_AI_PROCESSOR_VERSION",
    "GOOGLE_SERVICE_ACCOUNT_JSON",
})
CLOUD_SCOPE = "https://www.googleapis.com/auth/cloud-platform"


def repository_root():
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file() and (parent / ".git").exists():
            return parent
    raise ValueError("repository root not found; supply root explicitly")


class Config:
    def __init__(self, root=None, *, env_path=None):
        self.root = Path(root).resolve() if root is not None else repository_root()
        path = Path(env_path) if env_path is not None else self.root / ".env"
        self.env_present = path.is_file()
        self._values = {}
        self.redactor = Redactor()
        self._credentials = None
        self._google_kind = "absent"
        if self.env_present:
            with path.open(encoding="utf-8") as stream:
                for line in stream:
                    # Do not split, decode, retain or export values of other services.
                    key = line.split("=", 1)[0].strip()
                    if key not in ALLOWLIST or "=" not in line:
                        continue
                    value = line.partition("=")[2].strip()
                    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                        if value[0] == '"':
                            try:
                                value = json.loads(value)
                            except ValueError:
                                value = value[1:-1]
                        else:
                            value = value[1:-1]
                    self._values[key] = Secret(value)
                    if key in {"MISTRAL_API_KEY", "GOOGLE_SERVICE_ACCOUNT_JSON"} or key.startswith("GOOGLE_"):
                        self.redactor.add(value)
        self.provider = self.value("OCR_PROVIDER")
        if self.provider not in {"mistral", "google_docai"}:
            self.provider = "local"
        self.budget = self.number("OCR_BUDGET_USD")
        self.price = self.number("OCR_PRICE_USD_PER_PAGE")
        page_limit = self.number("OCR_PAGE_LIMIT")
        self.page_limit = int(page_limit) if page_limit <= 1_000_000_000 and page_limit == page_limit.to_integral_value() else 0

    def __repr__(self):
        return "Config(***)"

    def value(self, key):
        if key not in ALLOWLIST:
            raise KeyError("configuration key is not allowed")
        return self._values[key].reveal() if key in self._values else ""

    def number(self, key):
        try:
            value = Decimal(self.value(key))
            return value if value.is_finite() and value > 0 else Decimal(0)
        except (InvalidOperation, ValueError):
            return Decimal(0)

    def _base_reason(self):
        if not self.env_present:
            return "env_absent"
        if self.value("OCR_EXTERNAL_ENABLED").lower() != "true":
            return "external_disabled"
        if self.provider == "local":
            return "local_provider"
        if self.budget <= 0 or self.page_limit <= 0:
            return "limits_missing_or_zero"
        if self.price <= 0:
            return "price_unknown_or_zero"
        return None

    def google_credentials(self):
        if self._credentials is not None:
            return self._credentials
        try:
            raw = self.value("GOOGLE_SERVICE_ACCOUNT_JSON")
            project = self.value("GOOGLE_CLOUD_PROJECT")
            if raw:
                info = json.loads(raw)
                if not isinstance(info, dict) or info.get("type") != "service_account":
                    raise ValueError
                if not project or info.get("project_id") != project:
                    raise ValueError
                if info.get("token_uri") != "https://oauth2.googleapis.com/token":
                    raise ValueError
                for value in info.values():
                    self.redactor.add(value)
                from google.oauth2.service_account import Credentials
                self._credentials = Credentials.from_service_account_info(info, scopes=[CLOUD_SCOPE])
                self._google_kind = "service_account_json"
            else:
                import google.auth

                def no_discovery_network(*args, **kwargs):
                    raise RuntimeError("network discovery disabled")

                credentials, adc_project = google.auth.default(scopes=[CLOUD_SCOPE], request=no_discovery_network)
                if not credentials or (adc_project and adc_project != project):
                    raise ValueError
                self._credentials = credentials
                self._google_kind = "adc"
            return self._credentials
        except Exception:
            raise ValueError("google authorization unavailable") from None

    def readiness(self):
        reason = self._base_reason()
        if reason is None and self.provider == "mistral":
            if not self.value("MISTRAL_API_KEY"):
                reason = "authorization_missing"
            elif not self.value("MISTRAL_OCR_MODEL"):
                reason = "model_missing"
        if reason is None and self.provider == "google_docai":
            if not all(self.value(key) for key in (
                "GOOGLE_CLOUD_PROJECT", "GOOGLE_DOCUMENT_AI_LOCATION",
                "GOOGLE_DOCUMENT_AI_PROCESSOR_ID", "GOOGLE_DOCUMENT_AI_PROCESSOR_VERSION",
            )):
                reason = "processor_configuration_missing"
            else:
                try:
                    self.google_credentials()
                except ValueError:
                    reason = "authorization_unavailable"
        return {
            "env_file": "present" if self.env_present else "absent",
            "provider": self.provider,
            "external_allowed": reason is None,
            "reason": reason or "configured",
            "mistral_key": "present" if self.value("MISTRAL_API_KEY") else "absent",
            "google_credentials": self._google_kind,
        }


def readiness(root=None, *, env_path=None):
    return Config(root, env_path=env_path).readiness()
