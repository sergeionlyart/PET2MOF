"""Immutable private responses and explicitly sanitized public derivatives."""

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from .security import Redactor


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def cache_key(input_path, pages, *, regions=None, transformations=None, engine, version, params=None, input_sha256=None):
    digest = input_sha256 or sha256_file(input_path)
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("invalid input digest")
    payload = {
        "input_sha256": digest, "pages": list(pages),
        "regions": regions or [], "transformations": transformations or [],
        "engine": engine, "version": version, "params": params or {},
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()).hexdigest()


class RawCache:
    def __init__(self, root):
        self.root = Path(root) / "private" / "ocr_cache" / "raw"

    def path(self, key):
        if not re.fullmatch(r"[0-9a-f]{64}", key):
            raise ValueError("invalid cache key")
        return self.root / f"{key}.json"

    def read(self, key):
        with self.path(key).open(encoding="utf-8") as stream:
            return json.load(stream)

    def write_once(self, key, response):
        path = self.path(key)
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        payload = json.dumps(response, ensure_ascii=False, allow_nan=False).encode()
        descriptor, temporary = tempfile.mkstemp(dir=self.root, prefix=".raw-")
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            # Hard link publishes complete content atomically and refuses an existing key.
            os.link(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)
        return path


def sanitize(response, *, redactor=None):
    redactor = redactor or Redactor()
    blocked = {
        "authorization", "headers", "privatekey", "privatekeyid", "apikey", "accesstoken",
        "refreshtoken", "token", "credentials", "serviceaccount", "serviceaccountjson",
        "accountid", "account", "projectid", "project", "clientid", "clientemail", "email",
        "signedurl", "url", "documenturl", "resource", "processor", "name", "accountname",
        "accountnumber", "tenantid", "billingaccount", "googlecloudproject",
        "googleserviceaccountjson", "mistralapikey", "cookie", "setcookie",
        "id", "requestid", "documentid",
    }
    if isinstance(response, dict):
        return {
            redactor.text(str(key)): sanitize(value, redactor=redactor)
            for key, value in response.items()
            if re.sub(r"[^a-z0-9]", "", str(key).lower()) not in blocked
        }
    if isinstance(response, (list, tuple)):
        return [sanitize(item, redactor=redactor) for item in response]
    if isinstance(response, str):
        return redactor.text(response)
    return response
