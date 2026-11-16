"""Redaction shared by logs and public derivatives; never mutates raw responses."""

import json
import logging
import re
import traceback


class Secret:
    __slots__ = ("_value",)

    def __init__(self, value: str):
        self._value = value

    def reveal(self) -> str:
        return self._value

    def __bool__(self):
        return bool(self._value)

    def __str__(self):
        return "***"

    __repr__ = __str__


class Redactor:
    def __init__(self, secrets=()):
        self._secrets = set()
        for secret in secrets:
            self.add(secret)

    def __repr__(self):
        return "Redactor(***)"

    def add(self, value):
        value = value.reveal() if isinstance(value, Secret) else value
        if not isinstance(value, str) or not value:
            return
        self._secrets.add(value)
        self._secrets.add(json.dumps(value)[1:-1])

    def text(self, value: str) -> str:
        for secret in sorted(self._secrets, key=len, reverse=True):
            value = value.replace(secret, "***")
        value = re.sub(r"(?is)-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----", "***", value)
        value = re.sub(r"(?i)\bbearer\s+[^\s\"'<>]+", "[authorization removed]", value)
        value = re.sub(r'''(?i)(["']?private_key["']?\s*[:=]\s*)("(?:\\.|[^"\\])*"|'[^']*'|[^,}\n]+)''', r"\1\"***\"", value)
        # Remove URLs with queries/fragments entirely: signed URLs may use many schemes.
        value = re.sub(r"https?://[^\s\"'<>]*[?#][^\s\"'<>]*", "[url removed]", value)
        value = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[email removed]", value)
        value = re.sub(r"projects/[^/\s]+", "projects/[removed]", value)
        return value


class RedactingFilter(logging.Filter):
    def __init__(self, redactor=None):
        super().__init__()
        self.redactor = redactor or Redactor()

    def filter(self, record):
        message = record.getMessage()
        if record.exc_info:
            message += "\n" + "".join(traceback.format_exception(*record.exc_info))
        if record.exc_text:
            message += "\n" + record.exc_text
        record.msg = self.redactor.text(message)
        record.args = ()
        record.exc_info = None
        record.exc_text = None
        if record.stack_info:
            record.stack_info = self.redactor.text(record.stack_info)
        return True
